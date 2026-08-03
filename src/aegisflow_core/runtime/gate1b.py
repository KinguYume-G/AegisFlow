"""Asynchronous Gate 1B graph: policy, sandbox, review, approval, draft PR."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from aegisflow_core.gateway.github.pull_request import (
    ApprovalAuthorizer,
    FileChange,
    GitHubReadReconciler,
    GitHubWritePort,
    IdempotencyGuard,
    WriteAuthorization,
    create_draft_pull_request,
    digest_file_changes,
)
from aegisflow_core.gateway.github.webhook import WebhookVerificationResult
from aegisflow_core.gateway.policy.config import PolicyConfig
from aegisflow_core.gateway.policy.gate import ExecutionScope, PolicyGate
from aegisflow_core.gateway.policy.injection import InjectionPolicyGuard, Severity
from aegisflow_core.gateway.sandbox.runner import SandboxRunner
from aegisflow_core.packs.delivery.clarifier.hitl import InMemoryClarificationGateway
from aegisflow_core.packs.delivery.clarifier.ports import ClarificationReasoner
from aegisflow_core.packs.delivery.context.ports import ContextRetriever
from aegisflow_core.packs.delivery.contracts.determinism import Clock, IdGenerator
from aegisflow_core.packs.delivery.contracts.unit_of_work import AsyncUnitOfWork
from aegisflow_core.packs.delivery.executor.agent import ExecutorAgent
from aegisflow_core.packs.delivery.executor.ports import PatchReasoner
from aegisflow_core.packs.delivery.planner.ports import PlanReasoner
from aegisflow_core.packs.delivery.reviewer.agent import ReviewerAgent
from aegisflow_core.packs.delivery.reviewer.ports import ApprovalGateway, ReviewReasoner
from aegisflow_core.runtime.graph import InvalidResumeThreadError, build_gate1a_graph
from aegisflow_core.runtime.checkpoint import CheckpointIdentity, build_checkpoint_config
from aegisflow_core.runtime.state import AgentState
from aegisflow_core.runtime.tracing import (
    TraceRecorder,
    build_step_trace_record,
    unavailable_cost_usage,
    unavailable_token_usage,
)


Gate1BNodeName = Literal["policy_gate", "executor", "reviewer", "approval_wait", "draft_pr"]


class Gate1BNodeError(RuntimeError):
    def __init__(self, node: Gate1BNodeName, cause_type: str) -> None:
        self.node, self.cause_type = node, cause_type
        super().__init__(f"Gate 1B node failed: node={node}, cause_type={cause_type}")


class Gate1BDispatcher:
    """Convert one verified repository dispatch into one async graph invocation."""

    def __init__(
        self,
        graph: CompiledStateGraph[Any, Any, Any, Any],
        state_factory: Callable[[WebhookVerificationResult], Awaitable[AgentState]],
        *,
        workflow_version: int = 1,
    ) -> None:
        self._graph = graph
        self._state_factory = state_factory
        self._workflow_version = workflow_version

    async def dispatch(self, event: WebhookVerificationResult) -> None:
        if not event.accepted or event.event != "repository_dispatch":
            raise ValueError("Gate 1B accepts only verified repository_dispatch events")
        state = await self._state_factory(event)
        run_id = _run_id(state)
        await self._graph.ainvoke(
            state,
            config=_config(run_id, _tenant_id(state), self._workflow_version),
        )


def build_gate1b_graph(
    *,
    clock: Clock,
    id_generator: IdGenerator,
    clarification_reasoner: ClarificationReasoner,
    context_retriever: ContextRetriever,
    plan_reasoner: PlanReasoner,
    hitl_gateway: InMemoryClarificationGateway,
    policy_config: PolicyConfig,
    execution_scope: ExecutionScope,
    patch_reasoner: PatchReasoner,
    sandbox_runner: SandboxRunner,
    review_reasoner: ReviewReasoner,
    approval_gateway: ApprovalGateway,
    approval_authorizer: ApprovalAuthorizer,
    github_write_client: GitHubWritePort,
    github_read_client: GitHubReadReconciler,
    idempotency_guard: IdempotencyGuard,
    trace_recorder: TraceRecorder,
    unit_of_work_factory: Callable[[], AsyncUnitOfWork],
    max_rework_attempts: int = 2,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Build Gate 1B with no implicit adapters or external-write bypass."""
    if max_rework_attempts < 1:
        raise ValueError("max_rework_attempts must be positive")
    gate1a = build_gate1a_graph(
        clock=clock,
        id_generator=id_generator,
        clarification_reasoner=clarification_reasoner,
        context_retriever=context_retriever,
        plan_reasoner=plan_reasoner,
        hitl_gateway=hitl_gateway,
        trace_recorder=trace_recorder,
    )
    policy_gate = PolicyGate(policy_config)
    class UnitOfWorkInjectionAudit:
        async def record(self, **fields: object) -> None:
            async with unit_of_work_factory() as uow:
                await uow.record_audit(**fields)

    injection_guard = InjectionPolicyGuard(audit=UnitOfWorkInjectionAudit())
    executor = ExecutorAgent(patch_reasoner)
    reviewer = ReviewerAgent(review_reasoner)

    async def gate1a_node(state: AgentState, config: RunnableConfig) -> AgentState:
        result = await gate1a.ainvoke(dict(state), config=config)
        if result.get("plan") is None:
            raise Gate1BNodeError("policy_gate", "Gate1AIncomplete")
        return cast(AgentState, result)

    async def policy_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            plan = state.get("plan")
            if plan is None:
                raise ValueError("plan state is required")
            severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "unknown": 4}
            injection_severity: Severity = "none"
            context = state.get("context")
            if context is not None:
                for snippet in context.snippets:
                    assessment = await injection_guard.assess(
                        content=snippet.content,
                        source_reference=(
                            f"{snippet.relative_path}:{snippet.start_line}-{snippet.end_line}"
                        ),
                        tenant_id=_tenant_id(state),
                        actor="policy_gate",
                        trace_id=_trace_id(state),
                    )
                    if severity_rank[assessment.maximum_severity] > severity_rank[injection_severity]:
                        injection_severity = assessment.maximum_severity
            decision = policy_gate.evaluate(
                plan,
                execution_scope,
                injection_severity=injection_severity,
            )
            await _record_step(unit_of_work_factory, id_generator, state, "policy_gate", 5, "completed")
            async with unit_of_work_factory() as uow:
                await uow.record_audit(
                    tenant_id=_tenant_id(state), actor="policy_gate", action="evaluate",
                    resource_type="run", resource_id=str(_run_id(state)),
                    decision=decision.decision, reason=decision.violated_rule,
                    trace_id=_trace_id(state),
                )
                if decision.decision == "deny":
                    await uow.set_run_status(
                        tenant_id=_tenant_id(state), run_id=_run_id(state), status="failed"
                    )
            return {
                "policy_decision": decision,
                "run_status": "failed" if decision.decision == "deny" else "running",
            }
        except Exception as exc:
            raise _node_error("policy_gate", exc) from None

    def policy_route(state: AgentState) -> str:
        decision = state.get("policy_decision")
        return "executor" if decision is not None and decision.decision == "allow" else "end"

    async def executor_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            plan = state.get("plan")
            test_profile = state.get("test_profile")
            workspace = state.get("workspace_path")
            if plan is None or test_profile is None or not workspace:
                raise ValueError("plan, test_profile, and workspace_path are required")
            result = executor.execute(plan, Path(workspace), sandbox_runner, test_profile)
            await _record_step(unit_of_work_factory, id_generator, state, "executor", 6, "completed")
            _trace(trace_recorder, id_generator, state, "executor", started)
            return {"execution_result": result}
        except Exception as exc:
            raise _node_error("executor", exc) from None

    async def reviewer_node(state: AgentState) -> AgentState:
        started = perf_counter()
        try:
            plan, execution = state.get("plan"), state.get("execution_result")
            if plan is None or execution is None:
                raise ValueError("plan and execution_result are required")
            decision = reviewer.review(plan, execution)
            step_id = await _record_step(
                unit_of_work_factory, id_generator, state, "reviewer", 7, "completed"
            )
            _trace(trace_recorder, id_generator, state, "reviewer", started, step_id=step_id)
            count = int(state.get("rework_count", 0))
            update: AgentState = {"review_decision": decision, "review_step_id": step_id}
            if decision.outcome == "rework":
                count += 1
                update["rework_count"] = count
                if count >= max_rework_attempts:
                    update["run_status"] = "failed"
                    async with unit_of_work_factory() as uow:
                        await uow.set_run_status(
                            tenant_id=_tenant_id(state), run_id=_run_id(state), status="failed"
                        )
            return update
        except Exception as exc:
            raise _node_error("reviewer", exc) from None

    def reviewer_route(state: AgentState) -> str:
        decision = state.get("review_decision")
        if decision is None:
            return "end"
        if decision.approval_status == "pending":
            return "approval_wait"
        if decision.outcome == "rework" and state.get("run_status") != "failed":
            return "executor"
        return "end"

    async def approval_wait_node(state: AgentState) -> AgentState:
        try:
            decision = state.get("review_decision")
            step_id = state.get("review_step_id")
            if decision is None or step_id is None:
                raise ValueError("review decision and step identity are required")
            approval_id = await approval_gateway.request_approval(
                _tenant_id(state), _run_id(state), step_id, decision.findings
            )
            async with unit_of_work_factory() as uow:
                await uow.set_run_status(
                    tenant_id=_tenant_id(state), run_id=_run_id(state), status="waiting_approval"
                )
        except Exception as exc:
            raise _node_error("approval_wait", exc) from None

        response = interrupt(
            {
                "run_id": str(_run_id(state)),
                "approval_id": str(approval_id),
                "findings": [item.model_dump() for item in decision.findings],
            }
        )
        try:
            if not isinstance(response, Mapping):
                raise TypeError("approval response must be a mapping")
            outcome = await approval_gateway.submit_decision(
                approval_id,
                _run_id(state),
                cast(Literal["approved", "rejected"], response.get("decision")),
                str(response.get("decided_by") or "human"),
                cast(str | None, response.get("reason")),
            )
            resolved = reviewer.resolve(decision, outcome)
            status = "running" if outcome.decision == "approved" else "failed"
            async with unit_of_work_factory() as uow:
                await uow.set_run_status(
                    tenant_id=_tenant_id(state), run_id=_run_id(state), status=status
                )
            return {
                "approval_reference": approval_id,
                "review_decision": resolved,
                "run_status": status,
            }
        except Exception as exc:
            raise _node_error("approval_wait", exc) from None

    def approval_route(state: AgentState) -> str:
        decision = state.get("review_decision")
        return "draft_pr" if decision is not None and decision.outcome == "draft_pr" else "end"

    async def draft_pr_node(state: AgentState) -> AgentState:
        try:
            execution = state.get("execution_result")
            approval_id = state.get("approval_reference")
            step_id = state.get("review_step_id")
            workspace_path = state.get("workspace_path")
            target = state.get("repository_target")
            base_sha = state.get("base_sha")
            if None in (execution, approval_id, step_id, target) or not workspace_path or not base_sha:
                raise ValueError("approved draft PR state is incomplete")
            changes = _file_changes(Path(workspace_path), execution.changed_files)  # type: ignore[union-attr]
            authorization = WriteAuthorization(
                approval_id=approval_id,
                tenant_id=_tenant_id(state),
                run_id=_run_id(state),
                step_id=step_id,
                repository_target=target,
                base_sha=base_sha,
                content_digest=digest_file_changes(changes),
            )
            result = await create_draft_pull_request(
                github_client=github_write_client,
                read_client=github_read_client,
                changes=changes,
                authorization=authorization,
                approval_authorizer=approval_authorizer,
                idempotency_guard=idempotency_guard,
            )
            await _record_step(unit_of_work_factory, id_generator, state, "draft_pr", 8, "completed")
            async with unit_of_work_factory() as uow:
                await uow.record_audit(
                    tenant_id=_tenant_id(state), actor="github_draft_pr", action="create",
                    resource_type="pull_request", resource_id=str(result.pull_request_number),
                    decision="allow", reason="human_approved", trace_id=_trace_id(state),
                )
                await uow.set_run_status(
                    tenant_id=_tenant_id(state), run_id=_run_id(state), status="completed"
                )
            return {"draft_pr_result": result, "run_status": "completed"}
        except Exception as exc:
            raise _node_error("draft_pr", exc) from None

    builder = StateGraph(AgentState)
    builder.add_node("gate1a", gate1a_node)
    builder.add_node("policy_gate", policy_node)
    builder.add_node("executor", executor_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("approval_wait", approval_wait_node)
    builder.add_node("draft_pr", draft_pr_node)
    builder.add_edge(START, "gate1a")
    builder.add_edge("gate1a", "policy_gate")
    builder.add_conditional_edges("policy_gate", policy_route, {"executor": "executor", "end": END})
    builder.add_edge("executor", "reviewer")
    builder.add_conditional_edges(
        "reviewer", reviewer_route,
        {"approval_wait": "approval_wait", "executor": "executor", "end": END},
    )
    builder.add_conditional_edges(
        "approval_wait", approval_route, {"draft_pr": "draft_pr", "end": END}
    )
    builder.add_edge("draft_pr", END)
    return builder.compile(
        checkpointer=checkpointer or InMemorySaver(),
        name="aegisflow-gate1b",
    )


async def resume_gate1b(
    compiled_graph: CompiledStateGraph[Any, Any, Any, Any],
    run_id: UUID,
    decision: Mapping[str, str],
    *,
    tenant_id: UUID | None = None,
    workflow_version: int = 1,
) -> AgentState:
    config = _config(run_id, tenant_id, workflow_version)
    snapshot = await compiled_graph.aget_state(config)
    checkpoint_run_id = snapshot.values.get("run_id") if snapshot.values else None
    pending = snapshot.interrupts or tuple(
        item for task in snapshot.tasks for item in getattr(task, "interrupts", ())
    )
    if checkpoint_run_id != run_id or not pending:
        raise InvalidResumeThreadError(run_id)
    return cast(
        AgentState,
        await compiled_graph.ainvoke(Command(resume=dict(decision)), config=config),
    )


def _file_changes(root: Path, paths: list[str]) -> tuple[FileChange, ...]:
    changes = []
    for relative in sorted(set(paths)):
        target = root / relative
        changes.append(
            FileChange(
                path=relative,
                operation="update" if target.exists() else "delete",
                content=target.read_bytes() if target.exists() else None,
            )
        )
    if not changes:
        raise ValueError("execution produced no file changes")
    return tuple(changes)


async def _record_step(
    factory: Callable[[], AsyncUnitOfWork],
    id_generator: IdGenerator,
    state: AgentState,
    name: str,
    sequence: int,
    status: str,
) -> UUID:
    step_id = id_generator.new_id()
    async with factory() as uow:
        return await uow.record_step(
            tenant_id=_tenant_id(state), run_id=_run_id(state), step_id=step_id,
            name=name, sequence=sequence, status=status,
        )


def _trace(
    recorder: TraceRecorder,
    id_generator: IdGenerator,
    state: AgentState,
    agent: str,
    started: float,
    *,
    step_id: UUID | None = None,
) -> None:
    recorder.record(
        build_step_trace_record(
            tenant_id=_tenant_id(state), workflow_id=None, workflow_version=None,
            run_id=_run_id(state), step_id=step_id or id_generator.new_id(),
            trace_id=_trace_id(state), agent=agent, raw_prompt=agent,
            model=f"deterministic-{agent}-v1",
            token_usage=unavailable_token_usage(), cost=unavailable_cost_usage(),
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
        )
    )


def _run_id(state: AgentState) -> UUID:
    value = state.get("run_id")
    if not isinstance(value, UUID):
        raise TypeError("run_id must be a UUID")
    return value


def _tenant_id(state: AgentState) -> UUID:
    value = state.get("tenant_id")
    if not isinstance(value, UUID):
        raise TypeError("tenant_id must be a UUID")
    return value


def _trace_id(state: AgentState) -> UUID:
    value = state.get("trace_id")
    if not isinstance(value, UUID):
        raise TypeError("trace_id must be a UUID")
    return value


def _config(
    run_id: UUID,
    tenant_id: UUID | None = None,
    workflow_version: int = 1,
) -> RunnableConfig:
    if tenant_id is not None:
        return build_checkpoint_config(
            CheckpointIdentity(tenant_id, run_id, workflow_version)
        )
    return {"configurable": {"thread_id": str(run_id)}}


def _node_error(node: Gate1BNodeName, cause: Exception) -> Gate1BNodeError:
    if isinstance(cause, Gate1BNodeError):
        return cause
    return Gate1BNodeError(node, type(cause).__name__)
