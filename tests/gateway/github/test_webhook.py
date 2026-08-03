"""Signature, schema, and replay tests for the GitHub webhook boundary."""

import asyncio
import hashlib
import hmac

import pytest

from aegisflow_core.gateway.github.webhook import (
    InMemoryReplayGuard,
    ReplayClaim,
    WebhookRejectionReason,
    verify_webhook,
)


SECRET = "test-webhook-secret"
BODY = b'{"action":"gate1b","installation":{"id":42},"repository":{"full_name":"owner/repo"},"client_payload":{}}'


def _signature(body: bytes = BODY) -> str:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_webhook_rejects_invalid_signature_before_schema() -> None:
    result = verify_webhook(
        raw_body=b"not-json",
        signature_header="sha256=invalid",
        event_header="repository_dispatch",
        delivery_id_header="delivery-1",
        webhook_secret=SECRET,
        allowed_events=frozenset({"repository_dispatch"}),
    )

    assert result.accepted is False
    assert result.rejection_reason is WebhookRejectionReason.INVALID_SIGNATURE


def test_verify_webhook_uses_constant_time_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False
    original = hmac.compare_digest

    def spy(left: str, right: str) -> bool:
        nonlocal called
        called = True
        return original(left, right)

    monkeypatch.setattr(hmac, "compare_digest", spy)

    verify_webhook(
        raw_body=BODY,
        signature_header=_signature(),
        event_header="repository_dispatch",
        delivery_id_header="delivery-1",
        webhook_secret=SECRET,
        allowed_events=frozenset({"repository_dispatch"}),
    )

    assert called is True


@pytest.mark.parametrize(
    ("event", "body", "delivery_id"),
    [
        ("push", BODY, "delivery-1"),
        ("repository_dispatch", b"not-json", "delivery-1"),
        ("repository_dispatch", b"{}", "delivery-1"),
        ("repository_dispatch", BODY, None),
    ],
)
def test_verify_webhook_rejects_invalid_schema(
    event: str, body: bytes, delivery_id: str | None
) -> None:
    result = verify_webhook(
        raw_body=body,
        signature_header=_signature(body),
        event_header=event,
        delivery_id_header=delivery_id,
        webhook_secret=SECRET,
        allowed_events=frozenset({"repository_dispatch"}),
    )

    assert result.accepted is False
    assert result.rejection_reason is WebhookRejectionReason.SCHEMA_REJECTED


def test_verify_webhook_accepts_repository_dispatch() -> None:
    result = verify_webhook(
        raw_body=BODY,
        signature_header=_signature(),
        event_header="repository_dispatch",
        delivery_id_header="delivery-1",
        webhook_secret=SECRET,
        allowed_events=frozenset({"repository_dispatch"}),
    )

    assert result.accepted is True
    assert result.delivery_id == "delivery-1"
    assert result.installation_id == "42"
    assert result.repository == "owner/repo"
    assert result.rejection_reason is None


@pytest.mark.anyio
async def test_replay_guard_rejects_duplicate_and_expires() -> None:
    current = 100.0
    guard = InMemoryReplayGuard(
        ttl_seconds=600,
        max_entries=10,
        monotonic=lambda: current,
    )

    assert await guard.claim("42", "delivery-1") is ReplayClaim.CLAIMED
    assert await guard.claim("42", "delivery-1") is ReplayClaim.DUPLICATE

    current = 701.0
    assert await guard.claim("42", "delivery-1") is ReplayClaim.CLAIMED


@pytest.mark.anyio
async def test_replay_guard_is_atomic_for_concurrent_claims() -> None:
    guard = InMemoryReplayGuard(ttl_seconds=600, max_entries=10)

    results = await asyncio.gather(
        *(guard.claim("42", "delivery-1") for _ in range(20))
    )

    assert results.count(ReplayClaim.CLAIMED) == 1
    assert results.count(ReplayClaim.DUPLICATE) == 19


@pytest.mark.anyio
async def test_replay_guard_capacity_is_bounded() -> None:
    guard = InMemoryReplayGuard(ttl_seconds=600, max_entries=2)

    await guard.claim("42", "first")
    await guard.claim("42", "second")
    await guard.claim("42", "third")

    assert guard.entry_count == 2
    assert await guard.claim("42", "first") is ReplayClaim.CLAIMED
