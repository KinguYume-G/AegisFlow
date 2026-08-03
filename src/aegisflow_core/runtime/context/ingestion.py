"""Tenant-safe, incremental repository ingestion."""

from dataclasses import dataclass
from hashlib import sha256
import re
from uuid import UUID

from aegisflow_core.control_plane.domain.knowledge import RepositoryChunk
from aegisflow_core.runtime.context.chunking import chunk_text
from aegisflow_core.runtime.context.embedder import Embedder
from aegisflow_core.runtime.context.store import RepositoryChunkStore

_SECRET = re.compile(r"(?i)(?:api[_-]?key|secret|password|token)\s*[:=]|-----BEGIN [A-Z ]+PRIVATE KEY-----|\b(?:gh[opusr]_|sk-)[A-Za-z0-9_-]{12,}")


@dataclass(frozen=True, slots=True)
class IngestionReport:
    changed: int
    skipped: int
    removed: int
    security_skipped: int


async def ingest_file(store: RepositoryChunkStore, *, tenant_id: UUID, repository: str,
                      file_path: str, raw_text: str, embedder: Embedder) -> IngestionReport:
    current = {row.chunk_index: row for row in await store.list_file(tenant_id, repository, file_path)}
    chunks = chunk_text(raw_text)
    changed = skipped = security_skipped = 0
    retained: set[int] = set()
    for index, text in enumerate(chunks):
        if _SECRET.search(text.content):
            security_skipped += 1
            continue
        digest = sha256(text.content.encode("utf-8")).hexdigest()
        retained.add(index)
        existing = current.get(index)
        if existing is not None and existing.content_hash == digest:
            skipped += 1
            continue
        if existing is not None:
            existing.content_hash = digest
            existing.content = text.content
            existing.start_line = text.start_line
            existing.end_line = text.end_line
            existing.embedding = list(embedder.embed(text.content))
        else:
            await store.add(RepositoryChunk(
                tenant_id=tenant_id, repository=repository, file_path=file_path,
                chunk_index=index, content_hash=digest, content=text.content,
                start_line=text.start_line, end_line=text.end_line,
                embedding=list(embedder.embed(text.content)),
            ))
        changed += 1
    removed = await store.remove_indexes(tenant_id, repository, file_path, set(current) - retained)
    return IngestionReport(changed, skipped, removed, security_skipped)
