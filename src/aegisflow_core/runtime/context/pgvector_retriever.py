"""AF-106-compatible tenant-scoped pgvector retrieval adapter."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from aegisflow_core.control_plane.domain.knowledge import RepositoryChunk
from aegisflow_core.packs.delivery.contracts.context_package import CitedSnippet, ContextPackage
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


@dataclass(frozen=True, slots=True)
class RepositoryTarget:
    owner: str
    repository: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"


class ContextIsolationViolation(PermissionError):
    """A retrieval adapter returned data outside its trusted namespace."""


class PgVectorContextRetriever:
    """Map already tenant/repository-filtered rows to exact citations."""

    def __init__(self, *, tenant_id: UUID, target: RepositoryTarget,
                 query: Callable[[UUID, str, str, int], Sequence[RepositoryChunk]], limit: int = 5) -> None:
        self._tenant_id, self._target, self._query, self._limit = tenant_id, target, query, limit

    def retrieve(self, request: NormalizedRequest) -> ContextPackage:
        rows = self._query(self._tenant_id, self._target.full_name, request.title, self._limit)
        if any(
            row.tenant_id != self._tenant_id
            or row.repository.casefold() != self._target.full_name.casefold()
            for row in rows
        ):
            raise ContextIsolationViolation("context namespace mismatch")
        snippets = [CitedSnippet(relative_path=row.file_path, start_line=row.start_line,
                                 end_line=row.end_line, content=row.content) for row in rows[:self._limit]]
        return ContextPackage(snippets=snippets, unsupported_notes=[] if snippets else ["no repository evidence found"],
                              scanned_file_count=len({row.file_path for row in rows}), skipped_file_count=0,
                              security_skip_count=0)
