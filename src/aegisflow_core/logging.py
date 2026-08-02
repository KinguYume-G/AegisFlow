"""Structured stdout logging for the AegisFlow application boundary."""

from datetime import UTC, datetime
import json
import logging
import sys
from typing import Any

_LOGGER_NAME = "aegisflow"


class _JsonFormatter(logging.Formatter):
    """Serialize the stable, non-sensitive base log envelope as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    """Configure one idempotent JSON handler without exposing configuration."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if any(
        getattr(handler, "_aegisflow_managed", False)
        for handler in logger.handlers
    ):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler._aegisflow_managed = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
