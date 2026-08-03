from contextlib import asynccontextmanager
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from aegisflow_core.control_plane.identity import AuthenticationError, Principal
from aegisflow_core.control_plane.run_graph import RunGraph
from aegisflow_core.run_graph_router import router

TENANT = "00000000-0000-0000-0000-000000000001"
RUN = "00000000-0000-0000-0000-000000000002"


class Verifier:
    def __init__(self, error: str | None = None) -> None:
        self.error = error

    async def verify(self, _token: str) -> Principal:
        if self.error:
            raise AuthenticationError(self.error)
        return Principal("https://issuer.example.test", "subject")


def app_with(verifier: object) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.oidc_verifier = verifier

    @asynccontextmanager
    async def sessions():
        yield object()

    app.state.session_factory = sessions
    return app


async def get(app: FastAPI) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(
            f"/v1/tenants/{TENANT}/runs/{RUN}/graph",
            headers={"Authorization": "Bearer test-token"},
        )


@pytest.mark.anyio
async def test_graph_endpoint_rejects_invalid_identity() -> None:
    response = await get(app_with(Verifier("invalid_claims")))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_claims"


@pytest.mark.anyio
async def test_graph_endpoint_rejects_tenant_denial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def deny(**_kwargs):  # type: ignore[no-untyped-def]
        raise PermissionError("denied")

    monkeypatch.setattr("aegisflow_core.run_graph_router.resolve_tenant_scope", deny)
    response = await get(app_with(Verifier()))
    assert response.status_code == 403


@pytest.mark.anyio
async def test_graph_endpoint_returns_not_found_and_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def allow(**_kwargs):  # type: ignore[no-untyped-def]
        return None

    async def missing(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr("aegisflow_core.run_graph_router.resolve_tenant_scope", allow)
    monkeypatch.setattr("aegisflow_core.run_graph_router.load_run_graph", missing)
    assert (await get(app_with(Verifier()))).status_code == 404

    async def found(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return RunGraph(
            run_id=UUID(RUN),
            workflow_id=UUID("00000000-0000-0000-0000-000000000003"),
            workflow_version=1,
            status="completed",
            nodes=(),
        )

    monkeypatch.setattr("aegisflow_core.run_graph_router.load_run_graph", found)
    response = await get(app_with(Verifier()))
    assert response.status_code == 200
    assert response.json()["run_id"] == RUN
