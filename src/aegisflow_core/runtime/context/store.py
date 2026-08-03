"""Persistence ports and SQLAlchemy implementation for repository chunks."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain.knowledge import RepositoryChunk


class RepositoryChunkStore(Protocol):
    async def list_file(self, tenant_id: UUID, repository: str, file_path: str) -> Sequence[RepositoryChunk]: ...
    async def add(self, chunk: RepositoryChunk) -> None: ...
    async def remove_indexes(self, tenant_id: UUID, repository: str, file_path: str, indexes: set[int]) -> int: ...


class SqlAlchemyRepositoryChunkStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_file(self, tenant_id: UUID, repository: str, file_path: str) -> Sequence[RepositoryChunk]:
        result = await self._session.scalars(select(RepositoryChunk).where(
            RepositoryChunk.tenant_id == tenant_id,
            RepositoryChunk.repository == repository,
            RepositoryChunk.file_path == file_path,
        ))
        return result.all()

    async def add(self, chunk: RepositoryChunk) -> None:
        self._session.add(chunk)

    async def remove_indexes(self, tenant_id: UUID, repository: str, file_path: str, indexes: set[int]) -> int:
        if not indexes:
            return 0
        result = await self._session.execute(delete(RepositoryChunk).where(
            RepositoryChunk.tenant_id == tenant_id,
            RepositoryChunk.repository == repository,
            RepositoryChunk.file_path == file_path,
            RepositoryChunk.chunk_index.in_(indexes),
        ))
        return int(result.rowcount or 0)
