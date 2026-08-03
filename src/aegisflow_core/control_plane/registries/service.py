"""Validated registration, disablement and active lookup operations."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.audit import AuditService
from aegisflow_core.control_plane.domain.registry import ToolDisablement, ToolRegistration

_NAME = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")


class ToolRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)

    async def register(
        self,
        *,
        tenant_id: UUID,
        owner_scope: str,
        canonical_name: str,
        version: str,
        adapter_identifier: str,
        input_schema_hash: str,
        output_schema_hash: str,
        allowed_scopes: frozenset[str],
        risk_level: str,
        actor: str,
        trace_id: str,
    ) -> ToolRegistration:
        self._validate(owner_scope, canonical_name, version, adapter_identifier, input_schema_hash, output_schema_hash, allowed_scopes, risk_level, actor)
        existing = await self._session.scalar(
            select(ToolRegistration).where(
                ToolRegistration.tenant_id == tenant_id,
                ToolRegistration.canonical_name == canonical_name,
                ToolRegistration.version == version,
            )
        )
        values = (owner_scope, adapter_identifier, input_schema_hash, output_schema_hash, sorted(allowed_scopes), risk_level)
        if existing is not None:
            current = (existing.owner_scope, existing.adapter_identifier, existing.input_schema_hash, existing.output_schema_hash, sorted(existing.allowed_scopes), existing.risk_level)
            if current != values:
                raise ValueError("tool registration version is immutable")
            return existing
        registration = ToolRegistration(
            tenant_id=tenant_id, owner_scope=owner_scope, canonical_name=canonical_name,
            version=version, adapter_identifier=adapter_identifier,
            input_schema_hash=input_schema_hash, output_schema_hash=output_schema_hash,
            allowed_scopes=sorted(allowed_scopes), risk_level=risk_level, registered_by=actor,
        )
        self._session.add(registration)
        await self._session.flush()
        await self._audit.append(
            tenant_id=tenant_id, actor=actor, action="tool.register",
            resource_type="tool_registration", resource_id=str(registration.id),
            decision="allow", reason=f"{canonical_name}@{version}", trace_id=trace_id,
        )
        return registration

    async def disable(self, tenant_id: UUID, registration_id: UUID, *, actor: str, reason: str, trace_id: str) -> ToolDisablement:
        if not actor.strip() or len(actor) > 2304:
            raise ValueError("invalid disablement actor")
        if not reason.strip() or len(reason) > 4096:
            raise ValueError("invalid disablement reason")
        registration = await self._session.scalar(
            select(ToolRegistration).where(ToolRegistration.tenant_id == tenant_id, ToolRegistration.id == registration_id)
        )
        if registration is None:
            raise LookupError("tool registration not found")
        existing = await self._session.scalar(
            select(ToolDisablement).where(ToolDisablement.tenant_id == tenant_id, ToolDisablement.registration_id == registration_id)
        )
        if existing is not None:
            return existing
        disabled = ToolDisablement(tenant_id=tenant_id, registration_id=registration_id, disabled_by=actor, reason=reason)
        self._session.add(disabled)
        await self._session.flush()
        await self._audit.append(
            tenant_id=tenant_id, actor=actor, action="tool.disable",
            resource_type="tool_registration", resource_id=str(registration_id),
            decision="allow", reason=reason, trace_id=trace_id,
        )
        return disabled

    async def get_active(self, tenant_id: UUID, name: str, version: str) -> ToolRegistration | None:
        return await self._session.scalar(
            select(ToolRegistration)
            .outerjoin(
                ToolDisablement,
                (ToolDisablement.tenant_id == ToolRegistration.tenant_id)
                & (ToolDisablement.registration_id == ToolRegistration.id),
            )
            .where(
                ToolRegistration.tenant_id == tenant_id,
                ToolRegistration.canonical_name == name,
                ToolRegistration.version == version,
                ToolDisablement.id.is_(None),
            )
        )

    @staticmethod
    def _validate(owner: str, name: str, version: str, adapter: str, input_hash: str, output_hash: str, scopes: frozenset[str], risk: str, actor: str) -> None:
        if not owner.strip() or len(owner) > 255: raise ValueError("invalid owner scope")
        if not _NAME.fullmatch(name): raise ValueError("invalid canonical tool name")
        if not version.strip() or len(version) > 64: raise ValueError("invalid tool version")
        if not adapter.strip() or len(adapter) > 255: raise ValueError("invalid adapter identifier")
        if not _HASH.fullmatch(input_hash) or not _HASH.fullmatch(output_hash): raise ValueError("invalid schema hash")
        if not scopes or any(not value.strip() or len(value) > 255 for value in scopes): raise ValueError("invalid tool scopes")
        if risk not in {"L1", "L2", "L3"}: raise ValueError("invalid tool risk")
        if not actor.strip() or len(actor) > 2304: raise ValueError("invalid registration actor")
