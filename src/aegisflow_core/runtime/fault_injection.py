"""Reproducible Gate 2 fault-injection evidence contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Literal, Protocol


FaultScenario = Literal[
    "activity", "clarification", "approval", "completion_gap"
]
FAULT_SCENARIOS: tuple[FaultScenario, ...] = (
    "activity",
    "clarification",
    "approval",
    "completion_gap",
)


@dataclass(frozen=True, slots=True)
class FaultIteration:
    scenario: FaultScenario
    iteration: int
    run_reference: str
    recovery_ms: float
    terminal_status: Literal["completed", "compensated", "failed"]
    duplicate_effects: int
    lost_signals: int
    compensation_status: str

    def __post_init__(self) -> None:
        if self.iteration < 1 or not self.run_reference:
            raise ValueError("fault iteration identity is invalid")
        if self.recovery_ms < 0 or self.duplicate_effects < 0 or self.lost_signals < 0:
            raise ValueError("fault measurements must be non-negative")
        if not self.compensation_status:
            raise ValueError("compensation_status is required")


@dataclass(frozen=True, slots=True)
class FaultReport:
    iterations: tuple[FaultIteration, ...]
    recovery_p50_ms: float
    recovery_p95_ms: float

    @property
    def accepted(self) -> bool:
        return (
            len(self.iterations) == 20
            and all(item.terminal_status != "failed" for item in self.iterations)
            and sum(item.duplicate_effects for item in self.iterations) == 0
            and sum(item.lost_signals for item in self.iterations) == 0
        )

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for item in self.iterations:
                stream.write(json.dumps(asdict(item), sort_keys=True) + "\n")


class FaultDriver(Protocol):
    async def run_iteration(
        self, scenario: FaultScenario, iteration: int
    ) -> FaultIteration: ...


class FaultInjectionHarness:
    """Execute the fixed four-by-five matrix and reject incomplete evidence."""

    def __init__(self, driver: FaultDriver, *, repetitions: int = 5) -> None:
        if repetitions != 5:
            raise ValueError("Gate 2 requires exactly five repetitions per scenario")
        self._driver = driver
        self._repetitions = repetitions

    async def run(self) -> FaultReport:
        results: list[FaultIteration] = []
        identities: set[tuple[str, int]] = set()
        for scenario in FAULT_SCENARIOS:
            for iteration in range(1, self._repetitions + 1):
                result = await self._driver.run_iteration(scenario, iteration)
                if result.scenario != scenario or result.iteration != iteration:
                    raise ValueError("fault driver returned mismatched evidence")
                identity = (result.scenario, result.iteration)
                if identity in identities:
                    raise ValueError("duplicate fault iteration evidence")
                identities.add(identity)
                results.append(result)
        values = sorted(item.recovery_ms for item in results)
        return FaultReport(
            iterations=tuple(results),
            recovery_p50_ms=_nearest_rank(values, 0.50),
            recovery_p95_ms=_nearest_rank(values, 0.95),
        )


def _nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("at least one recovery measurement is required")
    index = max(0, math.ceil(percentile * len(values)) - 1)
    return values[index]
