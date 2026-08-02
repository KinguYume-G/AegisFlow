"""Create the initial tenant-owned domain model.

Revision ID: 0001_initial_domain_model
Revises: None
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_domain_model"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW_DEFAULT = sa.text("now()")


def upgrade() -> None:
    """Create six tables, tenant-safe relationships, and immutability guards."""
    op.create_table(
        "tenants",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW_DEFAULT,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_table(
        "workflows",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition_hash", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'superseded')",
            name=op.f("ck_workflows_status"),
        ),
        sa.CheckConstraint(
            "version > 0", name=op.f("ck_workflows_version_positive")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_workflows_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflows"),
        sa.UniqueConstraint(
            "tenant_id", "name", "version", name="uq_workflows_tenant_name_version"
        ),
        sa.UniqueConstraint(
            "tenant_id", "id", "version", name="uq_workflows_tenant_id_version"
        ),
    )
    op.create_table(
        "runs",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("workflow_id", UUID, nullable=False),
        sa.Column("workflow_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'waiting_clarification', "
            "'waiting_approval', 'completed', 'failed', 'cancelled')",
            name=op.f("ck_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_runs_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "workflow_id", "workflow_version"],
            ["workflows.tenant_id", "workflows.id", "workflows.version"],
            name="fk_runs_tenant_workflow_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_runs"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_runs_tenant_id"),
    )
    op.create_table(
        "steps",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'skipped')",
            name=op.f("ck_steps_status"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_steps_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_steps_tenant_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steps"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_steps_run_sequence"),
        sa.UniqueConstraint(
            "tenant_id", "run_id", "id", name="uq_steps_tenant_run_id"
        ),
    )
    op.create_table(
        "approvals",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("step_id", UUID, nullable=True),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint(
            "decision IN ('pending', 'approved', 'rejected')",
            name=op.f("ck_approvals_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_approvals_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id"],
            ["runs.tenant_id", "runs.id"],
            name="fk_approvals_tenant_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id", "step_id"],
            ["steps.tenant_id", "steps.run_id", "steps.id"],
            name="fk_approvals_tenant_run_step",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_approvals"),
    )
    op.create_table(
        "audit_events",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audit_events_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )

    op.execute(
        """
        CREATE FUNCTION public.aegisflow_prevent_workflow_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'workflows rows cannot be deleted';
            END IF;

            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
               OR NEW.name IS DISTINCT FROM OLD.name
               OR NEW.version IS DISTINCT FROM OLD.version
               OR NEW.definition_hash IS DISTINCT FROM OLD.definition_hash
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'workflows immutable columns cannot be modified';
            END IF;

            IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
                RETURN NEW;
            END IF;

            IF OLD.status = 'active' AND NEW.status = 'superseded' THEN
                RETURN NEW;
            END IF;

            RAISE EXCEPTION 'workflows.status can only transition from active to superseded';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_workflows_prevent_mutation
        BEFORE UPDATE OR DELETE ON workflows
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_workflow_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.aegisflow_prevent_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events rows are append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_events_prevent_mutation
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_audit_mutation()
        """
    )


def downgrade() -> None:
    """Remove all AF-103 database objects in dependency-safe order."""
    op.execute("DROP TRIGGER trg_audit_events_prevent_mutation ON audit_events")
    op.execute("DROP FUNCTION public.aegisflow_prevent_audit_mutation()")
    op.execute("DROP TRIGGER trg_workflows_prevent_mutation ON workflows")
    op.execute("DROP FUNCTION public.aegisflow_prevent_workflow_mutation()")
    op.drop_table("audit_events")
    op.drop_table("approvals")
    op.drop_table("steps")
    op.drop_table("runs")
    op.drop_table("workflows")
    op.drop_table("tenants")
