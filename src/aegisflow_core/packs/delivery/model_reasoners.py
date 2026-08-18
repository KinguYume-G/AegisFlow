"""Bounded structured DeliveryPack reasoners backed by ModelGateway."""

from __future__ import annotations

import asyncio
import json
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aegisflow_core.models.contracts import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
)
from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import (
    Plan,
    PlanTask,
    ToolRequirement,
)
from aegisflow_core.packs.delivery.contracts.review_decision import ReviewFinding

_MAX_MODEL_JSON = 200_000
_MAX_PATCH_FILES = 20
_MAX_PATCH_FILE_CHARS = 200_000
_MAX_PATCH_TOTAL_CHARS = 500_000


class ModelCompletionPort(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse: ...


class StructuredReasoningError(RuntimeError):
    pass


class _Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=1000)


class _ClarificationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_sufficient: bool
    questions: list[_Question] = Field(max_length=10)


class _PlanTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=1000)
    required_tools: list[
        Literal[
            "repository_read",
            "repository_write",
            "test_execute",
            "sandbox_execute",
            "pull_request_write",
        ]
    ] = Field(min_length=1, max_length=10)


class _PlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=5000)
    tasks: list[_PlanTaskPayload] = Field(min_length=1, max_length=20)
    risk_level: Literal["L1", "L2", "L3"]


class _PatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    files: dict[str, str] = Field(min_length=1, max_length=_MAX_PATCH_FILES)


class _Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["info", "warning", "blocking"]
    message: str = Field(min_length=1, max_length=1000)


class _ReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[_Finding] = Field(min_length=1, max_length=20)


