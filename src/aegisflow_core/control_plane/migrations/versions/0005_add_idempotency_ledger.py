"""Add the tenant-scoped idempotency fencing ledger."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_idempotency_ledger"
down_revision: str | None = "0004_protect_approval_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("arguments_hash", sa.Text(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("claim_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_reference", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("scope IN ('webhook_delivery','tool_call')", name="ck_idempotency_records_scope"),
        sa.CheckConstraint(
            "status IN ('executing','succeeded','failed_retryable','failed_final','compensated')",
            name="ck_idempotency_records_status",
        ),
        sa.CheckConstraint("attempt >= 1", name="ck_idempotency_records_attempt"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="RESTRICT",
            name="fk_idempotency_records_tenant_id_tenants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
        sa.UniqueConstraint("claim_token", name="uq_idempotency_records_claim_token"),
        sa.UniqueConstraint(
            "tenant_id", "scope", "idempotency_key",
            name="uq_idempotency_records_tenant_scope_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
