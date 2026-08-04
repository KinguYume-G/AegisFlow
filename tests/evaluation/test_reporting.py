"""AF-506 deterministic metric aggregation and report tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from aegisflow_core.evaluation.contracts import EvaluationRun, MetricObservation

from aegisflow_core.evaluation.reporting import (
    EvaluationReport,
    ReportMetric,
    build_report,
    render_markdown,
    write_report,
)


def run(index: int, *, controls_hash: str = "b" * 64) -> EvaluationRun:
    started = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)
    ratios = (
        "task_completion",
        "tool_success",
        "defect_detection",
        "false_positive",
        "patch_applicability",
        "test_pass",
    )
    observations = [
        MetricObservation(
            name=name,
            numerator=Decimal(0 if name == "false_positive" else 1),
            denominator=Decimal(1),
            unit="ratio",
        )
        for name in ratios
    ]
    observations.extend(
        (
            MetricObservation(name="token_cost", numerator=Decimal("0.01"), unit="currency"),
            MetricObservation(name="latency_ms", numerator=Decimal(index + 1), unit="milliseconds"),
        )
    )
    return EvaluationRun(
        run_id=f"run-{index}",
        subject="aegisflow",
        case_id=f"case-{index}",
        dataset_hash="a" * 64,
        controls_hash=controls_hash,
        started_at=started,
        completed_at=started + timedelta(milliseconds=index + 1),
        status="completed",
        metrics=tuple(observations),
    )


def test_report_retains_counts_cost_and_nearest_rank_p95() -> None:
    report = build_report((run(index) for index in range(20)), prompt_version="v1")

    completion = report.metric("task_completion")
    assert (completion.numerator, completion.denominator, completion.value) == (
        Decimal(20),
        Decimal(20),
        Decimal(1),
    )
    assert report.metric("false_positive").value == 0
    assert report.metric("token_cost").value == Decimal("0.20")
    assert report.metric("p95_latency_ms").value == Decimal(19)
    markdown = render_markdown(report)
    assert "20/20" in markdown
    assert "not available" not in markdown


def test_report_marks_missing_evidence_unavailable_instead_of_zero() -> None:
    item = run(0).model_copy(update={"metrics": ()})
    report = build_report((item,), prompt_version="v1")
    assert all(metric.status == "not_available" for metric in report.metrics)


def test_report_rejects_mixed_controls() -> None:
    with pytest.raises(ValueError, match="identical subject and controls"):
        build_report((run(0), run(1, controls_hash="c" * 64)), prompt_version="v1")


def test_report_rejects_empty_and_wrong_metric_shapes() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_report((), prompt_version="v1")

    bad_ratio = run(0).model_copy(
        update={
            "metrics": (
                MetricObservation(name="task_completion", numerator=1, unit="count"),
            )
        }
    )
    with pytest.raises(ValueError, match="ratio observations"):
        build_report((bad_ratio,), prompt_version="v1")

    bad_cost = run(0).model_copy(
        update={
            "metrics": (
                MetricObservation(
                    name="token_cost", numerator=1, denominator=1, unit="ratio"
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="currency observations"):
        build_report((bad_cost,), prompt_version="v1")

    bad_latency = run(0).model_copy(
        update={
            "metrics": (
                MetricObservation(name="latency_ms", numerator=1, unit="count"),
            )
        }
    )
    with pytest.raises(ValueError, match="millisecond observations"):
        build_report((bad_latency,), prompt_version="v1")


def test_report_models_fail_closed_and_write_both_formats(tmp_path) -> None:
    with pytest.raises(ValidationError):
        ReportMetric(name="bad", status="measured", unit="currency")
    with pytest.raises(ValidationError):
        ReportMetric(
            name="bad",
            status="not_available",
            numerator=Decimal(0),
            unit="currency",
        )
    with pytest.raises(ValidationError, match="ratio value"):
        ReportMetric(
            name="bad",
            status="measured",
            numerator=Decimal(1),
            denominator=Decimal(2),
            value=Decimal(1),
            unit="ratio",
        )
    with pytest.raises(ValidationError, match="scalar value"):
        ReportMetric(
            name="bad",
            status="measured",
            numerator=Decimal(1),
            value=Decimal(2),
            unit="currency",
        )

    report = build_report((run(0),), prompt_version="v1")
    with pytest.raises(KeyError):
        report.metric("unknown")
    with pytest.raises(ValidationError, match="unique"):
        EvaluationReport.model_validate(
            {
                **report.model_dump(),
                "metrics": [*report.metrics[:-1], report.metrics[0]],
            }
        )

    json_path = tmp_path / "nested" / "report.json"
    markdown_path = tmp_path / "nested" / "report.md"
    write_report(report, json_path=json_path, markdown_path=markdown_path)
    assert EvaluationReport.model_validate_json(json_path.read_text()).run_count == 1
    assert markdown_path.read_text(encoding="utf-8").startswith("# Evaluation Report")
