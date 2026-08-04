"""Fail-closed comparison for versioned evaluation reports."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aegisflow_core.evaluation.reporting import EvaluationReport, REPORT_METRICS


class RegressionThreshold(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str
    direction: Literal["higher_is_better", "lower_is_better"]
    max_relative_regression: Decimal = Field(ge=0, le=1)


class RegressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    thresholds: tuple[RegressionThreshold, ...]

    @model_validator(mode="after")
    def metric_names_are_unique(self) -> "RegressionConfig":
        names = [threshold.metric for threshold in self.thresholds]
        if len(names) != len(set(names)):
            raise ValueError("regression thresholds must be unique")
        if set(names) != set(REPORT_METRICS):
            raise ValueError("regression thresholds must cover every report metric")
        return self


class RegressionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str
    passed: bool
    baseline: Decimal | None
    candidate: Decimal | None
    allowed_boundary: Decimal | None
    reason: str


class RegressionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    passed: bool
    evidence_scope: Literal["measured_evaluation", "deterministic_gate_fixture"]
    baseline_prompt_version: str
    candidate_prompt_version: str
    decisions: tuple[RegressionDecision, ...]


def compare_reports(
    baseline: EvaluationReport,
    candidate: EvaluationReport,
    config: RegressionConfig,
) -> RegressionResult:
    compatible = (
        baseline.subject == candidate.subject
        and baseline.evidence_scope == candidate.evidence_scope
        and baseline.dataset_hash == candidate.dataset_hash
        and baseline.controls_hash == candidate.controls_hash
    )
    decisions: list[RegressionDecision] = []
    if not compatible:
        decisions.append(
            RegressionDecision(
                metric="report_compatibility",
                passed=False,
                baseline=None,
                candidate=None,
                allowed_boundary=None,
                reason="subject, evidence scope, dataset hash, or controls hash differ",
            )
        )

    for threshold in config.thresholds:
        try:
            before = baseline.metric(threshold.metric)
            after = candidate.metric(threshold.metric)
        except KeyError:
            decisions.append(
                RegressionDecision(
                    metric=threshold.metric,
                    passed=False,
                    baseline=None,
                    candidate=None,
                    allowed_boundary=None,
                    reason="required metric is missing",
                )
            )
            continue
        if (
            before.status != "measured"
            or after.status != "measured"
            or before.unit != after.unit
        ):
            decisions.append(
                RegressionDecision(
                    metric=threshold.metric,
                    passed=False,
                    baseline=before.value,
                    candidate=after.value,
                    allowed_boundary=None,
                    reason="metric is unavailable or units differ",
                )
            )
            continue
        assert before.value is not None and after.value is not None
        tolerance = threshold.max_relative_regression
        if threshold.direction == "higher_is_better":
            boundary = before.value * (Decimal(1) - tolerance)
            passed = after.value >= boundary
        else:
            boundary = before.value * (Decimal(1) + tolerance)
            passed = after.value <= boundary
        decisions.append(
            RegressionDecision(
                metric=threshold.metric,
                passed=passed,
                baseline=before.value,
                candidate=after.value,
                allowed_boundary=boundary,
                reason="within threshold" if passed else "regression exceeds threshold",
            )
        )

    return RegressionResult(
        passed=compatible and all(decision.passed for decision in decisions),
        evidence_scope=baseline.evidence_scope,
        baseline_prompt_version=baseline.prompt_version,
        candidate_prompt_version=candidate.prompt_version,
        decisions=tuple(decisions),
    )


def _load(path: Path, model: type[BaseModel]) -> BaseModel:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare evaluation reports")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    baseline = _load(args.baseline, EvaluationReport)
    candidate = _load(args.candidate, EvaluationReport)
    config = _load(args.thresholds, RegressionConfig)
    assert isinstance(baseline, EvaluationReport)
    assert isinstance(candidate, EvaluationReport)
    assert isinstance(config, RegressionConfig)
    result = compare_reports(baseline, candidate, config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
