import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aegisflow_core.control_plane.approvals import (
    PostgresApprovalAuthorizer,
    PostgresApprovalGateway,
    PostgresToolApprovalVerifier,
)
from aegisflow_core.gateway.github.pull_request import WriteAuthorization
from aegisflow_core.packs.delivery.contracts.action_approval import digest_action_preview
from aegisflow_core.gateway.policy.gate import RepositoryTarget
from aegisflow_core.packs.delivery.contracts.review_decision import ReviewFinding
from aegisflow_core.packs.delivery.reviewer.fakes import DuplicateApprovalDecisionError


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_approval_gateway_is_idempotent_and_terminal() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is required")
    engine = create_async_engine(url)
    tenant, workflow, run, step = uuid4(), uuid4(), uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.execute(text("INSERT INTO tenants (id,slug,name) VALUES (:id,:slug,'Approval Test')"),
                                 {"id":tenant,"slug":f"approval-{tenant.hex}"})
        await connection.execute(text("INSERT INTO workflows (id,tenant_id,name,version,definition_hash) VALUES (:id,:tenant,'delivery',1,'hash')"),
                                 {"id":workflow,"tenant":tenant})
        await connection.execute(text("INSERT INTO runs (id,tenant_id,workflow_id,workflow_version,status) VALUES (:id,:tenant,:workflow,1,'running')"),
                                 {"id":run,"tenant":tenant,"workflow":workflow})
        await connection.execute(text("INSERT INTO steps (id,tenant_id,run_id,name,sequence,status) VALUES (:id,:tenant,:run,'reviewer',1,'running')"),
                                 {"id":step,"tenant":tenant,"run":run})
    gateway = PostgresApprovalGateway(async_sessionmaker(engine, expire_on_commit=False))
    finding = ReviewFinding(severity="info",message="ready for human review")
    preview = {
        "effect": "create_draft_pr_candidate",
        "effect_mode": "dry_run",
        "repository": "owner/fixture",
        "base_ref": "main",
        "base_sha": "a" * 40,
        "branch_name": f"aegisflow/run-{run}",
        "changed_files": ["src/app.py"],
        "content_digest": "b" * 64,
        "risk": "L3",
    }
    action_digest = digest_action_preview(preview)
    approval = await gateway.request_approval(
        tenant, run, step, [finding], action_preview=preview, action_digest=action_digest
    )
    assert approval == await gateway.request_approval(
        tenant, run, step, [finding], action_preview=preview, action_digest=action_digest
    )
    assert await gateway.get_status(approval) == "pending"
    outcome = await gateway.submit_decision(approval,run,"approved","human")
    assert outcome.decision == "approved" and await gateway.get_status(approval) == "approved"
    authorizer = PostgresApprovalAuthorizer(async_sessionmaker(engine, expire_on_commit=False))
    authorization = WriteAuthorization(
        approval_id=approval, tenant_id=tenant, run_id=run, step_id=step,
        repository_target=RepositoryTarget("owner", "fixture"), base_ref="main",
        base_sha="a" * 40, content_digest="b" * 64,
        action_digest=action_digest, effect_mode="dry_run", risk="L3",
    )
    await authorizer.verify(authorization, "b" * 64, action_digest)
    with pytest.raises(PermissionError):
        await authorizer.verify(authorization, "c" * 64, action_digest)
    with pytest.raises(PermissionError):
        changed_action_digest = digest_action_preview(
            {**preview, "content_digest": "c" * 64}
        )
        await authorizer.verify(
            authorization.model_copy(
                update={
                    "content_digest": "c" * 64,
                    "action_digest": changed_action_digest,
                }
            ),
            "c" * 64,
            changed_action_digest,
        )
    with pytest.raises(PermissionError):
        await authorizer.verify(authorization, "b" * 64, "c" * 64)
    with pytest.raises(PermissionError):
        await authorizer.verify(
            authorization.model_copy(update={"tenant_id": uuid4()}),
            "b" * 64,
            action_digest,
        )
    with pytest.raises(DuplicateApprovalDecisionError):
        await gateway.submit_decision(approval,run,"rejected","human")
    verifier = PostgresToolApprovalVerifier(async_sessionmaker(engine, expire_on_commit=False))
    assert await verifier.approved_by(
        approval_id=approval, tenant_id=tenant, run_id=run, step_id=step
    ) == "human"
    assert await verifier.approved_by(
        approval_id=approval, tenant_id=uuid4(), run_id=run, step_id=step
    ) is None
    assert await verifier.approved_by(
        approval_id=approval, tenant_id=tenant, run_id=run, step_id=uuid4()
    ) is None
    await engine.dispose()
