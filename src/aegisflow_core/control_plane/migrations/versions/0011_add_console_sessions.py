"""Add revocable opaque Console sessions.

Revision ID: 0011_console_sessions
Revises: 0010_run_lifecycle
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_console_sessions"
down_revision: str | None = "0010_run_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW_DEFAULT = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "console_sessions",
        sa.Column("token_digest", sa.Text(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", UUID, server_default=UUID_DEFAULT, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW_DEFAULT,
            nullable=False,
        ),
        sa.CheckConstraint(
            "token_digest ~ '^[0-9a-f]{64}$'",
            name="ck_console_sessions_token_digest_format",
        ),
        sa.CheckConstraint(
            "issuer <> '' AND length(issuer) <= 2048",
            name="ck_console_sessions_issuer_bounded",
        ),
        sa.CheckConstraint(
            "subject <> '' AND length(subject) <= 255",
            name="ck_console_sessions_subject_bounded",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_console_sessions_expiry_after_creation",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_console_sessions_revocation_after_creation",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_console_sessions"),
        sa.UniqueConstraint(
            "token_digest", name="uq_console_sessions_token_digest"
        ),
    )
    op.create_index(
        "ix_console_sessions_principal",
        "console_sessions",
        ["issuer", "subject"],
    )
    op.create_index(
        "ix_console_sessions_expires_at",
        "console_sessions",
        ["expires_at"],
    )
    op.execute(
        """
        CREATE FUNCTION public.aegisflow_guard_console_session_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'console session rows cannot be deleted';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.token_digest IS DISTINCT FROM OLD.token_digest
               OR NEW.issuer IS DISTINCT FROM OLD.issuer
               OR NEW.subject IS DISTINCT FROM OLD.subject
               OR NEW.created_at IS DISTINCT FROM OLD.created_at
               OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
                RAISE EXCEPTION 'console session identity cannot be modified';
            END IF;
            IF OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL THEN
                RETURN NEW;
            END IF;
            IF NEW.revoked_at IS NOT DISTINCT FROM OLD.revoked_at THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'console session can only transition to revoked';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_console_sessions_guard_mutation
        BEFORE UPDATE OR DELETE ON console_sessions
        FOR EACH ROW EXECUTE FUNCTION public.aegisflow_guard_console_session_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_console_sessions_guard_mutation ON console_sessions")
    op.execute("DROP FUNCTION public.aegisflow_guard_console_session_mutation()")
    op.drop_index("ix_console_sessions_expires_at", table_name="console_sessions")
    op.drop_index("ix_console_sessions_principal", table_name="console_sessions")
    op.drop_table("console_sessions")
