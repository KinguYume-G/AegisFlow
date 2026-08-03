"""PostgreSQL implementation of the DeliveryPack approval gateway."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.approval import Approval
from aegisflow_core.packs.delivery.contracts.review_decision import ApprovalOutcome, ReviewFinding
from aegisflow_core.packs.delivery.reviewer.fakes import ApprovalRunMismatchError, DuplicateApprovalDecisionError


class WriteAuthorizationView(Protocol):
    approval_id: UUID
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    content_digest: str


class PostgresApprovalAuthorizer:
    """Verify that an exact runtime write is backed by an approved DB fact."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def verify(
        self, authorization: WriteAuthorizationView, actual_content_digest: str
    ) -> None:
        if authorization.content_digest != actual_content_digest:
            raise PermissionError("write content was not approved")
        async with self._factory() as session:
            row = await session.get(Approval, authorization.approval_id)
            if (
                row is None
                or row.decision != "approved"
                or row.tenant_id != authorization.tenant_id
                or row.run_id != authorization.run_id
                or row.step_id != authorization.step_id
            ):
                raise PermissionError("write approval was not verified")


class PostgresApprovalGateway:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._factory = session_factory

    async def request_approval(self, tenant_id: UUID, run_id: UUID, step_id: UUID,
                               findings: list[ReviewFinding]) -> UUID:
        async with self._factory() as session, session.begin():
            existing = await session.scalar(select(Approval).where(
                Approval.tenant_id == tenant_id, Approval.run_id == run_id, Approval.step_id == step_id))
            if existing:
                return existing.id
            row = Approval(tenant_id=tenant_id, run_id=run_id, step_id=step_id, decision="pending",
                           reason="; ".join(f.message for f in findings) or None)
            session.add(row)
            await session.flush()
            return row.id

    async def submit_decision(self, approval_id: UUID, run_id: UUID,
                              decision: Literal["approved", "rejected"], decided_by: str,
                              reason: str | None = None) -> ApprovalOutcome:
        async with self._factory() as session, session.begin():
            row = await session.get(Approval, approval_id, with_for_update=True)
            if row is None or row.run_id != run_id:
                raise ApprovalRunMismatchError
            if row.decision != "pending":
                raise DuplicateApprovalDecisionError
            row.decision, row.decided_by, row.decided_at, row.reason = decision, decided_by, datetime.now(timezone.utc), reason
        return ApprovalOutcome(approval_id=approval_id, decision=decision, decided_by=decided_by, reason=reason)

    async def get_status(self, approval_id: UUID) -> Literal["pending", "approved", "rejected"]:
        async with self._factory() as session:
            row = await session.get(Approval, approval_id)
            if row is None:
                raise KeyError(approval_id)
            return row.decision  # type: ignore[return-value]
