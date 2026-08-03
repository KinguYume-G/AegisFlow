"""Static contract tests for the initial SQLAlchemy domain model."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from aegisflow_core.control_plane.domain import (
    Approval,
    AuditEvent,
    Base,
    IdempotencyRecord,
    ModelCircuitState,
    PromptSeries,
    PromptVersion,
    Run,
    RepositoryChunk,
    RunPromptVersion,
    Step,
    Tenant,
    Workflow,
)


MODELS = (
    Tenant, Workflow, Run, Step, Approval, AuditEvent, RepositoryChunk,
    IdempotencyRecord,
    ModelCircuitState,
    PromptSeries,
    PromptVersion,
    RunPromptVersion,
)


def _constraint_names(model: type[Base], kind: type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, kind) and constraint.name is not None
    }


def test_all_tables_declared() -> None:
    assert set(Base.metadata.tables) == {
        "tenants",
        "workflows",
        "runs",
        "steps",
        "approvals",
        "audit_events",
        "repository_chunks",
        "idempotency_records",
        "model_circuit_states",
        "prompt_series",
        "prompt_versions",
        "run_prompt_versions",
    }
    assert {model.__tablename__ for model in MODELS} == set(Base.metadata.tables)


def test_tenant_owned_tables_have_non_nullable_tenant_id() -> None:
    for model in MODELS[1:]:
        tenant_id = model.__table__.c.tenant_id
        assert tenant_id.nullable is False
        assert any(foreign_key.target_fullname == "tenants.id" for foreign_key in tenant_id.foreign_keys)


def test_database_owned_uuid_and_timestamp_defaults() -> None:
    for model in MODELS:
        identifier = model.__table__.c.id
        created_at = model.__table__.c.created_at
        assert identifier.type.as_uuid is True
        assert "gen_random_uuid" in str(identifier.server_default.arg)
        assert created_at.type.timezone is True
        assert "now()" in str(created_at.server_default.arg)


def test_named_check_and_unique_constraints_exist() -> None:
    assert "ck_workflows_status" in _constraint_names(Workflow, CheckConstraint)
    assert "ck_runs_status" in _constraint_names(Run, CheckConstraint)
    assert "ck_steps_status" in _constraint_names(Step, CheckConstraint)
    assert "ck_approvals_decision" in _constraint_names(Approval, CheckConstraint)
    assert "uq_workflows_tenant_name_version" in _constraint_names(
        Workflow, UniqueConstraint
    )
    assert "uq_steps_tenant_run_id" in _constraint_names(Step, UniqueConstraint)
    assert "uq_prompt_versions_tenant_name_version" in _constraint_names(
        PromptVersion, UniqueConstraint
    )
    assert "uq_run_prompt_versions_binding" in _constraint_names(
        RunPromptVersion, UniqueConstraint
    )


def test_tenant_scoped_foreign_keys_are_declared() -> None:
    run_foreign_keys = {
        tuple(element.parent.name for element in constraint.elements)
        for constraint in Run.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    step_foreign_keys = {
        tuple(element.parent.name for element in constraint.elements)
        for constraint in Step.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    approval_foreign_keys = {
        tuple(element.parent.name for element in constraint.elements)
        for constraint in Approval.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert ("tenant_id", "workflow_id", "workflow_version") in run_foreign_keys
    assert ("tenant_id", "run_id") in step_foreign_keys
    assert ("tenant_id", "run_id") in approval_foreign_keys
    assert ("tenant_id", "run_id", "step_id") in approval_foreign_keys


def test_audit_events_are_structurally_append_only() -> None:
    assert "updated_at" not in AuditEvent.__table__.c
