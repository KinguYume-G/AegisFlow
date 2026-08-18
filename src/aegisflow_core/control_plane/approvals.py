"""PostgreSQL implementation of the DeliveryPack approval gateway."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import Run, RunEvent, Step
from aegisflow_core.control_plane.domain.approval import Approval
from aegisflow_core.packs.delivery.contracts.action_approval import (
    digest_action_preview,
)
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewFinding
from aegisflow_core.packs.delivery.reviewer.fakes import ApprovalRunMismatchError, DuplicateApprovalDecisionError


class WriteAuthorizationView(Protocol):
    approval_id: UUID
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    content_digest: str
    action_digest: str


class PostgresApprovalAuthorizer:
    """Verify that an exact runtime write is backed by an approved DB fact."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def verify(
        self,
        authorization: WriteAuthorizationView,
        actual_content_digest: str,
        actual_action_digest: str,
    ) -> None:
        if authorization.content_digest != actual_content_digest:
            raise PermissionError("write content was not approved")
        if authorization.action_digest != actual_action_digest:
            raise PermissionError("write action was not approved")
        async with self._factory() as session:
            row = await session.get(Approval, authorization.approval_id)
            if (
                row is None
                or row.decision != "approved"
                or row.tenant_id != authorization.tenant_id
                or row.run_id != authorization.run_id
                or row.step_id != authorization.step_id
                or row.action_digest != actual_action_digest
                or row.action_preview is None
                or digest_action_preview(row.action_preview) != actual_action_digest
            ):
                raise PermissionError("write approval was not verified")


class PostgresToolApprovalVerifier:
    """Resolve an approved, tenant/run/step-bound Human decision for one tool call."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def approved_by(
        self,
        *,
        approval_id: UUID,
        tenant_id: UUID,
        run_id: UUID,
        step_id: UUID,
    ) -> str | None:
        async with self._factory() as session:
            row = await session.get(Approval, approval_id)
            if (
                row is None
                or row.tenant_id != tenant_id
                or row.run_id != run_id
                or row.step_id != step_id
                or row.decision != "approved"
                or not row.decided_by
                or row.decided_at is None
            ):
                return None
            return row.decided_by


class PostgresApprovalGateway:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def request_approval(
        self,
        tenant_id: UUID,
        run_id: UUID,
        step_id: UUID,
        findings: list[ReviewFinding],
        *,
        action_preview: dict[str, object] | None = None,
        action_digest: str | None = None,
    ) -> UUID:
        async with self._factory() as session, session.begin():
            run = await session.scalar(
                select(Run)
                .where(Run.tenant_id == tenant_id, Run.id == run_id)
                .with_for_update()
            )
            if run is None:
                raise KeyError(run_id)
            existing = await session.scalar(select(Approval).where(
                Approval.tenant_id == tenant_id, Approval.run_id == run_id, Approval.step_id == step_id))
            if existing:
                if (
                    existing.action_preview != action_preview
                    or existing.action_digest != action_digest
                ):
                    raise PermissionError("approval replay did not match the original action")
                return UUID(str(existing.id))
            row = Approval(tenant_id=tenant_id, run_id=run_id, step_id=step_id, decision="pending",
                           reason="; ".join(f.message for f in findings) or None,
                           action_preview=action_preview, action_digest=action_digest)
            session.add(row)
            await session.flush()
            run.status = "waiting_approval"
            await _append_event(
                session,
                run,
                "approval.requested",
                "agent:reviewer",
                {
                    "approval_id": str(row.id),
                    "action_preview": action_preview,
                    "action_digest": action_digest,
                },
            )
            return UUID(str(row.id))

    async def submit_decision(self, approval_id: UUID, run_id: UUID,
                              decision: Literal["approved", "rejected"], decided_by: str,
                              reason: str | None = None) -> ApprovalOutcome:
        async with self._factory() as session, session.begin():
            run = await session.scalar(
                select(Run).where(Run.id == run_id).with_for_update()
            )
            if run is None:
                raise ApprovalRunMismatchError
            row = await session.get(Approval, approval_id, with_for_update=True)
            if row is None or row.run_id != run_id or row.tenant_id != run.tenant_id:
                raise ApprovalRunMismatchError
            if row.decision != "pending":
                raise DuplicateApprovalDecisionError
            row.decision, row.decided_by, row.decided_at, row.reason = decision, decided_by, datetime.now(timezone.utc), reason
            if row.step_id is not None:
                step = await session.get(Step, row.step_id)
                if step is not None:
                    step.status = "completed"
                    step.completed_at = datetime.now(timezone.utc)
            run.status = "running" if decision == "approved" else "failed"
            await _append_event(
                session,
                run,
                "approval.decided",
                decided_by,
                {
                    "approval_id": str(approval_id),
                    "decision": decision,
                },
            )
        return ApprovalOutcome(approval_id=approval_id, decision=decision, decided_by=decided_by, reason=reason)

    async def get_status(self, approval_id: UUID) -> Literal["pending", "approved", "rejected"]:
        async with self._factory() as session:
            row = await session.get(Approval, approval_id)
            if row is None:
                raise KeyError(approval_id)
            return row.decision  # type: ignore[return-value]


async def _append_event(
    session: AsyncSession,
    run: Run,
    event_type: str,
    actor: str,
    payload: dict[str, object],
) -> None:
    sequence = (
        await session.scalar(
            select(func.max(RunEvent.sequence)).where(
                RunEvent.tenant_id == run.tenant_id,
                RunEvent.run_id == run.id,
            )
        )
        or 0
    ) + 1
    session.add(
        RunEvent(
            tenant_id=run.tenant_id,
            run_id=run.id,
            sequence=sequence,
            event_type=event_type,
            actor=actor,
            payload=payload,
        )
    )
