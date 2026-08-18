"""AF-402 provider-neutral OIDC verification tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from time import time

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest
import httpx

from aegisflow_core.control_plane.identity import (
    AuthenticationError,
    HttpJwksResolver,
    OidcConfig,
    OidcVerifier,
    Principal,
    VerifiedIdentity,
    parse_bearer_token,
)


class RotatingResolver:
    def __init__(self, *snapshots: dict[str, object]) -> None:
        self.snapshots = snapshots
        self.calls = 0

    async def resolve(self) -> dict[str, object]:
        index = min(self.calls, len(self.snapshots) - 1)
        self.calls += 1
        return self.snapshots[index]


def key_pair(kid: str) -> tuple[object, dict[str, object]]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    public["kid"] = kid
    public["alg"] = "RS256"
    public["use"] = "sig"
    return private, public


def token(private: object, kid: str, **overrides: object) -> str:
    now = int(time())
    claims: dict[str, object] = {
        "iss": "https://issuer.example.test",
        "aud": "aegisflow-dev",
        "sub": "subject-123",
        "exp": now + 300,
        "nbf": now - 1,
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": kid})


def config(**overrides: object) -> OidcConfig:
    values: dict[str, object] = {
        "issuer": "https://issuer.example.test",
        "audience": "aegisflow-dev",
        "jwks_url": "https://issuer.example.test/.well-known/jwks.json",
        "algorithm": "RS256",
        "cache_ttl_seconds": 300,
        "max_cached_keys": 8,
        "http_timeout_seconds": 5.0,
    }
    values.update(overrides)
    return OidcConfig(**values)


@pytest.mark.anyio
async def test_valid_token_authenticates_and_rotation_refreshes_once() -> None:
    old_private, old_jwk = key_pair("old")
    new_private, new_jwk = key_pair("new")
    resolver = RotatingResolver({"old": old_jwk}, {"old": old_jwk, "new": new_jwk})
    verifier = OidcVerifier(config(), resolver)

    old = await verifier.verify(token(old_private, "old"))
    rotated = await verifier.verify(token(new_private, "new"))

    assert old.issuer == rotated.issuer == "https://issuer.example.test"
    assert old.subject == rotated.subject == "subject-123"
    assert old.actor_reference == "https://issuer.example.test|subject-123"
    assert resolver.calls == 2
    assert verifier.cached_key_count == 2


@pytest.mark.anyio
async def test_verified_identity_exposes_only_verified_expiry() -> None:
    private, jwk = key_pair("key")
    expires_at = datetime.now(timezone.utc).replace(microsecond=0)
    expires_at = expires_at.replace(second=(expires_at.second + 30) % 60)
    expected_timestamp = int(time()) + 300
    verifier = OidcVerifier(config(), RotatingResolver({"key": jwk}))

    identity = await verifier.verify_identity(
        token(private, "key", exp=expected_timestamp)
    )

    assert identity == VerifiedIdentity(
        principal=Principal("https://issuer.example.test", "subject-123"),
        expires_at=datetime.fromtimestamp(expected_timestamp, timezone.utc),
    )
    assert not hasattr(identity, "claims")


@pytest.mark.anyio
async def test_unknown_key_refreshes_once_and_cache_remains_bounded() -> None:
    private, first = key_pair("first")
    _, second = key_pair("second")
    resolver = RotatingResolver({"first": first, "second": second})
    verifier = OidcVerifier(config(max_cached_keys=1), resolver)
    assert (await verifier.verify(token(private, "first"))).subject == "subject-123"
    assert verifier.cached_key_count == 1
    with pytest.raises(AuthenticationError, match="unknown_key_id"):
        await verifier.verify(token(private, "missing"))
    assert resolver.calls == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda private: token(private, "key", iss="https://wrong.example"), "invalid_claims"),
        (lambda private: token(private, "key", aud="other"), "invalid_claims"),
        (lambda private: token(private, "key", exp=int(time()) - 1), "invalid_claims"),
        (lambda private: token(private, "key", nbf=int(time()) + 300), "invalid_claims"),
        (lambda private: token(private, "key", sub=""), "invalid_subject"),
    ],
)
async def test_claim_failures_are_stable_and_do_not_echo_token(mutator, code: str) -> None:
    private, jwk = key_pair("key")
    raw = mutator(private)
    with pytest.raises(AuthenticationError) as captured:
        await OidcVerifier(config(), RotatingResolver({"key": jwk})).verify(raw)
    assert captured.value.code == code
    assert raw not in str(captured.value)


@pytest.mark.anyio
async def test_header_signature_and_size_fail_closed() -> None:
    private, jwk = key_pair("key")
    other_private, _ = key_pair("other")
    verifier = OidcVerifier(config(), RotatingResolver({"key": jwk}))

    cases = [
        (jwt.encode({"sub": "x"}, key="", algorithm="none"), "invalid_algorithm"),
        (jwt.encode({"sub": "x"}, "s" * 32, algorithm="HS256", headers={"kid": "key"}), "invalid_algorithm"),
        (jwt.encode({"sub": "x"}, private, algorithm="RS256"), "missing_key_id"),
        (token(other_private, "key"), "invalid_signature"),
        ("not-a-token", "malformed_token"),
        ("x" * 16_385, "token_too_large"),
    ]
    for raw, code in cases:
        with pytest.raises(AuthenticationError) as captured:
            await verifier.verify(raw)
        assert captured.value.code == code


def test_bearer_header_is_strict_and_bounded() -> None:
    assert parse_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"
    assert parse_bearer_token("bearer abc.def.ghi") == "abc.def.ghi"
    for value in (None, "", "Basic abc", "Bearer", "Bearer a b"):
        with pytest.raises(AuthenticationError, match="invalid_authorization_header"):
            parse_bearer_token(value)


def test_oidc_config_rejects_unsafe_or_unbounded_values() -> None:
    with pytest.raises(ValueError):
        Principal("", "subject")
    with pytest.raises(ValueError):
        config(issuer="http://issuer.example.test")
    with pytest.raises(ValueError):
        config(jwks_url="http://issuer.example.test/jwks")
    with pytest.raises(ValueError):
        config(audience="")
    with pytest.raises(ValueError):
        config(algorithm="HS256")
    with pytest.raises(ValueError):
        config(cache_ttl_seconds=0)
    with pytest.raises(ValueError):
        config(max_cached_keys=0)
    with pytest.raises(ValueError):
        config(http_timeout_seconds=0)
    with pytest.raises(AuthenticationError, match="token_too_large"):
        parse_bearer_token("Bearer " + "x" * 16_385)


def test_oidc_config_allows_only_explicit_local_development_http() -> None:
    local = config(
        issuer="http://localhost:8080/realms/aegisflow",
        jwks_url="http://host.docker.internal:8080/realms/aegisflow/certs",
        allow_insecure_http=True,
    )

    assert local.allow_insecure_http is True
    with pytest.raises(ValueError):
        config(
            issuer="http://identity.example.test/realms/aegisflow",
            jwks_url="http://identity.example.test/certs",
            allow_insecure_http=True,
        )
    with pytest.raises(ValueError):
        config(
            issuer="http://localhost:8080/realms/aegisflow",
            jwks_url="http://user:secret@localhost:8080/certs",
            allow_insecure_http=True,
        )


@pytest.mark.anyio
async def test_http_jwks_resolver_is_bounded_and_sanitizes_failures() -> None:
    _, jwk = key_pair("key")

    async def success(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"keys": [jwk, {"missing": "kid"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(success))
    resolver = HttpJwksResolver("https://issuer.example.test/jwks", 1, client=client)
    assert list(await resolver.resolve()) == ["key"]
    await resolver.aclose()
    await client.aclose()

    async def failure(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("provider-secret-detail", request=request)

    failed_client = httpx.AsyncClient(transport=httpx.MockTransport(failure))
    failed = HttpJwksResolver(
        "https://issuer.example.test/jwks",
        1,
        client=failed_client,
    )
    with pytest.raises(AuthenticationError) as captured:
        await failed.resolve()
    assert captured.value.code == "jwks_unavailable"
    assert "provider-secret-detail" not in str(captured.value)
    await failed_client.aclose()

    malformed_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"keys": "invalid"}))
    )
    malformed = HttpJwksResolver("https://issuer.example.test/jwks", 1, client=malformed_client)
    with pytest.raises(AuthenticationError, match="jwks_malformed"):
        await malformed.resolve()
    await malformed_client.aclose()


@pytest.mark.anyio
async def test_jwk_metadata_and_resolver_failures_deny() -> None:
    private, jwk = key_pair("key")
    bad_algorithm = dict(jwk); bad_algorithm["alg"] = "RS512"
    with pytest.raises(AuthenticationError, match="invalid_algorithm"):
        await OidcVerifier(config(), RotatingResolver({"key": bad_algorithm})).verify(token(private, "key"))
    bad_use = dict(jwk); bad_use["use"] = "enc"
    with pytest.raises(AuthenticationError, match="invalid_key_use"):
        await OidcVerifier(config(), RotatingResolver({"key": bad_use})).verify(token(private, "key"))

    class BrokenResolver:
        async def resolve(self) -> dict[str, object]:
            raise RuntimeError("provider detail")

    with pytest.raises(AuthenticationError) as captured:
        await OidcVerifier(config(), BrokenResolver()).verify(token(private, "key"))
    assert captured.value.code == "jwks_unavailable"
    assert "provider detail" not in str(captured.value)
