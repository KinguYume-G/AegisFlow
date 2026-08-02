"""Schema tests for the AF-106 context package."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from aegisflow_core.packs.delivery.contracts.context_package import (
    CitedSnippet,
    ContextPackage,
)


def _snippet(**overrides: object) -> CitedSnippet:
    values: dict[str, object] = {
        "relative_path": "docs/architecture.md",
        "start_line": 2,
        "end_line": 3,
        "content": "line two\nline three",
    }
    values.update(overrides)
    return CitedSnippet.model_validate(values)


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../outside.txt",
        "docs/../../outside.txt",
        "C:\\secrets\\token.txt",
        "docs\\architecture.md",
        "",
    ],
)
def test_cited_snippet_validates_relative_path_and_lines(path: str) -> None:
    with pytest.raises(ValidationError):
        _snippet(relative_path=path)

    with pytest.raises(ValidationError):
        _snippet(start_line=0)
    with pytest.raises(ValidationError):
        _snippet(start_line=4, end_line=3)
    assert _snippet().source_trust == "repository_content"


def test_package_separates_snippets_and_unsupported_notes() -> None:
    package = ContextPackage(
        snippets=[_snippet()],
        unsupported_notes=["No evidence supports an inferred deployment target."],
        scanned_file_count=3,
        skipped_file_count=1,
        security_skip_count=1,
    )

    assert package.snippets[0].relative_path == "docs/architecture.md"
    assert package.unsupported_notes == [
        "No evidence supports an inferred deployment target."
    ]
    assert package.scanned_file_count == 3
    with pytest.raises(ValidationError):
        ContextPackage(
            snippets=["unsupported text"],
            unsupported_notes=[],
            scanned_file_count=0,
            skipped_file_count=0,
            security_skip_count=0,
        )


def test_package_enforces_result_and_counter_bounds() -> None:
    with pytest.raises(ValidationError):
        ContextPackage(
            snippets=[_snippet(relative_path=f"doc-{index}.md") for index in range(6)],
            unsupported_notes=[],
            scanned_file_count=6,
            skipped_file_count=0,
            security_skip_count=0,
        )
    with pytest.raises(ValidationError):
        ContextPackage(
            snippets=[],
            unsupported_notes=[],
            scanned_file_count=201,
            skipped_file_count=0,
            security_skip_count=0,
        )


def test_cited_snippet_rejects_empty_content_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _snippet(content="")
    with pytest.raises(ValidationError):
        _snippet(extra="not allowed")


def test_schema_uses_canonical_posix_paths() -> None:
    snippet = _snippet(relative_path=Path("docs", "guide.md").as_posix())

    assert snippet.relative_path == "docs/guide.md"
