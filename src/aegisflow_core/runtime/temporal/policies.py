"""Single-owner Activity error classification, retry, and timeout policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError


class FailureCategory(StrEnum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    AUTHORIZATION = "authorization"
    POLICY = "policy"
    INVALID_INPUT = "invalid_input"
    SEMANTIC = "semantic"
    IRREVERSIBLE = "irreversible"


class RuntimeFailure(RuntimeError):
    category: FailureCategory

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TransientFailure(RuntimeFailure):
    category = FailureCategory.TRANSIENT


class RateLimitFailure(RuntimeFailure):
    category = FailureCategory.RATE_LIMIT


class AuthorizationFailure(RuntimeFailure):
    category = FailureCategory.AUTHORIZATION


class PolicyFailure(RuntimeFailure):
    category = FailureCategory.POLICY


class InvalidInputFailure(RuntimeFailure):
    category = FailureCategory.INVALID_INPUT


class SemanticFailure(RuntimeFailure):
    category = FailureCategory.SEMANTIC


class IrreversibleFailure(RuntimeFailure):
    category = FailureCategory.IRREVERSIBLE


_NON_RETRYABLE = frozenset(
    {
        FailureCategory.AUTHORIZATION,
        FailureCategory.POLICY,
        FailureCategory.INVALID_INPUT,
        FailureCategory.SEMANTIC,
        FailureCategory.IRREVERSIBLE,
    }
)


@dataclass(frozen=True, slots=True)
class ActivityPolicy:
    start_to_close_timeout: timedelta
    schedule_to_close_timeout: timedelta
    retry_policy: RetryPolicy

    def __post_init__(self) -> None:
        if self.start_to_close_timeout <= timedelta(0):
            raise ValueError("start_to_close_timeout must be positive")
        if self.schedule_to_close_timeout < self.start_to_close_timeout:
            raise ValueError("schedule_to_close_timeout cannot be shorter")


def standard_activity_policy() -> ActivityPolicy:
    return ActivityPolicy(
        start_to_close_timeout=timedelta(minutes=2),
        schedule_to_close_timeout=timedelta(minutes=10),
        retry_policy=RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=5,
            non_retryable_error_types=[category.value for category in _NON_RETRYABLE],
        ),
    )


def classify_failure(error: BaseException) -> FailureCategory:
    if isinstance(error, RuntimeFailure):
        return error.category
    if isinstance(error, (TimeoutError, ConnectionError)):
        return FailureCategory.TRANSIENT
    if isinstance(error, (TypeError, ValueError)):
        return FailureCategory.INVALID_INPUT
    return FailureCategory.IRREVERSIBLE


def as_application_error(error: BaseException) -> ApplicationError:
    category = classify_failure(error)
    retry_after = getattr(error, "retry_after", None)
    return ApplicationError(
        f"runtime activity failed: {category.value}",
        type=category.value,
        non_retryable=category in _NON_RETRYABLE,
        next_retry_delay=(
            timedelta(seconds=float(retry_after))
            if category == FailureCategory.RATE_LIMIT and retry_after
            else None
        ),
    )


def is_retryable(error: BaseException) -> bool:
    return classify_failure(error) not in _NON_RETRYABLE
