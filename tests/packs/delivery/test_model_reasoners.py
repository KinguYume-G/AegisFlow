"""Structured model reasoners accept only bounded DeliveryPack contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from aegisflow_core.models.contracts import ModelResponse, RouteAttempt
from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.context_package import ContextPackage
from aegisflow_core.packs.delivery.contracts.execution_result import (
    ExecutionResult,
    TestOutcome as DeliveryTestOutcome,
)
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.model_reasoners import (
    StructuredClarificationReasoner,
    StructuredPatchReasoner,
    StructuredPlanReasoner,
    StructuredReviewReasoner,
    StructuredReasoningError,
)
from aegisflow_core.runtime.tracing import (
    CostUsage,
    TokenMeasurement,
    TokenUsage,
)


class Gateway:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        content = self.responses.pop(0)
        return ModelResponse(
            content=content,
            resolved_model="ollama_chat/qwen3:8b",
            token_usage=TokenUsage(
                input_tokens=TokenMeasurement(status="measured", value=10),
                output_tokens=TokenMeasurement(status="measured", value=5),
                total_tokens=TokenMeasurement(status="measured", value=15),
            ),
            cost=CostUsage(amount=Decimal("0"), currency="USD", source="estimated"),
            latency_ms=12.5,
            route_chain=(RouteAttempt("ollama", "ollama_chat/qwen3:8b", "succeeded"),),
        )


def identity():
    return {
        "tenant_id": UUID("10000000-0000-0000-0000-000000000001"),
        "run_id": UUID("20000000-0000-0000-0000-000000000002"),
        "trace_id": UUID("30000000-0000-0000-0000-000000000003"),
    }


def normalized() -> NormalizedRequest:
    return NormalizedRequest(
        source_type="prd",
        source_ref="local://prd/reasoner",
        title="Add a governed endpoint",
        body="Add tests, bounded output, audit evidence, and separate Reviewer approval.",
        idempotency_key="a" * 64,
        received_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
    )


def complete_plan() -> Plan:
    gateway = Gateway(
        [
            """{
              "summary":"Implement and verify the bounded endpoint.",
              "risk_level":"L2",
              "tasks":[
                {"description":"Read cited evidence.","required_tools":["repository_read"]},
                {"description":"Create the scoped change.","required_tools":["repository_write"]},
                {"description":"Run isolated tests.","required_tools":["test_execute","sandbox_execute"]},
                {"description":"Prepare a Draft PR candidate.","required_tools":["pull_request_write"]}
              ]
            }"""
        ]
    )
    reasoner = StructuredPlanReasoner(gateway, **identity())
    return reasoner.create_plan(
        normalized(),
        Clarification(questions=[], is_sufficient=True, reasoner_id="test"),
        ContextPackage(
            snippets=[],
            unsupported_notes=["no repository evidence found"],
            scanned_file_count=0,
            skipped_file_count=0,
            security_skip_count=0,
        ),
    )


def test_clarifier_retries_malformed_json_once_and_returns_contract() -> None:
    gateway = Gateway(
        [
            "not-json",
            '{"is_sufficient":false,"questions":[{"field":"acceptance_criteria",'
            '"question":"What tests and evidence define completion?"}]}',
        ]
    )
    reasoner = StructuredClarificationReasoner(gateway, **identity())

    clarification = reasoner.identify_gaps(normalized())

    assert clarification.questions[0].field == "acceptance_criteria"
    assert clarification.is_sufficient is False
    assert len(gateway.requests) == 2
    assert reasoner.last_model_response is not None
    assert all(request.response_format == "json_object" for request in gateway.requests)
    assert "JSON Schema" in gateway.requests[0].messages[0].content
    assert '"additionalProperties":false' in gateway.requests[0].messages[0].content


def test_planner_maps_only_fixed_tool_capabilities() -> None:
    plan = complete_plan()

    assert plan.risk_level == "L2"
    assert [tool.tool_name for task in plan.tasks for tool in task.required_tools] == [
        "repository_read",
        "repository_write",
        "test_execute",
        "sandbox_execute",
        "pull_request_write",
    ]


def test_patch_reasoner_bounds_paths_files_and_total_content() -> None:
    gateway = Gateway(
        [
            '{"files":{"delivery_status.py":"def status():\\n    return \'ok\'\\n",'
            '"tests/test_delivery_status.py":"from delivery_status import status\\n\\n'
            'def test_status():\\n    assert status() == \'ok\'\\n"}}'
        ]
    )
    reasoner = StructuredPatchReasoner(gateway, **identity())

    files = reasoner.generate_patch(complete_plan(), {"README.md": "fixture"})

    assert sorted(files) == ["delivery_status.py", "tests/test_delivery_status.py"]
    unsafe = Gateway(['{"files":{"../escape.py":"x=1"}}'])
    with pytest.raises(StructuredReasoningError):
        StructuredPatchReasoner(unsafe, **identity()).generate_patch(
            complete_plan(), {"README.md": "fixture"}
        )


def test_reviewer_returns_bounded_findings_without_granting_approval() -> None:
    gateway = Gateway(
        ['{"findings":[{"severity":"info","message":"Tests passed in the sandbox."}]}']
    )
    reasoner = StructuredReviewReasoner(gateway, **identity())
    execution = ExecutionResult(
        status="completed",
        patch="--- a/file\n+++ b/file\n",
        changed_files=["file"],
        test_outcome=DeliveryTestOutcome(status="passed", output_excerpt="1 passed"),
        reasoner_id="test",
    )

    findings = reasoner.summarize(complete_plan(), execution)

    assert findings[0].severity == "info"
    assert "approval" not in gateway.requests[0].messages[-1].content.casefold()


def test_structured_reasoning_fails_after_one_repair_attempt() -> None:
    gateway = Gateway(["bad", "still bad"])
    reasoner = StructuredClarificationReasoner(gateway, **identity())

    with pytest.raises(StructuredReasoningError, match="structured output"):
        reasoner.identify_gaps(normalized())
    assert len(gateway.requests) == 2


@pytest.mark.anyio
async def test_sync_reasoner_is_safe_when_graph_runs_it_in_a_worker_thread() -> None:
    gateway = Gateway(['{"is_sufficient":true,"questions":[]}'])
    reasoner = StructuredClarificationReasoner(gateway, **identity())

    result = await asyncio.to_thread(reasoner.identify_gaps, normalized())

    assert result.is_sufficient is True
