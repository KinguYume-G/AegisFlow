"""PostgreSQL enforcement tests for AF-103 invariants."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection

pytestmark = [pytest.mark.anyio, pytest.mark.database]


async def _insert_tenant(connection: AsyncConnection, slug: str) -> object:
    return await connection.scalar(
        text(
            "INSERT INTO tenants (slug, name) VALUES (:slug, :name) RETURNING id"
        ),
        {"slug": slug, "name": slug.title()},
    )


async def _insert_workflow(
    connection: AsyncConnection,
    tenant_id: object,
    *,
    name: str = "delivery",
    version: int = 1,
) -> object:
    return await connection.scalar(
        text(
            """
            INSERT INTO workflows (tenant_id, name, version, definition_hash)
            VALUES (:tenant_id, :name, :version, :definition_hash)
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "name": name,
            "version": version,
            "definition_hash": f"sha256:{uuid4().hex}",
        },
    )


async def _insert_run(
    connection: AsyncConnection,
    tenant_id: object,
    workflow_id: object,
    workflow_version: int = 1,
) -> object:
    return await connection.scalar(
        text(
            """
            INSERT INTO runs (tenant_id, workflow_id, workflow_version, status)
            VALUES (:tenant_id, :workflow_id, :workflow_version, 'pending')
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "workflow_id": workflow_id,
            "workflow_version": workflow_version,
        },
    )


async def _insert_step(
    connection: AsyncConnection,
    tenant_id: object,
    run_id: object,
    sequence: int = 1,
) -> object:
    return await connection.scalar(
        text(
            """
            INSERT INTO steps (tenant_id, run_id, name, sequence, status)
            VALUES (:tenant_id, :run_id, 'intake', :sequence, 'pending')
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "run_id": run_id, "sequence": sequence},
    )


async def _assert_rejected(
    connection: AsyncConnection, statement: str, parameters: dict[str, object]
) -> None:
    savepoint = await connection.begin_nested()
    try:
        with pytest.raises(DBAPIError):
            await connection.execute(text(statement), parameters)
    finally:
        if savepoint.is_active:
            await savepoint.rollback()


