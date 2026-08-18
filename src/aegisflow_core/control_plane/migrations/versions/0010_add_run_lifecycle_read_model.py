"""Add the local MVP Run lifecycle read model.

Revision ID: 0010_run_lifecycle
Revises: 0009_tool_registry
Create Date: 2026-08-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_run_lifecycle"
down_revision: str | None = "0009_tool_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW_DEFAULT = sa.text("now()")


def _identity(table: str) -> list[sa.Column]:
    return [
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False
        ),
    ]


def _tenant_run_foreign_key(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", "run_id"],
        ["runs.tenant_id", "runs.id"],
        name=f"fk_{table}_tenant_run",
        ondelete="RESTRICT",
    )


def _append_only(table: str) -> None:
    op.execute(
        f"""
        CREATE FUNCTION public.aegisflow_prevent_{table}_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION '{table} rows are append-only'; END; $$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_prevent_mutation
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_{table}_mutation()
        """
    )


def upgrade() -> None:
    op.add_column("approvals", sa.Column("action_preview", postgresql.JSONB(), nullable=True))
    op.add_column("approvals", sa.Column("action_digest", sa.Text(), nullable=True))
    op.create_check_constraint(
        "action_pair",
        "approvals",
        "(action_preview IS NULL AND action_digest IS NULL) OR "
        "(action_preview IS NOT NULL AND action_digest ~ '^[0-9a-f]{64}$')",
    )

    op.create_table(
        "run_requests",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("repository_owner", sa.Text(), nullable=False),
        sa.Column("repository_name", sa.Text(), nullable=False),
        sa.Column("base_ref", sa.Text(), nullable=False),
        sa.Column("base_sha", sa.Text(), nullable=False),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("trace_id", UUID, nullable=False),
        sa.Column("temporal_workflow_id", sa.Text(), nullable=False),
        *_identity("run_requests"),
        sa.CheckConstraint("source_type IN ('prd','issue','bug')", name="ck_run_requests_source_type"),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_run_requests_title_bounded"),
        sa.CheckConstraint("length(body) BETWEEN 20 AND 50000", name="ck_run_requests_body_bounded"),
        sa.CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'", name="ck_run_requests_input_hash"),
        sa.CheckConstraint("base_sha ~ '^[0-9a-f]{40}$'", name="ck_run_requests_base_sha"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_run_requests_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("run_requests"),
        sa.PrimaryKeyConstraint("id", name="pk_run_requests"),
        sa.UniqueConstraint("tenant_id", "run_id", name="uq_run_requests_tenant_run"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_run_requests_tenant_idempotency"),
    )
    op.create_table(
        "clarification_requests",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("step_key", sa.Text(), nullable=False),
        sa.Column("questions", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=True),
        sa.Column("answered_by", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        *_identity("clarification_requests"),
        sa.CheckConstraint("status IN ('pending','answered')", name="ck_clarification_requests_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_clarification_requests_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("clarification_requests"),
        sa.PrimaryKeyConstraint("id", name="pk_clarification_requests"),
        sa.UniqueConstraint("tenant_id", "run_id", "step_key", name="uq_clarification_requests_run_step"),
    )
    op.create_table(
        "run_events",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        *_identity("run_events"),
        sa.CheckConstraint("sequence > 0", name="ck_run_events_sequence_positive"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_run_events_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("run_events"),
        sa.PrimaryKeyConstraint("id", name="pk_run_events"),
        sa.UniqueConstraint("tenant_id", "run_id", "sequence", name="uq_run_events_sequence"),
    )
    op.create_table(
        "run_traces",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("step_id", UUID, nullable=True),
        sa.Column("trace_id", UUID, nullable=False),
        sa.Column("event_id", UUID, nullable=False),
        sa.Column("agent", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_digest", sa.Text(), nullable=False),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False),
        sa.Column("cost_usage", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        *_identity("run_traces"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_run_traces_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("run_traces"),
        sa.PrimaryKeyConstraint("id", name="pk_run_traces"),
        sa.UniqueConstraint("tenant_id", "event_id", name="uq_run_traces_event"),
    )
    op.create_table(
        "run_artifacts",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        *_identity("run_artifacts"),
        sa.CheckConstraint("kind IN ('context','plan','sandbox','diff','draft_pr_candidate','failure')", name="ck_run_artifacts_kind"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_run_artifacts_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("run_artifacts"),
        sa.PrimaryKeyConstraint("id", name="pk_run_artifacts"),
        sa.UniqueConstraint("tenant_id", "run_id", "kind", name="uq_run_artifacts_kind"),
    )
    op.create_table(
        "run_evaluations",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("task_success", sa.Boolean(), nullable=False),
        sa.Column("tool_success_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("completed_steps", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        *_identity("run_evaluations"),
        sa.CheckConstraint("outcome IN ('completed','failed','cancelled')", name="ck_run_evaluations_outcome"),
        sa.CheckConstraint("tool_success_rate BETWEEN 0 AND 1", name="ck_run_evaluations_tool_success_rate"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_run_evaluations_tenant_id_tenants", ondelete="RESTRICT"),
        _tenant_run_foreign_key("run_evaluations"),
        sa.PrimaryKeyConstraint("id", name="pk_run_evaluations"),
        sa.UniqueConstraint("tenant_id", "run_id", name="uq_run_evaluations_tenant_run"),
    )

    for table in ("run_requests", "run_events", "run_traces", "run_artifacts", "run_evaluations"):
        _append_only(table)
    op.execute(
        """
        CREATE FUNCTION public.aegisflow_protect_clarification_request()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'clarification_requests rows cannot be deleted';
            END IF;
            IF OLD.status <> 'pending' OR NEW.status <> 'answered'
               OR NEW.answers IS NULL OR NEW.answered_by IS NULL OR NEW.answered_at IS NULL THEN
                RAISE EXCEPTION 'clarification permits one pending to answered transition';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
               OR NEW.run_id IS DISTINCT FROM OLD.run_id OR NEW.step_key IS DISTINCT FROM OLD.step_key
               OR NEW.questions IS DISTINCT FROM OLD.questions OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'clarification identity cannot be modified';
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_clarification_requests_protect_transition
        BEFORE UPDATE OR DELETE ON clarification_requests
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_protect_clarification_request()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_clarification_requests_protect_transition ON clarification_requests")
    op.execute("DROP FUNCTION public.aegisflow_protect_clarification_request()")
    for table in reversed(("run_requests", "run_events", "run_traces", "run_artifacts", "run_evaluations")):
        op.execute(f"DROP TRIGGER trg_{table}_prevent_mutation ON {table}")
        op.execute(f"DROP FUNCTION public.aegisflow_prevent_{table}_mutation()")
    for table in (
        "run_evaluations",
        "run_artifacts",
        "run_traces",
        "run_events",
        "clarification_requests",
        "run_requests",
    ):
        op.drop_table(table)
    op.drop_constraint("action_pair", "approvals", type_="check")
    op.drop_column("approvals", "action_digest")
    op.drop_column("approvals", "action_preview")
