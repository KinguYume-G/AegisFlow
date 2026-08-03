"""Fail-closed registry, policy, schema and adapter invocation gate."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Protocol
from uuid import UUID

from aegisflow_core.gateway.policy.contextual import (
    ContextualPolicy,
    PolicyInput,
    PolicyOutcome,
)


class Registry(Protocol):
    async def get_active(self, tenant_id: UUID, name: str, version: str) -> object | None: ...


class Adapter(Protocol):
    identifier: str
    input_schema_hash: str
    output_schema_hash: str

    def validate_input(self, arguments: dict[str, object]) -> bool: ...
    def validate_output(self, result: object) -> bool: ...
    async def invoke(self, arguments: dict[str, object], credentials: object | None) -> object: ...


class CredentialResolver(Protocol):
    async def resolve(self, adapter_identifier: str) -> object: ...


class AuditRecorder(Protocol):
    async def record(self, **fields: object) -> None: ...


@dataclass(frozen=True, slots=True)
class InvocationRequest:
    tenant_id: UUID
    tool_name: str
    tool_version: str
    requested_scope: str
    arguments: dict[str, object]
    policy_input: PolicyInput
    trace_id: str


class McpInvocationGate:
    def __init__(
        self,
        *,
        registry: Registry,
        adapters: Mapping[str, Adapter],
        credential_resolver: CredentialResolver,
        audit: AuditRecorder,
        policy: ContextualPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._adapters = dict(adapters)
        self._credential_resolver = credential_resolver
        self._audit = audit
        self._policy = policy or ContextualPolicy()

    async def invoke(self, request: InvocationRequest) -> object:
        if request.policy_input.tenant_id != request.tenant_id:
            return await self._deny(request, "tenant_membership.mismatch")
        registration = await self._registry.get_active(
            request.tenant_id, request.tool_name, request.tool_version
        )
        reason = "tool_registration_scope.unregistered"
        if registration is None or getattr(registration, "tenant_id", None) != request.tenant_id:
            return await self._deny(request, reason)
        adapter = self._adapters.get(str(getattr(registration, "adapter_identifier", "")))
        if adapter is None:
            return await self._deny(request, "tool_registration_scope.adapter_unavailable")
        if (
            adapter.input_schema_hash != getattr(registration, "input_schema_hash", None)
            or adapter.output_schema_hash != getattr(registration, "output_schema_hash", None)
        ):
            return await self._deny(request, "tool_registration_scope.schema_mismatch")
        scopes = frozenset(str(value) for value in getattr(registration, "allowed_scopes", ()))
        policy_input = replace(
            request.policy_input,
            tenant_id=request.tenant_id,
            tool_registered=True,
            registered_scopes=scopes,
            requested_scope=request.requested_scope,
            risk_level=getattr(registration, "risk_level", request.policy_input.risk_level),
        )
        decision = self._policy.evaluate(policy_input)
        if decision.outcome is not PolicyOutcome.ALLOW:
            return await self._deny(request, decision.reason_code)
        if not adapter.validate_input(request.arguments):
            return await self._deny(request, "tool_registration_scope.input_schema_invalid")
        try:
            credentials = await self._credential_resolver.resolve(adapter.identifier)
            result = await adapter.invoke(dict(request.arguments), credentials)
        except Exception as exc:
            await self._record(request, "deny", f"adapter.{type(exc).__name__}")
            raise RuntimeError("registered tool invocation failed") from None
        if not adapter.validate_output(result):
            await self._record(request, "deny", "tool_registration_scope.output_schema_invalid")
            raise RuntimeError("registered tool returned invalid output")
        await self._record(request, "allow", "policy.allowed")
        return result

    async def _deny(self, request: InvocationRequest, reason: str) -> object:
        await self._record(request, "deny", reason)
        raise PermissionError(reason)

    async def _record(self, request: InvocationRequest, decision: str, reason: str) -> None:
        await self._audit.record(
            tenant_id=request.tenant_id,
            actor=request.policy_input.request_actor,
            action="tool.invoke",
            resource_type="tool_registration",
            resource_id=f"{request.tool_name}@{request.tool_version}",
            decision=decision,
            reason=reason,
            trace_id=request.trace_id,
        )
