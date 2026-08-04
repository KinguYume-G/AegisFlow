"""AF-507 fail-closed regression gate tests."""

from decimal import Decimal
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from aegisflow_core.evaluation.regression import (
    RegressionConfig,
    RegressionThreshold,
    compare_reports,
    main,
)
from aegisflow_core.evaluation.reporting import EvaluationReport

DATA = Path(__file__).parents[2] / "src" / "aegisflow_core" / "evaluation" / "data"


def load(name: str, model: type[EvaluationReport] | type[RegressionConfig]):
    return model.model_validate_json((DATA / name).read_text(encoding="utf-8"))


def test_approved_candidate_passes_zero_and_ten_percent_thresholds() -> None:
    result = compare_reports(
        load("regression_baseline_v1.json", EvaluationReport),
        load("regression_candidate_v1.json", EvaluationReport),
        load("regression_thresholds_v1.json", RegressionConfig),
    )
    assert result.passed
    assert result.evidence_scope == "deterministic_gate_fixture"
    assert all(decision.passed for decision in result.decisions)


def test_correctness_drop_and_excess_cost_fail() -> None:
    baseline = load("regression_baseline_v1.json", EvaluationReport)
    candidate = load("regression_candidate_v1.json", EvaluationReport)
    metrics = []
    for metric in candidate.metrics:
        if metric.name == "task_completion":
            metric = metric.model_copy(update={"numerator": Decimal(17), "value": Decimal("0.85")})
        if metric.name == "token_cost":
            metric = metric.model_copy(update={"numerator": Decimal("1.11"), "value": Decimal("1.11")})
        metrics.append(metric)
    result = compare_reports(
        baseline,
        candidate.model_copy(update={"metrics": tuple(metrics)}),
        load("regression_thresholds_v1.json", RegressionConfig),
    )
    assert not result.passed
    assert {decision.metric for decision in result.decisions if not decision.passed} == {
        "task_completion",
        "token_cost",
    }


def test_cli_writes_machine_readable_failure_before_nonzero_exit(tmp_path: Path) -> None:
    baseline = DATA / "regression_baseline_v1.json"
    payload = json.loads((DATA / "regression_candidate_v1.json").read_text(encoding="utf-8"))
    next(metric for metric in payload["metrics"] if metric["name"] == "p95_latency_ms")[
        "value"
    ] = "1000"
    next(metric for metric in payload["metrics"] if metric["name"] == "p95_latency_ms")[
        "numerator"
    ] = "1000"
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "decision.json"

    exit_code = main(
        [
            "--baseline", str(baseline),
            "--candidate", str(candidate),
            "--thresholds", str(DATA / "regression_thresholds_v1.json"),
            "--output", str(output),
        ]
    )
    assert exit_code == 1
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False


def test_regression_fails_closed_for_incompatible_missing_and_unavailable_metrics() -> None:
    baseline = load("regression_baseline_v1.json", EvaluationReport)
    candidate = load("regression_candidate_v1.json", EvaluationReport)

    incompatible = compare_reports(
        baseline,
        candidate.model_copy(update={"controls_hash": "c" * 64}),
        load("regression_thresholds_v1.json", RegressionConfig),
    )
    assert not incompatible.passed
    assert incompatible.decisions[0].metric == "report_compatibility"

    missing = compare_reports(
        baseline,
        candidate,
        RegressionConfig.model_construct(
            thresholds=(
                RegressionThreshold(
                    metric="unknown",
                    direction="higher_is_better",
                    max_relative_regression=0,
                ),
            )
        ),
    )
    assert not missing.passed
    assert missing.decisions[0].reason == "required metric is missing"

    unavailable_metric = candidate.metric("task_completion").model_copy(
        update={
            "status": "not_available",
            "numerator": None,
            "denominator": None,
            "value": None,
        }
    )
    unavailable = candidate.model_copy(
        update={
            "metrics": tuple(
                unavailable_metric if metric.name == "task_completion" else metric
                for metric in candidate.metrics
            )
        }
    )
    result = compare_reports(
        baseline,
        unavailable,
        load("regression_thresholds_v1.json", RegressionConfig),
    )
    assert not result.passed
    assert "unavailable" in result.decisions[0].reason


def test_threshold_config_rejects_duplicates_and_cli_passes(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="unique"):
        RegressionConfig(
            thresholds=(
                RegressionThreshold(
                    metric="same", direction="higher_is_better", max_relative_regression=0
                ),
                RegressionThreshold(
                    metric="same", direction="lower_is_better", max_relative_regression=0
                ),
            )
        )
    with pytest.raises(ValidationError, match="every report metric"):
        RegressionConfig(
            thresholds=(
                RegressionThreshold(
                    metric="only-one",
                    direction="higher_is_better",
                    max_relative_regression=0,
                ),
            )
        )

    output = tmp_path / "decision.json"
    assert main(
        [
            "--baseline", str(DATA / "regression_baseline_v1.json"),
            "--candidate", str(DATA / "regression_candidate_v1.json"),
            "--thresholds", str(DATA / "regression_thresholds_v1.json"),
            "--output", str(output),
        ]
    ) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
