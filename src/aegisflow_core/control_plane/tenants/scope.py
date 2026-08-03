"""Fail-closed tenant-aware wrapper around an explicit AsyncSession."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Delete, Select, Update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_loader_criteria

from aegisflow_core.control_plane.domain import Base


class TenantScopeRequired(ValueError):
    """Raised before database access when no valid tenant scope exists."""


class TenantScopeViolation(PermissionError):
    """Raised when an operation can escape or contradict its tenant scope."""


@dataclass(frozen=True, slots=True)
class TenantScope:
    tenant_id: UUID
    actor_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, UUID):
            raise TenantScopeRequired("tenant_id is required")
        if not self.actor_reference.strip():
            raise TenantScopeRequired("actor_reference is required")


ModelT = TypeVar("ModelT", bound=Base)


def _tenant_models() -> tuple[type[Base], ...]:
    models = []
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if "tenant_id" in mapper.local_table.c:
            models.append(model)
    return tuple(models)


class TenantSession:
    """Expose only operations that can enforce an explicit tenant predicate."""

    def __init__(self, session: AsyncSession, scope: TenantScope) -> None:
        self._session = session
        self.scope = scope

    def add(self, instance: Base) -> None:
        self._assert_instance(instance)
        self._session.add(instance)

    def add_all(self, instances: list[Base]) -> None:
        for instance in instances:
            self._assert_instance(instance)
        self._session.add_all(instances)

    async def delete(self, instance: Base) -> None:
        self._assert_instance(instance)
        await self._session.delete(instance)

    async def execute(self, statement: Any) -> Any:
        return await self._session.execute(self._scoped(statement))

    async def scalar(self, statement: Any) -> Any:
        return (await self.execute(statement)).scalar_one_or_none()

    async def scalars(self, statement: Any) -> Any:
        return (await self.execute(statement)).scalars()

    async def get(self, model: type[ModelT], identifier: object) -> ModelT | None:
        if "tenant_id" not in model.__table__.c:
            raise TenantScopeViolation("tenant sessions cannot access root models")
        primary_key = list(model.__table__.primary_key.columns)
        if len(primary_key) != 1:
            raise TenantScopeViolation("composite primary keys require an explicit query")
        return await self.scalar(select(model).where(primary_key[0] == identifier))

    async def flush(self) -> None:
        for instance in self._session.new | self._session.dirty | self._session.deleted:
            if isinstance(instance, Base) and hasattr(instance, "tenant_id"):
                self._assert_instance(instance)
        await self._session.flush()

    async def commit(self) -> None:
        await self.flush()
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def close(self) -> None:
        await self._session.close()

    def _assert_instance(self, instance: Base) -> None:
        tenant_id = getattr(instance, "tenant_id", None)
        if tenant_id is None:
            raise TenantScopeViolation("tenant session requires a tenant-owned model")
        if tenant_id != self.scope.tenant_id:
            raise TenantScopeViolation("row tenant does not match session tenant")

    def _scoped(self, statement: Any) -> Any:
        tenant_id = self.scope.tenant_id
        if isinstance(statement, Select):
            entities = {
                item.get("entity") for item in statement.column_descriptions
                if item.get("entity") is not None
            }
            if not entities or any(
                not hasattr(entity, "__table__")
                or "tenant_id" not in entity.__table__.c
                for entity in entities
            ):
                raise TenantScopeViolation(
                    "tenant sessions require tenant-owned ORM entities"
                )
            for model in _tenant_models():
                statement = statement.options(
                    with_loader_criteria(
                        model,
                        lambda candidate: candidate.tenant_id == tenant_id,
                        include_aliases=True,
                    )
                )
            return statement
        if isinstance(statement, (Update, Delete)):
            entity = statement.entity_description.get("entity")
            if entity is None or "tenant_id" not in entity.__table__.c:
                raise TenantScopeViolation(
                    "tenant mutations require a tenant-owned ORM entity"
                )
            return statement.where(entity.tenant_id == tenant_id)
        raise TenantScopeViolation("raw or unscoped SQL is forbidden")
