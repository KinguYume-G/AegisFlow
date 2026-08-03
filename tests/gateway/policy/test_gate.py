from decimal import Decimal
from aegisflow_core.gateway.policy.config import PolicyConfig
from aegisflow_core.gateway.policy.gate import ExecutionScope, PolicyGate, RepositoryTarget
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement


def make_plan(tool="repository_read", risk="L1"):
    return Plan(summary="x",tasks=[PlanTask(description="x",required_tools=[ToolRequirement(tool_name=tool)])],risk_level=risk,budget_estimate=Measurement(status="measured",value=Decimal(1),unit="step"),reasoner_id="x")


def test_policy_fixed_order_and_default_deny() -> None:
    gate = PolicyGate(PolicyConfig(allowed_repository="o/r",enabled_tool_capabilities=frozenset({"repository_read"}),max_allowed_risk_level="L1"))
    assert gate.evaluate(make_plan("repository_write","L3"),ExecutionScope(RepositoryTarget("wrong","repo"))).violated_rule == "repository_scope"
    assert gate.evaluate(make_plan("repository_write","L3"),ExecutionScope(RepositoryTarget("o","r"))).violated_rule == "tool_capability_scope"
    assert gate.evaluate(make_plan(risk="L3"),ExecutionScope(RepositoryTarget("o","r"))).violated_rule == "risk_ceiling"
    assert gate.evaluate(make_plan(),ExecutionScope(RepositoryTarget("o","r"))).decision == "allow"
