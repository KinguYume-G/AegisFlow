"""Strict local loaders for versioned evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Iterable

from pydantic import ValidationError

from aegisflow_core.evaluation.contracts import DatasetManifest, EvaluationCase

_REAL_SECRET = re.compile(
    r"(?i)(?:github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|(?:sk|pk)-(?:lf-)?(?!testplaceholder)[a-z0-9_-]{16,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


class DatasetLoadError(ValueError):
    """Stable failure for malformed or unsafe evaluation data."""


def _reject_secrets(raw: str) -> None:
    if _REAL_SECRET.search(raw):
        raise DatasetLoadError("dataset contains secret-shaped content")


def load_manifest(path: Path) -> DatasetManifest:
    try:
        raw = path.read_text(encoding="utf-8")
        _reject_secrets(raw)
        payload = json.loads(raw)
        return DatasetManifest.model_validate(payload)
    except DatasetLoadError:
        raise
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise DatasetLoadError(type(exc).__name__) from None


def load_jsonl_cases(path: Path) -> tuple[EvaluationCase, ...]:
    try:
        raw = path.read_text(encoding="utf-8")
        _reject_secrets(raw)
        cases = tuple(
            EvaluationCase.model_validate(json.loads(line))
            for line in raw.splitlines()
            if line.strip()
        )
    except DatasetLoadError:
        raise
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise DatasetLoadError(type(exc).__name__) from None
    identifiers = [case.case_id for case in cases]
    if not cases:
        raise DatasetLoadError("dataset contains no cases")
    if len(identifiers) != len(set(identifiers)):
        raise DatasetLoadError("dataset case IDs must be unique")
    return cases


def build_manifest(
    *,
    dataset_id: str,
    version: str,
    revision: str,
    description: str,
    selection_criteria: Iterable[str],
    cases: Iterable[EvaluationCase],
) -> DatasetManifest:
    frozen_cases = tuple(cases)
    return DatasetManifest(
        dataset_id=dataset_id,
        version=version,
        revision=revision,
        description=description,
        selection_criteria=tuple(selection_criteria),
        declared_case_count=len(frozen_cases),
        cases=frozen_cases,
    )
