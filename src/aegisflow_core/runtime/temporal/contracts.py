"""Plain deterministic contracts stored in Temporal Event History."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


WaitKind = Literal["clarification", "approval"]
AdvanceStatus = Literal["completed", "failed", "waiting_clarification", "waiting_approval"]


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    tenant_id: str
    run_id: str
    trace_id: str
    workflow_version: int

    def __post_init__(self) -> None:
        UUID(self.tenant_id)
        UUID(self.run_id)
        UUID(self.trace_id)
        if self.workflow_version < 1:
            raise ValueError("workflow_version must be positive")

    @property
    def temporal_workflow_id(self) -> str:
        return f"aegisflow:{self.tenant_id}:{self.run_id}"


@dataclass(frozen=True, slots=True)
class HumanSignal:
    signal_id: str
    kind: WaitKind
    tenant_id: str
    run_id: str
    target_reference: str
    value: str
    actor_reference: str
    received_at: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.signal_id,
                self.target_reference,
                self.value,
                self.actor_reference,
                self.received_at,
            )
        ):
            raise ValueError("human signal fields must be non-empty")
        UUID(self.tenant_id)
        UUID(self.run_id)


@dataclass(frozen=True, slots=True)
class DeliveryWorkflowInput:
    identity: RuntimeIdentity
    approval_timeout_seconds: int = 604800

    def __post_init__(self) -> None:
        if self.approval_timeout_seconds < 1:
            raise ValueError("approval_timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class AdvanceRequest:
    identity: RuntimeIdentity
    signal: HumanSignal | None = None


@dataclass(frozen=True, slots=True)
class AdvanceResult:
    status: AdvanceStatus
    result_reference: str | None = None
    wait_reference: str | None = None

    def __post_init__(self) -> None:
        waiting = self.status in {"waiting_clarification", "waiting_approval"}
        if waiting != (self.wait_reference is not None):
            raise ValueError("waiting results require exactly one wait_reference")

    @property
    def wait_kind(self) -> WaitKind | None:
        if self.status == "waiting_clarification":
            return "clarification"
        if self.status == "waiting_approval":
            return "approval"
        return None


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    status: Literal["completed", "failed"]
    result_reference: str | None = None
