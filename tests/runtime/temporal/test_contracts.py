from dataclasses import replace
from uuid import uuid4

import pytest

from aegisflow_core.runtime.temporal.contracts import (
    AdvanceResult,
    DeliveryWorkflowInput,
    HumanSignal,
    RuntimeIdentity,
)


def identity() -> RuntimeIdentity:
    return RuntimeIdentity(str(uuid4()), str(uuid4()), str(uuid4()), 3)


def test_runtime_identity_has_stable_temporal_id() -> None:
    value = identity()
    assert value.temporal_workflow_id == f"aegisflow:{value.tenant_id}:{value.run_id}"


@pytest.mark.parametrize("field", ["tenant_id", "run_id", "trace_id"])
def test_runtime_identity_rejects_invalid_uuid(field: str) -> None:
    values = identity().__dict__ if hasattr(identity(), "__dict__") else {
        "tenant_id": str(uuid4()), "run_id": str(uuid4()),
        "trace_id": str(uuid4()), "workflow_version": 1,
    }
    values[field] = "not-a-uuid"
    with pytest.raises(ValueError):
        RuntimeIdentity(**values)


def test_wait_result_requires_reference() -> None:
    with pytest.raises(ValueError, match="wait_reference"):
        AdvanceResult("waiting_approval")
    with pytest.raises(ValueError, match="wait_reference"):
        AdvanceResult("completed", wait_reference="unexpected")


def test_signal_and_workflow_input_reject_empty_or_invalid_values() -> None:
    value = identity()
    with pytest.raises(ValueError):
        DeliveryWorkflowInput(value, approval_timeout_seconds=0)
    with pytest.raises(ValueError):
        HumanSignal("", "approval", value.tenant_id, value.run_id, "a", "approved", "u", "now")
    good = HumanSignal("s", "approval", value.tenant_id, value.run_id, "a", "approved", "u", "now")
    with pytest.raises(ValueError):
        replace(good, tenant_id="invalid")
