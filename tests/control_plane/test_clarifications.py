import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from aegisflow_core.control_plane.clarifications import (
    PostgresClarificationGateway,
)
from aegisflow_core.packs.delivery.clarifier.hitl import (
    ClarificationStatus,
    DuplicateClarificationResponseError,
)
from aegisflow_core.packs.delivery.contracts.clarification import (
    ClarificationQuestion,
)


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_clarification_survives_gateway_reconstruction() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(database_url)
    tenant, workflow, run = uuid4(), uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO tenants (id,slug,name) VALUES (:id,:slug,'Clarification Test')"),
            {"id": tenant, "slug": f"clarification-{tenant.hex}"},
        )
        await connection.execute(
            text(
                "INSERT INTO workflows (id,tenant_id,name,version,definition_hash) "
                "VALUES (:id,:tenant,'delivery',1,'hash')"
            ),
            {"id": workflow, "tenant": tenant},
        )
        await connection.execute(
            text(
                "INSERT INTO runs (id,tenant_id,workflow_id,workflow_version,status) "
                "VALUES (:id,:tenant,:workflow,1,'running')"
            ),
            {"id": run, "tenant": tenant, "workflow": workflow},
        )

    question = ClarificationQuestion(
        field="acceptance_scope", question="Which behavior defines acceptance?"
    )
    first = PostgresClarificationGateway(database_url, tenant_id=tenant)
    request_id = first.request_clarification(run, "clarifier", [question])

    reconstructed = PostgresClarificationGateway(database_url, tenant_id=tenant)
    assert reconstructed.request_clarification(run, "clarifier", [question]) == request_id
    assert reconstructed.get_status(request_id) is ClarificationStatus.PENDING

    outcome = reconstructed.submit_response(
        request_id,
        run,
        {"acceptance_scope": "The unit test passes."},
        answered_by="local:developer",
    )
    assert outcome.status is ClarificationStatus.ANSWERED
    assert outcome.answers["acceptance_scope"] == "The unit test passes."
    assert reconstructed.get_status(request_id) is ClarificationStatus.ANSWERED

    with pytest.raises(DuplicateClarificationResponseError):
        reconstructed.submit_response(
            request_id,
            run,
            {"acceptance_scope": "A different answer."},
            answered_by="local:developer",
        )

    async with engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    "SELECT c.answered_by, r.status, s.status AS step_status "
                    "FROM clarification_requests c "
                    "JOIN runs r ON r.tenant_id=c.tenant_id AND r.id=c.run_id "
                    "JOIN steps s ON s.tenant_id=c.tenant_id AND s.run_id=c.run_id "
                    "AND s.sequence=2 WHERE c.id=:id"
                ),
                {"id": request_id},
            )
        ).mappings().one()
    assert row == {
        "answered_by": "local:developer",
        "status": "running",
        "step_status": "completed",
    }
    await engine.dispose()
