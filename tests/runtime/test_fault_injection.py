from pathlib import Path

import pytest

from aegisflow_core.runtime.fault_injection import (
    FaultInjectionHarness,
    FaultIteration,
)


class FakeDriver:
    def __init__(self, *, duplicate_at: tuple[str, int] | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self._duplicate_at = duplicate_at

    async def run_iteration(self, scenario: str, iteration: int) -> FaultIteration:
        self.calls.append((scenario, iteration))
        duplicate = int(self._duplicate_at == (scenario, iteration))
        return FaultIteration(
            scenario=scenario,  # type: ignore[arg-type]
            iteration=iteration,
            run_reference=f"{scenario}:{iteration}",
            recovery_ms=float(len(self.calls)),
            terminal_status="completed",
            duplicate_effects=duplicate,
            lost_signals=0,
            compensation_status="not_required",
        )


@pytest.mark.asyncio
async def test_fixed_matrix_produces_exactly_twenty_unique_results() -> None:
    driver = FakeDriver()
    report = await FaultInjectionHarness(driver).run()
    assert len(report.iterations) == 20
    assert len(set(driver.calls)) == 20
    assert report.recovery_p50_ms == 10
    assert report.recovery_p95_ms == 19
    assert report.accepted


@pytest.mark.asyncio
async def test_duplicate_effect_measurement_fails_acceptance() -> None:
    report = await FaultInjectionHarness(
        FakeDriver(duplicate_at=("completion_gap", 5))
    ).run()
    assert not report.accepted


@pytest.mark.asyncio
async def test_driver_cannot_return_mismatched_evidence() -> None:
    class BadDriver:
        async def run_iteration(self, scenario: str, iteration: int) -> FaultIteration:
            return FaultIteration(
                scenario="activity",
                iteration=iteration,
                run_reference="bad",
                recovery_ms=1,
                terminal_status="completed",
                duplicate_effects=0,
                lost_signals=0,
                compensation_status="not_required",
            )

    with pytest.raises(ValueError, match="mismatched"):
        await FaultInjectionHarness(BadDriver()).run()


@pytest.mark.asyncio
async def test_jsonl_is_canonical_and_contains_twenty_lines(tmp_path: Path) -> None:
    report = await FaultInjectionHarness(FakeDriver()).run()
    output = tmp_path / "evidence" / "iterations.jsonl"
    report.write_jsonl(output)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    assert lines[0].startswith('{"compensation_status":')


def test_gate2_matrix_cannot_be_reduced() -> None:
    with pytest.raises(ValueError, match="exactly five"):
        FaultInjectionHarness(FakeDriver(), repetitions=4)
