"""Add tenant-isolated pgvector repository chunks."""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_knowledge_chunks"
down_revision: str | None = "0002_normalize_check_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "repository_chunks",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("chunk_index >= 0", name="ck_repository_chunks_chunk_index"),
        sa.CheckConstraint("start_line >= 1 AND end_line >= start_line", name="ck_repository_chunks_line_range"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT", name="fk_repository_chunks_tenant_id_tenants"),
        sa.PrimaryKeyConstraint("id", name="pk_repository_chunks"),
        sa.UniqueConstraint("tenant_id", "repository", "file_path", "chunk_index", name="uq_repository_chunks_location"),
    )


def downgrade() -> None:
    op.drop_table("repository_chunks")
