"""Tests for the deterministic AF-105 gap rules."""

from datetime import datetime, timezone

import pytest

from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.packs.delivery.clarifier.fakes import (
    DeterministicClarificationReasoner,
)


FIXED_QUESTIONS = {
    "authorized_roles": "哪些角色被明确允许执行该操作？",
    "time_range": "默认时间范围与最大可选时间跨度是多少？",
    "record_limit": "单次处理的最大记录数是多少？",
    "output_fields_and_redaction": "输出字段及敏感信息脱敏规则是什么？",
    "delivery_mode": "何时同步返回，何时转为异步任务？",
}

COMPLETE_BODY = """Only administrators may export audit data.
The default range is 7 days and the maximum custom range is 90 days.
Each request is limited to a maximum of 1000 records.
Output fields include event_id, actor, timestamp; sensitive fields are redacted.
Small datasets return synchronously; large datasets use an asynchronous job.
"""


def _request(body: str) -> NormalizedRequest:
    return NormalizedRequest(
        source_type="prd",
        source_ref="PRD-1",
        title="Audit export",
        body=body,
        idempotency_key="a" * 64,
        received_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


def _missing_fields(body: str) -> list[str]:
    result = DeterministicClarificationReasoner().identify_gaps(_request(body))
    return [question.field for question in result.questions]


@pytest.mark.parametrize(
    "body",
    [
        COMPLETE_BODY.replace("Only administrators may export audit data.\n", ""),
        COMPLETE_BODY.replace("Only administrators", "Administrators"),
    ],
)
def test_reasoner_rule_authorized_roles(body: str) -> None:
    assert "authorized_roles" in _missing_fields(body)


@pytest.mark.parametrize(
    "body",
    [
        COMPLETE_BODY.replace("The default range is 7 days and ", ""),
        COMPLETE_BODY.replace("the maximum custom range is 90 days", "the maximum range is configurable"),
    ],
)
def test_reasoner_rule_time_range(body: str) -> None:
    assert "time_range" in _missing_fields(body)


def test_reasoner_rule_record_limit() -> None:
    body = COMPLETE_BODY.replace("a maximum of 1000 records", "a configurable record limit")

    assert "record_limit" in _missing_fields(body)


@pytest.mark.parametrize(
    "body",
    [
        COMPLETE_BODY.replace("Output fields include event_id, actor, timestamp; ", ""),
        COMPLETE_BODY.replace("sensitive fields are redacted", "sensitive fields are returned"),
    ],
)
def test_reasoner_rule_output_and_redaction(body: str) -> None:
    assert "output_fields_and_redaction" in _missing_fields(body)


@pytest.mark.parametrize(
    "body",
    [
        COMPLETE_BODY.replace("Small datasets return synchronously; ", ""),
        COMPLETE_BODY.replace("large datasets use an asynchronous job", "large datasets are supported"),
    ],
)
def test_reasoner_rule_delivery_mode(body: str) -> None:
    assert "delivery_mode" in _missing_fields(body)


def test_reasoner_question_order_is_stable() -> None:
    result = DeterministicClarificationReasoner().identify_gaps(
        _request("Export the requested information.")
    )

    assert [question.field for question in result.questions] == list(FIXED_QUESTIONS)
    assert [question.question for question in result.questions] == list(FIXED_QUESTIONS.values())
    assert result.reasoner_id == "deterministic-clarifier-v1"
    assert result.is_sufficient is False


def test_reasoner_accepts_complete_request() -> None:
    result = DeterministicClarificationReasoner().identify_gaps(_request(COMPLETE_BODY))

    assert result.is_sufficient is True
    assert result.questions == []
    assert result.answers is None


def test_reasoner_matches_chinese_evidence_case_insensitively() -> None:
    body = """仅允许管理员导出审计数据。
默认范围为 7 天，最大自定义范围为 90 天。
单次最多返回 1000 条记录。
输出字段包括事件、操作者、时间；敏感字段必须脱敏。
小数据量同步返回，大数据量使用异步任务。
"""

    assert _missing_fields(body) == []
