"""Lazy Temporal client adapter used by the Run application service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from aegisflow_core.runtime.temporal.client import (
    connect_temporal,
    signal_approval,
    signal_clarification,
    start_delivery_workflow,
)
from aegisflow_core.runtime.temporal.contracts import (
    DeliveryWorkflowInput,
    HumanSignal,
    RuntimeIdentity,
)

Connector = Callable[[str, str], Awaitable[Client]]


class TemporalRunGateway:
    """Start and signal only the workflow derived from a RuntimeIdentity."""

    def __init__(
        self,
        *,
        address: str,
        namespace: str,
        task_queue: str,
        connector: Connector = connect_temporal,
    ) -> None:
        if not all((address, namespace, task_queue)):
            raise ValueError("Temporal Run gateway configuration is required")
        self._address = address
        self._namespace = namespace
        self._task_queue = task_queue
        self._connector = connector
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    @property
    def client(self) -> Client | None:
        return self._client

    async def _get_client(self) -> Client:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                self._client = await self._connector(self._address, self._namespace)
        return self._client

    async def start(self, workflow_input: DeliveryWorkflowInput) -> None:
        client = await self._get_client()
        try:
            await start_delivery_workflow(
                client, workflow_input, task_queue=self._task_queue
            )
        except WorkflowAlreadyStartedError:
            # The deterministic workflow ID makes API retries safe.
            return

    async def signal_clarification(
        self, identity: RuntimeIdentity, signal: HumanSignal
    ) -> None:
        client = await self._get_client()
        handle = client.get_workflow_handle(identity.temporal_workflow_id)
        await signal_clarification(handle, signal)

    async def signal_approval(
        self, identity: RuntimeIdentity, signal: HumanSignal
    ) -> None:
        client = await self._get_client()
        handle = client.get_workflow_handle(identity.temporal_workflow_id)
        await signal_approval(handle, signal)
