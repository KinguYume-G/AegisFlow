"""Add tenant memberships and fixed role assignments.

Revision ID: 0008_identity_rbac
Revises: 0007_tenant_versions
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_identity_rbac"
down_revision: str | None = "0007_tenant_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW_DEFAULT = sa.text("now()")


def upgrade() -> None:
    """Create tenant-local identity and role facts."""
    op.create_table(
        "tenant_memberships",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint("issuer <> '' AND length(issuer) <= 2048", name="ck_tenant_memberships_issuer_bounded"),
        sa.CheckConstraint("subject <> '' AND length(subject) <= 255", name="ck_tenant_memberships_subject_bounded"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_tenant_memberships_tenant_id_tenants", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_tenant_memberships"),
        sa.UniqueConstraint("tenant_id", "issuer", "subject", name="uq_tenant_memberships_principal"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tenant_memberships_tenant_id"),
    )
    op.create_table(
        "role_assignments",
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("membership_id", UUID, nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("assigned_by", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Text(), nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW_DEFAULT, nullable=False),
        sa.CheckConstraint("role IN ('Admin','Developer','Reviewer','Security','DevOps','Viewer')", name="ck_role_assignments_role"),
        sa.CheckConstraint("assigned_by <> '' AND length(assigned_by) <= 2304", name="ck_role_assignments_actor_bounded"),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by IS NULL) OR (revoked_at IS NOT NULL AND revoked_by IS NOT NULL)",
            name="ck_role_assignments_revocation_pair",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_role_assignments_tenant_id_tenants", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id", "membership_id"], ["tenant_memberships.tenant_id", "tenant_memberships.id"], name="fk_role_assignments_tenant_membership", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_role_assignments"),
    )
    op.create_index(
        "uq_role_assignments_active_role",
        "role_assignments",
        ["tenant_id", "membership_id", "role"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION public.aegisflow_guard_role_assignment_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'role_assignments rows cannot be deleted';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
               OR NEW.membership_id IS DISTINCT FROM OLD.membership_id
               OR NEW.role IS DISTINCT FROM OLD.role
               OR NEW.assigned_by IS DISTINCT FROM OLD.assigned_by
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'role assignment identity cannot be modified';
            END IF;
            IF OLD.revoked_at IS NULL
               AND NEW.revoked_at IS NOT NULL
               AND NEW.revoked_by IS NOT NULL THEN
                RETURN NEW;
            END IF;
            IF NEW.revoked_at IS NOT DISTINCT FROM OLD.revoked_at
               AND NEW.revoked_by IS NOT DISTINCT FROM OLD.revoked_by THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'role assignment can only transition to revoked';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_role_assignments_guard_mutation
        BEFORE UPDATE OR DELETE ON role_assignments
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_guard_role_assignment_mutation()
        """
    )


def downgrade() -> None:
    """Remove Wave 2 identity and RBAC facts."""
    op.execute("DROP TRIGGER trg_role_assignments_guard_mutation ON role_assignments")
    op.execute("DROP FUNCTION public.aegisflow_guard_role_assignment_mutation()")
    op.drop_index("uq_role_assignments_active_role", table_name="role_assignments")
    op.drop_table("role_assignments")
    op.drop_table("tenant_memberships")
