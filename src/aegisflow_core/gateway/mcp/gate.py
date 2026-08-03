"""Fail-closed authorization, registry, idempotency and adapter invocation gate."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Mapping, Protocol
from uuid import UUID

from aegisflow_core.gateway.policy.contextual import ContextualPolicy, PolicyInput, PolicyOutcome
from aegisflow_core.packs.delivery.contracts.idempotency import (
    Execute,
    FinalFailure,
    IdempotentCommand,
    InProgress,
    Reuse,
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


class ApprovalVerifier(Protocol):
    async def approved_by(
        self, *, approval_id: UUID, tenant_id: UUID, run_id: UUID, step_id: UUID
    ) -> str | None: ...


class IdempotencyGuard(Protocol):
    async def begin(self, command: IdempotentCommand) -> Execute | Reuse | InProgress | FinalFailure: ...
    async def complete(self, claim_token: UUID, result_reference: str) -> None: ...
    async def fail(self, claim_token: UUID, retryable: bool, reason: str) -> None: ...


class ApprovalRequiredError(PermissionError):
    """A registered operation requires a separate persisted Human approval."""


class InvocationInProgressError(RuntimeError):
    def __init__(self, retry_after_seconds: float) -> None:
        super().__init__("tool invocation is already in progress")
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class ReusedInvocation:
    result_reference: str


@dataclass(frozen=True, slots=True)
class InvocationRequest:
    tenant_id: UUID
    run_id: UUID
    step_id: UUID
    tool_name: str
    tool_version: str
    requested_scope: str
    arguments: dict[str, object]
    policy_input: PolicyInput
    trace_id: str
    idempotency_key: str
    approval_id: UUID | None = None


class McpInvocationGate:
    def __init__(
        self,
        *,
        registry: Registry,
        adapters: Mapping[str, Adapter],
        credential_resolver: CredentialResolver,
        audit: AuditRecorder,
        idempotency: IdempotencyGuard,
        approval_verifier: ApprovalVerifier,
        policy: ContextualPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._adapters = dict(adapters)
        self._credential_resolver = credential_resolver
        self._audit = audit
        self._idempotency = idempotency
        self._approval_verifier = approval_verifier
        self._policy = policy or ContextualPolicy()

    async def invoke(self, request: InvocationRequest) -> object:
        if request.policy_input.tenant_id != request.tenant_id:
            return await self._deny(request, "authorization.denied", "tenant_membership.mismatch")
        caller = self._policy.evaluate_caller(request.policy_input)
        if caller.outcome is not PolicyOutcome.ALLOW:
            return await self._deny(request, "authorization.denied", caller.reason_code)

        registration = await self._registry.get_active(
            request.tenant_id, request.tool_name, request.tool_version
        )
        if registration is None or getattr(registration, "tenant_id", None) != request.tenant_id:
            return await self._deny(request, "tool_registration_scope.unavailable")
        adapter = self._adapters.get(str(getattr(registration, "adapter_identifier", "")))
        if adapter is None:
            return await self._deny(request, "tool_registration_scope.unavailable")
        if (
            adapter.input_schema_hash != getattr(registration, "input_schema_hash", None)
            or adapter.output_schema_hash != getattr(registration, "output_schema_hash", None)
        ):
            return await self._deny(request, "tool_registration_scope.schema_mismatch")

        risk_level = str(getattr(registration, "risk_level", ""))
        approval_required = risk_level == "L3"
        approved_by: str | None = None
        if approval_required and request.approval_id is not None:
            approved_by = await self._approval_verifier.approved_by(
                approval_id=request.approval_id,
                tenant_id=request.tenant_id,
                run_id=request.run_id,
                step_id=request.step_id,
            )
        scopes = frozenset(str(value) for value in getattr(registration, "allowed_scopes", ()))
        policy_input = replace(
            request.policy_input,
            tenant_id=request.tenant_id,
            tool_registered=True,
            registered_scopes=scopes,
            requested_scope=request.requested_scope,
            risk_level=risk_level,
            approval_required=approval_required,
            approval_granted=approved_by is not None,
            approval_actor=approved_by,
        )
        decision = self._policy.evaluate(policy_input)
        if decision.outcome is PolicyOutcome.REQUIRE_APPROVAL:
            await self._record(request, PolicyOutcome.REQUIRE_APPROVAL.value, decision.reason_code)
            raise ApprovalRequiredError(decision.reason_code)
        if decision.outcome is PolicyOutcome.DENY:
            return await self._deny(request, decision.reason_code)
        if not adapter.validate_input(request.arguments):
            return await self._deny(request, "tool_registration_scope.input_schema_invalid")

        command = IdempotentCommand(
            scope="tool_call",
            idempotency_key=request.idempotency_key,
            arguments_hash=self._arguments_hash(request),
            tenant_id=request.tenant_id,
            run_id=request.run_id,
            step_id=request.step_id,
            tool_name=request.tool_name,
        )
        claim = await self._idempotency.begin(command)
        if isinstance(claim, Reuse):
            await self._record(request, "allow", "idempotency.reuse")
            return ReusedInvocation(claim.result_reference)
        if isinstance(claim, InProgress):
            await self._record(request, "deny", "idempotency.in_progress")
            raise InvocationInProgressError(claim.retry_after_seconds)
        if isinstance(claim, FinalFailure):
            return await self._deny(request, "idempotency.final_failure")

        try:
            credentials = await self._credential_resolver.resolve(adapter.identifier)
            result = await adapter.invoke(dict(request.arguments), credentials)
        except Exception as exc:
            await self._idempotency.fail(claim.claim_token, True, type(exc).__name__)
            await self._record(request, "deny", f"adapter.{type(exc).__name__}")
            raise RuntimeError("registered tool invocation failed") from None
        if not adapter.validate_output(result):
            await self._idempotency.fail(
                claim.claim_token, False, "output_schema_invalid"
            )
            await self._record(request, "deny", "tool_registration_scope.output_schema_invalid")
            raise RuntimeError("registered tool returned invalid output")
        result_reference = sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        await self._idempotency.complete(claim.claim_token, result_reference)
        await self._record(request, "allow", "policy.allowed")
        return result

    @staticmethod
    def _arguments_hash(request: InvocationRequest) -> str:
        value = {
            "tool": request.tool_name,
            "version": request.tool_version,
            "scope": request.requested_scope,
            "arguments": request.arguments,
        }
        return sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()

    async def _deny(
        self, request: InvocationRequest, exposed_reason: str, audit_reason: str | None = None
    ) -> object:
        await self._record(request, "deny", audit_reason or exposed_reason)
        raise PermissionError(exposed_reason)

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
