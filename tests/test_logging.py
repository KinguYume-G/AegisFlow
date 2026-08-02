"""Unit tests for deterministic structured logging configuration."""

import json
import logging

import pytest

from aegisflow_core.logging import configure_logging


@pytest.fixture(autouse=True)
def reset_managed_handlers() -> None:
    logger = logging.getLogger("aegisflow")
    for handler in list(logger.handlers):
        if getattr(handler, "_aegisflow_managed", False):
            logger.removeHandler(handler)
            handler.close()


def test_configure_logging_is_idempotent() -> None:
    logger = logging.getLogger("aegisflow")

    configure_logging()
    configure_logging()

    managed_handlers = [
        handler
        for handler in logger.handlers
        if getattr(handler, "_aegisflow_managed", False)
    ]
    assert len(managed_handlers) == 1


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    logger = logging.getLogger("aegisflow")
    configure_logging()

    logger.info("application_started")

    captured = capsys.readouterr()
    record = json.loads(captured.out)
    assert record["level"] == "INFO"
    assert record["logger"] == "aegisflow"
    assert record["message"] == "application_started"
    assert record["trace_id"] is None
    assert record["timestamp"].endswith("Z")
