"""AF-410/AF-411 immutable version service tests."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.domain import (
    AuditEvent,
    PromptVersion,
    Run,
    RunPromptVersion,
    Tenant,
    Workflow,
)
from aegisflow_core.control_plane.versions import (
    LegacyWorkflowDefinitionUnavailable,
    VersionConflict,
    bind_prompt_version,
    canonical_definition,
    content_hash,
    publish_prompt_version,
    publish_workflow_version,
    resolve_workflow_definition,
    rollback_prompt_version,
    rollback_workflow_version,
)


def test_canonical_definition_and_hash_are_stable() -> None:
    first, first_hash = canonical_definition({"b": [2, 1], "a": "x"})
    second, second_hash = canonical_definition({"a": "x", "b": [2, 1]})
    assert first == second == {"a": "x", "b": [2, 1]}
    assert first_hash == second_hash == content_hash('{"a":"x","b":[2,1]}')
    with pytest.raises(ValueError):
        canonical_definition({"invalid": float("nan")})


@pytest.mark.database
@pytest.mark.anyio
async def test_prompt_and_workflow_versions_are_immutable_and_run_bound() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            async with sessions.begin() as session:
                tenant = Tenant(slug=f"version-{uuid4()}", name="Versions")
                session.add(tenant)
                await session.flush()

                prompt_v1 = await publish_prompt_version(
                    session, tenant.id, "planner.system", "Plan safely.", "subject:admin"
                )
                assert (
                    await publish_prompt_version(
                        session,
                        tenant.id,
                        "planner.system",
                        "Plan safely.",
                        "subject:admin",
                        requested_version=1,
                    )
                ).id == prompt_v1.id
                with pytest.raises(VersionConflict):
                    await publish_prompt_version(
                        session,
                        tenant.id,
                        "planner.system",
                        "Different content.",
                        "subject:admin",
                        requested_version=1,
                    )
                prompt_v2 = await publish_prompt_version(
                    session, tenant.id, "planner.system", "Plan with evidence.", "subject:admin"
                )
                prompt_v3 = await rollback_prompt_version(
                    session, tenant.id, "planner.system", 1, "subject:admin"
                )
                assert [prompt_v1.version, prompt_v2.version, prompt_v3.version] == [1, 2, 3]
                assert prompt_v3.template == prompt_v1.template
                assert prompt_v3.source_version_id == prompt_v1.id

                workflow_v1 = await publish_workflow_version(
                    session,
                    tenant.id,
                    "delivery",
                    {"entrypoint": "aegisflow.delivery.v1", "nodes": ["intake"]},
                    "subject:admin",
                )
                assert (
                    await publish_workflow_version(
                        session,
                        tenant.id,
                        "delivery",
                        {"nodes": ["intake"], "entrypoint": "aegisflow.delivery.v1"},
                        "subject:admin",
                        requested_version=1,
                    )
                ).id == workflow_v1.id
                with pytest.raises(VersionConflict):
                    await publish_workflow_version(
                        session,
                        tenant.id,
                        "delivery",
                        {"entrypoint": "different"},
                        "subject:admin",
                        requested_version=1,
                    )
                run = Run(
                    tenant_id=tenant.id,
                    workflow_id=workflow_v1.id,
                    workflow_version=workflow_v1.version,
                    status="pending",
                )
                session.add(run)
                await session.flush()
                binding = await bind_prompt_version(
                    session, tenant.id, run.id, prompt_v1.id, "subject:admin"
                )
                assert (
                    await bind_prompt_version(
                        session, tenant.id, run.id, prompt_v1.id, "subject:admin"
                    )
                ).id == binding.id
                with pytest.raises(VersionConflict):
                    await bind_prompt_version(
                        session, tenant.id, run.id, prompt_v2.id, "subject:admin"
                    )
                other_tenant = Tenant(slug=f"other-{uuid4()}", name="Other")
                session.add(other_tenant)
                await session.flush()
                with pytest.raises(LookupError):
                    await bind_prompt_version(
                        session,
                        other_tenant.id,
                        run.id,
                        prompt_v1.id,
                        "subject:admin",
                    )

                workflow_v2 = await publish_workflow_version(
                    session,
                    tenant.id,
                    "delivery",
                    {"entrypoint": "aegisflow.delivery.v1", "nodes": ["intake", "planner"]},
                    "subject:admin",
                )
                workflow_v3 = await rollback_workflow_version(
                    session, tenant.id, "delivery", 1, "subject:admin"
                )
                assert [workflow_v1.version, workflow_v2.version, workflow_v3.version] == [1, 2, 3]
                assert workflow_v1.status == "superseded"
                assert run.workflow_id == workflow_v1.id
                assert run.workflow_version == 1
                assert await resolve_workflow_definition(
                    session, tenant.id, workflow_v1.id, 1
                ) == {"entrypoint": "aegisflow.delivery.v1", "nodes": ["intake"]}
                assert workflow_v3.definition == workflow_v1.definition

                audit_actions = set(
                    await session.scalars(
                        select(AuditEvent.action).where(AuditEvent.tenant_id == tenant.id)
                    )
                )
                assert {
                    "prompt.version.published",
                    "prompt.version.rolled_back",
                    "prompt.version.bound",
                    "workflow.version.published",
                    "workflow.version.rolled_back",
                } <= audit_actions
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_legacy_workflow_definition_fails_honestly() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            async with sessions.begin() as session:
                slug = f"legacy-{uuid4()}"
                tenant = Tenant(slug=slug, name="Legacy")
                session.add(tenant)
                await session.flush()
                from aegisflow_core.control_plane.domain import Workflow

                legacy = Workflow(
                    tenant_id=tenant.id,
                    name="legacy",
                    version=1,
                    definition_hash="legacy-hash",
                    definition=None,
                    status="active",
                )
                session.add(legacy)
                await session.flush()
                with pytest.raises(LegacyWorkflowDefinitionUnavailable):
                    await resolve_workflow_definition(
                        session, tenant.id, legacy.id, legacy.version
                    )
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_database_triggers_reject_version_and_binding_mutation() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            async with sessions.begin() as session:
                tenant = Tenant(slug=f"trigger-{uuid4()}", name="Triggers")
                session.add(tenant)
                await session.flush()
                prompt = await publish_prompt_version(
                    session, tenant.id, "system", "immutable", "subject:admin"
                )
                workflow = await publish_workflow_version(
                    session, tenant.id, "delivery", {"nodes": []}, "subject:admin"
                )
                run = Run(
                    tenant_id=tenant.id,
                    workflow_id=workflow.id,
                    workflow_version=workflow.version,
                    status="pending",
                )
                session.add(run)
                await session.flush()
                binding = await bind_prompt_version(
                    session, tenant.id, run.id, prompt.id, "subject:admin"
                )

                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(
                            update(PromptVersion)
                            .where(PromptVersion.id == prompt.id)
                            .values(template="changed")
                        )
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(
                            delete(PromptVersion).where(PromptVersion.id == prompt.id)
                        )
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(
                            update(RunPromptVersion)
                            .where(RunPromptVersion.id == binding.id)
                            .values(bound_by="subject:other")
                        )
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.database
@pytest.mark.anyio
async def test_concurrent_publication_allocates_unique_ordered_versions() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    slug = f"concurrent-version-{uuid4()}"
    async with sessions.begin() as session:
        tenant = Tenant(slug=slug, name="Concurrent Versions")
        session.add(tenant)
        await session.flush()
        tenant_id = tenant.id

    async def prompt(index: int) -> int:
        async with sessions.begin() as session:
            item = await publish_prompt_version(
                session, tenant_id, "planner", f"template-{index}", f"subject:{index}"
            )
            return item.version

    async def workflow(index: int) -> int:
        async with sessions.begin() as session:
            item = await publish_workflow_version(
                session,
                tenant_id,
                "delivery",
                {"generation": index},
                f"subject:{index}",
            )
            return item.version

    try:
        prompt_versions = await asyncio.gather(*(prompt(index) for index in range(5)))
        workflow_versions = await asyncio.gather(
            *(workflow(index) for index in range(5))
        )
        assert sorted(prompt_versions) == [1, 2, 3, 4, 5]
        assert sorted(workflow_versions) == [1, 2, 3, 4, 5]
        async with sessions() as session:
            active = list(
                await session.scalars(
                    select(Workflow).where(
                        Workflow.tenant_id == tenant_id,
                        Workflow.name == "delivery",
                        Workflow.status == "active",
                    )
                )
            )
            assert len(active) == 1 and active[0].version == 5
    finally:
        # Immutable version rows intentionally remain until the disposable test
        # database is reset; deleting them would invalidate the trigger proof.
        await engine.dispose()
