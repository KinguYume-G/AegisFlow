"""AF-404 deterministic contextual-policy tests."""

from uuid import uuid4

import pytest

from aegisflow_core.control_plane.rbac import Capability
from aegisflow_core.gateway.policy.contextual import (
    ContextualPolicy,
    PolicyInput,
    PolicyOutcome,
)


def policy_input(**overrides: object) -> PolicyInput:
    values: dict[str, object] = {
        "tenant_id": uuid4(),
        "membership_active": True,
        "capabilities": frozenset({Capability.TOOL_INVOKE}),
        "required_capability": Capability.TOOL_INVOKE,
        "repository": "KinguYume-G/AegisFlow",
        "allowed_repositories": frozenset({"kinguyume-g/aegisflow"}),
        "environment": "development",
        "allowed_environments": frozenset({"development"}),
        "tool_registered": True,
        "registered_scopes": frozenset({"repository:read"}),
        "requested_scope": "repository:read",
        "risk_level": "L1",
        "max_risk_level": "L2",
        "injection_severity": "none",
        "approval_required": False,
        "approval_granted": False,
        "request_actor": "issuer|developer",
        "approval_actor": None,
    }
    values.update(overrides)
    return PolicyInput(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("overrides", "rule"),
    [
        ({"tenant_id": None}, "tenant_membership"),
        ({"membership_active": False}, "tenant_membership"),
        ({"capabilities": frozenset()}, "rbac_capability"),
        ({"repository": "other/repo"}, "repository_environment"),
        ({"environment": "production"}, "repository_environment"),
        ({"tool_registered": False}, "tool_registration_scope"),
        ({"requested_scope": "repository:write"}, "tool_registration_scope"),
        ({"risk_level": "L3"}, "risk_injection"),
        ({"injection_severity": "unknown"}, "risk_injection"),
        ({"risk_level": "L9"}, "risk_injection"),
        ({"contradictory_evidence": True}, "tenant_membership"),
    ],
)
def test_policy_default_denies_in_stable_order(overrides: dict[str, object], rule: str) -> None:
    decision = ContextualPolicy().evaluate(policy_input(**overrides))
    assert decision.outcome is PolicyOutcome.DENY
    assert decision.rule_code == rule
    assert decision.reason_code.startswith(f"{rule}.")


def test_policy_requires_separate_human_approval_then_allows() -> None:
    required = ContextualPolicy().evaluate(policy_input(approval_required=True))
    assert required.outcome is PolicyOutcome.REQUIRE_APPROVAL
    assert required.reason_code == "approval_evidence.required"

    self_approval = ContextualPolicy().evaluate(
        policy_input(
            approval_required=True,
            approval_granted=True,
            approval_actor="issuer|developer",
        )
    )
    assert self_approval.outcome is PolicyOutcome.DENY
    assert self_approval.reason_code == "approval_evidence.actor_separation"

    allowed = ContextualPolicy().evaluate(
        policy_input(
            approval_required=True,
            approval_granted=True,
            approval_actor="issuer|reviewer",
        )
    )
    assert allowed.outcome is PolicyOutcome.ALLOW
    assert allowed.reason_code == "policy.allowed"


def test_high_injection_allows_read_but_denies_write_or_high_risk() -> None:
    read = ContextualPolicy().evaluate(policy_input(injection_severity="high"))
    write = ContextualPolicy().evaluate(
        policy_input(
            injection_severity="high",
            risk_level="L1",
            registered_scopes=frozenset({"repository:write"}),
            requested_scope="repository:write",
        )
    )
    high_risk_read = ContextualPolicy().evaluate(
        policy_input(injection_severity="high", risk_level="L2")
    )

    assert read.outcome is PolicyOutcome.ALLOW
    assert write.outcome is PolicyOutcome.DENY
    assert write.reason_code == "risk_injection.unsafe_content"
    assert high_risk_read.outcome is PolicyOutcome.DENY


def test_policy_input_is_frozen_and_has_no_prompt_override_field() -> None:
    value = policy_input()
    with pytest.raises(AttributeError):
        value.environment = "production"  # type: ignore[misc]
    assert "prompt" not in value.__dataclass_fields__
