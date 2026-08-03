"""AF-502/AF-503/AF-504 dataset selection and safety tests."""

import json
from pathlib import Path

import pytest

from aegisflow_core.evaluation.datasets import (
    DatasetLoadError,
    build_manifest,
    load_jsonl_cases,
    load_manifest,
)

DATA = Path(__file__).parents[2] / "src" / "aegisflow_core" / "evaluation" / "data"


def test_swebench_subset_is_pinned_diverse_and_metadata_only() -> None:
    manifest = load_manifest(DATA / "swebench_verified_python_v1.json")

    assert manifest.revision == "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"
    assert len(manifest.cases) == 12
    assert len({case.input.repository for case in manifest.cases}) == 12
    assert all(case.category == "swe_bench" for case in manifest.cases)
    assert all(case.input.base_commit and len(case.input.base_commit) == 40 for case in manifest.cases)
    assert all("diff --git" not in case.input.body for case in manifest.cases)
    assert all(case.expected.ground_truth_reference for case in manifest.cases)


def test_security_set_has_required_truth_categories_and_no_real_secrets() -> None:
    cases = load_jsonl_cases(DATA / "security_injection_v1.jsonl")
    categories = {case.category for case in cases}

    assert len(cases) == 15
    assert categories == {
        "security_sql",
        "security_secret",
        "security_token",
        "security_authorization",
        "security_prompt",
    }
    assert sum(case.expected.injection_expected is True for case in cases) >= 4
    manifest = build_manifest(
        dataset_id="security-injection",
        version="1.0.0",
        revision="af-503-v1",
        description="Deterministic security truth cases",
        selection_criteria=("no real secrets", "five required categories"),
        cases=cases,
    )
    assert manifest.declared_case_count == 15


def test_loaders_reject_duplicate_ids_and_secret_shaped_content(tmp_path: Path) -> None:
    safe = (DATA / "security_injection_v1.jsonl").read_text(encoding="utf-8").splitlines()[0]
    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_text(f"{safe}\n{safe}\n", encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="unique"):
        load_jsonl_cases(duplicate)

    secret = tmp_path / "secret.jsonl"
    payload = json.loads(safe)
    payload["input"]["body"] = "github_pat_abcdefghijklmnopqrstuvwxyz123456"
    secret.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="secret-shaped"):
        load_jsonl_cases(secret)


def test_historical_import_rejects_unprovenanced_synthetic_case(tmp_path: Path) -> None:
    payload = json.loads(
        (DATA / "security_injection_v1.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    payload.update(
        case_id="history.fake-1",
        dataset_id="historical",
        category="historical",
        tags=["synthetic"],
    )
    payload["provenance"].update(source_system="XueMai", sanitization="redacted")
    payload["expected"]["ground_truth_reference"] = "fix:fake"
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetLoadError, match="ValidationError"):
        load_jsonl_cases(path)


def test_loaders_normalize_io_json_and_empty_failures(tmp_path: Path) -> None:
    malformed = tmp_path / "manifest.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="JSONDecodeError"):
        load_manifest(malformed)

    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(DatasetLoadError, match="no cases"):
        load_jsonl_cases(empty)
