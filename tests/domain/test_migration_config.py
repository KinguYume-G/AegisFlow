"""Alembic entry-point and metadata registration tests."""

from pathlib import Path

from alembic.config import Config

from aegisflow_core.control_plane.domain import Base


REPOSITORY_ROOT = Path(__file__).parents[2]


def test_alembic_entry_point_targets_control_plane_migrations() -> None:
    config = Config(REPOSITORY_ROOT / "alembic.ini")
    script_location = config.get_main_option("script_location")

    assert script_location.endswith(
        "src/aegisflow_core/control_plane/migrations"
    )


def test_alembic_metadata_is_complete() -> None:
    assert set(Base.metadata.tables) == {
        "tenants",
        "workflows",
        "runs",
        "steps",
        "approvals",
        "audit_events",
        "repository_chunks",
        "idempotency_records",
    }
    assert all(table.schema is None for table in Base.metadata.tables.values())
