from datetime import timedelta

import pytest
from temporalio.exceptions import ApplicationError

from aegisflow_core.runtime.temporal.policies import (
    ActivityPolicy,
    AuthorizationFailure,
    FailureCategory,
    InvalidInputFailure,
    RateLimitFailure,
    SemanticFailure,
    TransientFailure,
    as_application_error,
    classify_failure,
    is_retryable,
    standard_activity_policy,
)


@pytest.mark.parametrize(
    ("error", "category", "retryable"),
    [
        (TransientFailure("temporary"), FailureCategory.TRANSIENT, True),
        (RateLimitFailure("limited", retry_after=7), FailureCategory.RATE_LIMIT, True),
        (AuthorizationFailure("denied"), FailureCategory.AUTHORIZATION, False),
        (InvalidInputFailure("bad"), FailureCategory.INVALID_INPUT, False),
        (SemanticFailure("tests failed"), FailureCategory.SEMANTIC, False),
        (TimeoutError(), FailureCategory.TRANSIENT, True),
        (ValueError(), FailureCategory.INVALID_INPUT, False),
    ],
)
def test_failure_classification(error: BaseException, category: FailureCategory, retryable: bool) -> None:
    assert classify_failure(error) == category
    assert is_retryable(error) is retryable


def test_rate_limit_carries_bounded_next_retry_delay() -> None:
    converted = as_application_error(RateLimitFailure("limited", retry_after=7))
    assert isinstance(converted, ApplicationError)
    assert converted.type == FailureCategory.RATE_LIMIT
    assert converted.next_retry_delay == timedelta(seconds=7)
    assert not converted.non_retryable


def test_permission_failure_is_non_retryable() -> None:
    converted = as_application_error(AuthorizationFailure("denied"))
    assert converted.non_retryable
    assert converted.type == FailureCategory.AUTHORIZATION


def test_activity_policy_is_bounded() -> None:
    policy = standard_activity_policy()
    assert policy.retry_policy.maximum_attempts == 5
    assert policy.retry_policy.maximum_interval == timedelta(seconds=30)
    assert policy.schedule_to_close_timeout >= policy.start_to_close_timeout
    with pytest.raises(ValueError):
        ActivityPolicy(timedelta(0), timedelta(seconds=1), policy.retry_policy)
