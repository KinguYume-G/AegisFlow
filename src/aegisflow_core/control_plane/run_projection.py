"""Authoritative PostgreSQL projection of graph evidence and terminal evaluation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from typing import Literal, cast
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import (
    AuditEvent,
    Run,
    RunArtifact,
    RunEvaluation,
    RunEvent,
    RunTrace,
    Step,
)
from aegisflow_core.runtime.state import AgentState


_STEP_NAMESPACE = UUID("2dd2ba1e-11e1-4c03-9ea1-d20c0aac76b5")
TerminalStatus = Literal["completed", "failed"]
_FAILURE_STEPS = {
    "intake": ("intake", 1),
    "clarifier": ("clarifier", 2),
    "context": ("context", 3),
    "planner": ("planner", 4),
    "policy_gate": ("policy_gate", 5),
    "executor": ("executor", 6),
    "reviewer": ("reviewer", 7),
    "approval_wait": ("human_approval", 8),
    "draft_pr": ("draft_pr", 9),
}


class PostgresRunProjection:
    """Project bounded graph values without taking ownership from LangGraph."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sessions = session_factory

    async def project(self, state: AgentState, *, status: str) -> str | None:
        tenant_id = _uuid(state, "tenant_id")
        run_id = _uuid(state, "run_id")
        artifacts = _artifacts(state, status=status)
        async with self._sessions() as session, session.begin():
            run = await session.scalar(
                select(Run)
                .where(Run.tenant_id == tenant_id, Run.id == run_id)
                .with_for_update()
            )
            if run is None:
                raise KeyError(run_id)
            for kind, payload in artifacts:
                canonical = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                await session.execute(
                    insert(RunArtifact)
                    .values(
                        tenant_id=tenant_id,
                        run_id=run_id,
                        kind=kind,
                        content_digest=sha256(canonical).hexdigest(),
                        payload=payload,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["tenant_id", "run_id", "kind"]
                    )
                )

            if status in {"completed", "failed"}:
                await self._project_evaluation(
                    session,
                    state,
                    tenant_id=tenant_id,
                    run_id=run_id,
                    status=status,
                )
                run.status = status
                await self._append_terminal_event(
                    session, run, status=status, state=state
                )

        result = state.get("draft_pr_result")
        if status == "completed" and result is not None:
            return result.candidate_reference or result.pull_request_url
        return f"run:{run_id}:{status}" if status in {"completed", "failed"} else None

    async def project_runtime_failure(
        self,
        *,
        tenant_id: UUID,
        run_id: UUID,
        trace_id: UUID,
        reason: str,
    ) -> str:
        """Idempotently turn an Activity failure into truthful business evidence."""
        _validate_failure_reason(reason)
        state = cast(
            AgentState,
            {
                "tenant_id": tenant_id,
                "run_id": run_id,
                "trace_id": trace_id,
                "run_status": "failed",
                "failure_reason": reason,
            },
        )
        async with self._sessions() as session, session.begin():
            run = await session.scalar(
                select(Run)
                .where(Run.tenant_id == tenant_id, Run.id == run_id)
                .with_for_update()
            )
            if run is None:
                raise KeyError(run_id)
            if run.status == "completed":
                raise RuntimeError("completed Run cannot be projected as failed")

            failure_step = _failure_step(reason)
            if failure_step is not None:
                name, sequence = failure_step
                step_id = uuid5(
                    _STEP_NAMESPACE, f"{tenant_id}:{run_id}:{sequence}:{name}"
                )
                await session.execute(
                    insert(Step)
                    .values(
                        id=step_id,
                        tenant_id=tenant_id,
                        run_id=run_id,
                        name=name,
                        sequence=sequence,
                        status="failed",
                        completed_at=func.now(),
                    )
                    .on_conflict_do_update(
                        index_elements=["run_id", "sequence"],
                        set_={"status": "failed", "completed_at": func.now()},
                    )
                )

            for kind, payload in _artifacts(state, status="failed"):
                canonical = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                await session.execute(
                    insert(RunArtifact)
                    .values(
                        tenant_id=tenant_id,
                        run_id=run_id,
                        kind=kind,
                        content_digest=sha256(canonical).hexdigest(),
                        payload=payload,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["tenant_id", "run_id", "kind"]
                    )
                )

            await self._project_evaluation(
                session,
                state,
                tenant_id=tenant_id,
                run_id=run_id,
                status="failed",
            )
            run.status = "failed"
            run.updated_at = datetime.now(timezone.utc)
            await self._append_terminal_event(
                session, run, status="failed", state=state
            )
            existing_audit = await session.scalar(
                select(AuditEvent.id).where(
                    AuditEvent.tenant_id == tenant_id,
                    AuditEvent.action == "runtime_fail",
                    AuditEvent.resource_type == "run",
                    AuditEvent.resource_id == str(run_id),
                )
            )
            if existing_audit is None:
                session.add(
                    AuditEvent(
                        tenant_id=tenant_id,
                        actor="system:worker",
                        action="runtime_fail",
                        resource_type="run",
                        resource_id=str(run_id),
                        decision="deny",
                        reason=reason,
                        trace_id=str(trace_id),
                    )
                )
        return f"run:{run_id}:failed"

    async def _project_evaluation(
        self,
        session: AsyncSession,
        state: AgentState,
        *,
        tenant_id: UUID,
        run_id: UUID,
        status: str,
    ) -> None:
        step_id = uuid5(
            _STEP_NAMESPACE, f"{tenant_id}:{run_id}:10:evaluation"
        )
        await session.execute(
            insert(Step)
            .values(
                id=step_id,
                tenant_id=tenant_id,
                run_id=run_id,
                name="evaluation",
                sequence=10,
                status="completed",
                completed_at=func.now(),
            )
            .on_conflict_do_update(
                index_elements=["run_id", "sequence"],
                set_={"status": "completed", "completed_at": func.now()},
            )
        )
        traces = tuple(
            await session.scalars(
                select(RunTrace).where(
                    RunTrace.tenant_id == tenant_id, RunTrace.run_id == run_id
                )
            )
        )
        steps = tuple(
            await session.scalars(
                select(Step).where(Step.tenant_id == tenant_id, Step.run_id == run_id)
            )
        )
        input_tokens, output_tokens = _token_totals(traces)
        cost_usd = _cost_total(traces)
        execution = state.get("execution_result")
        tool_success_rate = Decimal(
            "1" if execution is not None and execution.status == "completed" else "0"
        )
        detail: dict[str, object] = {
            "policy_decision": (
                state["policy_decision"].decision
                if state.get("policy_decision") is not None
                else None
            ),
            "sandbox_status": (
                execution.test_outcome.status if execution is not None else None
            ),
            "effect_mode": (
                state["draft_pr_result"].effect_mode
                if state.get("draft_pr_result") is not None
                else None
            ),
            "token_measurement": (
                "measured"
                if input_tokens is not None and output_tokens is not None
                else "not_available"
            ),
            "cost_measurement": (
                "measured" if cost_usd is not None else "not_available"
            ),
            "failure_reason": state.get("failure_reason"),
        }
        await session.execute(
            insert(RunEvaluation)
            .values(
                tenant_id=tenant_id,
                run_id=run_id,
                outcome=status,
                task_success=status == "completed",
                tool_success_rate=tool_success_rate,
                total_steps=len(steps),
                completed_steps=sum(item.status == "completed" for item in steps),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                detail=detail,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "run_id"])
        )

    @staticmethod
    async def _append_terminal_event(
        session: AsyncSession,
        run: Run,
        *,
        status: str,
        state: AgentState,
    ) -> None:
        event_type = f"run.{status}"
        exists = await session.scalar(
            select(RunEvent.id).where(
                RunEvent.tenant_id == run.tenant_id,
                RunEvent.run_id == run.id,
                RunEvent.event_type == event_type,
            )
        )
        if exists is not None:
            return
        sequence = (
            await session.scalar(
                select(func.max(RunEvent.sequence)).where(
                    RunEvent.tenant_id == run.tenant_id,
                    RunEvent.run_id == run.id,
                )
            )
            or 0
        ) + 1
        result = state.get("draft_pr_result")
        session.add(
            RunEvent(
                tenant_id=run.tenant_id,
                run_id=run.id,
                sequence=sequence,
                event_type=event_type,
                actor="system:worker",
                payload={
                    "effect_mode": result.effect_mode if result is not None else None,
                    "result_reference": (
                        result.candidate_reference or result.pull_request_url
                        if result is not None
                        else None
                    ),
                    "failure_reason": state.get("failure_reason"),
                },
            )
        )


