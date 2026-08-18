"""Shared HTTP identity resolution for OIDC and the local MVP BFF."""

from __future__ import annotations

from fastapi import Request

from aegisflow_core.control_plane.identity import (
    AuthenticationError,
    LocalPersona,
    Principal,
    parse_bearer_token,
)
from aegisflow_core.control_plane.identity.sessions import (
    SessionAuthenticationError,
)


class IdentityNotConfiguredError(RuntimeError):
    pass


async def authenticate_request(
    request: Request,
    *,
    authorization: str | None,
    local_token: str | None,
    local_persona: str | None,
) -> Principal:
    oidc = getattr(request.app.state, "oidc_verifier", None)
    local = getattr(request.app.state, "local_identity_verifier", None)
    has_local = local_token is not None or local_persona is not None
    if authorization is not None and has_local:
        raise AuthenticationError("ambiguous_identity")
    if has_local:
        if local is None:
            raise AuthenticationError("local_identity_denied")
        try:
            persona = LocalPersona(local_persona or "")
        except ValueError:
            raise AuthenticationError("local_identity_denied") from None
        return local.verify(local_token or "", expected_persona=persona)
    if authorization is not None:
        scheme, separator, credential = authorization.partition(" ")
        if not separator or not credential or " " in credential:
            raise AuthenticationError("invalid_authorization_header")
        if scheme.casefold() == "aegissession":
            session_factory = getattr(request.app.state, "session_factory", None)
            manager_factory = getattr(
                request.app.state, "console_session_manager_factory", None
            )
            if session_factory is None or manager_factory is None:
                raise AuthenticationError("session_identity_denied")
            try:
                async with session_factory.begin() as session:
                    return await manager_factory(session).authenticate(credential)
            except SessionAuthenticationError as exc:
                raise AuthenticationError(exc.code) from None
        if scheme.casefold() != "bearer":
            raise AuthenticationError("invalid_authorization_header")
        if oidc is None:
            raise AuthenticationError("oidc_identity_denied")
        return await oidc.verify(parse_bearer_token(authorization))
    if local is not None or oidc is not None:
        raise AuthenticationError("authentication_required")
    raise IdentityNotConfiguredError
