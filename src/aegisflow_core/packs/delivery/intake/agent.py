"""Framework-independent Intake Agent."""

import hashlib
import json
import re
import unicodedata

from aegisflow_core.packs.delivery.contracts.determinism import Clock
from aegisflow_core.packs.delivery.contracts.normalized_request import (
    NormalizedRequest,
    SourceType,
)


_INLINE_WHITESPACE = re.compile(r"[ \t]+")


class IntakeAgent:
    """Normalize external demand into the stable DeliveryPack request schema."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def normalize(
        self,
        source_type: SourceType,
        source_ref: str | None,
        title: str,
        body: str,
    ) -> NormalizedRequest:
        """Normalize input and derive an idempotency key from content only."""
        normalized_title = _normalize_content(title)
        normalized_body = _normalize_content(body)
        normalized_ref = _normalize_source_ref(source_ref)
        idempotency_key = _content_hash(
            source_type=source_type,
            title=normalized_title,
            body=normalized_body,
        )

        return NormalizedRequest(
            source_type=source_type,
            source_ref=normalized_ref,
            title=normalized_title,
            body=normalized_body,
            idempotency_key=idempotency_key,
            received_at=self._clock.now(),
        )


def _normalize_content(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_INLINE_WHITESPACE.sub(" ", line.strip()) for line in normalized.split("\n")]

    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _normalize_source_ref(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip()
    return normalized or None


def _content_hash(*, source_type: str, title: str, body: str) -> str:
    canonical = json.dumps(
        {
            "source_type": source_type,
            "title": title,
            "body": body,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
