"""Deterministic evaluation aggregation with honest small-sample evidence."""

from __future__ import annotations

from decimal import Decimal
import json
from math import ceil
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aegisflow_core.evaluation.contracts import EvaluationRun

RATIO_METRICS = (
    "task_completion",
    "tool_success",
    "defect_detection",
    "false_positive",
    "patch_applicability",
    "test_pass",
)
SCALAR_METRICS = ("token_cost",)
REPORT_METRICS = (*RATIO_METRICS, *SCALAR_METRICS, "p95_latency_ms")


class ReportMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: Literal["measured", "not_available"]
    numerator: Decimal | None = None
    denominator: Decimal | None = None
    value: Decimal | None = None
    unit: Literal["ratio", "currency", "milliseconds"]

    @model_validator(mode="after")
    def evidence_is_consistent(self) -> "ReportMetric":
        values = (self.numerator, self.value)
        if self.status == "not_available":
            if any(value is not None for value in (*values, self.denominator)):
                raise ValueError("unavailable metrics cannot contain measurements")
            return self
        if any(value is None for value in values):
            raise ValueError("measured metrics require numerator and value")
        assert self.numerator is not None and self.value is not None
        if not self.numerator.is_finite() or self.numerator < 0:
            raise ValueError("metric numerator must be finite and non-negative")
        if not self.value.is_finite() or self.value < 0:
            raise ValueError("metric value must be finite and non-negative")
        if self.unit == "ratio":
            if self.denominator is None:
                raise ValueError("ratio metrics require a denominator")
            if not self.denominator.is_finite() or self.denominator <= 0:
                raise ValueError("metric denominator must be finite and positive")
            if self.value != self.numerator / self.denominator:
                raise ValueError("ratio value must equal numerator divided by denominator")
        elif self.denominator is not None or self.value != self.numerator:
            raise ValueError("scalar value must equal numerator without a denominator")
        return self


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    subject: Literal["aegisflow", "single_agent"]
    evidence_scope: Literal["measured_evaluation", "deterministic_gate_fixture"]
    prompt_version: str = Field(min_length=1, max_length=128)
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    controls_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_count: int = Field(ge=1)
    metrics: tuple[ReportMetric, ...]

    @model_validator(mode="after")
    def metric_names_are_complete_and_unique(self) -> "EvaluationReport":
        names = tuple(metric.name for metric in self.metrics)
        if len(names) != len(set(names)):
            raise ValueError("report metric names must be unique")
        if set(names) != set(REPORT_METRICS):
            raise ValueError("report must contain every required metric")
        return self

    def metric(self, name: str) -> ReportMetric:
        try:
            return next(metric for metric in self.metrics if metric.name == name)
        except StopIteration as exc:
            raise KeyError(name) from exc


def _nearest_rank(values: list[Decimal], percentile: Decimal) -> Decimal:
    if not values:
        raise ValueError("percentile requires observations")
    ordered = sorted(values)
    rank = max(1, ceil(float(percentile) * len(ordered)))
    return ordered[rank - 1]


def build_report(
    runs: Iterable[EvaluationRun],
    *,
    prompt_version: str,
    evidence_scope: Literal[
        "measured_evaluation", "deterministic_gate_fixture"
    ] = "measured_evaluation",
) -> EvaluationReport:
    evidence = tuple(runs)
    if not evidence:
        raise ValueError("at least one evaluation run is required")
    first = evidence[0]
    if any(
        run.subject != first.subject
        or run.dataset_hash != first.dataset_hash
        or run.controls_hash != first.controls_hash
        for run in evidence
    ):
        raise ValueError("evaluation runs must use identical subject and controls")

    observations: dict[str, list[tuple[Decimal, Decimal | None, str]]] = {}
    for run in evidence:
        for metric in run.metrics:
            observations.setdefault(metric.name, []).append(
                (metric.numerator, metric.denominator, metric.unit)
            )

    report_metrics: list[ReportMetric] = []
    for name in RATIO_METRICS:
        values = observations.get(name, [])
        if not values:
            report_metrics.append(
                ReportMetric(name=name, status="not_available", unit="ratio")
            )
            continue
        if any(unit != "ratio" or denominator is None for _, denominator, unit in values):
            raise ValueError(f"{name} requires ratio observations")
        numerator = sum((value for value, _, _ in values), Decimal(0))
        denominator = sum(
            (value for _, value, _ in values if value is not None), Decimal(0)
        )
        report_metrics.append(
            ReportMetric(
                name=name,
                status="measured",
                numerator=numerator,
                denominator=denominator,
                value=numerator / denominator,
                unit="ratio",
            )
        )

    cost_values = observations.get("token_cost", [])
    if cost_values:
        if any(unit != "currency" or denominator is not None for _, denominator, unit in cost_values):
            raise ValueError("token_cost requires scalar currency observations")
        total_cost = sum((value for value, _, _ in cost_values), Decimal(0))
        report_metrics.append(
            ReportMetric(
                name="token_cost",
                status="measured",
                numerator=total_cost,
                value=total_cost,
                unit="currency",
            )
        )
    else:
        report_metrics.append(
            ReportMetric(name="token_cost", status="not_available", unit="currency")
        )

    latencies = observations.get("latency_ms", [])
    if latencies:
        if any(unit != "milliseconds" or denominator is not None for _, denominator, unit in latencies):
            raise ValueError("latency_ms requires scalar millisecond observations")
        p95 = _nearest_rank([value for value, _, _ in latencies], Decimal("0.95"))
        report_metrics.append(
            ReportMetric(
                name="p95_latency_ms",
                status="measured",
                numerator=p95,
                value=p95,
                unit="milliseconds",
            )
        )
    else:
        report_metrics.append(
            ReportMetric(
                name="p95_latency_ms", status="not_available", unit="milliseconds"
            )
        )

    return EvaluationReport(
        subject=first.subject,
        evidence_scope=evidence_scope,
        prompt_version=prompt_version,
        dataset_hash=first.dataset_hash,
        controls_hash=first.controls_hash,
        run_count=len(evidence),
        metrics=tuple(report_metrics),
    )


def render_markdown(report: EvaluationReport) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"- Subject: `{report.subject}`",
        f"- Evidence scope: `{report.evidence_scope}`",
        f"- Prompt version: `{report.prompt_version}`",
        f"- Runs: `{report.run_count}`",
        "",
        "| Metric | Evidence | Value |",
        "|---|---:|---:|",
    ]
    for metric in report.metrics:
        if metric.status == "not_available":
            lines.append(f"| {metric.name} | not available | not available |")
        elif metric.denominator is not None:
            lines.append(
                f"| {metric.name} | {metric.numerator}/{metric.denominator} | {metric.value} |"
            )
        else:
            lines.append(f"| {metric.name} | {metric.numerator} | {metric.value} |")
    return "\n".join(lines) + "\n"


def write_report(report: EvaluationReport, *, json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
