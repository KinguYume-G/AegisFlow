"""Contract tests for the minimal liveness endpoint."""

import httpx
import pytest

pytestmark = pytest.mark.anyio


async def test_health_returns_200(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).status_code == 200


async def test_health_response_body_contract(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json() == {
        "status": "ok",
        "service": "aegisflow-core",
    }


async def test_health_wrong_method_not_allowed(client: httpx.AsyncClient) -> None:
    assert (await client.post("/health")).status_code == 405


async def test_health_content_type_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers["content-type"] == "application/json"
