"""PostgreSQL application service for the tenant-scoped Run lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import (
    Approval,
    AuditEvent,
    ClarificationRequest,
    RoleAssignment,
    Run,
    RunArtifact,
    RunEvaluation,
    RunEvent,
    RunRequest,
    RunTrace,
    Step,
    Tenant,
    TenantMembership,
    Workflow,
)
from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.rbac import (
    Capability,
    RbacService,
    Role,
    capability_matrix,
)
from aegisflow_core.control_plane.runs import (
    CreateRunRequest,
    RunDetail,
    RunEventView,
    RunList,
    RunSummary,
    SessionView,
    TenantSession,
    canonical_run_input_hash,
)
from aegisflow_core.runtime.temporal.contracts import (
    DeliveryWorkflowInput,
    HumanSignal,
    RuntimeIdentity,
)


class RunWorkflowGateway(Protocol):
    async def start(self, workflow_input: DeliveryWorkflowInput) -> None: ...

    async def signal_clarification(
        self, identity: RuntimeIdentity, signal: HumanSignal
    ) -> None: ...

    async def signal_approval(
        self, identity: RuntimeIdentity, signal: HumanSignal
    ) -> None: ...


class IdempotencyConflictError(ValueError):
    pass


class PostgresRunService:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        temporal: RunWorkflowGateway,
        *,
        profile: Literal["oidc", "local_mvp"] = "oidc",
    ) -> None:
        self._sessions = session_factory
        self._temporal = temporal
        self._profile = profile

    async def session(self, principal: Principal) -> SessionView:
        async with self._sessions() as session:
            memberships = tuple(
                await session.scalars(
                    select(TenantMembership).where(
                        TenantMembership.issuer == principal.issuer,
                        TenantMembership.subject == principal.subject,
                    )
                )
            )
            tenants: list[TenantSession] = []
            matrix = capability_matrix()
            for membership in memberships:
                tenant = await session.get(Tenant, membership.tenant_id)
                if tenant is None:
                    continue
                role_values = list(
                    await session.scalars(
                        select(RoleAssignment.role).where(
                            RoleAssignment.tenant_id == membership.tenant_id,
                            RoleAssignment.membership_id == membership.id,
                            RoleAssignment.revoked_at.is_(None),
                        )
                    )
                )
                roles = sorted({Role(value) for value in role_values}, key=lambda item: item.value)
                capabilities = sorted(
                    {capability.value for role in roles for capability in matrix[role]}
                )
                tenants.append(
                    TenantSession(
                        tenant_id=tenant.id,
                        slug=tenant.slug,
                        roles=[role.value for role in roles],
                        capabilities=capabilities,
                    )
                )
        return SessionView(
            actor_reference=principal.actor_reference,
            profile=self._profile,
            tenants=sorted(tenants, key=lambda item: item.slug),
        )

    async def create_run(
        self,
        tenant_id: UUID,
        principal: Principal,
        request: CreateRunRequest,
        idempotency_key: str,
    ) -> RunDetail:
        digest = canonical_run_input_hash(request)
        should_start = False
        identity: RuntimeIdentity | None = None
        async with self._sessions() as session, session.begin():
            await self._authorize(session, tenant_id, principal, Capability.RUN_EXECUTE)
            existing = await session.scalar(
                select(RunRequest).where(
                    RunRequest.tenant_id == tenant_id,
                    RunRequest.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                if existing.input_hash != digest:
                    raise IdempotencyConflictError(
                        "idempotency key was already used for different input"
                    )
                run = await session.scalar(
                    select(Run).where(Run.tenant_id == tenant_id, Run.id == existing.run_id)
                )
                if run is None:
                    raise RuntimeError("idempotent Run request has no Run")
                should_start = run.status == "pending"
                identity = self._identity(existing, run.workflow_version)
                run_id = run.id
            else:
                workflow = await session.scalar(
                    select(Workflow).where(
                        Workflow.tenant_id == tenant_id,
                        Workflow.name == "delivery",
                        Workflow.status == "active",
                    )
                )
                if workflow is None:
                    raise RuntimeError("active Delivery workflow is not configured")
                run_id = uuid4()
                trace_id = uuid4()
                run = Run(
                    id=run_id,
                    tenant_id=tenant_id,
                    workflow_id=workflow.id,
                    workflow_version=workflow.version,
                    status="pending",
                )
                identity = RuntimeIdentity(
                    tenant_id=str(tenant_id),
                    run_id=str(run_id),
                    trace_id=str(trace_id),
                    workflow_version=workflow.version,
                )
                stored = RunRequest(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    source_type=request.source_type,
                    source_ref=request.source_ref,
                    title=request.title,
                    body=request.body,
                    repository_owner=request.repository.owner,
                    repository_name=request.repository.name,
                    base_ref=request.repository.base_ref,
                    base_sha=request.repository.base_sha,
                    requested_by=principal.actor_reference,
                    idempotency_key=idempotency_key,
                    input_hash=digest,
                    trace_id=trace_id,
                    temporal_workflow_id=identity.temporal_workflow_id,
                )
                session.add_all([run, stored])
                await session.flush()
                session.add(
                    RunEvent(
                        tenant_id=tenant_id,
                        run_id=run_id,
                        sequence=1,
                        event_type="run.created",
                        actor=principal.actor_reference,
                        payload={
                            "source_type": request.source_type,
                            "repository": (
                                f"{request.repository.owner}/{request.repository.name}"
                            ),
                            "input_hash": digest,
                        },
                    )
                )
                should_start = True

        assert identity is not None
        if should_start:
            await self._temporal.start(DeliveryWorkflowInput(identity))
            async with self._sessions() as session, session.begin():
                locked = await self._locked_run(session, tenant_id, run_id)
                if locked.status == "pending":
                    locked.status = "running"
                    locked.updated_at = datetime.now(timezone.utc)
                    await self._append_event(
                        session,
                        locked,
                        "run.started",
                        "system:temporal",
                        {"temporal_workflow_id": identity.temporal_workflow_id},
                    )
        return await self.get_run(tenant_id, principal, run_id)

    async def list_runs(
        self, tenant_id: UUID, principal: Principal, limit: int
    ) -> RunList:
        async with self._sessions() as session:
            await self._authorize(session, tenant_id, principal, Capability.RUN_READ)
            rows = tuple(
                (
                    await session.execute(
                        select(Run, RunRequest)
                        .join(
                            RunRequest,
                            (RunRequest.tenant_id == Run.tenant_id)
                            & (RunRequest.run_id == Run.id),
                        )
                        .where(Run.tenant_id == tenant_id)
                        .order_by(Run.created_at.desc(), Run.id.desc())
                        .limit(limit)
                    )
                ).all()
            )
        return RunList(
            items=[self._summary(run, stored) for run, stored in rows],
            next_cursor=None,
        )

    async def get_run(
        self, tenant_id: UUID, principal: Principal, run_id: UUID
    ) -> RunDetail:
        async with self._sessions() as session:
            await self._authorize(session, tenant_id, principal, Capability.RUN_READ)
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
            run, stored = row
            steps = tuple(
                await session.scalars(
                    select(Step)
                    .where(Step.tenant_id == tenant_id, Step.run_id == run_id)
                    .order_by(Step.sequence)
                )
            )
            clarifications = tuple(
                await session.scalars(
                    select(ClarificationRequest)
                    .where(
                        ClarificationRequest.tenant_id == tenant_id,
                        ClarificationRequest.run_id == run_id,
                    )
                    .order_by(ClarificationRequest.created_at)
                )
            )
            approvals = tuple(
                await session.scalars(
                    select(Approval)
                    .where(Approval.tenant_id == tenant_id, Approval.run_id == run_id)
                    .order_by(Approval.created_at)
                )
            )
            artifacts = tuple(
                await session.scalars(
                    select(RunArtifact)
                    .where(RunArtifact.tenant_id == tenant_id, RunArtifact.run_id == run_id)
                    .order_by(RunArtifact.created_at)
                )
            )
            traces = tuple(
                await session.scalars(
                    select(RunTrace)
                    .where(RunTrace.tenant_id == tenant_id, RunTrace.run_id == run_id)
                    .order_by(RunTrace.created_at)
                )
            )
            evaluation = await session.scalar(
                select(RunEvaluation).where(
                    RunEvaluation.tenant_id == tenant_id,
                    RunEvaluation.run_id == run_id,
                )
            )
            audits = tuple(
                await session.scalars(
                    select(AuditEvent)
                    .where(
                        AuditEvent.tenant_id == tenant_id,
                        AuditEvent.resource_id == str(run_id),
                    )
                    .order_by(AuditEvent.created_at)
                )
            )
        pending: dict[str, object] | None = None
        clarification = next(
            (item for item in reversed(clarifications) if item.status == "pending"), None
        )
        approval = next(
            (item for item in reversed(approvals) if item.decision == "pending"), None
        )
        if clarification is not None:
            pending = {
                "kind": "clarification",
                "request_id": str(clarification.id),
                "questions": clarification.questions,
            }
        elif approval is not None:
            pending = {
                "kind": "approval",
                "request_id": str(approval.id),
                "action_preview": approval.action_preview,
                "action_digest": approval.action_digest,
                "reason": approval.reason,
            }
        return RunDetail(
            summary=self._summary(run, stored),
            request=self._request(stored),
            steps=[
                {
                    "step_id": str(item.id),
                    "name": item.name,
                    "sequence": item.sequence,
                    "status": item.status,
                    "started_at": item.created_at.isoformat(),
                    "completed_at": item.completed_at.isoformat()
                    if item.completed_at
                    else None,
                }
                for item in steps
            ],
            pending_action=pending,
            approvals=[
                {
                    "approval_id": str(item.id),
                    "decision": item.decision,
                    "decided_by": item.decided_by,
                    "decided_at": item.decided_at.isoformat() if item.decided_at else None,
                    "reason": item.reason,
                    "action_preview": item.action_preview,
                    "action_digest": item.action_digest,
                }
                for item in approvals
            ],
            artifacts=[
                {
                    "kind": item.kind,
                    "content_digest": item.content_digest,
                    "payload": item.payload,
                    "created_at": item.created_at.isoformat(),
                }
                for item in artifacts
            ],
            traces=[
                {
                    "event_id": str(item.event_id),
                    "agent": item.agent,
                    "model": item.model,
                    "token_usage": item.token_usage,
                    "cost_usage": item.cost_usage,
                    "latency_ms": item.latency_ms,
                    "created_at": item.created_at.isoformat(),
                }
                for item in traces
            ],
            evaluation=self._evaluation(evaluation),
            audit=[
                {
                    "event_id": str(item.id),
                    "actor": item.actor,
                    "action": item.action,
                    "decision": item.decision,
                    "reason": item.reason,
                    "trace_id": item.trace_id,
                    "created_at": item.created_at.isoformat(),
                }
                for item in audits
            ],
        )

    async def list_events(
        self,
        tenant_id: UUID,
        principal: Principal,
        run_id: UUID,
        after: int,
        limit: int,
    ) -> list[RunEventView]:
        async with self._sessions() as session:
            await self._authorize(session, tenant_id, principal, Capability.RUN_READ)
            if not await session.scalar(
                select(Run.id).where(Run.tenant_id == tenant_id, Run.id == run_id)
            ):
                raise KeyError(run_id)
            events = tuple(
                await session.scalars(
                    select(RunEvent)
                    .where(
                        RunEvent.tenant_id == tenant_id,
                        RunEvent.run_id == run_id,
                        RunEvent.sequence > after,
                    )
                    .order_by(RunEvent.sequence)
                    .limit(limit)
                )
            )
        return [
            RunEventView(
                sequence=item.sequence,
                event_type=item.event_type,
                actor=item.actor,
                payload=item.payload,
                created_at=item.created_at,
            )
            for item in events
        ]

    async def submit_clarification(
        self,
        tenant_id: UUID,
        principal: Principal,
        run_id: UUID,
        request_id: UUID,
        answers: dict[str, str],
        signal_id: str,
    ) -> dict[str, object]:
        if not answers or any(not value.strip() or len(value) > 8192 for value in answers.values()):
            raise ValueError("clarification answers are invalid")
        async with self._sessions() as session:
            await self._authorize(session, tenant_id, principal, Capability.RUN_EXECUTE)
            stored, run = await self._run_identity(session, tenant_id, run_id)
            pending = await session.scalar(
                select(ClarificationRequest).where(
                    ClarificationRequest.tenant_id == tenant_id,
                    ClarificationRequest.run_id == run_id,
                    ClarificationRequest.id == request_id,
                    ClarificationRequest.status == "pending",
                )
            )
            if pending is None:
                raise KeyError(request_id)
            if await self._signal_already_recorded(session, tenant_id, run_id, signal_id):
                return {"accepted": True, "run_id": str(run_id), "status": run.status}
            identity = self._identity(stored, run.workflow_version)
        signal = HumanSignal(
            signal_id=signal_id,
            kind="clarification",
            tenant_id=str(tenant_id),
            run_id=str(run_id),
            target_reference=str(request_id),
            value=json.dumps({"answers": answers}, sort_keys=True),
            actor_reference=principal.actor_reference,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._temporal.signal_clarification(identity, signal)
        await self._record_signal_event(tenant_id, run_id, principal, signal)
        return {"accepted": True, "run_id": str(run_id), "status": "waiting_clarification"}

    async def submit_approval(
        self,
        tenant_id: UUID,
        principal: Principal,
        run_id: UUID,
        approval_id: UUID,
        decision: Literal["approved", "rejected"],
        reason: str | None,
        signal_id: str,
    ) -> dict[str, object]:
        async with self._sessions() as session:
            stored, run = await self._run_identity(session, tenant_id, run_id)
            await self._authorize(
                session,
                tenant_id,
                principal,
                Capability.APPROVAL_DECIDE,
                target_actor_reference=stored.requested_by,
            )
            pending = await session.scalar(
                select(Approval).where(
                    Approval.tenant_id == tenant_id,
                    Approval.run_id == run_id,
                    Approval.id == approval_id,
                    Approval.decision == "pending",
                )
            )
            if pending is None:
                raise KeyError(approval_id)
            if await self._signal_already_recorded(session, tenant_id, run_id, signal_id):
                return {"accepted": True, "run_id": str(run_id), "status": run.status}
            identity = self._identity(stored, run.workflow_version)
        signal = HumanSignal(
            signal_id=signal_id,
            kind="approval",
            tenant_id=str(tenant_id),
            run_id=str(run_id),
            target_reference=str(approval_id),
            value=json.dumps({"decision": decision, "reason": reason}, sort_keys=True),
            actor_reference=principal.actor_reference,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._temporal.signal_approval(identity, signal)
        await self._record_signal_event(tenant_id, run_id, principal, signal)
        return {"accepted": True, "run_id": str(run_id), "status": "waiting_approval"}

    async def _record_signal_event(
        self,
        tenant_id: UUID,
        run_id: UUID,
        principal: Principal,
        signal: HumanSignal,
    ) -> None:
        async with self._sessions() as session, session.begin():
            run = await self._locked_run(session, tenant_id, run_id)
            if await self._signal_already_recorded(
                session, tenant_id, run_id, signal.signal_id
            ):
                return
            await self._append_event(
                session,
                run,
                f"human.{signal.kind}.submitted",
                principal.actor_reference,
                {
                    "signal_id": signal.signal_id,
                    "target_reference": signal.target_reference,
                },
            )

    @staticmethod
    async def _authorize(
        session: AsyncSession,
        tenant_id: UUID,
        principal: Principal,
        capability: Capability,
        *,
        target_actor_reference: str | None = None,
    ) -> None:
        decision = await RbacService(session).authorize(
            tenant_id,
            principal,
            capability,
            target_actor_reference=target_actor_reference,
        )
        if not decision.allowed:
            raise PermissionError(
                decision.reason_code
                if decision.reason_code == "rbac_self_approval_forbidden"
                else "tenant_access_denied"
            )

    @staticmethod
    async def _locked_run(session: AsyncSession, tenant_id: UUID, run_id: UUID) -> Run:
        run = await session.scalar(
            select(Run)
            .where(Run.tenant_id == tenant_id, Run.id == run_id)
            .with_for_update()
        )
        if run is None:
            raise KeyError(run_id)
        return run

    @staticmethod
    async def _append_event(
        session: AsyncSession,
        run: Run,
        event_type: str,
        actor: str,
        payload: dict[str, object],
    ) -> None:
        maximum = await session.scalar(
            select(func.max(RunEvent.sequence)).where(
                RunEvent.tenant_id == run.tenant_id, RunEvent.run_id == run.id
            )
        )
        session.add(
            RunEvent(
                tenant_id=run.tenant_id,
                run_id=run.id,
                sequence=int(maximum or 0) + 1,
                event_type=event_type,
                actor=actor,
                payload=payload,
            )
        )

    @staticmethod
    async def _signal_already_recorded(
        session: AsyncSession, tenant_id: UUID, run_id: UUID, signal_id: str
    ) -> bool:
        existing = await session.scalar(
            select(RunEvent.id).where(
                RunEvent.tenant_id == tenant_id,
                RunEvent.run_id == run_id,
                RunEvent.payload["signal_id"].astext == signal_id,
            )
        )
        return existing is not None

    @staticmethod
    async def _run_identity(
        session: AsyncSession, tenant_id: UUID, run_id: UUID
    ) -> tuple[RunRequest, Run]:
        row = (
            await session.execute(
                select(RunRequest, Run)
                .join(
                    Run,
                    (Run.tenant_id == RunRequest.tenant_id)
                    & (Run.id == RunRequest.run_id),
                )
                .where(RunRequest.tenant_id == tenant_id, RunRequest.run_id == run_id)
            )
        ).one_or_none()
        if row is None:
            raise KeyError(run_id)
        return row

    @staticmethod
    def _identity(stored: RunRequest, workflow_version: int) -> RuntimeIdentity:
        return RuntimeIdentity(
            tenant_id=str(stored.tenant_id),
            run_id=str(stored.run_id),
            trace_id=str(stored.trace_id),
            workflow_version=workflow_version,
        )

    @staticmethod
    def _request(stored: RunRequest) -> CreateRunRequest:
        from aegisflow_core.control_plane.runs import RepositoryInput

        return CreateRunRequest(
            source_type=stored.source_type,  # type: ignore[arg-type]
            source_ref=stored.source_ref,
            title=stored.title,
            body=stored.body,
            repository=RepositoryInput(
                owner=stored.repository_owner,
                name=stored.repository_name,
                base_ref=stored.base_ref,
                base_sha=stored.base_sha,
            ),
        )

    @classmethod
    def _summary(cls, run: Run, stored: RunRequest) -> RunSummary:
        return RunSummary(
            run_id=run.id,
            tenant_id=run.tenant_id,
            status=run.status,
            source_type=stored.source_type,
            title=stored.title,
            requested_by=stored.requested_by,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _evaluation(value: RunEvaluation | None) -> dict[str, object] | None:
        if value is None:
            return None
        return {
            "outcome": value.outcome,
            "task_success": value.task_success,
            "tool_success_rate": float(value.tool_success_rate),
            "total_steps": value.total_steps,
            "completed_steps": value.completed_steps,
            "input_tokens": value.input_tokens,
            "output_tokens": value.output_tokens,
            "cost_usd": float(value.cost_usd) if isinstance(value.cost_usd, Decimal) else None,
            "detail": value.detail,
            "created_at": value.created_at.isoformat(),
        }
