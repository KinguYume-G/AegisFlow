"""Bounded local fixture retriever for the M1 Context contract."""

from dataclasses import dataclass
from pathlib import Path
import re

from aegisflow_core.packs.delivery.contracts.context_package import (
    CitedSnippet,
    ContextPackage,
)
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


_ALLOWED_SUFFIXES = frozenset({".md", ".py", ".txt"})
_MAX_FILE_BYTES = 256 * 1024
_MAX_SCANNED_FILES = 200
_MAX_RESULTS = 5
_MAX_SNIPPET_LINES = 5
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_NO_MATCH_NOTE = "No repository evidence matched the normalized request."


@dataclass(frozen=True, slots=True)
class _Match:
    score: int
    relative_path: str
    snippet: CitedSnippet


class LocalFixtureContextRetriever:
    """Search a caller-provided local root without network or semantic inference."""

    def __init__(self, root: Path) -> None:
        try:
            resolved_root = root.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise ValueError("root must be an existing directory") from error
        if not resolved_root.is_dir():
            raise ValueError("root must be an existing directory")
        self._root = resolved_root

    def retrieve(self, request: NormalizedRequest) -> ContextPackage:
        """Return deterministic, exactly cited lexical matches from the root."""
        request_tokens = _tokens(f"{request.title}\n{request.body}")
        matches: list[_Match] = []
        scanned = 0
        skipped = 0
        security_skips = 0

        candidates = sorted(
            self._root.rglob("*"),
            key=lambda path: path.relative_to(self._root).as_posix(),
        )
        for candidate in candidates:
            if candidate.is_symlink():
                security_skips += 1
                continue
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                security_skips += 1
                continue
            if not resolved.is_relative_to(self._root):
                security_skips += 1
                continue
            if not resolved.is_file() or resolved.suffix.lower() not in _ALLOWED_SUFFIXES:
                continue
            if scanned == _MAX_SCANNED_FILES:
                break
            scanned += 1

            try:
                if resolved.stat().st_size > _MAX_FILE_BYTES:
                    skipped += 1
                    continue
                with resolved.open("rb") as file_handle:
                    raw_content = file_handle.read(_MAX_FILE_BYTES + 1)
                if len(raw_content) > _MAX_FILE_BYTES:
                    skipped += 1
                    continue
                content = raw_content.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue

            file_tokens = _tokens(content)
            score = len(request_tokens & file_tokens)
            if score == 0:
                continue
            lines = content.splitlines()
            first_match_index = next(
                index
                for index, line in enumerate(lines)
                if request_tokens & _tokens(line)
            )
            selected_lines = lines[
                first_match_index : first_match_index + _MAX_SNIPPET_LINES
            ]
            relative_path = resolved.relative_to(self._root).as_posix()
            snippet = CitedSnippet(
                relative_path=relative_path,
                start_line=first_match_index + 1,
                end_line=first_match_index + len(selected_lines),
                content="\n".join(selected_lines),
            )
            matches.append(
                _Match(
                    score=score,
                    relative_path=relative_path,
                    snippet=snippet,
                )
            )

        matches.sort(key=lambda match: (-match.score, match.relative_path))
        snippets = [match.snippet for match in matches[:_MAX_RESULTS]]
        unsupported_notes = [] if snippets else [_NO_MATCH_NOTE]
        return ContextPackage(
            snippets=snippets,
            unsupported_notes=unsupported_notes,
            scanned_file_count=scanned,
            skipped_file_count=skipped,
            security_skip_count=security_skips,
        )


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(value.lower())
        if len(token) >= 3
    }
