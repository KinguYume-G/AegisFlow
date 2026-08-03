"""Activity adapters are the only bridge from Temporal to side effects."""

from __future__ import annotations

from typing import Protocol

from temporalio import activity

from aegisflow_core.runtime.temporal.contracts import AdvanceRequest, AdvanceResult
from aegisflow_core.runtime.temporal.policies import as_application_error
from aegisflow_core.runtime.observability import Correlation, operation_span


class DurableGraphPort(Protocol):
    async def advance(self, request: AdvanceRequest) -> AdvanceResult: ...


class DeliveryActivities:
    def __init__(self, graph: DurableGraphPort) -> None:
        self._graph = graph

    @activity.defn(name="advance_gate1b")
    async def advance_gate1b(self, request: AdvanceRequest) -> AdvanceResult:
        identity = request.identity
        with operation_span(
            "temporal.advance_gate1b",
            Correlation(
                tenant_id=identity.tenant_id,
                run_id=identity.run_id,
                trace_id=identity.trace_id,
                workflow_version=identity.workflow_version,
            ),
        ):
            try:
                return await self._graph.advance(request)
            except Exception as error:
                raise as_application_error(error) from None


class UnconfiguredGraphPort:
    """Allows a worker to start while failing any unconfigured task loudly."""

    async def advance(self, request: AdvanceRequest) -> AdvanceResult:
        del request
        raise RuntimeError("durable Gate 1B graph adapter is not configured")
