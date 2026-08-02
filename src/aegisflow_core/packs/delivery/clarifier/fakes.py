"""Deterministic reasoner used before a real model provider is introduced."""

import re
from collections.abc import Callable

from aegisflow_core.packs.delivery.contracts.clarification import (
    Clarification,
    ClarificationQuestion,
)
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest


_REASONER_ID = "deterministic-clarifier-v1"
_DURATION_UNIT = r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|秒|分钟|小时|天|日|周|月|年)"


def _matches(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _has_authorized_roles(text: str) -> bool:
    role = r"(?:admin(?:istrator)?s?|owners?|reviewers?|developers?|operators?|auditors?|users?|roles?)"
    english = rf"(?:\bonly\b|\bexclusively\b).{{0,64}}\b{role}\b|\b{role}\b.{{0,32}}\bonly\b"
    chinese = r"(?:仅允许|只允许|仅限).{0,32}(?:管理员|审计员|所有者|开发者|运维|用户|角色)"
    return _matches(english, text) or _matches(chinese, text)


def _has_time_range(text: str) -> bool:
    default = rf"(?:\bdefault\b|默认).{{0,48}}\d+\s*{_DURATION_UNIT}"
    maximum = rf"(?:\bmaximum\b|\bmax\b|最大|最多|上限).{{0,64}}\d+\s*{_DURATION_UNIT}"
    return _matches(default, text) and _matches(maximum, text)


def _has_record_limit(text: str) -> bool:
    return _matches(
        r"(?:\bmaximum\b|\bmax\b|\blimit(?:ed)?\b|\bup to\b|最多|上限|不超过)"
        r".{0,40}\d+\s*(?:records?|rows?|items?|条(?:记录)?|行|项|个)",
        text,
    )


def _has_output_and_redaction(text: str) -> bool:
    fields = _matches(
        r"(?:\boutput\b|\breturn(?:ed)?\b)(?:\s+\w+){0,3}\s+\bfields?\b"
        r"|\bfields?\b\s+include\b|输出字段|返回字段",
        text,
    )
    redaction = _matches(
        r"\bredact(?:ed|ion)?\b|\bmask(?:ed|ing)?\b|\bpseudonym(?:ize|ized|ization)?\b"
        r"|\bhash(?:ed|ing)?\b|脱敏|掩码|隐藏|哈希|去标识",
        text,
    )
    return fields and redaction


def _has_delivery_mode(text: str) -> bool:
    small_sync = _matches(
        r"\bsmall\b.{0,64}\bsync(?:hronous(?:ly)?)?\b|小(?:型|量|数据量)?.{0,32}同步",
        text,
    )
    large_async = _matches(
        r"\blarge\b.{0,64}\basync(?:hronous(?:ly)?)?\b|大(?:型|量|数据量)?.{0,32}异步",
        text,
    )
    return small_sync and large_async


_RULES: tuple[tuple[str, str, Callable[[str], bool]], ...] = (
    ("authorized_roles", "哪些角色被明确允许执行该操作？", _has_authorized_roles),
    ("time_range", "默认时间范围与最大可选时间跨度是多少？", _has_time_range),
    ("record_limit", "单次处理的最大记录数是多少？", _has_record_limit),
    (
        "output_fields_and_redaction",
        "输出字段及敏感信息脱敏规则是什么？",
        _has_output_and_redaction,
    ),
    ("delivery_mode", "何时同步返回，何时转为异步任务？", _has_delivery_mode),
)


class DeterministicClarificationReasoner:
    """Apply the five approved rules in a stable order without external I/O."""

    def identify_gaps(self, request: NormalizedRequest) -> Clarification:
        text = f"{request.title}\n{request.body}"
        questions = [
            ClarificationQuestion(field=field, question=question)
            for field, question, has_evidence in _RULES
            if not has_evidence(text)
        ]
        return Clarification(
            questions=questions,
            is_sufficient=not questions,
            reasoner_id=_REASONER_ID,
        )
