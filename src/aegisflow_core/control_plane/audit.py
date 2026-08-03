"""Validated append-only audit writer and tenant-scoped reader."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.audit import AuditEvent
from aegisflow_core.control_plane.tenants.scope import TenantScope, TenantScopeViolation

_BOUNDS = {
    "actor": 2304,
    "action": 255,
    "resource_type": 255,
    "resource_id": 2048,
    "decision": 64,
    "reason": 4096,
    "trace_id": 255,
}
_SENSITIVE = re.compile(
    r"(?i)(authorization\s*[=:]\s*(?:bearer\s+)?|bearer\s+|"
    r"(?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+"
)
_PEM = re.compile(
    r"-----BEGIN [^-\r\n]+-----.*?-----END [^-\r\n]+-----",
    re.IGNORECASE | re.DOTALL,
)
_STANDALONE_TOKEN = re.compile(
    r"(?i)\b(?:gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|"
    r"(?:sk|pk)-(?:lf-)?[a-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})\b"
)
_URI_CREDENTIAL = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://)[^\s/@:]+:[^\s/@]+@")


def redact_audit_text(value: str) -> str:
    value = _PEM.sub("[REDACTED]", value)
    value = _URI_CREDENTIAL.sub(r"\1[REDACTED]@", value)
    value = _STANDALONE_TOKEN.sub("[REDACTED]", value)
    return _SENSITIVE.sub(lambda match: f"{match.group(1)}[REDACTED]", value)


def _field(name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} is required")
    if len(cleaned) > _BOUNDS[name]:
        raise ValueError(f"{name} exceeds {_BOUNDS[name]} characters")
    return redact_audit_text(cleaned)


class AuditService:
    def __init__(self, session: AsyncSession, scope: TenantScope | None = None) -> None:
        self._session = session
        self._scope = scope

    async def append(
        self,
        *,
        tenant_id: UUID,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        decision: str,
        reason: str,
        trace_id: str,
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=tenant_id,
            actor=_field("actor", actor),
            action=_field("action", action),
            resource_type=_field("resource_type", resource_type),
            resource_id=_field("resource_id", resource_id),
            decision=_field("decision", decision),
            reason=_field("reason", reason),
            trace_id=_field("trace_id", trace_id),
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def record(self, **fields: object) -> None:
        await self.append(**fields)  # type: ignore[arg-type]

    async def list_for_tenant(self, tenant_id: UUID, *, limit: int = 100) -> list[AuditEvent]:
        if self._scope is None:
            raise TenantScopeViolation("authenticated tenant scope is required for audit reads")
        if tenant_id != self._scope.tenant_id:
            raise TenantScopeViolation("audit tenant does not match authenticated scope")
        if limit < 1 or limit > 500:
            raise ValueError("audit query limit must be between 1 and 500")
        return list(
            await self._session.scalars(
                select(AuditEvent)
                .where(AuditEvent.tenant_id == tenant_id)
                .order_by(AuditEvent.created_at, AuditEvent.id)
                .limit(limit)
            )
        )
