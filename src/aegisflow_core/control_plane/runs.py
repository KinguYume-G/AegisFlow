"""Bounded API contracts and service boundary for tenant-scoped Runs."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from aegisflow_core.control_plane.identity import Principal


GitHubName = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$"),
]
BaseRef = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$"),
]


class RepositoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: GitHubName
    name: GitHubName
    base_ref: BaseRef = "main"
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")

    @field_validator("base_ref")
    @classmethod
    def base_ref_cannot_traverse(cls, value: str) -> str:
        if ".." in value.split("/"):
            raise ValueError("base_ref cannot contain traversal segments")
        return value


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: Literal["prd", "issue", "bug"]
    source_ref: str | None = Field(default=None, max_length=2048)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=20, max_length=50_000)
    repository: RepositoryInput


def canonical_run_input_hash(request: CreateRunRequest) -> str:
    """Hash the canonical bounded request for idempotency conflict detection."""
    encoded = json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    tenant_id: UUID
    status: str
    source_type: str
    title: str
    requested_by: str
    created_at: datetime
    updated_at: datetime


class RunDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RunSummary
    request: CreateRunRequest
    steps: list[dict[str, object]] = Field(default_factory=list)
    pending_action: dict[str, object] | None = None
    approvals: list[dict[str, object]] = Field(default_factory=list)
    artifacts: list[dict[str, object]] = Field(default_factory=list)
    traces: list[dict[str, object]] = Field(default_factory=list)
    evaluation: dict[str, object] | None = None
    audit: list[dict[str, object]] = Field(default_factory=list)


class RunList(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[RunSummary]
    next_cursor: str | None


class RunEventView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(gt=0)
    event_type: str
    actor: str
    payload: dict[str, object]
    created_at: datetime


class TenantSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: UUID
    slug: str
    roles: list[str]
    capabilities: list[str]


class SessionView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_reference: str
    profile: Literal["oidc", "local_mvp"]
    tenants: list[TenantSession]


class ClarificationSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    answers: dict[str, str] = Field(min_length=1, max_length=50)


class ApprovalSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=4096)


class RunApplicationService(Protocol):
    async def session(self, principal: Principal) -> SessionView: ...

    async def create_run(
        self,
        tenant_id: UUID,
        principal: Principal,
        request: CreateRunRequest,
        idempotency_key: str,
    ) -> RunDetail: ...

    async def list_runs(
        self, tenant_id: UUID, principal: Principal, limit: int
    ) -> RunList: ...

    async def get_run(
        self, tenant_id: UUID, principal: Principal, run_id: UUID
    ) -> RunDetail: ...

    async def list_events(
        self,
        tenant_id: UUID,
        principal: Principal,
        run_id: UUID,
        after: int,
        limit: int,
    ) -> list[RunEventView]: ...


class RunServiceUnavailable(RuntimeError):
    pass


class UnavailableRunService:
    """Fail closed until application assembly supplies the durable service."""

    def __getattr__(self, _name: str):
        async def unavailable(*_args: object, **_kwargs: object) -> None:
            raise RunServiceUnavailable("run service is not configured")

        return unavailable
