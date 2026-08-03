"""Tenant-scoped read model for the workflow run graph."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import AuditEvent, Run, Step


class RunGraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    step_id: UUID
    name: str
    sequence: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    trace_id: str | None
    failure_reason: str | None


class RunGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: UUID
    workflow_id: UUID
    workflow_version: int
    status: str
    nodes: tuple[RunGraphNode, ...]


async def load_run_graph(
    session: AsyncSession, *, tenant_id: UUID, run_id: UUID
) -> RunGraph | None:
    run = await session.scalar(
        select(Run).where(Run.tenant_id == tenant_id, Run.id == run_id)
    )
    if run is None:
        return None
    steps = tuple(
        await session.scalars(
            select(Step)
            .where(Step.tenant_id == tenant_id, Step.run_id == run_id)
            .order_by(Step.sequence)
        )
    )
    audit_rows = tuple(
        await session.scalars(
            select(AuditEvent).where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.resource_type == "step",
                AuditEvent.resource_id.in_([str(step.id) for step in steps]),
            )
        )
    ) if steps else ()
    evidence = {row.resource_id: row for row in audit_rows}
    nodes = []
    for step in steps:
        audit = evidence.get(str(step.id))
        duration = (
            (step.completed_at - step.created_at).total_seconds() * 1000
            if step.completed_at is not None
            else None
        )
        nodes.append(
            RunGraphNode(
                step_id=step.id,
                name=step.name,
                sequence=step.sequence,
                status=step.status,
                started_at=step.created_at,
                completed_at=step.completed_at,
                duration_ms=duration,
                trace_id=audit.trace_id if audit else None,
                failure_reason=(
                    audit.reason if audit and step.status == "failed" else None
                ),
            )
        )
    return RunGraph(
        run_id=run.id,
        workflow_id=run.workflow_id,
        workflow_version=run.workflow_version,
        status=run.status,
        nodes=tuple(nodes),
    )
