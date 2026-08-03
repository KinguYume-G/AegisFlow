"""AF-110 Gate 1A interrupt/resume end-to-end contract tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import socket
from typing import Any
from uuid import UUID

import pytest

from aegisflow_core.packs.delivery.clarifier.fakes import (
    DeterministicClarificationReasoner,
)
from aegisflow_core.packs.delivery.clarifier.hitl import (
    InMemoryClarificationGateway,
)
from aegisflow_core.packs.delivery.context.fakes import LocalFixtureContextRetriever
from aegisflow_core.packs.delivery.contracts.determinism import (
    FixedClock,
    SequentialIdGenerator,
)
from aegisflow_core.packs.delivery.planner.fakes import DeterministicPlanReasoner
from aegisflow_core.runtime.graph import (
    Gate1ANodeError,
    InvalidResumeThreadError,
    build_gate1a_graph,
    resume_gate1a,
)
from aegisflow_core.runtime.state import AgentState
from aegisflow_core.runtime.tracing import InMemoryTraceRecorder


ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fixtures"
GATE1A_ROOT = FIXTURE_ROOT / "gate1a"
CONTEXT_ROOT = FIXTURE_ROOT / "context"
RUN_ID = UUID("10000000-0000-0000-0000-000000000110")
TRACE_ID = UUID("20000000-0000-0000-0000-000000000110")
WRONG_RUN_ID = UUID("30000000-0000-0000-0000-000000000110")
FIXED_TIME = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)


def _json(name: str) -> dict[str, Any]:
    return json.loads((GATE1A_ROOT / name).read_text(encoding="utf-8"))


class CountingClarificationReasoner:
    def __init__(self) -> None:
        self.calls = 0
        self._delegate = DeterministicClarificationReasoner()

    def identify_gaps(self, request: Any) -> Any:
        self.calls += 1
        return self._delegate.identify_gaps(request)


class FailingPort:
    def __init__(self, method_name: str) -> None:
        setattr(self, method_name, self._fail)

    def _fail(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise RuntimeError("untrusted failure detail must not escape")


class FailingClock:
    def now(self) -> datetime:
        raise RuntimeError("untrusted failure detail must not escape")


def _initial_state(run_id: UUID = RUN_ID, trace_id: UUID = TRACE_ID) -> AgentState:
    fixture = _json("sample_request.json")
    request = fixture["request"]
    return {
        "run_id": run_id,
        "trace_id": trace_id,
        "source_type": fixture["source_type"],
        "source_ref": request["source_ref"],
        "title": request["title"],
        "body": request["body"],
    }


def _answers() -> dict[str, str]:
    return _json("fixed_clarification_response.json")["answers"]


def _build(
    *,
    seed: str = "af-110",
    clock: Any | None = None,
    clarification_reasoner: Any | None = None,
    context_retriever: Any | None = None,
    plan_reasoner: Any | None = None,
) -> tuple[Any, InMemoryClarificationGateway, InMemoryTraceRecorder, Any]:
    step_ids = SequentialIdGenerator(f"{seed}-steps")
    gateway = InMemoryClarificationGateway(SequentialIdGenerator(f"{seed}-hitl"))
    recorder = InMemoryTraceRecorder()
    reasoner = clarification_reasoner or CountingClarificationReasoner()
    graph = build_gate1a_graph(
        clock=clock or FixedClock(FIXED_TIME),
        id_generator=step_ids,
        clarification_reasoner=reasoner,
        context_retriever=context_retriever
        or LocalFixtureContextRetriever(CONTEXT_ROOT),
        plan_reasoner=plan_reasoner or DeterministicPlanReasoner(),
        hitl_gateway=gateway,
        trace_recorder=recorder,
    )
    return graph, gateway, recorder, reasoner


def _config(run_id: UUID = RUN_ID) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": str(run_id)}}


def _pause(graph: Any, run_id: UUID = RUN_ID) -> dict[str, Any]:
    return graph.invoke(_initial_state(run_id=run_id), config=_config(run_id))


def _complete(graph: Any, run_id: UUID = RUN_ID) -> dict[str, Any]:
    _pause(graph, run_id)
    return resume_gate1a(graph, run_id, _answers())


def test_agent_state_requires_run_and_trace_identity() -> None:
    assert AgentState.__required_keys__ == frozenset({"run_id", "trace_id"})
    assert {"request", "clarification", "context", "plan"} <= AgentState.__optional_keys__


def test_graph_requires_all_explicit_dependencies() -> None:
    signature = inspect.signature(build_gate1a_graph)
    expected = {
        "clock",
        "id_generator",
        "clarification_reasoner",
        "context_retriever",
        "plan_reasoner",
        "hitl_gateway",
        "trace_recorder",
    }
    assert set(signature.parameters) == expected
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_fixture_migration_is_complete_and_sanitized() -> None:
    sample = _json("sample_request.json")
    expected = _json("expected_clarification.json")
    response = _json("fixed_clarification_response.json")

    assert sample["fixture_id"] == "gate1a-refund-audit-export-v1"
    assert len(sample["existing_context"]) == 5
    assert len(sample["acceptance_criteria"]) == 5
    assert sample["sanitization_record"]["contains_secrets"] is False
    assert sample["sanitization_record"]["contains_pii"] is False
    assert [question["field"] for question in expected["questions"]] == [
        "authorized_roles",
        "time_range",
        "record_limit",
        "output_fields_and_redaction",
        "delivery_mode",
    ]
    assert len(response["answers"]) == 7
    assert not (ROOT / "gemini-code-1785679381247.md").exists()


def test_fixture_triggers_real_interrupt() -> None:
    graph, gateway, recorder, reasoner = _build()

    result = _pause(graph)

    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) == 1
    payload = result["__interrupt__"][0].value
    assert payload["run_id"] == str(RUN_ID)
    assert payload["step_key"] == "clarifier"
    assert payload["questions"] == _json("expected_clarification.json")["questions"]
    assert "plan" not in result
    assert gateway.request_count == 1
    assert reasoner.calls == 1
    assert [record.agent for record in recorder.records] == ["intake"]


def test_resume_with_answers_completes_plan() -> None:
    graph, _, _, _ = _build()
    _pause(graph)

    result = resume_gate1a(graph, RUN_ID, _answers())

    assert result["run_id"] == RUN_ID
    assert result["trace_id"] == TRACE_ID
    assert result["clarification"].is_sufficient is True
    assert result["clarification"].answers == _answers()
    assert result["context"].snippets
    assert result["plan"].risk_level == "L3"


def test_resume_calls_resolve_not_reasoner() -> None:
    graph, _, _, reasoner = _build()
    _pause(graph)
    assert reasoner.calls == 1

    resume_gate1a(graph, RUN_ID, _answers())

    assert reasoner.calls == 1


def test_incomplete_answers_do_not_pass_gate() -> None:
    graph, gateway, _, _ = _build()
    _pause(graph)
    incomplete = _answers()
    incomplete.pop("record_limit")

    with pytest.raises(Gate1ANodeError) as caught:
        resume_gate1a(graph, RUN_ID, incomplete)

    assert caught.value.node == "clarifier"
    assert caught.value.cause_type == "IncompleteClarificationAnswersError"
    assert gateway.request_count == 1
    snapshot = graph.get_state(_config())
    assert snapshot.values.get("context") is None
    assert snapshot.values.get("plan") is None


def test_wrong_thread_is_rejected_before_resume() -> None:
    graph, _, _, _ = _build()
    _pause(graph)
    before = deepcopy(graph.get_state(_config()).values)

    with pytest.raises(InvalidResumeThreadError):
        resume_gate1a(graph, WRONG_RUN_ID, _answers())

    after = graph.get_state(_config()).values
    assert after == before
    assert after.get("plan") is None


def test_completed_thread_cannot_resume_again() -> None:
    graph, _, recorder, _ = _build()
    completed = _complete(graph)
    assert completed["plan"] is not None
    trace_count = len(recorder.records)

    with pytest.raises(InvalidResumeThreadError):
        resume_gate1a(graph, RUN_ID, _answers())

    assert len(recorder.records) == trace_count
    assert graph.get_state(_config()).values["plan"] == completed["plan"]


def test_request_replay_reuses_hitl_request() -> None:
    graph, gateway, _, _ = _build()
    _complete(graph)

    assert gateway.request_count == 1


def test_context_has_valid_nonempty_citation() -> None:
    graph, _, _, _ = _build()
    result = _complete(graph)

    for snippet in result["context"].snippets:
        source = CONTEXT_ROOT / snippet.relative_path
        lines = source.read_text(encoding="utf-8").splitlines()
        assert source.is_file()
        assert snippet.content == "\n".join(
            lines[snippet.start_line - 1 : snippet.end_line]
        )


def test_plan_matches_fixed_four_task_contract() -> None:
    graph, _, _, _ = _build()
    plan = _complete(graph)["plan"]

    assert [task.required_tools[0].tool_name for task in plan.tasks] == [
        "repository_read",
        "repository_write",
        "test_execute",
        "pull_request_write",
    ]
    assert plan.risk_level == "L3"
    assert plan.budget_estimate.status == "not_available"


def test_trace_one_completion_record_per_node() -> None:
    graph, _, recorder, _ = _build()
    _complete(graph)

    assert [record.agent for record in recorder.records] == [
        "intake",
        "clarifier",
        "context",
        "planner",
    ]


def test_trace_correlation_and_usage() -> None:
    graph, _, recorder, _ = _build()
    _complete(graph)

    assert len({record.run_id for record in recorder.records}) == 1
    assert len({record.trace_id for record in recorder.records}) == 1
    assert all(record.run_id == RUN_ID for record in recorder.records)
    assert all(record.trace_id == TRACE_ID for record in recorder.records)
    assert all(record.tenant_id is None for record in recorder.records)
    assert all(record.workflow_id is None for record in recorder.records)
    assert all(record.workflow_version is None for record in recorder.records)
    assert len({record.step_id for record in recorder.records}) == 4
    assert len({record.event_id for record in recorder.records}) == 4
    assert all(
        record.token_usage.total_tokens.status == "not_available"
        for record in recorder.records
    )
    assert all(record.cost.source == "not_available" for record in recorder.records)


def _without_latency(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {
            key: _without_latency(item)
            for key, item in value.items()
            if key != "latency_ms"
        }
    if isinstance(value, (list, tuple)):
        return [_without_latency(item) for item in value]
    return value


def test_two_fresh_runs_are_reproducible() -> None:
    first_graph, _, first_recorder, _ = _build(seed="repeatable")
    second_graph, _, second_recorder, _ = _build(seed="repeatable")

    first = _complete(first_graph)
    second = _complete(second_graph)

    assert _without_latency(first) == _without_latency(second)
    assert _without_latency(first_recorder.records) == _without_latency(
        second_recorder.records
    )


@pytest.mark.parametrize("node", ["intake", "clarifier", "context", "planner"])
def test_each_node_failure_is_locatable(node: str) -> None:
    kwargs: dict[str, Any] = {}
    if node == "intake":
        kwargs["clock"] = FailingClock()
    elif node == "clarifier":
        kwargs["clarification_reasoner"] = FailingPort("identify_gaps")
    elif node == "context":
        kwargs["context_retriever"] = FailingPort("retrieve")
    else:
        kwargs["plan_reasoner"] = FailingPort("create_plan")
    graph, _, _, _ = _build(**kwargs)

    with pytest.raises(Gate1ANodeError) as caught:
        if node in {"intake", "clarifier"}:
            _pause(graph)
        else:
            _complete(graph)

    assert caught.value.node == node
    assert caught.value.cause_type == "RuntimeError"
    assert "untrusted failure detail" not in str(caught.value)


def test_no_external_clients_are_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_network(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("external network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    graph, _, _, _ = _build()

    assert _complete(graph)["plan"] is not None
