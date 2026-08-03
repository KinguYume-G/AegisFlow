"""Add immutable scoped tool registry.

Revision ID: 0009_tool_registry
Revises: 0008_identity_rbac
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_tool_registry"
down_revision: str | None = "0008_identity_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "tool_registrations",
        sa.Column("tenant_id", UUID, nullable=False), sa.Column("owner_scope", sa.Text(), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False), sa.Column("version", sa.Text(), nullable=False),
        sa.Column("adapter_identifier", sa.Text(), nullable=False), sa.Column("input_schema_hash", sa.Text(), nullable=False),
        sa.Column("output_schema_hash", sa.Text(), nullable=False), sa.Column("allowed_scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False), sa.Column("registered_by", sa.Text(), nullable=False),
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("canonical_name ~ '^[a-z][a-z0-9_]{0,127}$'", name="ck_tool_registrations_canonical_name"),
        sa.CheckConstraint("owner_scope <> '' AND length(owner_scope) <= 255", name="ck_tool_registrations_owner_scope"),
        sa.CheckConstraint("version <> '' AND length(version) <= 64", name="ck_tool_registrations_version"),
        sa.CheckConstraint("adapter_identifier <> '' AND length(adapter_identifier) <= 255", name="ck_tool_registrations_adapter_identifier"),
        sa.CheckConstraint("input_schema_hash ~ '^[0-9a-f]{64}$'", name="ck_tool_registrations_input_schema_hash"),
        sa.CheckConstraint("output_schema_hash ~ '^[0-9a-f]{64}$'", name="ck_tool_registrations_output_schema_hash"),
        sa.CheckConstraint("cardinality(allowed_scopes) > 0", name="ck_tool_registrations_allowed_scopes"),
        sa.CheckConstraint("risk_level IN ('L1','L2','L3')", name="ck_tool_registrations_risk_level"),
        sa.CheckConstraint("registered_by <> '' AND length(registered_by) <= 2304", name="ck_tool_registrations_registered_by"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_tool_registrations_tenant_id_tenants", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_tool_registrations"),
        sa.UniqueConstraint("tenant_id", "canonical_name", "version", name="uq_tool_registrations_tenant_name_version"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tool_registrations_tenant_id"),
    )
    op.create_table(
        "tool_disablements",
        sa.Column("tenant_id", UUID, nullable=False), sa.Column("registration_id", UUID, nullable=False),
        sa.Column("disabled_by", sa.Text(), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("disabled_by <> '' AND length(disabled_by) <= 2304", name="ck_tool_disablements_disabled_by"),
        sa.CheckConstraint("reason <> '' AND length(reason) <= 4096", name="ck_tool_disablements_reason"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_tool_disablements_tenant_id_tenants", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "registration_id"], ["tool_registrations.tenant_id", "tool_registrations.id"], name="fk_tool_disablements_tenant_registration", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_tool_disablements"),
        sa.UniqueConstraint("tenant_id", "registration_id", name="uq_tool_disablements_registration"),
    )
    for table in ("tool_registrations", "tool_disablements"):
        op.execute(f"""
        CREATE FUNCTION public.aegisflow_prevent_{table}_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION '{table} rows are append-only'; END; $$
        """)
        op.execute(f"""
        CREATE TRIGGER trg_{table}_prevent_mutation BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_prevent_{table}_mutation()
        """)


def downgrade() -> None:
    for table in ("tool_disablements", "tool_registrations"):
        op.execute(f"DROP TRIGGER trg_{table}_prevent_mutation ON {table}")
        op.execute(f"DROP FUNCTION public.aegisflow_prevent_{table}_mutation()")
    op.drop_table("tool_disablements")
    op.drop_table("tool_registrations")
