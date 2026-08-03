"""Add M4 tenant-version foundations.

Revision ID: 0007_tenant_versions
Revises: 0006_add_model_circuit_state
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_tenant_versions"
down_revision: str | None = "0006_add_model_circuit_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW_DEFAULT = sa.text("now()")


def upgrade() -> None:
    """Store immutable prompt/workflow payloads and exact Run bindings."""
    op.add_column(
        "workflows",
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        "uq_workflows_tenant_name_active",
        "workflows",
        ["tenant_id", "name"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.aegisflow_prevent_workflow_mutation()
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
               OR NEW.definition IS DISTINCT FROM OLD.definition
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

    op.create_table(
        "prompt_series",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("latest_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint(
            "latest_version >= 0", name="ck_prompt_series_latest_version_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_prompt_series_tenant_id_tenants", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_prompt_series"),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_prompt_series_tenant_name"
        ),
    )
    op.create_table(
        "prompt_versions",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("source_version_id", UUID, nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint("version > 0", name="ck_prompt_versions_version_positive"),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_prompt_versions_content_hash_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_prompt_versions_tenant_id_tenants", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            name="fk_prompt_versions_tenant_source", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_prompt_versions"),
        sa.UniqueConstraint(
            "tenant_id", "name", "version",
            name="uq_prompt_versions_tenant_name_version",
        ),
        sa.UniqueConstraint(
            "tenant_id", "id", name="uq_prompt_versions_tenant_id"
        ),
    )
    op.create_table(
        "run_prompt_versions",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("prompt_name", sa.Text(), nullable=False),
        sa.Column("prompt_version_id", UUID, nullable=False),
        sa.Column("bound_by", sa.Text(), nullable=False),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_run_prompt_versions_tenant_id_tenants", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "run_id"], ["runs.tenant_id", "runs.id"],
            name="fk_run_prompt_versions_tenant_run", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "prompt_version_id"],
            ["prompt_versions.tenant_id", "prompt_versions.id"],
            name="fk_run_prompt_versions_tenant_prompt", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_run_prompt_versions"),
        sa.UniqueConstraint(
            "tenant_id", "run_id", "prompt_name",
            name="uq_run_prompt_versions_binding",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION public.aegisflow_prevent_prompt_version_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'prompt_versions rows are immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prompt_versions_prevent_mutation
        BEFORE UPDATE OR DELETE ON prompt_versions
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_prompt_version_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.aegisflow_prevent_run_prompt_binding_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'run_prompt_versions rows are immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_run_prompt_versions_prevent_mutation
        BEFORE UPDATE OR DELETE ON run_prompt_versions
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_run_prompt_binding_mutation()
        """
    )


def downgrade() -> None:
    """Remove M4 version facts and restore the previous workflow guard."""
    op.execute(
        "DROP TRIGGER trg_run_prompt_versions_prevent_mutation ON run_prompt_versions"
    )
    op.execute("DROP FUNCTION public.aegisflow_prevent_run_prompt_binding_mutation()")
    op.execute("DROP TRIGGER trg_prompt_versions_prevent_mutation ON prompt_versions")
    op.execute("DROP FUNCTION public.aegisflow_prevent_prompt_version_mutation()")
    op.drop_table("run_prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_table("prompt_series")
    op.drop_index("uq_workflows_tenant_name_active", table_name="workflows")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.aegisflow_prevent_workflow_mutation()
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
    op.drop_column("workflows", "definition")
