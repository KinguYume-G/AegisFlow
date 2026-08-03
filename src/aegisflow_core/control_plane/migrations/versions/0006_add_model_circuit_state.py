"""Add shared model circuit state and compensation ledger scope."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_add_model_circuit_state"
down_revision: str | None = "0005_add_idempotency_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_idempotency_records_scope", "idempotency_records", type_="check"
    )
    op.create_check_constraint(
        "ck_idempotency_records_scope",
        "idempotency_records",
        "scope IN ('webhook_delivery','tool_call','compensation')",
    )
    op.create_table(
        "model_circuit_states",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("probe_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("probe_lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('closed','open','half_open')",
            name="ck_model_circuit_states_status",
        ),
        sa.CheckConstraint(
            "failure_count >= 0", name="ck_model_circuit_states_failure_count"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_model_circuit_states_tenant_id_tenants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_circuit_states"),
        sa.UniqueConstraint(
            "tenant_id",
            "route",
            name="uq_model_circuit_states_tenant_route",
        ),
    )


def downgrade() -> None:
    op.drop_table("model_circuit_states")
    op.drop_constraint(
        "ck_idempotency_records_scope", "idempotency_records", type_="check"
    )
    op.create_check_constraint(
        "ck_idempotency_records_scope",
        "idempotency_records",
        "scope IN ('webhook_delivery','tool_call')",
    )
