"""Canonical digest for one exact Human-reviewed external action."""

from collections.abc import Mapping
from hashlib import sha256
import json


def digest_action_preview(action_preview: Mapping[str, object]) -> str:
    return sha256(
        json.dumps(
            action_preview,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
