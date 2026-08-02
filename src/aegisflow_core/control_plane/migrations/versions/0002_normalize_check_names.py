"""Normalize CHECK constraint names created by the initial migration.

Revision ID: 0002_normalize_check_names
Revises: 0001_initial_domain_model
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_normalize_check_names"
down_revision: str | None = "0001_initial_domain_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_RENAMES = (
    ("workflows", "ck_workflows_ck_workflows_status", "ck_workflows_status"),
    (
        "workflows",
        "ck_workflows_ck_workflows_version_positive",
        "ck_workflows_version_positive",
    ),
    ("runs", "ck_runs_ck_runs_status", "ck_runs_status"),
    ("steps", "ck_steps_ck_steps_status", "ck_steps_status"),
    ("approvals", "ck_approvals_ck_approvals_decision", "ck_approvals_decision"),
)


def _rename_constraint(table: str, old_name: str, new_name: str) -> None:
    op.execute(
        f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
    )


def upgrade() -> None:
    """Converge databases that already applied revision 0001 on stable names."""
    for table, old_name, new_name in CONSTRAINT_RENAMES:
        _rename_constraint(table, old_name, new_name)


def downgrade() -> None:
    """Restore the names produced by the immutable initial revision."""
    for table, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        _rename_constraint(table, new_name, old_name)
