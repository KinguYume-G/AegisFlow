"""Fail-closed API tenant resolution from verified identity and membership."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from aegisflow_core.control_plane.identity import Principal
from aegisflow_core.control_plane.rbac import AuthorizationDecision, Capability
from aegisflow_core.control_plane.tenants import TenantScope


class TenantAuthorizer(Protocol):
    async def authorize(
        self, tenant_id: UUID, principal: Principal, capability: Capability
    ) -> AuthorizationDecision: ...


async def resolve_tenant_scope(
    *,
    tenant_id: UUID | None,
    principal: Principal | None,
    capability: Capability,
    authorizer: TenantAuthorizer,
) -> TenantScope:
    """Resolve an API scope without trusting a tenant header by itself."""
    if tenant_id is None or principal is None:
        raise PermissionError("tenant_access_denied")
    decision = await authorizer.authorize(tenant_id, principal, capability)
    if not decision.allowed:
        raise PermissionError("tenant_access_denied")
    return TenantScope(tenant_id, principal.actor_reference)
