"""Gate 1A LangGraph assembly with safe clarification resume semantics."""

from __future__ import annotations

from collections.abc import Mapping
import json
from time import perf_counter
from typing import Any, Literal, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from aegisflow_core.packs.delivery.clarifier.agent import (
    ClarifierAgent,
    IncompleteClarificationAnswersError,
)
from aegisflow_core.packs.delivery.clarifier.hitl import (
    InMemoryClarificationGateway,
)
from aegisflow_core.packs.delivery.clarifier.ports import ClarificationReasoner
from aegisflow_core.packs.delivery.context.agent import ContextAgent
from aegisflow_core.packs.delivery.context.ports import ContextRetriever
from aegisflow_core.packs.delivery.contracts.clarification import Clarification
from aegisflow_core.packs.delivery.contracts.determinism import Clock, IdGenerator
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.intake.agent import IntakeAgent
from aegisflow_core.packs.delivery.planner.agent import PlannerAgent
from aegisflow_core.packs.delivery.planner.ports import PlanReasoner
from aegisflow_core.runtime.state import AgentState
from aegisflow_core.runtime.tracing import (
    TraceRecorder,
    build_step_trace_record,
    unavailable_cost_usage,
    unavailable_token_usage,
)


NodeName = Literal["intake", "clarifier", "context", "planner"]


class Gate1ANodeError(RuntimeError):
    """Expose only a stable node and exception type for a failed graph node."""

    def __init__(self, node: NodeName, cause_type: str) -> None:
        self.node = node
        self.cause_type = cause_type
        super().__init__(f"Gate 1A node failed: node={node}, cause_type={cause_type}")


class InvalidResumeThreadError(RuntimeError):
    """Raised before resume when a thread is absent, mismatched, or completed."""

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"Gate 1A thread is not awaiting resume: {run_id}")


