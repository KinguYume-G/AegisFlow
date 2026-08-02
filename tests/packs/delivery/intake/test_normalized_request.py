"""Tests for the NormalizedRequest schema."""

from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from pydantic import ValidationError

from aegisflow_core.packs.delivery.contracts.normalized_request import (
    NormalizedRequest,
)


UTC_NOW = datetime(2026, 8, 2, 12, 30, tzinfo=timezone.utc)
VALID_KEY = "a" * 64


def _request(**overrides: object) -> NormalizedRequest:
    values: dict[str, object] = {
        "source_type": "prd",
        "source_ref": "PRD-1",
        "title": "Export audit data",
        "body": "Authorized administrators can export audit data.",
        "idempotency_key": VALID_KEY,
        "received_at": UTC_NOW,
    }
    values.update(overrides)
    return NormalizedRequest.model_validate(values)


@pytest.mark.parametrize(
    "source_type", ["prd", "bug", "github_issue", "feature_request"]
)
def test_normalized_request_accepts_all_source_types(source_type: str) -> None:
    request = _request(source_type=source_type)

    assert request.schema_version == 1
    assert request.source_type == source_type


@pytest.mark.parametrize(
    ("field", "limit"),
    [("source_ref", 2_048), ("title", 500), ("body", 1_000_000)],
)
def test_request_enforces_exact_length_limits(field: str, limit: int) -> None:
    assert getattr(_request(**{field: "x" * limit}), field) == "x" * limit

    with pytest.raises(ValidationError):
        _request(**{field: "x" * (limit + 1)})


@pytest.mark.parametrize(
    "received_at",
    [
        datetime(2026, 8, 2, 12, 30),
        datetime(2026, 8, 2, 20, 30, tzinfo=timezone(timedelta(hours=8))),
    ],
)
def test_request_rejects_non_utc_received_at(received_at: datetime) -> None:
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        _request(received_at=received_at)


@pytest.mark.parametrize("invalid_key", ["A" * 64, "a" * 63, "g" * 64])
def test_request_rejects_invalid_idempotency_key(invalid_key: str) -> None:
    with pytest.raises(ValidationError):
        _request(idempotency_key=invalid_key)


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _request(unexpected="value")


def test_canonical_sha256_fixture_is_independently_reproducible() -> None:
    payload = {
        "source_type": "prd",
        "title": "Export audit data",
        "body": "Authorized administrators can export audit data.",
    }
    expected = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert len(expected) == 64
    assert expected == "0424918ea034e9dddef4569d2803632e1e43fb67e63e53075fcd6deaa5a4f2f3"
