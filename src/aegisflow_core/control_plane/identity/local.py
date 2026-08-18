"""Explicit development-only identities for the local MVP profile."""

from __future__ import annotations

from enum import StrEnum
from secrets import compare_digest

from aegisflow_core.control_plane.identity.oidc import AuthenticationError, Principal


class LocalPersona(StrEnum):
    """The two intentionally separate local actors."""

    DEVELOPER = "developer"
    REVIEWER = "reviewer"


class LocalIdentityVerifier:
    """Map server-side synthetic tokens to fixed local principals."""

    issuer = "urn:aegisflow:local-mvp"

    def __init__(self, *, developer_token: str, reviewer_token: str) -> None:
        tokens = (developer_token, reviewer_token)
        if any(not 16 <= len(value) <= 256 for value in tokens):
            raise ValueError("local identity token length must be 16 through 256")
        if compare_digest(developer_token, reviewer_token):
            raise ValueError("local identity tokens must be distinct")
        self._tokens = {
            LocalPersona.DEVELOPER: developer_token,
            LocalPersona.REVIEWER: reviewer_token,
        }

    def verify(self, token: str, *, expected_persona: LocalPersona) -> Principal:
        """Return a fixed principal or one stable token-free denial."""
        expected = self._tokens[expected_persona]
        if not token or not compare_digest(token, expected):
            raise AuthenticationError("local_identity_denied")
        return Principal(self.issuer, expected_persona.value)
