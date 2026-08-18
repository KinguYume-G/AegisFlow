"""Authenticated, tenant-scoped read-only run graph endpoint."""

from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from aegisflow_core.control_plane.identity import AuthenticationError
from aegisflow_core.control_plane.rbac import Capability, RbacService
from aegisflow_core.control_plane.run_graph import load_run_graph
from aegisflow_core.gateway.tenant import resolve_tenant_scope
from aegisflow_core.request_identity import (
    IdentityNotConfiguredError,
    authenticate_request,
)

router = APIRouter(prefix="/v1")


@router.get("/tenants/{tenant_id}/runs/{run_id}/graph")
async def get_run_graph(
    tenant_id: UUID,
    run_id: UUID,
    request: Request,
    authorization: str | None = Header(default=None),
    local_token: str | None = Header(default=None, alias="X-AegisFlow-Local-Token"),
    local_persona: str | None = Header(default=None, alias="X-AegisFlow-Local-Persona"),
):
    try:
        principal = await authenticate_request(
            request,
            authorization=authorization,
            local_token=local_token,
            local_persona=local_persona,
        )
    except IdentityNotConfiguredError:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "identity_not_configured"}},
        )
    except AuthenticationError as exc:
        return JSONResponse(status_code=401, content={"error": {"code": exc.code}})
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            await resolve_tenant_scope(
                tenant_id=tenant_id,
                principal=principal,
                capability=Capability.RUN_READ,
                authorizer=RbacService(session),
            )
        except PermissionError:
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "tenant_access_denied"}},
            )
        graph = await load_run_graph(session, tenant_id=tenant_id, run_id=run_id)
    if graph is None:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "run_not_found"}},
        )
    return graph
