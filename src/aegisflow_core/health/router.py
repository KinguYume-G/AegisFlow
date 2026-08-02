"""HTTP router for the dependency-free liveness contract."""

from typing import Literal, TypedDict

from fastapi import APIRouter


class HealthResponse(TypedDict):
    """Exact response shape consumed by later infrastructure work."""

    status: Literal["ok"]
    service: Literal["aegisflow-core"]


router = APIRouter()


@router.get("/health")
async def health() -> HealthResponse:
    """Report process liveness without probing future dependencies."""
    return {"status": "ok", "service": "aegisflow-core"}
