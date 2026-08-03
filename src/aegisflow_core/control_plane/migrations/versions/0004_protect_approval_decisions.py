"""Make approval requests idempotent and terminal decisions immutable."""

from collections.abc import Sequence
from alembic import op

revision: str = "0004_protect_approval_decisions"
down_revision: str | None = "0003_add_knowledge_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_approvals_tenant_run_step", "approvals", ["tenant_id", "run_id", "step_id"]
    )
    op.execute("""
        CREATE FUNCTION public.aegisflow_protect_approval_decision()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.decision <> 'pending' OR NEW.decision NOT IN ('approved', 'rejected') THEN
                RAISE EXCEPTION 'approval decision only permits pending to approved or rejected';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
               OR NEW.run_id IS DISTINCT FROM OLD.run_id OR NEW.step_id IS DISTINCT FROM OLD.step_id
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'approval identity cannot be modified';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute("""
        CREATE TRIGGER trg_approvals_protect_decision BEFORE UPDATE ON approvals
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_protect_approval_decision()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_approvals_protect_decision ON approvals")
    op.execute("DROP FUNCTION public.aegisflow_protect_approval_decision()")
    op.drop_constraint("uq_approvals_tenant_run_step", "approvals", type_="unique")
