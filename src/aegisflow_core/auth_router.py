"""OIDC access-token exchange for short-lived, revocable Console sessions."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from aegisflow_core.control_plane.identity import AuthenticationError, parse_bearer_token
from aegisflow_core.control_plane.identity.sessions import (
    SessionAuthenticationError,
    SessionAuthorizationError,
)

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code}},
        headers={"Cache-Control": "no-store"},
    )


def _session_token(value: str | None) -> str:
    if value is None:
        raise SessionAuthenticationError("invalid_authorization_header")
    scheme, separator, token = value.partition(" ")
    if (
        not separator
        or scheme.casefold() != "aegissession"
        or not token
        or " " in token
    ):
        raise SessionAuthenticationError("invalid_authorization_header")
    return token


@router.post("/sessions", status_code=201)
async def create_console_session(
    request: Request,
    authorization: str | None = Header(default=None),
):
    verifier = getattr(request.app.state, "oidc_verifier", None)
    session_factory = getattr(request.app.state, "session_factory", None)
    manager_factory = getattr(
        request.app.state, "console_session_manager_factory", None
    )
    if verifier is None or session_factory is None or manager_factory is None:
        return _error(503, "session_identity_not_configured")
    try:
        identity = await verifier.verify_identity(parse_bearer_token(authorization))
        async with session_factory.begin() as session:
            created = await manager_factory(session).create(identity)
    except AuthenticationError as exc:
        return _error(401, exc.code)
    except SessionAuthenticationError as exc:
        return _error(401, exc.code)
    except SessionAuthorizationError as exc:
        return _error(403, exc.code)
    except SQLAlchemyError:
        return _error(503, "session_store_unavailable")
    return JSONResponse(
        status_code=201,
        headers={"Cache-Control": "no-store"},
        content={
            "session_token": created.token,
            "expires_at": created.expires_at.isoformat().replace("+00:00", "Z"),
            "actor_reference": created.principal.actor_reference,
        },
    )


@router.delete("/session", status_code=204)
async def revoke_console_session(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    session_factory = getattr(request.app.state, "session_factory", None)
    manager_factory = getattr(
        request.app.state, "console_session_manager_factory", None
    )
    if session_factory is None or manager_factory is None:
        return _error(503, "session_identity_not_configured")
    try:
        token = _session_token(authorization)
        async with session_factory.begin() as session:
            await manager_factory(session).revoke(token)
    except SessionAuthenticationError as exc:
        return _error(401, exc.code)
    except SQLAlchemyError:
        return _error(503, "session_store_unavailable")
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
