"""Tenant-scoped Run lifecycle HTTP endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from aegisflow_core.control_plane.identity import AuthenticationError
from aegisflow_core.control_plane.runs import (
    ApprovalSubmission,
    ClarificationSubmission,
    CreateRunRequest,
    RunServiceUnavailable,
)
from aegisflow_core.request_identity import IdentityNotConfiguredError, authenticate_request
from aegisflow_core.control_plane.run_service import IdempotencyConflictError

router = APIRouter(prefix="/v1")
IdempotencyHeader = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$"),
]


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code}})


async def _principal(
    request: Request,
    authorization: str | None,
    local_token: str | None,
    local_persona: str | None,
):
    try:
        return await authenticate_request(
            request,
            authorization=authorization,
            local_token=local_token,
            local_persona=local_persona,
        )
    except IdentityNotConfiguredError:
        return _error(503, "identity_not_configured")
    except AuthenticationError as exc:
        return _error(401, exc.code)


def _headers(
    authorization: str | None,
    local_token: str | None,
    local_persona: str | None,
) -> tuple[str | None, str | None, str | None]:
    return authorization, local_token, local_persona


@router.get("/system/profile")
async def system_profile(request: Request):
    settings = request.app.state.settings
    return {
        "profile": "local_mvp" if settings.local_mvp_profile_enabled else "standard",
        "github_effect_mode": "dry_run" if settings.local_mvp_github_dry_run else "github",
        "model_mode": "ollama" if settings.model_ollama_enabled else "disabled",
    }


@router.get("/session")
async def get_session(
    request: Request,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, *_headers(authorization, local_token, local_persona))
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.session(principal)
    except RunServiceUnavailable:
        return _error(503, "run_service_unavailable")


@router.post("/tenants/{tenant_id}/runs", status_code=202)
async def create_run(
    tenant_id: UUID,
    body: CreateRunRequest,
    request: Request,
    idempotency_key: IdempotencyHeader,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.create_run(
            tenant_id, principal, body, idempotency_key
        )
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")
    except IdempotencyConflictError:
        return _error(409, "idempotency_conflict")
    except RunServiceUnavailable:
        return _error(503, "run_service_unavailable")


@router.get("/tenants/{tenant_id}/runs")
async def list_runs(
    tenant_id: UUID,
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.list_runs(tenant_id, principal, limit)
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")
    except RunServiceUnavailable:
        return _error(503, "run_service_unavailable")


@router.get("/tenants/{tenant_id}/runs/{run_id}")
async def get_run(
    tenant_id: UUID,
    run_id: UUID,
    request: Request,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.get_run(tenant_id, principal, run_id)
    except KeyError:
        return _error(404, "run_not_found")
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")
    except RunServiceUnavailable:
        return _error(503, "run_service_unavailable")


@router.get("/tenants/{tenant_id}/runs/{run_id}/events")
async def list_events(
    tenant_id: UUID,
    run_id: UUID,
    request: Request,
    after: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.list_events(
            tenant_id, principal, run_id, after, limit
        )
    except KeyError:
        return _error(404, "run_not_found")
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")


@router.post(
    "/tenants/{tenant_id}/runs/{run_id}/clarifications/{request_id}",
    status_code=202,
)
async def submit_clarification(
    tenant_id: UUID,
    run_id: UUID,
    request_id: UUID,
    body: ClarificationSubmission,
    request: Request,
    idempotency_key: IdempotencyHeader,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.submit_clarification(
            tenant_id, principal, run_id, request_id, body.answers, idempotency_key
        )
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")
    except (KeyError, ValueError):
        return _error(409, "clarification_conflict")


@router.post(
    "/tenants/{tenant_id}/runs/{run_id}/approvals/{approval_id}", status_code=202
)
async def submit_approval(
    tenant_id: UUID,
    run_id: UUID,
    approval_id: UUID,
    body: ApprovalSubmission,
    request: Request,
    idempotency_key: IdempotencyHeader,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    principal = await _principal(request, authorization, local_token, local_persona)
    if isinstance(principal, JSONResponse):
        return principal
    try:
        return await request.app.state.run_service.submit_approval(
            tenant_id,
            principal,
            run_id,
            approval_id,
            body.decision,
            body.reason,
            idempotency_key,
        )
    except PermissionError as exc:
        return _error(403, str(exc) or "tenant_access_denied")
    except (KeyError, ValueError):
        return _error(409, "approval_conflict")