async def test_schema_and_triggers_exist(db_connection: AsyncConnection) -> None:
    tables = set(
        (
            await db_connection.execute(
                text(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename IN (
                        'tenants', 'workflows', 'runs', 'steps',
                        'approvals', 'audit_events'
                      )
                    """
                )
            )
        ).scalars()
    )
    triggers = set(
        (
            await db_connection.execute(
                text(
                    """
                    SELECT tgname FROM pg_trigger
                    WHERE NOT tgisinternal
                      AND tgname IN (
                        'trg_workflows_prevent_mutation',
                        'trg_audit_events_prevent_mutation'
                      )
                    """
                )
            )
        ).scalars()
    )
    check_constraints = set(
        (
            await db_connection.execute(
                text(
                    """
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE constraint_schema = 'public'
                      AND constraint_type = 'CHECK'
                      AND table_name IN ('workflows', 'runs', 'steps', 'approvals')
                      AND constraint_name LIKE 'ck\\_%' ESCAPE '\\'
                    """
                )
            )
        ).scalars()
    )

    assert tables == {
        "tenants",
        "workflows",
        "runs",
        "steps",
        "approvals",
        "audit_events",
    }
    assert triggers == {
        "trg_workflows_prevent_mutation",
        "trg_audit_events_prevent_mutation",
    }
    assert check_constraints == {
        "ck_workflows_status",
        "ck_workflows_version_positive",
        "ck_runs_status",
        "ck_steps_status",
        "ck_approvals_decision",
    }


async def test_valid_chain_and_run_level_approval(
    db_connection: AsyncConnection,
) -> None:
    tenant_id = await _insert_tenant(db_connection, f"tenant-{uuid4().hex}")
    workflow_id = await _insert_workflow(db_connection, tenant_id)
    run_id = await _insert_run(db_connection, tenant_id, workflow_id)
    step_id = await _insert_step(db_connection, tenant_id, run_id)

    step_approval = await db_connection.scalar(
        text(
            """
            INSERT INTO approvals (tenant_id, run_id, step_id, decision)
            VALUES (:tenant_id, :run_id, :step_id, 'pending') RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "run_id": run_id, "step_id": step_id},
    )
    run_approval = await db_connection.scalar(
        text(
            """
            INSERT INTO approvals (tenant_id, run_id, step_id, decision)
            VALUES (:tenant_id, :run_id, NULL, 'pending') RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "run_id": run_id},
    )
    audit_id = await db_connection.scalar(
        text(
            """
            INSERT INTO audit_events (tenant_id, actor, action, resource_type)
            VALUES (:tenant_id, 'system', 'created', 'run') RETURNING id
            """
        ),
        {"tenant_id": tenant_id},
    )

    assert all((step_approval, run_approval, audit_id))


async def test_workflow_immutability_and_status_transition(
    db_connection: AsyncConnection,
) -> None:
    tenant_id = await _insert_tenant(db_connection, f"tenant-{uuid4().hex}")
    workflow_id = await _insert_workflow(db_connection, tenant_id)

    await db_connection.execute(
        text("UPDATE workflows SET status = 'superseded' WHERE id = :id"),
        {"id": workflow_id},
    )
    status = await db_connection.scalar(
        text("SELECT status FROM workflows WHERE id = :id"), {"id": workflow_id}
    )
    assert status == "superseded"

    await _assert_rejected(
        db_connection,
        "UPDATE workflows SET definition_hash = 'changed' WHERE id = :id",
        {"id": workflow_id},
    )
    await _assert_rejected(
        db_connection,
        "UPDATE workflows SET status = 'active' WHERE id = :id",
        {"id": workflow_id},
    )
    await _assert_rejected(
        db_connection,
        "DELETE FROM workflows WHERE id = :id",
        {"id": workflow_id},
    )


async def test_audit_events_are_append_only(
    db_connection: AsyncConnection,
) -> None:
    tenant_id = await _insert_tenant(db_connection, f"tenant-{uuid4().hex}")
    audit_id = await db_connection.scalar(
        text(
            """
            INSERT INTO audit_events (tenant_id, actor, action, resource_type)
            VALUES (:tenant_id, 'system', 'created', 'workflow') RETURNING id
            """
        ),
        {"tenant_id": tenant_id},
    )

    await _assert_rejected(
        db_connection,
        "UPDATE audit_events SET action = 'changed' WHERE id = :id",
        {"id": audit_id},
    )
    await _assert_rejected(
        db_connection,
        "DELETE FROM audit_events WHERE id = :id",
        {"id": audit_id},
    )


async def test_cross_tenant_and_version_links_are_rejected(
    db_connection: AsyncConnection,
) -> None:
    tenant_a = await _insert_tenant(db_connection, f"tenant-a-{uuid4().hex}")
    tenant_b = await _insert_tenant(db_connection, f"tenant-b-{uuid4().hex}")
    workflow_a = await _insert_workflow(db_connection, tenant_a)
    workflow_b = await _insert_workflow(db_connection, tenant_b)
    run_a = await _insert_run(db_connection, tenant_a, workflow_a)
    run_b = await _insert_run(db_connection, tenant_b, workflow_b)

    await _assert_rejected(
        db_connection,
        """
        INSERT INTO runs (tenant_id, workflow_id, workflow_version, status)
        VALUES (:tenant_id, :workflow_id, 1, 'pending')
        """,
        {"tenant_id": tenant_a, "workflow_id": workflow_b},
    )
    await _assert_rejected(
        db_connection,
        """
        INSERT INTO runs (tenant_id, workflow_id, workflow_version, status)
        VALUES (:tenant_id, :workflow_id, 2, 'pending')
        """,
        {"tenant_id": tenant_a, "workflow_id": workflow_a},
    )
    await _assert_rejected(
        db_connection,
        """
        INSERT INTO steps (tenant_id, run_id, name, sequence, status)
        VALUES (:tenant_id, :run_id, 'intake', 1, 'pending')
        """,
        {"tenant_id": tenant_a, "run_id": run_b},
    )

    step_a = await _insert_step(db_connection, tenant_a, run_a)
    second_run_a = await _insert_run(db_connection, tenant_a, workflow_a)
    step_second_run = await _insert_step(db_connection, tenant_a, second_run_a)
    await _assert_rejected(
        db_connection,
        """
        INSERT INTO approvals (tenant_id, run_id, step_id, decision)
        VALUES (:tenant_id, :run_id, :step_id, 'pending')
        """,
        {"tenant_id": tenant_a, "run_id": run_a, "step_id": step_second_run},
    )
    await _assert_rejected(
        db_connection,
        """
        INSERT INTO approvals (tenant_id, run_id, step_id, decision)
        VALUES (:tenant_id, :run_id, :step_id, 'pending')
        """,
        {"tenant_id": tenant_b, "run_id": run_a, "step_id": step_a},
    )


async def test_unique_and_check_constraints_are_enforced(
    db_connection: AsyncConnection,
) -> None:
    tenant_id = await _insert_tenant(db_connection, f"tenant-{uuid4().hex}")
    await _insert_workflow(db_connection, tenant_id, name="delivery", version=1)

    await _assert_rejected(
        db_connection,
        """
        INSERT INTO workflows (tenant_id, name, version, definition_hash)
        VALUES (:tenant_id, 'delivery', 1, 'sha256:duplicate')
        """,
        {"tenant_id": tenant_id},
    )
    await _assert_rejected(
        db_connection,
        """
        INSERT INTO runs (tenant_id, workflow_id, workflow_version, status)
        VALUES (:tenant_id, :workflow_id, 1, 'unknown')
        """,
        {"tenant_id": tenant_id, "workflow_id": uuid4()},
    )
