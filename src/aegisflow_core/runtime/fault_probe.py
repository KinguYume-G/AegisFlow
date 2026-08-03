"""Temporal probe used only by the bounded Gate 2 fault-injection harness."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@dataclass(frozen=True, slots=True)
class FaultProbeInput:
    scenario: Literal["activity", "clarification", "approval", "completion_gap"]
    run_reference: str


@dataclass(frozen=True, slots=True)
class FaultEffectInput:
    run_reference: str
    delay_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class FaultProbeResult:
    effect_reference: str


@activity.defn(name="gate2_fault_effect")
async def gate2_fault_effect(effect: FaultEffectInput) -> str:
    import os

    root = _validated_root(os.environ.get("AEGISFLOW_FAULT_EVIDENCE_ROOT", ""))
    started = root / f"{effect.run_reference}.started"
    marker = root / f"{effect.run_reference}.effect"
    activity.heartbeat(effect.run_reference)
    await asyncio.sleep(0.2)
    started.write_text("started\n", encoding="utf-8")
    try:
        with marker.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("owned-effect\n")
    except FileExistsError:
        return str(marker)

    remaining = effect.delay_seconds
    while remaining > 0:
        activity.heartbeat(effect.run_reference)
        interval = min(0.2, remaining)
        await asyncio.sleep(interval)
        remaining -= interval
    return str(marker)


@workflow.defn(name="aegisflow.gate2-fault-probe.v1")
class FaultProbeWorkflow:
    def __init__(self) -> None:
        self._phase = "starting"
        self._released = False

    @workflow.run
    async def run(self, probe: FaultProbeInput) -> FaultProbeResult:
        if probe.scenario in {"clarification", "approval"}:
            self._phase = f"waiting_{probe.scenario}"
            await workflow.wait_condition(lambda: self._released)

        delay = 5.0 if probe.scenario == "activity" else 0.0
        self._phase = "activity"
        effect_reference = await workflow.execute_activity(
            gate2_fault_effect,
            FaultEffectInput(probe.run_reference, delay),
            start_to_close_timeout=timedelta(seconds=3),
            heartbeat_timeout=timedelta(seconds=1),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(milliseconds=250),
                maximum_interval=timedelta(seconds=1),
                maximum_attempts=5,
            ),
        )
        if probe.scenario == "completion_gap":
            self._phase = "completion_gap"
            await workflow.wait_condition(lambda: self._released)
        self._phase = "completed"
        return FaultProbeResult(effect_reference)

    @workflow.signal(name="clarification")
    def clarification(self) -> None:
        self._released = True

    @workflow.signal(name="approval")
    def approval(self) -> None:
        self._released = True

    @workflow.signal(name="finish")
    def finish(self) -> None:
        self._released = True

    @workflow.query(name="phase")
    def phase(self) -> str:
        return self._phase


def _validated_root(value: str) -> Path:
    if not value:
        raise RuntimeError("AEGISFLOW_FAULT_EVIDENCE_ROOT is required")
    root = Path(value).resolve()
    if not root.name.startswith("aegisflow-fault-"):
        raise RuntimeError("fault evidence root must use the aegisflow-fault- prefix")
    root.mkdir(parents=True, exist_ok=True)
    return root
