from decimal import Decimal
from pathlib import Path
import pytest

from aegisflow_core.gateway.sandbox.runner import InMemorySandboxRunner, SandboxResult, TestProfile as SandboxTestProfile
from aegisflow_core.packs.delivery.contracts.measurement import Measurement
from aegisflow_core.packs.delivery.contracts.plan import Plan, PlanTask, ToolRequirement
from aegisflow_core.packs.delivery.executor.agent import ExecutorAgent, ExecutorNodeError
from aegisflow_core.packs.delivery.executor.fakes import DeterministicPatchReasoner


def plan():
    return Plan(summary="change",tasks=[PlanTask(description="edit",required_tools=[ToolRequirement(tool_name="sandbox_execute")])],risk_level="L2",budget_estimate=Measurement(status="measured",value=Decimal("1"),unit="step"),reasoner_id="fixture")


def test_executor_applies_bounded_patch_and_returns_structured_evidence(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("old\n")
    runner = InMemorySandboxRunner(SandboxResult(status="completed",exit_code=0,stdout="1 passed",stderr="",duration_ms=1,workspace_output=tmp_path))
    result = ExecutorAgent(DeterministicPatchReasoner({"change":{"a.py":"new\n"}})).execute(plan(),tmp_path,runner,SandboxTestProfile(name="python_pytest",image="python@sha256:"+"a"*64))
    assert result.status == "completed" and result.changed_files == ["a.py"] and "-old" in result.patch
    assert result.test_outcome.passed_count.status == "not_available"


def test_executor_rejects_path_escape(tmp_path: Path) -> None:
    runner = InMemorySandboxRunner(SandboxResult(status="completed",exit_code=0,stdout="",stderr="",duration_ms=1,workspace_output=tmp_path))
    with pytest.raises(ExecutorNodeError) as error:
        ExecutorAgent(DeterministicPatchReasoner({"change":{"../escape":"bad"}})).execute(plan(),tmp_path,runner,SandboxTestProfile(name="python_pytest",image="python@sha256:"+"a"*64))
    assert error.value.stage == "apply"
