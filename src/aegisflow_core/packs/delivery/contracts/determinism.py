"""Injectable deterministic time and identifier ports."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID, uuid4, uuid5


_SEQUENTIAL_ID_NAMESPACE = UUID("7a3758de-2b48-5ec3-a6d8-14ed1d5f58c5")


class Clock(Protocol):
    """Provide the current time without coupling callers to the system clock."""

    def now(self) -> datetime:
        """Return a timezone-aware UTC instant."""


class IdGenerator(Protocol):
    """Provide UUIDs without coupling callers to randomness."""

    def new_id(self) -> UUID:
        """Return the next UUID."""


class SystemClock:
    """Read the real system clock in UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class FixedClock:
    """Always return one validated UTC instant."""

    instant: datetime

    def __post_init__(self) -> None:
        if not _is_aware_utc(self.instant):
            raise ValueError("instant must be a timezone-aware UTC datetime")

    def now(self) -> datetime:
        return self.instant


class RandomIdGenerator:
    """Generate random UUID4 identifiers for production callers."""

    def new_id(self) -> UUID:
        return uuid4()


class SequentialIdGenerator:
    """Generate a reproducible UUID5 sequence for a seed."""

    def __init__(self, seed: str) -> None:
        self._seed = seed
        self._counter = 0

    def new_id(self) -> UUID:
        identifier = uuid5(
            _SEQUENTIAL_ID_NAMESPACE,
            f"{self._seed}:{self._counter}",
        )
        self._counter += 1
        return identifier


def _is_aware_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timedelta(0)
