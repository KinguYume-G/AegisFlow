"""AF-406 immutable registry and invocation-gate tests."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from aegisflow_core.control_plane.rbac import Capability
from aegisflow_core.gateway.mcp.gate import InvocationRequest, McpInvocationGate
from aegisflow_core.gateway.policy.contextual import PolicyInput


class Registration:
    def __init__(self) -> None:
        self.id = uuid4()
        self.tenant_id = uuid4()
        self.canonical_name = "repository_read"
        self.version = "1.0.0"
        self.adapter_identifier = "internal.github.read"
        self.input_schema_hash = "a" * 64
        self.output_schema_hash = "b" * 64
        self.allowed_scopes = ["repository:read"]
        self.risk_level = "L1"


class Registry:
    def __init__(self, registration: Registration | None) -> None:
        self.registration = registration

    async def get_active(self, tenant_id: UUID, name: str, version: str) -> Registration | None:
        value = self.registration
        if value and value.tenant_id == tenant_id and value.canonical_name == name and value.version == version:
            return value
        return None


class Adapter:
    identifier = "internal.github.read"
    input_schema_hash = "a" * 64
    output_schema_hash = "b" * 64

    def __init__(self) -> None:
        self.calls = 0
        self.credentials_seen: object | None = None
        self.output_valid = True
        self.fail = False

    def validate_input(self, arguments: dict[str, object]) -> bool:
        return set(arguments) == {"path"} and isinstance(arguments["path"], str)

    def validate_output(self, result: object) -> bool:
        return self.output_valid and isinstance(result, dict) and set(result) == {"path", "content"}

    async def invoke(self, arguments: dict[str, object], credentials: object | None) -> dict[str, object]:
        self.calls += 1
        self.credentials_seen = credentials
        if self.fail:
            raise ValueError("secret backend detail")
        return {"path": arguments["path"], "content": "fixture"}


class Resolver:
    async def resolve(self, adapter_identifier: str) -> object:
        assert adapter_identifier == "internal.github.read"
        return object()


class Audit:
    def __init__(self) -> None:
        self.decisions: list[str] = []

    async def record(self, **fields: object) -> None:
        self.decisions.append(str(fields["decision"]))


def base_policy(tenant_id: UUID) -> PolicyInput:
    return PolicyInput(
        tenant_id=tenant_id, membership_active=True,
        capabilities=frozenset({Capability.TOOL_INVOKE}), required_capability=Capability.TOOL_INVOKE,
        repository="o/r", allowed_repositories=frozenset({"o/r"}),
        environment="development", allowed_environments=frozenset({"development"}),
        tool_registered=True, registered_scopes=frozenset({"repository:read"}), requested_scope="repository:read",
        risk_level="L1", max_risk_level="L2", injection_severity="none",
        approval_required=False, approval_granted=False,
        request_actor="issuer|developer", approval_actor=None,
    )


def request(registration: Registration, **overrides: object) -> InvocationRequest:
    values: dict[str, object] = {
        "tenant_id": registration.tenant_id,
        "tool_name": registration.canonical_name,
        "tool_version": registration.version,
        "requested_scope": "repository:read",
        "arguments": {"path": "README.md"},
        "policy_input": base_policy(registration.tenant_id),
        "trace_id": "trace-1",
    }
    values.update(overrides)
    return InvocationRequest(**values)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_registered_authorized_tool_invokes_internal_adapter() -> None:
    registration = Registration(); adapter = Adapter(); audit = Audit()
    gate = McpInvocationGate(
        registry=Registry(registration), adapters={adapter.identifier: adapter},
        credential_resolver=Resolver(), audit=audit,
    )
    result = await gate.invoke(request(registration))
    assert result == {"path": "README.md", "content": "fixture"}
    assert adapter.calls == 1 and adapter.credentials_seen is not None
    assert audit.decisions == ["allow"]


@pytest.mark.parametrize("case", ["unknown", "scope", "schema", "policy", "tenant"])
@pytest.mark.anyio
async def test_denials_never_invoke_adapter(case: str) -> None:
    registration = Registration(); adapter = Adapter(); audit = Audit()
    registry = Registry(None if case == "unknown" else registration)
    value = request(registration)
    if case == "scope":
        value = replace(value, requested_scope="repository:write")
    elif case == "schema":
        value = replace(value, arguments={"token": "must-not-pass"})
    elif case == "policy":
        value = replace(value, policy_input=replace(value.policy_input, capabilities=frozenset()))
    elif case == "tenant":
        value = replace(value, tenant_id=uuid4())
    gate = McpInvocationGate(
        registry=registry, adapters={adapter.identifier: adapter},
        credential_resolver=Resolver(), audit=audit,
    )
    with pytest.raises(PermissionError):
        await gate.invoke(value)
    assert adapter.calls == 0
    assert audit.decisions == ["deny"]


@pytest.mark.anyio
async def test_schema_hash_output_and_adapter_failures_are_sanitized_and_audited() -> None:
    registration = Registration(); adapter = Adapter(); audit = Audit()
    gate = McpInvocationGate(registry=Registry(registration), adapters={adapter.identifier: adapter}, credential_resolver=Resolver(), audit=audit)
    registration.input_schema_hash = "c" * 64
    with pytest.raises(PermissionError, match="schema_mismatch"):
        await gate.invoke(request(registration))
    assert adapter.calls == 0

    registration.input_schema_hash = adapter.input_schema_hash
    adapter.output_valid = False
    with pytest.raises(RuntimeError, match="invalid output"):
        await gate.invoke(request(registration))
    adapter.output_valid = True; adapter.fail = True
    with pytest.raises(RuntimeError, match="invocation failed") as failure:
        await gate.invoke(request(registration))
    assert "backend detail" not in str(failure.value)
    assert audit.decisions == ["deny", "deny", "deny"]
