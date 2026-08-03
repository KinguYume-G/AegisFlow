"""AF-501 immutable evaluation contract tests."""

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError
import pytest

from aegisflow_core.evaluation.contracts import (
    CaseInput,
    CaseProvenance,
    DatasetManifest,
    EvaluationCase,
    EvaluationRun,
    ExpectedOutcome,
    MetricObservation,
    canonical_hash,
)


def case(**overrides: object) -> EvaluationCase:
    values: dict[str, object] = {
        "case_id": "delivery.example-1",
        "dataset_id": "delivery-golden",
        "category": "delivery",
        "input": CaseInput(source_type="bug", title="Fix bug", body="Reproduce safely"),
        "expected": ExpectedOutcome(task_completed=True, required_checks=("pytest",)),
        "provenance": CaseProvenance(
            source_system="AegisFlow",
            source_reference="fixture:1",
            source_revision="1",
            license_note="Project-owned synthetic fixture.",
        ),
    }
    values.update(overrides)
    return EvaluationCase(**values)  # type: ignore[arg-type]


def test_manifest_is_immutable_versioned_and_canonically_hashed() -> None:
    item = case()
    manifest = DatasetManifest(
        dataset_id="delivery-golden",
        version="1.0.0",
        revision="commit-1",
        description="Delivery fixtures",
        selection_criteria=("sanitized",),
        declared_case_count=1,
        cases=(item,),
    )

    assert manifest.content_hash == canonical_hash(manifest)
    assert len(manifest.content_hash) == 64
    assert manifest.content_hash == DatasetManifest.model_validate(
        manifest.model_dump()
    ).content_hash
    with pytest.raises(ValidationError):
        manifest.version = "2.0.0"  # type: ignore[misc]


@pytest.mark.parametrize(
    "update",
    [
        {"version": "v1"},
        {"declared_case_count": 2},
        {"cases": (case(), case())},
        {"cases": (case(dataset_id="other-dataset"),)},
    ],
)
def test_manifest_rejects_inconsistent_identity_and_counts(update: dict[str, object]) -> None:
    values: dict[str, object] = {
        "dataset_id": "delivery-golden",
        "version": "1.0.0",
        "revision": "commit-1",
        "description": "Delivery fixtures",
        "selection_criteria": ("sanitized",),
        "declared_case_count": 1,
        "cases": (case(),),
    }
    values.update(update)
    with pytest.raises(ValidationError):
        DatasetManifest(**values)  # type: ignore[arg-type]


def test_historical_case_requires_real_source_sanitization_and_ground_truth() -> None:
    provenance = CaseProvenance(
        source_system="XueMai",
        source_reference="issue:redacted-1",
        source_revision="immutable-export-1",
        license_note="Project-owned private source; sanitized derivative.",
        sanitization="Removed names, URLs, credentials, and customer data.",
    )
    historical = case(
        case_id="history.xuemai-1",
        dataset_id="historical",
        category="historical",
        provenance=provenance,
        expected=ExpectedOutcome(
            task_completed=True,
            ground_truth_reference="fix:commit-redacted-1",
        ),
    )
    assert historical.category == "historical"

    with pytest.raises(ValidationError):
        case(
            case_id="history.fake-1",
            dataset_id="historical",
            category="historical",
            provenance=provenance,
            expected=ExpectedOutcome(task_completed=True),
            tags=("synthetic",),
        )


def test_run_and_metrics_preserve_numerator_denominator_and_failure_state() -> None:
    now = datetime.now(timezone.utc)
    metric = MetricObservation(
        name="completion",
        numerator=Decimal(8),
        denominator=Decimal(10),
        unit="ratio",
    )
    run = EvaluationRun(
        run_id="run-1",
        subject="single_agent",
        case_id="delivery.example-1",
        dataset_hash="a" * 64,
        controls_hash="b" * 64,
        started_at=now,
        completed_at=now,
        status="completed",
        metrics=(metric,),
    )
    assert run.metrics[0].numerator == 8
    assert run.metrics[0].denominator == 10
    with pytest.raises(ValidationError):
        EvaluationRun.model_validate({**run.model_dump(), "status": "failed"})


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "bad", "numerator": Decimal(-1), "unit": "count"},
        {"name": "bad", "numerator": Decimal("NaN"), "unit": "count"},
        {"name": "bad", "numerator": Decimal(1), "denominator": 0, "unit": "ratio"},
        {"name": "bad", "numerator": Decimal(1), "unit": "ratio"},
    ],
)
def test_metric_rejects_invalid_measurements(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        MetricObservation(**payload)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "update",
    [
        {"title": " "},
        {"body": "\t"},
        {"base_commit": "short"},
    ],
)
def test_case_input_rejects_blank_text_and_partial_commits(update: dict[str, object]) -> None:
    values: dict[str, object] = {
        "source_type": "bug",
        "title": "Title",
        "body": "Body",
    }
    values.update(update)
    with pytest.raises(ValidationError):
        CaseInput(**values)  # type: ignore[arg-type]
