"""Provider-neutral identity verification boundary."""

from aegisflow_core.control_plane.identity.oidc import (
    AuthenticationError,
    HttpJwksResolver,
    JwksResolver,
    OidcConfig,
    OidcVerifier,
    Principal,
    VerifiedIdentity,
    parse_bearer_token,
)
from aegisflow_core.control_plane.identity.local import (
    LocalIdentityVerifier,
    LocalPersona,
)

__all__ = [
    "AuthenticationError",
    "HttpJwksResolver",
    "JwksResolver",
    "LocalIdentityVerifier",
    "LocalPersona",
    "OidcConfig",
    "OidcVerifier",
    "Principal",
    "VerifiedIdentity",
    "parse_bearer_token",
]
