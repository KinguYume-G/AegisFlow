"""Strict, tenant-scoped lifecycle for LangGraph's PostgreSQL checkpointer."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from psycopg import AsyncConnection, sql


CHECKPOINT_SCHEMA = "langgraph"


class InvalidCheckpointIdentityError(ValueError):
    """A caller attempted to read or resume another checkpoint identity."""


@dataclass(frozen=True, slots=True)
class CheckpointIdentity:
    tenant_id: UUID
    run_id: UUID
    workflow_version: int

    def __post_init__(self) -> None:
        if self.workflow_version < 1:
            raise ValueError("workflow_version must be positive")

    @property
    def thread_id(self) -> str:
        # LangGraph reserves checkpoint_ns for subgraph traversal and rewrites it
        # at the root graph. The complete isolation key therefore belongs here.
        return (
            f"tenant:{self.tenant_id}:run:{self.run_id}:"
            f"workflow:{self.workflow_version}"
        )


def build_checkpoint_config(identity: CheckpointIdentity) -> RunnableConfig:
    """Build the only supported tenant/run checkpoint locator."""
    return {
        "configurable": {
            "thread_id": identity.thread_id,
            "checkpoint_ns": "",
            "aegisflow_tenant_id": str(identity.tenant_id),
            "aegisflow_run_id": str(identity.run_id),
            "aegisflow_workflow_version": identity.workflow_version,
        }
    }


def validate_checkpoint_config(
    config: RunnableConfig,
    expected: CheckpointIdentity,
) -> None:
    configurable = config.get("configurable") or {}
    if (
        configurable.get("thread_id") != expected.thread_id
        or configurable.get("checkpoint_ns") != ""
        or configurable.get("aegisflow_tenant_id") != str(expected.tenant_id)
        or configurable.get("aegisflow_run_id") != str(expected.run_id)
        or configurable.get("aegisflow_workflow_version")
        != expected.workflow_version
    ):
        raise InvalidCheckpointIdentityError(
            "checkpoint identity does not match tenant, run, and workflow version"
        )


def strict_checkpoint_serializer(
    allowed_types: Iterable[type[Any]] = (),
) -> JsonPlusSerializer:
    """Disable pickle and allow only explicitly named application types."""
    allowlist = tuple(allowed_types)
    return JsonPlusSerializer(
        pickle_fallback=False,
        allowed_json_modules=allowlist,
        allowed_msgpack_modules=allowlist,
    )


class PostgresCheckpointManager:
    """Own schema bootstrap and connection lifecycle for PostgresSaver."""

    def __init__(
        self,
        database_url: str,
        *,
        allowed_types: Iterable[type[Any]] = (),
    ) -> None:
        self._database_url = _psycopg_url(database_url)
        self._checkpoint_url = _with_search_path(self._database_url, CHECKPOINT_SCHEMA)
        self._serializer = strict_checkpoint_serializer(allowed_types)

    async def setup(self) -> None:
        """Idempotently create the library-owned schema and checkpoint tables."""
        async with await AsyncConnection.connect(
            self._database_url, autocommit=True
        ) as connection:
            await connection.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(CHECKPOINT_SCHEMA)
                )
            )
        async with AsyncPostgresSaver.from_conn_string(
            self._checkpoint_url, serde=self._serializer
        ) as saver:
            await saver.setup()

    @asynccontextmanager
    async def open(self) -> AsyncIterator[AsyncPostgresSaver]:
        async with AsyncPostgresSaver.from_conn_string(
            self._checkpoint_url, serde=self._serializer
        ) as saver:
            yield cast(AsyncPostgresSaver, saver)


def _psycopg_url(database_url: str) -> str:
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not normalized.startswith(("postgresql://", "postgres://")):
        raise ValueError("checkpoint database URL must be PostgreSQL")
    return normalized


def _with_search_path(database_url: str, schema: str) -> str:
    parts = urlsplit(database_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["options"] = f"-csearch_path={schema}"
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
