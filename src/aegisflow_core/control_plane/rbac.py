"""Fixed, code-owned, tenant-local role and capability evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import AuditEvent
from aegisflow_core.control_plane.domain.access import RoleAssignment, TenantMembership
from aegisflow_core.control_plane.identity import Principal


class Role(StrEnum):
    ADMIN = "Admin"
    DEVELOPER = "Developer"
    REVIEWER = "Reviewer"
    SECURITY = "Security"
    DEVOPS = "DevOps"
    VIEWER = "Viewer"


class Capability(StrEnum):
    TENANT_ADMIN = "tenant:admin"
    RUN_READ = "run:read"
    RUN_EXECUTE = "run:execute"
    APPROVAL_DECIDE = "approval:decide"
    AUDIT_READ = "audit:read"
    SECURITY_READ = "security:read"
    TOOL_INVOKE = "tool:invoke"
    SANDBOX_EXECUTE = "sandbox:execute"
    DEPLOYMENT_OPERATE = "deployment:operate"


_MATRIX: dict[Role, frozenset[Capability]] = {
    Role.ADMIN: frozenset(Capability),
    Role.DEVELOPER: frozenset({Capability.RUN_READ, Capability.RUN_EXECUTE, Capability.TOOL_INVOKE, Capability.SANDBOX_EXECUTE}),
    Role.REVIEWER: frozenset({Capability.RUN_READ, Capability.APPROVAL_DECIDE}),
    Role.SECURITY: frozenset({Capability.RUN_READ, Capability.AUDIT_READ, Capability.SECURITY_READ}),
    Role.DEVOPS: frozenset({Capability.RUN_READ, Capability.SANDBOX_EXECUTE, Capability.DEPLOYMENT_OPERATE}),
    Role.VIEWER: frozenset({Capability.RUN_READ}),
}


def capability_matrix() -> dict[Role, frozenset[Capability]]:
    return dict(_MATRIX)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str
    capability: Capability


class RbacService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authorize(
        self,
        tenant_id: UUID,
        principal: Principal,
        capability: Capability,
        *,
        target_actor_reference: str | None = None,
    ) -> AuthorizationDecision:
        if not isinstance(capability, Capability):
            raise ValueError("unknown capability")
        membership = await self._membership(tenant_id, principal)
        if membership is None:
            return AuthorizationDecision(False, "rbac_membership_missing", capability)
        values = list(
            await self._session.scalars(
                select(RoleAssignment.role).where(
                    RoleAssignment.tenant_id == tenant_id,
                    RoleAssignment.membership_id == membership.id,
                    RoleAssignment.revoked_at.is_(None),
                )
            )
        )
        try:
            roles = {Role(value) for value in values}
        except ValueError:
            return AuthorizationDecision(False, "rbac_unknown_role", capability)
        capabilities = frozenset().union(*(_MATRIX[role] for role in roles)) if roles else frozenset()
        if capability not in capabilities:
            return AuthorizationDecision(False, "rbac_capability_denied", capability)
        if capability is Capability.APPROVAL_DECIDE and target_actor_reference == principal.actor_reference:
            return AuthorizationDecision(False, "rbac_self_approval_forbidden", capability)
        return AuthorizationDecision(True, "rbac_allowed", capability)

    async def assign_role(
        self,
        tenant_id: UUID,
        actor: Principal,
        membership_id: UUID,
        role: Role,
    ) -> RoleAssignment:
        if not isinstance(role, Role):
            raise ValueError("unknown role")
        decision = await self.authorize(tenant_id, actor, Capability.TENANT_ADMIN)
        if not decision.allowed:
            raise PermissionError(decision.reason_code)
        target = await self._session.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id, TenantMembership.id == membership_id))
        if target is None:
            raise LookupError("membership not found")
        existing = await self._session.scalar(select(RoleAssignment).where(RoleAssignment.tenant_id == tenant_id, RoleAssignment.membership_id == membership_id, RoleAssignment.role == role.value, RoleAssignment.revoked_at.is_(None)))
        if existing is not None:
            return existing
        assignment = RoleAssignment(tenant_id=tenant_id, membership_id=membership_id, role=role.value, assigned_by=actor.actor_reference)
        self._session.add(assignment)
        await self._session.flush()
        self._session.add(self._audit(tenant_id, actor, "rbac.role.assigned", assignment, role))
        return assignment

    async def revoke_role(self, tenant_id: UUID, actor: Principal, assignment_id: UUID) -> RoleAssignment:
        decision = await self.authorize(tenant_id, actor, Capability.TENANT_ADMIN)
        if not decision.allowed:
            raise PermissionError(decision.reason_code)
        assignment = await self._session.scalar(select(RoleAssignment).where(RoleAssignment.tenant_id == tenant_id, RoleAssignment.id == assignment_id, RoleAssignment.revoked_at.is_(None)))
        if assignment is None:
            raise LookupError("active role assignment not found")
        assignment.revoked_at = datetime.now(timezone.utc)
        assignment.revoked_by = actor.actor_reference
        await self._session.flush()
        self._session.add(self._audit(tenant_id, actor, "rbac.role.revoked", assignment, Role(assignment.role)))
        return assignment

    async def _membership(self, tenant_id: UUID, principal: Principal) -> TenantMembership | None:
        return await self._session.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id, TenantMembership.issuer == principal.issuer, TenantMembership.subject == principal.subject))

    @staticmethod
    def _audit(tenant_id: UUID, actor: Principal, action: str, assignment: RoleAssignment, role: Role) -> AuditEvent:
        return AuditEvent(tenant_id=tenant_id, actor=actor.actor_reference, action=action, resource_type="role_assignment", resource_id=str(assignment.id), decision="allow", reason=role.value)
