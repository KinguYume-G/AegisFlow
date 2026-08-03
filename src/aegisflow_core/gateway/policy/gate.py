"""Default-deny policy rules with fixed evaluation order."""

from dataclasses import dataclass
from aegisflow_core.gateway.policy.config import PolicyConfig
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.contracts.policy_decision import PolicyDecision
from aegisflow_core.gateway.policy.injection import Severity

_RISK = {"L1": 1, "L2": 2, "L3": 3}


@dataclass(frozen=True, slots=True)
class RepositoryTarget:
    owner: str
    repository: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"


@dataclass(frozen=True, slots=True)
class ExecutionScope:
    repository_target: RepositoryTarget


class PolicyGate:
    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    def evaluate(
        self,
        plan: Plan,
        scope: ExecutionScope,
        *,
        injection_severity: Severity = "none",
    ) -> PolicyDecision:
        repository = scope.repository_target.full_name
        if repository.casefold() != self._config.allowed_repository.casefold():
            return PolicyDecision(decision="deny", violated_rule="repository_scope",
                                  reasons=[f"repository {repository!r} is not allowed"])
        requested = {tool.tool_name for task in plan.tasks for tool in task.required_tools}
        disallowed = sorted(requested - self._config.enabled_tool_capabilities)
        if disallowed:
            return PolicyDecision(decision="deny", violated_rule="tool_capability_scope",
                                  reasons=[f"capability {name!r} is not enabled" for name in disallowed])
        if _RISK[plan.risk_level] > _RISK[self._config.max_allowed_risk_level]:
            return PolicyDecision(decision="deny", violated_rule="risk_ceiling",
                                  reasons=[f"risk level {plan.risk_level} exceeds configured maximum"])
        if injection_severity == "unknown":
            return PolicyDecision(
                decision="deny",
                violated_rule="prompt_injection_unknown",
                reasons=["untrusted context classification is unavailable"],
            )
        side_effect_capabilities = {
            "repository_write",
            "test_execute",
            "sandbox_execute",
            "pull_request_write",
        }
        if injection_severity == "high" and (
            plan.risk_level in {"L2", "L3"} or bool(requested & side_effect_capabilities)
        ):
            return PolicyDecision(
                decision="deny",
                violated_rule="prompt_injection",
                reasons=["high-severity untrusted context cannot drive side effects"],
            )
        return PolicyDecision(decision="allow", reasons=[])
