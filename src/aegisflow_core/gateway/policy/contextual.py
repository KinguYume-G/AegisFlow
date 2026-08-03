"""Versioned, deterministic and explainable contextual authorization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal
from uuid import UUID

from aegisflow_core.control_plane.rbac import Capability

RiskLevel = Literal["L1", "L2", "L3"]
InjectionSeverity = Literal["none", "low", "medium", "high", "unknown"]
_RISK: dict[RiskLevel, int] = {"L1": 1, "L2": 2, "L3": 3}


class PolicyOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class PolicyInput:
    """Trusted facts only; prompts and model output deliberately have no field."""

    tenant_id: UUID | None
    membership_active: bool
    capabilities: frozenset[Capability]
    required_capability: Capability
    repository: str
    allowed_repositories: frozenset[str]
    environment: str
    allowed_environments: frozenset[str]
    tool_registered: bool
    registered_scopes: frozenset[str]
    requested_scope: str
    risk_level: RiskLevel
    max_risk_level: RiskLevel
    injection_severity: InjectionSeverity
    approval_required: bool
    approval_granted: bool
    request_actor: str
    approval_actor: str | None
    schema_version: Literal[1] = 1
    contradictory_evidence: bool = False


@dataclass(frozen=True, slots=True)
class ContextualPolicyDecision:
    outcome: PolicyOutcome
    rule_code: str
    reason_code: str
    schema_version: Literal[1] = 1


class ContextualPolicy:
    """Evaluate trusted inputs in the frozen M4 rule order."""

    @staticmethod
    def _decision(outcome: PolicyOutcome, rule: str, reason: str) -> ContextualPolicyDecision:
        return ContextualPolicyDecision(outcome, rule, f"{rule}.{reason}")

    def evaluate(self, value: PolicyInput) -> ContextualPolicyDecision:
        if value.contradictory_evidence:
            return self._decision(PolicyOutcome.DENY, "tenant_membership", "contradictory_evidence")
        if not isinstance(value.tenant_id, UUID) or not value.membership_active:
            return self._decision(PolicyOutcome.DENY, "tenant_membership", "missing")
        if value.required_capability not in value.capabilities:
            return self._decision(PolicyOutcome.DENY, "rbac_capability", "missing")
        allowed_repositories = {item.casefold() for item in value.allowed_repositories}
        if not value.repository.strip() or value.repository.casefold() not in allowed_repositories:
            return self._decision(PolicyOutcome.DENY, "repository_environment", "repository_denied")
        if not value.environment.strip() or value.environment.casefold() not in {item.casefold() for item in value.allowed_environments}:
            return self._decision(PolicyOutcome.DENY, "repository_environment", "environment_denied")
        if not value.tool_registered:
            return self._decision(PolicyOutcome.DENY, "tool_registration_scope", "unregistered")
        if not value.requested_scope.strip() or value.requested_scope not in value.registered_scopes:
            return self._decision(PolicyOutcome.DENY, "tool_registration_scope", "scope_denied")
        if value.injection_severity not in {"none", "low", "medium"}:
            return self._decision(PolicyOutcome.DENY, "risk_injection", "unsafe_content")
        requested_risk = _RISK.get(value.risk_level)
        maximum_risk = _RISK.get(value.max_risk_level)
        if requested_risk is None or maximum_risk is None:
            return self._decision(PolicyOutcome.DENY, "risk_injection", "invalid_risk")
        if requested_risk > maximum_risk:
            return self._decision(PolicyOutcome.DENY, "risk_injection", "risk_ceiling")
        if value.approval_required and not value.approval_granted:
            return self._decision(PolicyOutcome.REQUIRE_APPROVAL, "approval_evidence", "required")
        if value.approval_granted and (
            value.approval_actor is None or value.approval_actor == value.request_actor
        ):
            return self._decision(PolicyOutcome.DENY, "approval_evidence", "actor_separation")
        return ContextualPolicyDecision(PolicyOutcome.ALLOW, "policy", "policy.allowed")