class _StructuredReasoner:
    def __init__(
        self,
        gateway: ModelCompletionPort,
        *,
        tenant_id: UUID,
        run_id: UUID,
        trace_id: UUID,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._gateway = gateway
        self._tenant_id = tenant_id
        self._run_id = run_id
        self._trace_id = trace_id
        self._event_loop = event_loop
        self.last_model_response: ModelResponse | None = None

    def _complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        max_output_tokens: int,
    ) -> BaseModel:
        schema_json = json.dumps(
            schema.model_json_schema(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        messages = (
            ModelMessage(
                "system",
                f"{system}\nReturn exactly one JSON object valid against this JSON Schema: {schema_json}",
            ),
            ModelMessage("user", user),
        )
        for attempt in range(2):
            request = ModelRequest(
                tenant_id=self._tenant_id,
                run_id=self._run_id,
                trace_id=self._trace_id,
                messages=messages,
                max_output_tokens=max_output_tokens,
                response_format="json_object",
            )
            try:
                response = self._complete(request)
                self.last_model_response = response
                return schema.model_validate(_decode_json_object(response.content))
            except (ValueError, TypeError, json.JSONDecodeError, ValidationError):
                if attempt == 1:
                    break
                messages = messages + (
                    ModelMessage(
                        "user",
                        "The previous result failed schema validation. Return only one valid JSON object matching the requested schema.",
                    ),
                )
        raise StructuredReasoningError("model structured output was invalid")

    def _complete(self, request: ModelRequest) -> ModelResponse:
        if self._event_loop is None:
            return asyncio.run(self._gateway.complete(request))
        if not self._event_loop.is_running():
            raise RuntimeError("model event loop is not running")
        future = asyncio.run_coroutine_threadsafe(
            self._gateway.complete(request), self._event_loop
        )
        try:
            return future.result(timeout=90)
        except TimeoutError:
            future.cancel()
            raise


class StructuredClarificationReasoner(_StructuredReasoner):
    def identify_gaps(self, request: NormalizedRequest) -> Clarification:
        payload = self._complete_json(
            system=(
                "You are AegisFlow Clarifier. Identify only information required to implement and test the request. "
                "Return JSON with is_sufficient and questions[{field,question}]. Use snake_case fields, at most 10 questions. "
                "Do not include analysis, permissions, or tool calls. /no_think"
            ),
            user=json.dumps(
                {"title": request.title, "body": request.body},
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=_ClarificationPayload,
            max_output_tokens=768,
        )
        assert isinstance(payload, _ClarificationPayload)
        questions = [
            ClarificationQuestion(field=item.field, question=item.question)
            for item in payload.questions
        ]
        sufficient = payload.is_sufficient and not questions
        if not questions and not sufficient:
            raise StructuredReasoningError("clarifier returned inconsistent state")
        if questions and payload.is_sufficient:
            raise StructuredReasoningError("clarifier returned inconsistent state")
        return Clarification(
            questions=questions,
            is_sufficient=sufficient,
            reasoner_id=_reasoner_id(self.last_model_response),
        )


class StructuredPlanReasoner(_StructuredReasoner):
    def create_plan(
        self,
        request: NormalizedRequest,
        clarification: Clarification,
        context: ContextPackage,
    ) -> Plan:
        payload = self._complete_json(
            system=(
                "You are AegisFlow Planner. Return JSON with summary, risk_level L1/L2/L3, and ordered tasks. "
                "Each task has description and required_tools selected only from repository_read, repository_write, "
                "test_execute, sandbox_execute, pull_request_write. Include reading, implementation, isolated tests, "
                "and a Draft PR candidate. Never grant permission. /no_think"
            ),
            user=json.dumps(
                {
                    "request": {"title": request.title, "body": request.body},
                    "clarification_answers": clarification.answers or {},
                    "context": [snippet.model_dump(mode="json") for snippet in context.snippets],
                    "unsupported_notes": context.unsupported_notes,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=_PlanPayload,
            max_output_tokens=1400,
        )
        assert isinstance(payload, _PlanPayload)
        return Plan(
            summary=payload.summary,
            tasks=[
                PlanTask(
                    description=item.description,
                    required_tools=[ToolRequirement(tool_name=name) for name in item.required_tools],
                )
                for item in payload.tasks
            ],
            risk_level=payload.risk_level,
            budget_estimate=Measurement(status="not_available"),
            reasoner_id=_reasoner_id(self.last_model_response),
        )


class StructuredPatchReasoner(_StructuredReasoner):
    def generate_patch(
        self, plan: Plan, workspace_files: dict[str, str]
    ) -> dict[str, str]:
        bounded_files = {
            path: content[:20_000]
            for path, content in sorted(workspace_files.items())[:50]
        }
        payload = self._complete_json(
            system=(
                "You are AegisFlow Executor. Return JSON {files:{relative_path:complete_utf8_content}}. "
                "Implement the smallest plan-compliant change and its tests. Use at most 20 repository-relative files. "
                "Do not use absolute paths, traversal, secrets, shell commands, markdown fences, or commentary. /no_think"
            ),
            user=json.dumps(
                {"plan": plan.model_dump(mode="json"), "workspace_files": bounded_files},
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=_PatchPayload,
            max_output_tokens=4096,
        )
        assert isinstance(payload, _PatchPayload)
        total = 0
        for path, content in payload.files.items():
            posix, windows = PurePosixPath(path), PureWindowsPath(path)
            if (
                not path
                or posix.is_absolute()
                or windows.is_absolute()
                or windows.drive
                or ".." in posix.parts
                or "\\" in path
            ):
                raise StructuredReasoningError("model returned an unsafe patch path")
            if len(content) > _MAX_PATCH_FILE_CHARS:
                raise StructuredReasoningError("model returned an oversized patch file")
            total += len(content)
        if total > _MAX_PATCH_TOTAL_CHARS:
            raise StructuredReasoningError("model returned an oversized patch")
        return dict(payload.files)


class StructuredReviewReasoner(_StructuredReasoner):
    def summarize(self, plan: Plan, result: ExecutionResult) -> list[ReviewFinding]:
        payload = self._complete_json(
            system=(
                "You are AegisFlow Reviewer. Return JSON findings[{severity,message}] based only on the plan, diff, "
                "changed files, and sandbox result. Severity is info, warning, or blocking. Do not decide permissions. /no_think"
            ),
            user=json.dumps(
                {
                    "plan": plan.model_dump(mode="json"),
                    "execution": {
                        "changed_files": result.changed_files,
                        "patch": result.patch[:50_000],
                        "test_outcome": result.test_outcome.model_dump(mode="json"),
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=_ReviewPayload,
            max_output_tokens=1000,
        )
        assert isinstance(payload, _ReviewPayload)
        return [
            ReviewFinding(severity=item.severity, message=item.message)
            for item in payload.findings
        ]


def _decode_json_object(value: str) -> object:
    if len(value) > _MAX_MODEL_JSON:
        raise ValueError("model output exceeded bound")
    stripped = value.strip()
    if stripped.startswith("```json") and stripped.endswith("```"):
        stripped = stripped[7:-3].strip()
    elif stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped[3:-3].strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model output did not contain a JSON object")
    return json.loads(stripped[start : end + 1])


def _reasoner_id(response: ModelResponse | None) -> str:
    return f"model:{response.resolved_model}" if response else "model:unknown"