def _artifacts(
    state: AgentState, *, status: str
) -> list[tuple[str, dict[str, object]]]:
    values: list[tuple[str, dict[str, object]]] = []
    context = state.get("context")
    if context is not None:
        values.append(("context", context.model_dump(mode="json")))
    plan = state.get("plan")
    if plan is not None:
        values.append(("plan", plan.model_dump(mode="json")))
    execution = state.get("execution_result")
    if execution is not None:
        values.append(
            (
                "sandbox",
                {
                    "status": execution.status,
                    "test_outcome": execution.test_outcome.model_dump(mode="json"),
                    "reasoner_id": execution.reasoner_id,
                },
            )
        )
        values.append(
            (
                "diff",
                {
                    "changed_files": execution.changed_files,
                    "patch": execution.patch,
                },
            )
        )
    result = state.get("draft_pr_result")
    if result is not None:
        values.append(("draft_pr_candidate", result.model_dump(mode="json")))
    if status == "failed":
        policy = state.get("policy_decision")
        review = state.get("review_decision")
        values.append(
            (
                "failure",
                {
                    "reason": state.get("failure_reason"),
                    "policy_rule": policy.violated_rule if policy is not None else None,
                    "review_outcome": review.outcome if review is not None else None,
                    "sandbox_status": (
                        execution.test_outcome.status if execution is not None else None
                    ),
                },
            )
        )
    return values


