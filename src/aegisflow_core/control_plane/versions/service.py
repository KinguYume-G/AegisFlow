"""Concurrency-safe immutable prompt and workflow publication."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from aegisflow_core.control_plane.domain import (
    AuditEvent,
    PromptSeries,
    PromptVersion,
    Run,
    RunPromptVersion,
    Workflow,
)

_MAX_DEFINITION_BYTES = 262_144
_MAX_PROMPT_CHARS = 100_000


class VersionConflict(ValueError):
    """An immutable version identity was reused with different content."""


class LegacyWorkflowDefinitionUnavailable(LookupError):
    """A legacy hash-only workflow cannot be falsely reconstructed."""


def content_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def canonical_definition(
    definition: Mapping[str, object],
) -> tuple[dict[str, object], str]:
    try:
        encoded = json.dumps(
            definition,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("workflow definition must be finite JSON") from exc
    if len(encoded.encode("utf-8")) > _MAX_DEFINITION_BYTES:
        raise ValueError("workflow definition is too large")
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ValueError("workflow definition must be an object")
    return decoded, content_hash(encoded)


def _text(value: str, field: str, *, maximum: int = 255) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain at most {maximum} characters")
    return normalized


async def _workflow_lock(
    session: AsyncSession, tenant_id: UUID, kind: str, name: str
) -> None:
    key = f"aegisflow:{tenant_id}:{kind}:{name}"
    await session.execute(
        select(func.pg_advisory_xact_lock(func.hashtextextended(key, 0)))
    )


def _audit(
    *,
    tenant_id: UUID,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: UUID,
    reason: str,
) -> AuditEvent:
    return AuditEvent(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        decision="allow",
        reason=reason,
    )


async def publish_prompt_version(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    template: str,
    actor_reference: str,
    *,
    requested_version: int | None = None,
    source_version_id: UUID | None = None,
    audit_action: str = "prompt.version.published",
) -> PromptVersion:
    name = _text(name, "prompt name")
    actor = _text(actor_reference, "actor reference")
    if not template or len(template) > _MAX_PROMPT_CHARS:
        raise ValueError("prompt template must contain bounded text")
    if requested_version is not None and requested_version < 1:
        raise ValueError("requested_version must be positive")

    await session.execute(
        insert(PromptSeries)
        .values(tenant_id=tenant_id, name=name, latest_version=0)
        .on_conflict_do_nothing(
            index_elements=[PromptSeries.tenant_id, PromptSeries.name]
        )
    )
    series = await session.scalar(
        select(PromptSeries)
        .where(PromptSeries.tenant_id == tenant_id, PromptSeries.name == name)
        .with_for_update()
    )
    if series is None:
        raise RuntimeError("prompt series could not be locked")

    version = requested_version or series.latest_version + 1
    digest = content_hash(template)
    existing = await session.scalar(
        select(PromptVersion).where(
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.name == name,
            PromptVersion.version == version,
        )
    )
    if existing is not None:
        if (
            existing.content_hash != digest
            or existing.template != template
            or existing.source_version_id != source_version_id
        ):
            raise VersionConflict("prompt version already has different content")
        return existing
    if version != series.latest_version + 1:
        raise VersionConflict("prompt versions must be sequential")

    prompt = PromptVersion(
        tenant_id=tenant_id,
        name=name,
        version=version,
        template=template,
        content_hash=digest,
        created_by=actor,
        source_version_id=source_version_id,
    )
    series.latest_version = version
    session.add(prompt)
    await session.flush()
    session.add(
        _audit(
            tenant_id=tenant_id,
            actor=actor,
            action=audit_action,
            resource_type="prompt_version",
            resource_id=prompt.id,
            reason=f"{name}@{version}",
        )
    )
    return prompt


async def rollback_prompt_version(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    source_version: int,
    actor_reference: str,
) -> PromptVersion:
    source = await session.scalar(
        select(PromptVersion).where(
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.name == name.strip(),
            PromptVersion.version == source_version,
        )
    )
    if source is None:
        raise LookupError("prompt source version does not exist")
    return await publish_prompt_version(
        session,
        tenant_id,
        source.name,
        source.template,
        actor_reference,
        source_version_id=source.id,
        audit_action="prompt.version.rolled_back",
    )


async def bind_prompt_version(
    session: AsyncSession,
    tenant_id: UUID,
    run_id: UUID,
    prompt_version_id: UUID,
    actor_reference: str,
) -> RunPromptVersion:
    actor = _text(actor_reference, "actor reference")
    run = await session.scalar(
        select(Run).where(Run.tenant_id == tenant_id, Run.id == run_id)
    )
    prompt = await session.scalar(
        select(PromptVersion).where(
            PromptVersion.tenant_id == tenant_id,
            PromptVersion.id == prompt_version_id,
        )
    )
    if run is None or prompt is None:
        raise LookupError("run and prompt version must belong to the tenant")

    statement = (
        insert(RunPromptVersion)
        .values(
            tenant_id=tenant_id,
            run_id=run_id,
            prompt_name=prompt.name,
            prompt_version_id=prompt.id,
            bound_by=actor,
        )
        .on_conflict_do_nothing(
            index_elements=[
                RunPromptVersion.tenant_id,
                RunPromptVersion.run_id,
                RunPromptVersion.prompt_name,
            ]
        )
        .returning(RunPromptVersion)
    )
    binding = (await session.execute(statement)).scalar_one_or_none()
    if binding is None:
        binding = await session.scalar(
            select(RunPromptVersion).where(
                RunPromptVersion.tenant_id == tenant_id,
                RunPromptVersion.run_id == run_id,
                RunPromptVersion.prompt_name == prompt.name,
            )
        )
        if binding is None:
            raise RuntimeError("prompt binding could not be loaded")
        if binding.prompt_version_id != prompt.id:
            raise VersionConflict("run prompt binding is immutable")
        return binding
    session.add(
        _audit(
            tenant_id=tenant_id,
            actor=actor,
            action="prompt.version.bound",
            resource_type="run_prompt_version",
            resource_id=binding.id,
            reason=f"run={run_id};prompt={prompt.name}@{prompt.version}",
        )
    )
    return binding


async def publish_workflow_version(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    definition: Mapping[str, object],
    actor_reference: str,
    *,
    requested_version: int | None = None,
    audit_action: str = "workflow.version.published",
) -> Workflow:
    name = _text(name, "workflow name")
    actor = _text(actor_reference, "actor reference")
    canonical, digest = canonical_definition(definition)
    if requested_version is not None and requested_version < 1:
        raise ValueError("requested_version must be positive")

    await _workflow_lock(session, tenant_id, "workflow", name)
    latest = await session.scalar(
        select(func.max(Workflow.version)).where(
            Workflow.tenant_id == tenant_id, Workflow.name == name
        )
    )
    latest = latest or 0
    version = requested_version or latest + 1
    existing = await session.scalar(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.name == name,
            Workflow.version == version,
        )
    )
    if existing is not None:
        if existing.definition_hash != digest or existing.definition != canonical:
            raise VersionConflict("workflow version already has different content")
        return existing
    if version != latest + 1:
        raise VersionConflict("workflow versions must be sequential")

    active = await session.scalar(
        select(Workflow)
        .where(
            Workflow.tenant_id == tenant_id,
            Workflow.name == name,
            Workflow.status == "active",
        )
        .with_for_update()
    )
    if active is not None:
        active.status = "superseded"
        await session.flush()

    workflow = Workflow(
        tenant_id=tenant_id,
        name=name,
        version=version,
        definition_hash=digest,
        definition=canonical,
        status="active",
    )
    session.add(workflow)
    await session.flush()
    session.add(
        _audit(
            tenant_id=tenant_id,
            actor=actor,
            action=audit_action,
            resource_type="workflow_version",
            resource_id=workflow.id,
            reason=f"{name}@{version}",
        )
    )
    return workflow


async def rollback_workflow_version(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    source_version: int,
    actor_reference: str,
) -> Workflow:
    source = await session.scalar(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.name == name.strip(),
            Workflow.version == source_version,
        )
    )
    if source is None:
        raise LookupError("workflow source version does not exist")
    if source.definition is None:
        raise LegacyWorkflowDefinitionUnavailable(
            "legacy workflow definition payload is unavailable"
        )
    return await publish_workflow_version(
        session,
        tenant_id,
        source.name,
        source.definition,
        actor_reference,
        audit_action="workflow.version.rolled_back",
    )


async def resolve_workflow_definition(
    session: AsyncSession,
    tenant_id: UUID,
    workflow_id: UUID,
    workflow_version: int,
) -> dict[str, Any]:
    workflow = await session.scalar(
        select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.id == workflow_id,
            Workflow.version == workflow_version,
        )
    )
    if workflow is None:
        raise LookupError("workflow version does not exist for tenant")
    if workflow.definition is None:
        raise LegacyWorkflowDefinitionUnavailable(
            "legacy workflow definition payload is unavailable"
        )
    return json.loads(json.dumps(workflow.definition))
