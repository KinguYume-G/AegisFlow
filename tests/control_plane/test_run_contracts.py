"""Public Run API contracts are bounded and deterministic."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from aegisflow_core.control_plane.runs import (
    CreateRunRequest,
    RepositoryInput,
    canonical_run_input_hash,
)


def request() -> CreateRunRequest:
    return CreateRunRequest(
        source_type="prd",
        source_ref="local://prd/first",
        title="Add a governed delivery status endpoint",
        body=(
            "Create a tenant-scoped status endpoint with tests, audit evidence, "
            "a bounded response, and a separate Reviewer approval before any write."
        ),
        repository=RepositoryInput(
            owner="KinguYume-G",
            name="AegisFlow",
            base_ref="main",
            base_sha="a" * 40,
        ),
    )


def test_run_input_hash_is_stable_and_content_sensitive() -> None:
    first = request()
    reconstructed = CreateRunRequest.model_validate(first.model_dump())

    assert canonical_run_input_hash(first) == canonical_run_input_hash(reconstructed)
    assert len(canonical_run_input_hash(first)) == 64
    changed = first.model_copy(update={"title": "A different bounded title"})
    assert canonical_run_input_hash(first) != canonical_run_input_hash(changed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ""),
        ("title", "x" * 201),
        ("body", "too short"),
        ("body", "x" * 50_001),
        ("source_ref", "x" * 2049),
    ],
    ids=["empty-title", "long-title", "short-body", "long-body", "long-source-ref"],
)
def test_run_input_rejects_unbounded_text(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        CreateRunRequest.model_validate({**request().model_dump(), field: value})


@pytest.mark.parametrize(
    "values",
    [
        {"owner": "../escape"},
        {"name": "repo/name"},
        {"base_ref": "refs/heads/../main"},
        {"base_sha": "not-a-sha"},
    ],
)
def test_repository_input_rejects_invalid_scope(values: dict[str, str]) -> None:
    payload = request().repository.model_dump()
    payload.update(values)
    with pytest.raises(ValidationError):
        RepositoryInput.model_validate(payload)


def test_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CreateRunRequest.model_validate({**request().model_dump(), "tenant_id": str(UUID(int=1))})
