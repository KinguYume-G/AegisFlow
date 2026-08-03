"""Replay-safe outer Delivery workflow; all side effects are Activities."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from aegisflow_core.runtime.temporal.contracts import (
        AdvanceRequest,
        AdvanceResult,
        DeliveryWorkflowInput,
        HumanSignal,
        WorkflowResult,
    )
    from aegisflow_core.runtime.temporal.policies import standard_activity_policy


@workflow.defn(name="aegisflow.delivery.v1")
class DeliveryWorkflow:
    """Temporal owns lifetime and durable human waits, never agent state."""

    def __init__(self) -> None:
        self._input: DeliveryWorkflowInput | None = None
        self._pending: HumanSignal | None = None
        self._seen: dict[str, HumanSignal] = {}
        self._conflict: str | None = None

    @workflow.run
    async def run(self, workflow_input: DeliveryWorkflowInput) -> WorkflowResult:
        self._input = workflow_input
        request = AdvanceRequest(workflow_input.identity)
        policy = standard_activity_policy()
        while True:
            result = await workflow.execute_activity(
                "advance_gate1b",
                request,
                result_type=AdvanceResult,
                start_to_close_timeout=policy.start_to_close_timeout,
                schedule_to_close_timeout=policy.schedule_to_close_timeout,
                retry_policy=policy.retry_policy,
            )
            if result.status in {"completed", "failed"}:
                return WorkflowResult(result.status, result.result_reference)

            signal = await self._wait_for_human(result, workflow_input)
            request = AdvanceRequest(workflow_input.identity, signal)

    @workflow.signal(name="clarification")
    def clarification(self, signal: HumanSignal) -> None:
        self._accept_signal("clarification", signal)

    @workflow.signal(name="approval")
    def approval(self, signal: HumanSignal) -> None:
        self._accept_signal("approval", signal)

    async def _wait_for_human(
        self,
        result: AdvanceResult,
        workflow_input: DeliveryWorkflowInput,
    ) -> HumanSignal:
        expected_kind = result.wait_kind
        if expected_kind is None or result.wait_reference is None:
            raise ApplicationError(
                "activity returned an invalid wait state",
                type="invalid_input",
                non_retryable=True,
            )

        def ready() -> bool:
            return self._pending is not None or self._conflict is not None

        try:
            if expected_kind == "approval":
                await workflow.wait_condition(
                    ready,
                    timeout=timedelta(seconds=workflow_input.approval_timeout_seconds),
                    timeout_summary="approval wait expired",
                )
            else:
                await workflow.wait_condition(ready)
        except TimeoutError:
            return HumanSignal(
                signal_id=f"timeout:{result.wait_reference}",
                kind="approval",
                tenant_id=workflow_input.identity.tenant_id,
                run_id=workflow_input.identity.run_id,
                target_reference=result.wait_reference,
                value="expired",
                actor_reference="temporal",
                received_at=workflow.now().isoformat(),
            )

        if self._conflict is not None:
            raise ApplicationError(
                "conflicting or unauthorized human signal",
                type="invalid_input",
                non_retryable=True,
            )
        signal = self._pending
        self._pending = None
        if (
            signal is None
            or signal.kind != expected_kind
            or signal.tenant_id != workflow_input.identity.tenant_id
            or signal.run_id != workflow_input.identity.run_id
            or signal.target_reference != result.wait_reference
        ):
            raise ApplicationError(
                "human signal does not match the active wait",
                type="invalid_input",
                non_retryable=True,
            )
        return signal

    def _accept_signal(self, expected_kind: str, signal: HumanSignal) -> None:
        identity = self._input.identity if self._input is not None else None
        if signal.kind != expected_kind or (
            identity is not None
            and (
                signal.tenant_id != identity.tenant_id
                or signal.run_id != identity.run_id
            )
        ):
            self._conflict = "signal identity mismatch"
            return
        previous = self._seen.get(signal.signal_id)
        if previous is not None:
            if previous != signal:
                self._conflict = "signal id reused with different payload"
            return
        self._seen[signal.signal_id] = signal
        if self._pending is not None:
            self._conflict = "multiple unresolved human signals"
            return
        self._pending = signal
