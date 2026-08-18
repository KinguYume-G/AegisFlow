"""Development-only identity remains explicit, separated, and fail-closed."""

import pytest

from aegisflow_core.control_plane.identity import (
    AuthenticationError,
    LocalIdentityVerifier,
    LocalPersona,
)


def verifier() -> LocalIdentityVerifier:
    return LocalIdentityVerifier(
        developer_token="local-developer-token-123",
        reviewer_token="local-reviewer-token-456",
    )


def test_local_identity_maps_tokens_to_distinct_principals() -> None:
    identity = verifier()

    developer = identity.verify(
        "local-developer-token-123", expected_persona=LocalPersona.DEVELOPER
    )
    reviewer = identity.verify(
        "local-reviewer-token-456", expected_persona=LocalPersona.REVIEWER
    )

    assert developer.issuer == "urn:aegisflow:local-mvp"
    assert developer.subject == "developer"
    assert reviewer.subject == "reviewer"
    assert developer.actor_reference != reviewer.actor_reference


@pytest.mark.parametrize(
    "token,persona",
    [
        ("", LocalPersona.DEVELOPER),
        ("unknown-local-token-000", LocalPersona.DEVELOPER),
        ("local-reviewer-token-456", LocalPersona.DEVELOPER),
        ("local-developer-token-123", LocalPersona.REVIEWER),
    ],
)
def test_local_identity_rejects_missing_unknown_or_wrong_persona(
    token: str, persona: LocalPersona
) -> None:
    with pytest.raises(AuthenticationError, match="local_identity_denied"):
        verifier().verify(token, expected_persona=persona)


def test_local_identity_constructor_rejects_same_or_short_tokens() -> None:
    with pytest.raises(ValueError, match="distinct"):
        LocalIdentityVerifier(
            developer_token="same-local-token-123",
            reviewer_token="same-local-token-123",
        )
    with pytest.raises(ValueError, match="token"):
        LocalIdentityVerifier(developer_token="short", reviewer_token="also-short")
