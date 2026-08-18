"""Development-only OIDC membership bootstrap remains explicit and idempotent."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.bootstrap import bootstrap_oidc_development
from aegisflow_core.control_plane.domain import RoleAssignment, TenantMembership
from aegisflow_core.control_plane.identity import Principal


@pytest.mark.database
@pytest.mark.anyio
async def test_oidc_development_bootstrap_assigns_fixed_roles_idempotently() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            async with sessions.begin() as session:
                issuer = "http://localhost:8080/realms/aegisflow"
                principals = {
                    "Developer": Principal(issuer, f"dev-{uuid4()}"),
                    "Reviewer": Principal(issuer, f"review-{uuid4()}"),
                    "Admin": Principal(issuer, f"admin-{uuid4()}"),
                }
                slug = f"oidc-{uuid4()}"
                first = await bootstrap_oidc_development(
                    session, slug=slug, principals=principals
                )
                second = await bootstrap_oidc_development(
                    session, slug=slug, principals=principals
                )

                assert first == second
                memberships = list(
                    await session.scalars(
                        select(TenantMembership).where(
                            TenantMembership.tenant_id == first.tenant_id
                        )
                    )
                )
                assignments = list(
                    await session.scalars(
                        select(RoleAssignment).where(
                            RoleAssignment.tenant_id == first.tenant_id,
                            RoleAssignment.revoked_at.is_(None),
                        )
                    )
                )
                assert {row.subject for row in memberships} == {
                    principal.subject for principal in principals.values()
                }
                assert {row.role for row in assignments} == set(principals)
                assert all(
                    row.assigned_by == "bootstrap:oidc-development"
                    for row in assignments
                )
        finally:
            await transaction.rollback()
    await engine.dispose()
