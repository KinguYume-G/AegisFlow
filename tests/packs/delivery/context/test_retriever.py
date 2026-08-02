"""Filesystem and deterministic scoring tests for the local retriever."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from aegisflow_core.packs.delivery.context.fakes import LocalFixtureContextRetriever
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


TRACKED_FIXTURE_ROOT = Path(__file__).parents[3] / "fixtures" / "context"


def _request(title: str = "alpha beta", body: str = "gamma") -> NormalizedRequest:
    return NormalizedRequest(
        source_type="prd",
        source_ref=None,
        title=title,
        body=body,
        idempotency_key="c" * 64,
        received_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("root_kind", ["missing", "file"])
def test_retriever_rejects_missing_or_file_root(tmp_path: Path, root_kind: str) -> None:
    root = tmp_path / root_kind
    if root_kind == "file":
        root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="existing directory"):
        LocalFixtureContextRetriever(root)


def test_retriever_accepts_only_allowed_regular_files(tmp_path: Path) -> None:
    _write(tmp_path / "a.md", "alpha evidence")
    _write(tmp_path / "b.py", "beta = 'evidence'")
    _write(tmp_path / "c.txt", "gamma evidence")
    _write(tmp_path / "ignored.json", "alpha beta gamma")
    (tmp_path / "directory.md").mkdir()

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request())

    assert [snippet.relative_path for snippet in package.snippets] == [
        "a.md",
        "b.py",
        "c.txt",
    ]
    assert package.scanned_file_count == 3


def test_retriever_skips_symlink_and_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("alpha secret outside root", encoding="utf-8")
    link = tmp_path / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {type(error).__name__}")

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request("alpha", ""))

    assert package.snippets == []
    assert package.security_skip_count == 1
    assert "secret outside root" not in repr(package)


def test_retriever_skips_file_over_256_kib(tmp_path: Path) -> None:
    _write(tmp_path / "oversized.txt", "alpha" + ("x" * (256 * 1024)))

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request("alpha", ""))

    assert package.snippets == []
    assert package.scanned_file_count == 1
    assert package.skipped_file_count == 1


def test_retriever_scans_at_most_200_files(tmp_path: Path) -> None:
    for index in range(200):
        _write(tmp_path / f"{index:03}.txt", "unrelated")
    _write(tmp_path / "zzz.txt", "alpha should not be scanned")

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request("alpha", ""))

    assert package.scanned_file_count == 200
    assert package.snippets == []
    assert package.skipped_file_count == 0


def test_retriever_scores_and_sorts_deterministically(tmp_path: Path) -> None:
    contents = {
        "f.md": "alpha beta gamma",
        "b.md": "alpha beta",
        "a.md": "alpha beta",
        "c.md": "alpha",
        "d.md": "beta",
        "e.md": "gamma",
    }
    for relative_path, content in contents.items():
        _write(tmp_path / relative_path, content)

    retriever = LocalFixtureContextRetriever(tmp_path)
    first = retriever.retrieve(_request())
    second = retriever.retrieve(_request())

    expected = ["f.md", "a.md", "b.md", "c.md", "d.md"]
    assert [snippet.relative_path for snippet in first.snippets] == expected
    assert first == second
    assert len(first.snippets) == 5


def test_retriever_reports_exact_first_match_lines(tmp_path: Path) -> None:
    _write(
        tmp_path / "nested" / "evidence.md",
        "zero\nalpha starts here\nline 3\nline 4\nline 5\nline 6\nline 7",
    )

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request("alpha", ""))
    snippet = package.snippets[0]

    assert snippet.relative_path == "nested/evidence.md"
    assert snippet.start_line == 2
    assert snippet.end_line == 6
    assert snippet.content == "alpha starts here\nline 3\nline 4\nline 5\nline 6"


def test_retriever_no_match_is_explicit(tmp_path: Path) -> None:
    _write(tmp_path / "document.md", "unrelated repository material")

    package = LocalFixtureContextRetriever(tmp_path).retrieve(
        _request("zebra", "quantum")
    )

    assert package.snippets == []
    assert package.unsupported_notes == [
        "No repository evidence matched the normalized request."
    ]


def test_retriever_handles_no_eligible_tokens(tmp_path: Path) -> None:
    _write(tmp_path / "document.md", "a an to")

    package = LocalFixtureContextRetriever(tmp_path).retrieve(_request("a", "to"))

    assert package.snippets == []
    assert package.unsupported_notes


def test_tracked_fixture_root_is_selected_by_the_caller() -> None:
    package = LocalFixtureContextRetriever(TRACKED_FIXTURE_ROOT).retrieve(
        _request("repository evidence", "relative path")
    )

    assert package.snippets
    assert package.snippets[0].relative_path == "retrieval_contract.md"