def _validate_failure_reason(reason: str) -> None:
    if not reason or len(reason) > 200:
        raise ValueError("failure reason must be bounded")
    parts = reason.split(":")
    if len(parts) not in {2, 3} or not all(
        part and part.replace("_", "").isalnum() for part in parts
    ):
        raise ValueError("failure reason must be a stable diagnostic code")


def _failure_step(reason: str) -> tuple[str, int] | None:
    parts = reason.split(":")
    return _FAILURE_STEPS.get(parts[1]) if len(parts) == 3 else None


def _token_totals(traces: tuple[RunTrace, ...]) -> tuple[int | None, int | None]:
    inputs: list[int] = []
    outputs: list[int] = []
    for trace in traces:
        input_measurement = trace.token_usage.get("input_tokens", {})
        output_measurement = trace.token_usage.get("output_tokens", {})
        if (
            input_measurement.get("status") == "measured"
            and output_measurement.get("status") == "measured"
            and isinstance(input_measurement.get("value"), int)
            and isinstance(output_measurement.get("value"), int)
        ):
            inputs.append(input_measurement["value"])
            outputs.append(output_measurement["value"])
    return (sum(inputs), sum(outputs)) if inputs or outputs else (None, None)


def _cost_total(traces: tuple[RunTrace, ...]) -> Decimal | None:
    values: list[Decimal] = []
    for trace in traces:
        if trace.cost_usage.get("source") == "not_available":
            continue
        if trace.cost_usage.get("currency") != "USD":
            continue
        amount = trace.cost_usage.get("amount")
        if amount is not None:
            values.append(Decimal(str(amount)))
    return sum(values, Decimal("0")) if values else None


def _uuid(state: AgentState, key: str) -> UUID:
    value = state.get(key)  # type: ignore[literal-required]
    if not isinstance(value, UUID):
        raise TypeError(f"{key} must be a UUID")
    return value