def build_gate1a_graph(
    *,
    clock: Clock,
    id_generator: IdGenerator,
    clarification_reasoner: ClarificationReasoner,
    context_retriever: ContextRetriever,
    plan_reasoner: PlanReasoner,
    hitl_gateway: InMemoryClarificationGateway,
    trace_recorder: TraceRecorder,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Assemble the approved Gate 1A graph without implicit fake dependencies."""
    intake_agent = IntakeAgent(clock)
    clarifier_agent = ClarifierAgent(clarification_reasoner)
    context_agent = ContextAgent(context_retriever)
    planner_agent = PlannerAgent(plan_reasoner)

    def intake_node(state: AgentState, config: RunnableConfig) -> AgentState:
        started = perf_counter()
        try:
            _validate_run_identity(state, config)
            request = intake_agent.normalize(
                source_type=state["source_type"],
                source_ref=state.get("source_ref"),
                title=state["title"],
                body=state["body"],
            )
            _record_completion(
                node="intake",
                state=state,
                raw_prompt=f"{state['title']}\n{state['body']}",
                started=started,
                id_generator=id_generator,
                trace_recorder=trace_recorder,
            )
            return {"request": request}
        except Gate1ANodeError:
            raise
        except Exception as exc:
            raise _node_error("intake", exc) from None

    def clarifier_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            request = _request(state)
            clarification = clarifier_agent.clarify(request)
            if clarification.is_sufficient:
                _record_completion(
                    node="clarifier",
                    state=state,
                    raw_prompt=request.body,
                    started=started,
                    id_generator=id_generator,
                    trace_recorder=trace_recorder,
                )
            return {"clarification": clarification}
        except Exception as exc:
            raise _node_error("clarifier", exc) from None

    def clarification_route(state: AgentState) -> str:
        clarification = _clarification(state)
        return "context" if clarification.is_sufficient else "clarification_wait"

    def clarification_wait_node(state: AgentState) -> AgentState:
        started = perf_counter()
        run_id = _run_id(state)
        clarification = _clarification(state)
        try:
            request_id = hitl_gateway.request_clarification(
                run_id,
                "clarifier",
                clarification.questions,
            )
        except Exception as exc:
            raise _node_error("clarifier", exc) from None

        answers = interrupt(
            {
                "run_id": str(run_id),
                "step_key": "clarifier",
                "request_id": str(request_id),
                "questions": [
                    {"field": question.field, "question": question.question}
                    for question in clarification.questions
                ],
            }
        )

        try:
            mapped_answers = _validate_answers_before_commit(
                clarification,
                answers,
            )
            hitl_gateway.submit_response(request_id, run_id, mapped_answers)
            resolved = clarifier_agent.resolve(clarification, mapped_answers)
            _record_completion(
                node="clarifier",
                state=state,
                raw_prompt=json.dumps(
                    mapped_answers,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                started=started,
                id_generator=id_generator,
                trace_recorder=trace_recorder,
            )
            return {"clarification": resolved}
        except Exception as exc:
            raise _node_error("clarifier", exc) from None

    def context_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            request = _request(state)
            context = context_agent.gather(request)
            _record_completion(
                node="context",
                state=state,
                raw_prompt=request.body,
                started=started,
                id_generator=id_generator,
                trace_recorder=trace_recorder,
            )
            return {"context": context}
        except Exception as exc:
            raise _node_error("context", exc) from None

    def planner_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            request = _request(state)
            clarification = _clarification(state)
            context = state.get("context")
            if context is None:
                raise ValueError("context state is required")
            plan = planner_agent.plan(request, clarification, context)
            _record_completion(
                node="planner",
                state=state,
                raw_prompt=f"{request.body}\n{context.model_dump_json()}",
                started=started,
                id_generator=id_generator,
                trace_recorder=trace_recorder,
            )
            return {"plan": plan}
        except Exception as exc:
            raise _node_error("planner", exc) from None

    builder = StateGraph(AgentState)
    builder.add_node("intake", intake_node)
    builder.add_node("clarifier", clarifier_node)
    builder.add_node("clarification_wait", clarification_wait_node)
    builder.add_node("context", context_node)
    builder.add_node("planner", planner_node)
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "clarifier")
    builder.add_conditional_edges(
        "clarifier",
        clarification_route,
        {
            "clarification_wait": "clarification_wait",
            "context": "context",
        },
    )
    builder.add_edge("clarification_wait", "context")
    builder.add_edge("context", "planner")
    builder.add_edge("planner", END)
    return builder.compile(checkpointer=InMemorySaver(), name="aegisflow-gate1a")


def resume_gate1a(
    compiled_graph: CompiledStateGraph[Any, Any, Any, Any],
    run_id: UUID,
    answers: Mapping[str, str],
) -> AgentState:
    """Resume only an existing matching thread with a pending interrupt."""
    if not isinstance(run_id, UUID):
        raise TypeError("run_id must be a UUID")
    config = _config(run_id)
    snapshot = compiled_graph.get_state(config)
    checkpoint_run_id = snapshot.values.get("run_id") if snapshot.values else None
    pending_interrupts = snapshot.interrupts or tuple(
        item
        for task in snapshot.tasks
        for item in getattr(task, "interrupts", ())
    )
    if checkpoint_run_id != run_id or not pending_interrupts:
        raise InvalidResumeThreadError(run_id)
    return cast(
        AgentState,
        compiled_graph.invoke(Command(resume=dict(answers)), config=config),
    )


def _config(run_id: UUID) -> RunnableConfig:
    return {"configurable": {"thread_id": str(run_id)}}


def _validate_run_identity(state: AgentState, config: RunnableConfig) -> None:
    run_id = state.get("run_id")
    trace_id = state.get("trace_id")
    if not isinstance(run_id, UUID):
        raise TypeError("run_id must be a UUID")
    if not isinstance(trace_id, UUID):
        raise TypeError("trace_id must be a UUID")
    thread_id = config.get("configurable", {}).get("thread_id")
    if thread_id != str(run_id):
        raise ValueError("thread_id must equal run_id")


def _run_id(state: AgentState) -> UUID:
    run_id = state.get("run_id")
    if not isinstance(run_id, UUID):
        raise TypeError("run_id must be a UUID")
    return run_id


def _request(state: AgentState) -> NormalizedRequest:
    request = state.get("request")
    if request is None:
        raise ValueError("request state is required")
    return request


def _clarification(state: AgentState) -> Clarification:
    clarification = state.get("clarification")
    if clarification is None:
        raise ValueError("clarification state is required")
    return clarification


def _validate_answers_before_commit(
    clarification: Clarification,
    answers: Any,
) -> dict[str, str]:
    if not isinstance(answers, Mapping):
        raise TypeError("clarification answers must be a mapping")
    copied = dict(answers)
    if not all(isinstance(key, str) for key in copied):
        raise TypeError("clarification answer keys must be strings")
    if not all(isinstance(value, str) for value in copied.values()):
        raise TypeError("clarification answer values must be strings")
    missing = [
        question.field
        for question in clarification.questions
        if not copied.get(question.field, "").strip()
    ]
    if missing:
        raise IncompleteClarificationAnswersError(missing)
    return cast(dict[str, str], copied)


def _record_completion(
    *,
    node: NodeName,
    state: AgentState,
    raw_prompt: str,
    started: float,
    id_generator: IdGenerator,
    trace_recorder: TraceRecorder,
) -> None:
    run_id = _run_id(state)
    trace_id = state.get("trace_id")
    if not isinstance(trace_id, UUID):
        raise TypeError("trace_id must be a UUID")
    step_id = id_generator.new_id()
    trace_recorder.record(
        build_step_trace_record(
            tenant_id=None,
            workflow_id=None,
            workflow_version=None,
            run_id=run_id,
            step_id=step_id,
            trace_id=trace_id,
            agent=node,
            raw_prompt=raw_prompt,
            model=f"deterministic-{node}-v1",
            token_usage=unavailable_token_usage(),
            cost=unavailable_cost_usage(),
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
        )
    )


def _node_error(node: NodeName, cause: Exception) -> Gate1ANodeError:
    return Gate1ANodeError(node, type(cause).__name__)
