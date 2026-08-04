"""AF-504 real sanitized historical dataset tests."""

from pathlib import Path
import re

from aegisflow_core.evaluation.datasets import build_manifest, load_jsonl_cases

DATA = Path(__file__).parents[2] / "src" / "aegisflow_core" / "evaluation" / "data"


def test_historical_dataset_has_five_real_traceable_sanitized_fixes() -> None:
    cases = load_jsonl_cases(DATA / "historical_project_fixes_v1.jsonl")

    assert len(cases) == 5
    assert len({case.case_id for case in cases}) == 5
    assert {case.provenance.source_system for case in cases} == {
        "XueMai",
        "exilian-cyms",
    }
    for case in cases:
        assert case.category == "historical"
        assert case.input.base_commit and re.fullmatch(r"[0-9a-f]{40}", case.input.base_commit)
        assert re.fullmatch(r"[0-9a-f]{40}", case.provenance.source_revision)
        assert case.expected.ground_truth_reference == (
            f"commit:{case.provenance.source_revision}"
        )
        assert case.provenance.sanitization
        assert "synthetic" not in case.tags

    manifest = build_manifest(
        dataset_id="historical-project-fixes",
        version="1.0.0",
        revision="af-504-approved-2026-08-04",
        description="Real sanitized project fixes",
        selection_criteria=("real fix", "immutable source", "sanitized"),
        cases=cases,
    )
    assert manifest.declared_case_count == 5
    assert len(manifest.content_hash) == 64
