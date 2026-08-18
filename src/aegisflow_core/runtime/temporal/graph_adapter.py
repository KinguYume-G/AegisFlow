"""PostgreSQL/LangGraph adapter used by the local MVP Temporal Worker."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.approvals import (
    PostgresApprovalAuthorizer,
    PostgresApprovalGateway,
)
from aegisflow_core.control_plane.clarifications import (
    PostgresClarificationGateway,
)
from aegisflow_core.control_plane.domain import Run, RunRequest
from aegisflow_core.control_plane.idempotency_ledger import IdempotencyLedger
from aegisflow_core.control_plane.run_projection import PostgresRunProjection
from aegisflow_core.control_plane.runtime_uow import PostgresRuntimeUnitOfWork
from aegisflow_core.gateway.github.idempotency_guard import PostgresIdempotencyGuard
from aegisflow_core.gateway.github.pull_request import (
    CreatedCommit,
    DraftPullRequestResult,
)
from aegisflow_core.gateway.github.read_tools import PullRequestSnapshot
from aegisflow_core.gateway.policy.config import PolicyConfig
from aegisflow_core.gateway.policy.gate import ExecutionScope, RepositoryTarget
from aegisflow_core.gateway.sandbox.docker_runner import DockerSandboxRunner
from aegisflow_core.gateway.sandbox.runner import SandboxRunner, TestProfile
from aegisflow_core.models.circuit_breaker import CircuitBreaker
from aegisflow_core.models.contracts import ModelRoute
from aegisflow_core.models.gateway import EnvironmentSecretResolver, ModelGateway
from aegisflow_core.models.litellm_adapter import LiteLLMAdapter
from aegisflow_core.models.postgres_circuit import PostgresCircuitStateStore
from aegisflow_core.packs.delivery.context.fakes import LocalFixtureContextRetriever
from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)
from aegisflow_core.packs.delivery.contracts.context_package import (
    CitedSnippet,
    ContextPackage,
)
from aegisflow_core.packs.delivery.contracts.determinism import (
    RandomIdGenerator,
    SystemClock,
)
from aegisflow_core.packs.delivery.contracts.execution_result import (
    ExecutionResult,
    TestOutcome,
)
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement
from aegisflow_core.packs.delivery.contracts.policy_decision import PolicyDecision
from aegisflow_core.packs.delivery.contracts.review_decision import (
    ApprovalOutcome,
    ReviewDecision,
    ReviewFinding,
)
from aegisflow_core.packs.delivery.model_reasoners import (
    StructuredClarificationReasoner,
    StructuredPatchReasoner,
    StructuredPlanReasoner,
    StructuredReviewReasoner,
)
from aegisflow_core.runtime.checkpoint import (
    CheckpointIdentity,
    PostgresCheckpointManager,
    build_checkpoint_config,
)
from aegisflow_core.runtime.gate1b import build_gate1b_graph
from aegisflow_core.runtime.state import AgentState
from aegisflow_core.runtime.temporal.contracts import (
    AdvanceRequest,
    AdvanceResult,
    HumanSignal,
    RuntimeIdentity,
)
from aegisflow_core.runtime.tracing import PostgresTraceRecorder
from aegisflow_core.settings import Settings


class LocalMvpConfigurationError(RuntimeError):
    pass


CHECKPOINT_ALLOWED_TYPES = (
    NormalizedRequest,
    Clarification,
    ClarificationQuestion,
    ContextPackage,
    CitedSnippet,
    Plan,
    PlanTask,
    ToolRequirement,
    Measurement,
    PolicyDecision,
    ExecutionResult,
    TestOutcome,
    ReviewDecision,
    ReviewFinding,
    ApprovalOutcome,
    DraftPullRequestResult,
    RepositoryTarget,
    TestProfile,
)


class PostgresDeliveryGraphAdapter:
    """Advance one checkpointed graph until its next durable wait or terminal state."""

    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: Any,
        checkpoint_manager: PostgresCheckpointManager,
        model_gateway: ModelGateway | None = None,
        sandbox_runner: SandboxRunner | None = None,
    ) -> None:
        if not settings.local_mvp_profile_enabled:
            raise LocalMvpConfigurationError("local MVP profile is not enabled")
        if not settings.local_mvp_github_dry_run:
            raise LocalMvpConfigurationError("local MVP requires GitHub dry-run mode")
        if not settings.model_ollama_configured:
            raise LocalMvpConfigurationError("local MVP Ollama route is not configured")
        if not settings.sandbox_broker_url:
            raise LocalMvpConfigurationError("sandbox broker URL is required")
        self._settings = settings
        self._sessions = session_factory
        self._checkpoints = checkpoint_manager
        self._clock = SystemClock()
        self._model_gateway = model_gateway or _local_model_gateway(
            settings, session_factory, self._clock
        )
        self._projection = PostgresRunProjection(session_factory)
        self._trace_recorder = PostgresTraceRecorder(settings.database_url)
        self._sandbox = sandbox_runner or DockerSandboxRunner(
            settings.sandbox_broker_url
        )

    async def advance(self, request: AdvanceRequest) -> AdvanceResult:
        identity = request.identity
        tenant_id, run_id, trace_id = (
            UUID(identity.tenant_id),
            UUID(identity.run_id),
            UUID(identity.trace_id),
        )
        stored_run, stored_request = await self._load(
            tenant_id, run_id, trace_id, identity.workflow_version
        )
        workspace = await asyncio.to_thread(
            _prepare_workspace,
            Path(self._settings.local_mvp_workspace_root),
            tenant_id,
            run_id,
            stored_request,
        )
        target = RepositoryTarget(
            stored_request.repository_owner, stored_request.repository_name
        )
        graph_identity = CheckpointIdentity(
            tenant_id, run_id, identity.workflow_version
        )
        config = build_checkpoint_config(graph_identity)

        reasoner_args = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "trace_id": trace_id,
            "event_loop": asyncio.get_running_loop(),
        }
        clarification_gateway = PostgresClarificationGateway(
            self._settings.database_url, tenant_id=tenant_id
        )
        approval_gateway = PostgresApprovalGateway(self._sessions)
        ledger = IdempotencyLedger(self._sessions, self._clock)
        idempotency = PostgresIdempotencyGuard(ledger)
        denied_github = _DryRunOnlyGitHubPort()

        async with self._checkpoints.open() as saver:
            graph = build_gate1b_graph(
                clock=self._clock,
                id_generator=RandomIdGenerator(),
                clarification_reasoner=StructuredClarificationReasoner(
                    self._model_gateway, **reasoner_args
                ),
                context_retriever=LocalFixtureContextRetriever(workspace),
                plan_reasoner=StructuredPlanReasoner(
                    self._model_gateway, **reasoner_args
                ),
                hitl_gateway=clarification_gateway,
                policy_config=PolicyConfig(
                    allowed_repository=target.full_name,
                    enabled_tool_capabilities=frozenset(
                        {
                            "repository_read",
                            "repository_write",
                            "test_execute",
                            "sandbox_execute",
                            "pull_request_write",
                        }
                    ),
                    max_allowed_risk_level="L3",
                ),
                execution_scope=ExecutionScope(target),
                patch_reasoner=StructuredPatchReasoner(
                    self._model_gateway, **reasoner_args
                ),
                sandbox_runner=self._sandbox,
                review_reasoner=StructuredReviewReasoner(
                    self._model_gateway, **reasoner_args
                ),
                approval_gateway=approval_gateway,
                approval_authorizer=PostgresApprovalAuthorizer(self._sessions),
                github_write_client=denied_github,
                github_read_client=denied_github,
                idempotency_guard=idempotency,
                trace_recorder=self._trace_recorder,
                unit_of_work_factory=lambda: PostgresRuntimeUnitOfWork(
                    self._sessions()
                ),
                checkpointer=saver,
                github_dry_run=True,
            )
            snapshot = await graph.aget_state(config)
            pending = _pending_interrupt(snapshot)

            if request.signal is None and pending is not None:
                return _waiting_result(pending)
            if request.signal is not None:
                if pending is None:
                    raise ValueError("human signal has no matching graph interrupt")
                resume = _resume_payload(request.signal, pending)
                result = await graph.ainvoke(Command(resume=resume), config=config)
            elif snapshot.values:
                status = str(snapshot.values.get("run_status") or "")
                if status in {"completed", "failed"}:
                    reference = await self._projection.project(
                        cast(AgentState, snapshot.values), status=status
                    )
                    return AdvanceResult(status, reference)  # type: ignore[arg-type]
                result = await graph.ainvoke(None, config=config)
            else:
                result = await graph.ainvoke(
                    _initial_state(
                        stored_run,
                        stored_request,
                        tenant_id=tenant_id,
                        run_id=run_id,
                        trace_id=trace_id,
                        workspace=workspace,
                        target=target,
                        sandbox_image=self._settings.sandbox_test_image,
                    ),
                    config=config,
                )

            updated = await graph.aget_state(config)
            pending = _pending_interrupt(updated)
            state = cast(AgentState, updated.values or result)
            if pending is not None:
                wait = _waiting_result(pending)
                await self._projection.project(state, status=wait.status)
                return wait
            status = str(state.get("run_status") or "")
            if status not in {"completed", "failed"}:
                raise RuntimeError("graph ended without a terminal status or interrupt")
            reference = await self._projection.project(state, status=status)
            return AdvanceResult(status, reference)  # type: ignore[arg-type]

    async def fail(
        self, identity: RuntimeIdentity, failure_reference: str
    ) -> str:
        return await self._projection.project_runtime_failure(
            tenant_id=UUID(identity.tenant_id),
            run_id=UUID(identity.run_id),
            trace_id=UUID(identity.trace_id),
            reason=failure_reference,
        )

    async def _load(
        self,
        tenant_id: UUID,
        run_id: UUID,
        trace_id: UUID,
        workflow_version: int,
    ) -> tuple[Run, RunRequest]:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(Run, RunRequest)
                    .join(
                        RunRequest,
                        (RunRequest.tenant_id == Run.tenant_id)
                        & (RunRequest.run_id == Run.id),
                    )
                    .where(Run.tenant_id == tenant_id, Run.id == run_id)
                )
            ).one_or_none()
            if row is None:
                raise KeyError(run_id)
            stored_run, stored_request = row
            if (
                stored_run.workflow_version != workflow_version
                or stored_request.trace_id != trace_id
                or stored_request.temporal_workflow_id
                != f"aegisflow:{tenant_id}:{run_id}"
            ):
                raise PermissionError("runtime identity does not match the stored Run")
            return stored_run, stored_request


def _local_model_gateway(
    settings: Settings, session_factory: Any, clock: SystemClock
) -> ModelGateway:
    assert settings.model_ollama_name is not None
    assert settings.model_ollama_api_key_env is not None
    assert settings.model_ollama_base_url is not None
    model_name = settings.model_ollama_name
    if not model_name.startswith(("ollama/", "ollama_chat/")):
        model_name = f"ollama_chat/{model_name}"
    return ModelGateway.local_only(
        LiteLLMAdapter(),
        CircuitBreaker(PostgresCircuitStateStore(session_factory), clock),
        EnvironmentSecretResolver(),
        route=ModelRoute(
            name="local_ollama",
            model=model_name,
            api_key_env=settings.model_ollama_api_key_env,
            api_base=settings.model_ollama_base_url,
        ),
    )


def _initial_state(
    run: Run,
    request: RunRequest,
    *,
    tenant_id: UUID,
    run_id: UUID,
    trace_id: UUID,
    workspace: Path,
    target: RepositoryTarget,
    sandbox_image: str,
) -> AgentState:
    source_type = "github_issue" if request.source_type == "issue" else request.source_type
    return {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "workflow_id": UUID(str(run.workflow_id)),
        "workflow_version": run.workflow_version,
        "trace_id": trace_id,
        "source_type": cast(Any, source_type),
        "source_ref": request.source_ref,
        "title": request.title,
        "body": request.body,
        "repository_target": target,
        "base_ref": request.base_ref,
        "base_sha": request.base_sha,
        "workspace_path": str(workspace),
        "test_profile": TestProfile(
            name="python_unittest", image=sandbox_image, test_path="tests"
        ),
        "rework_count": 0,
        "run_status": "running",
    }


def _prepare_workspace(
    root: Path,
    tenant_id: UUID,
    run_id: UUID,
    request: RunRequest,
) -> Path:
    resolved_root = root.resolve()
    workspace = (resolved_root / str(tenant_id) / str(run_id)).resolve()
    if resolved_root not in workspace.parents:
        raise ValueError("workspace escaped the configured root")
    workspace.mkdir(parents=True, exist_ok=True)
    tests = workspace / "tests"
    tests.mkdir(exist_ok=True)
    seed = {
        "README.md": f"# {request.title}\n\n{request.body}\n",
        "app.py": (
            '"""Controlled local MVP fixture."""\n\n'
            "def deliverable() -> str:\n"
            '    return "pending"\n'
        ),
        "tests/test_app.py": (
            "import unittest\n\n"
            "from app import deliverable\n\n\n"
            "class DeliverableTest(unittest.TestCase):\n"
            "    def test_deliverable_is_text(self):\n"
            "        self.assertIsInstance(deliverable(), str)\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        ),
    }
    for relative, content in seed.items():
        target = workspace / relative
        if not target.exists():
            target.write_text(content, encoding="utf-8")
    return workspace


def _pending_interrupt(snapshot: Any) -> dict[str, object] | None:
    items = tuple(snapshot.interrupts or ())
    if not items:
        items = tuple(
            item
            for task in snapshot.tasks
            for item in getattr(task, "interrupts", ())
        )
    if not items:
        return None
    if len(items) != 1 or not isinstance(items[0].value, dict):
        raise RuntimeError("graph must expose exactly one structured interrupt")
    return cast(dict[str, object], items[0].value)


def _waiting_result(payload: dict[str, object]) -> AdvanceResult:
    if payload.get("request_id") is not None and payload.get("step_key") == "clarifier":
        return AdvanceResult(
            "waiting_clarification", wait_reference=str(payload["request_id"])
        )
    if payload.get("approval_id") is not None:
        return AdvanceResult(
            "waiting_approval", wait_reference=str(payload["approval_id"])
        )
    raise RuntimeError("graph interrupt kind is not recognized")


def _resume_payload(
    signal: HumanSignal, pending: dict[str, object]
) -> dict[str, object]:
    waiting = _waiting_result(pending)
    if signal.kind != waiting.wait_kind or signal.target_reference != waiting.wait_reference:
        raise PermissionError("human signal does not match the active graph interrupt")
    if signal.value == "expired" and signal.kind == "approval":
        return {
            "decision": "rejected",
            "decided_by": signal.actor_reference,
            "reason": "approval_expired",
        }
    try:
        payload = json.loads(signal.value)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("human signal value must be valid JSON") from None
    if not isinstance(payload, dict):
        raise ValueError("human signal value must be a JSON object")
    if signal.kind == "clarification":
        answers = payload.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("clarification signal requires answers")
        return {
            "answers": answers,
            "actor_reference": signal.actor_reference,
        }
    decision = payload.get("decision")
    if decision not in {"approved", "rejected"}:
        raise ValueError("approval signal decision is invalid")
    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("approval reason must be text")
    return {
        "decision": decision,
        "decided_by": signal.actor_reference,
        "reason": reason,
    }


class _DryRunOnlyGitHubPort:
    """Tripwire proving the local profile never contacts GitHub."""

    async def find_pull_request_by_head_or_marker(
        self, *args: object, **kwargs: object
    ) -> PullRequestSnapshot | None:
        raise RuntimeError("GitHub reads are disabled in local dry-run mode")

    async def create_commit_from_changes(
        self, **kwargs: object
    ) -> CreatedCommit:
        raise RuntimeError("GitHub writes are disabled in local dry-run mode")

    async def open_draft_pull_request(
        self, **kwargs: object
    ) -> PullRequestSnapshot:
        raise RuntimeError("GitHub writes are disabled in local dry-run mode")
