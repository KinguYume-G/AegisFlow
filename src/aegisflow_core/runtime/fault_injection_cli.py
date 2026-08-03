"""Run the real 20-iteration Temporal worker-loss matrix."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

from temporalio.client import Client, WorkflowHandle

from aegisflow_core.runtime.fault_injection import (
    FaultInjectionHarness,
    FaultIteration,
    FaultScenario,
)
from aegisflow_core.runtime.fault_probe import FaultProbeInput, FaultProbeWorkflow


class TemporalProcessFaultDriver:
    def __init__(self, client: Client, root: Path, task_queue: str) -> None:
        self._client = client
        self._root = root
        self._task_queue = task_queue

    async def run_iteration(
        self, scenario: FaultScenario, iteration: int
    ) -> FaultIteration:
        run_reference = f"{scenario}-{iteration}-{uuid4().hex}"
        worker = await self._start_worker()
        handle: WorkflowHandle | None = None
        started = monotonic()
        lost_signals = 0
        try:
            print(f"fault_iteration_start scenario={scenario} iteration={iteration}", flush=True)
            handle = await self._client.start_workflow(
                FaultProbeWorkflow.run,
                FaultProbeInput(scenario, run_reference),
                id=f"aegisflow:gate2-fault:{run_reference}",
                task_queue=self._task_queue,
                task_timeout=timedelta(seconds=2),
            )
            if scenario == "activity":
                await self._wait_for_file(self._root / f"{run_reference}.started")
            else:
                expected = (
                    "completion_gap"
                    if scenario == "completion_gap"
                    else f"waiting_{scenario}"
                )
                await self._wait_for_phase(handle, expected)
            await _stop_worker(worker)
            started = monotonic()
            if scenario in {"clarification", "approval"}:
                await handle.signal(scenario)
            elif scenario == "completion_gap":
                await handle.signal("finish")
            worker = await self._start_worker()
            await asyncio.wait_for(handle.result(), timeout=20)
            terminal_status = "completed"
        except Exception as error:
            terminal_status = "failed"
            lost_signals = int(scenario in {"clarification", "approval"})
            print(
                f"fault_iteration_failed scenario={scenario} iteration={iteration} "
                f"error_type={type(error).__name__}",
                flush=True,
            )
        finally:
            await _stop_worker(worker)
        effect_count = int((self._root / f"{run_reference}.effect").exists())
        result = FaultIteration(
            scenario=scenario,
            iteration=iteration,
            run_reference=run_reference,
            recovery_ms=(monotonic() - started) * 1000,
            terminal_status=terminal_status,
            duplicate_effects=max(0, effect_count - 1),
            lost_signals=lost_signals,
            compensation_status="not_required",
        )
        print(
            f"fault_iteration_end scenario={scenario} iteration={iteration} "
            f"status={terminal_status}",
            flush=True,
        )
        return result

    async def _start_worker(self) -> asyncio.subprocess.Process:
        environment = os.environ.copy()
        environment["AEGISFLOW_FAULT_EVIDENCE_ROOT"] = str(self._root)
        environment["AEGISFLOW_FAULT_TASK_QUEUE"] = self._task_queue
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "aegisflow_core.runtime.fault_probe_worker",
            env=environment,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.5)
        if process.returncode is not None:
            error = await process.stderr.read() if process.stderr else b""
            raise RuntimeError(
                f"fault worker failed to start: {error.decode('utf-8', 'replace')[:500]}"
            )
        return process

    async def _wait_for_file(self, path: Path) -> None:
        for _ in range(100):
            if path.exists():
                return
            await asyncio.sleep(0.1)
        raise TimeoutError("fault Activity did not reach its marker")

    @staticmethod
    async def _wait_for_phase(handle: WorkflowHandle, expected: str) -> None:
        for _ in range(100):
            if await handle.query("phase") == expected:
                return
            await asyncio.sleep(0.1)
        raise TimeoutError(f"fault workflow did not reach {expected}")


async def _stop_worker(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    # Fault injection models an abrupt worker loss, not graceful deployment drain.
    process.kill()
    await asyncio.wait_for(process.wait(), timeout=5)


async def run(
    root: Path, output: Path, scenario: FaultScenario | None = None
) -> int:
    root = root.resolve()
    if not root.name.startswith("aegisflow-fault-"):
        raise ValueError("work root must use the aegisflow-fault- prefix")
    root.mkdir(parents=True, exist_ok=True)
    address = os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233"
    namespace = os.environ.get("TEMPORAL_NAMESPACE") or "default"
    task_queue = f"aegisflow-gate2-fault-{uuid4().hex}"
    client = await Client.connect(address, namespace=namespace)
    driver = TemporalProcessFaultDriver(client, root, task_queue)
    if scenario is not None:
        result = await driver.run_iteration(scenario, 1)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(result), sort_keys=True) + "\n", encoding="utf-8")
        return 0 if result.terminal_status != "failed" else 1
    report = await FaultInjectionHarness(driver).run()
    report.write_jsonl(output)
    print(
        f"iterations={len(report.iterations)} accepted={str(report.accepted).lower()} "
        f"p50_ms={report.recovery_p50_ms:.2f} p95_ms={report.recovery_p95_ms:.2f}"
    )
    return 0 if report.accepted else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        choices=("activity", "clarification", "approval", "completion_gap"),
    )
    arguments = parser.parse_args()
    raise SystemExit(
        asyncio.run(run(arguments.work_root, arguments.output, arguments.scenario))
    )


if __name__ == "__main__":
    main()
