"""Tests for deterministic time and identifier ports."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from aegisflow_core.packs.delivery.contracts.determinism import (
    FixedClock,
    RandomIdGenerator,
    SequentialIdGenerator,
    SystemClock,
)


def test_fixed_clock_returns_aware_utc_constant() -> None:
    instant = datetime(2026, 8, 2, 12, 30, tzinfo=timezone.utc)
    clock = FixedClock(instant)

    assert clock.now() is instant
    assert clock.now() is instant
    assert clock.now().utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    "invalid",
    [
        datetime(2026, 8, 2, 12, 30),
        datetime(2026, 8, 2, 20, 30, tzinfo=timezone(timedelta(hours=8))),
    ],
)
def test_fixed_clock_rejects_non_utc_instant(invalid: datetime) -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        FixedClock(invalid)


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()

    assert now.tzinfo is timezone.utc
    assert now.utcoffset() == timedelta(0)


def test_sequential_id_generator_reproducible() -> None:
    first = SequentialIdGenerator("gate-1a")
    second = SequentialIdGenerator("gate-1a")

    first_sequence = [first.new_id() for _ in range(3)]
    second_sequence = [second.new_id() for _ in range(3)]

    assert first_sequence == second_sequence
    assert len(set(first_sequence)) == 3
    assert all(identifier.version == 5 for identifier in first_sequence)


def test_random_id_generator_returns_uuid4() -> None:
    identifier = RandomIdGenerator().new_id()

    assert isinstance(identifier, UUID)
    assert identifier.version == 4
