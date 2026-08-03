"""Deterministic prompt-injection findings at the untrusted-content boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import re
import unicodedata
from typing import Literal, Protocol
from uuid import UUID

from aegisflow_core.control_plane.audit import redact_audit_text
from aegisflow_core.gateway.policy.contextual import (
    ContextualPolicy,
    ContextualPolicyDecision,
    PolicyInput,
)

Severity = Literal["none", "low", "medium", "high", "unknown"]
_DETECTOR_VERSION = "deterministic-v1"
_MAX_INPUT = 100_000
_MAX_EXCERPT = 160


@dataclass(frozen=True, slots=True)
class UntrustedContent:
    source_reference: str
    content: str


@dataclass(frozen=True, slots=True)
class InjectionFinding:
    source_reference: str
    rule_id: str
    severity: Literal["low", "medium", "high"]
    evidence_hash: str
    evidence_excerpt: str
    detector_version: str = _DETECTOR_VERSION


@dataclass(frozen=True, slots=True)
class InjectionAssessment:
    status: Literal["classified", "unknown"]
    findings: tuple[InjectionFinding, ...]
    maximum_severity: Severity
    detector_version: str = _DETECTOR_VERSION


class InjectionAudit(Protocol):
    async def record(self, **fields: object) -> None: ...


class PromptInjectionDetector:
    """Fixed rules; findings are evidence, never executable instructions."""

    _RULES = (
        (
            "instruction_override",
            "high",
            re.compile(
                r"\b(?:ignore|disregard|override)\b.{0,48}\b(?:previous|prior|system|developer)\b.{0,24}\b(?:instruction|prompt|message)s?\b|"
                r"忽略.{0,16}(?:之前|先前|系统|开发者).{0,12}(?:指令|提示|消息)",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "credential_exfiltration",
            "high",
            re.compile(
                r"\b(?:reveal|show|print|export|exfiltrat\w*)\b.{0,48}\b(?:secret|token|password|api[-_ ]?key|credential|tool credential)s?\b|"
                r"(?:泄露|显示|输出|导出).{0,32}(?:密钥|令牌|密码|凭据|token)",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "authority_impersonation",
            "medium",
            re.compile(
                r"\b(?:i am|act as|pretend to be)\b.{0,24}\b(?:the )?(?:system|administrator|developer)\b|"
                r"(?:我是|充当|假装是).{0,16}(?:系统|管理员|开发者)",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "encoded_command",
            "high",
            re.compile(
                r"\b(?:powershell\s+(?:-enc|-encodedcommand)|eval\s*\(\s*atob|base64\s+(?:-d|--decode)|curl\b.{0,80}\|\s*(?:sh|bash)\b)",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
    )

    def detect(self, text: str, *, source_reference: str) -> InjectionAssessment:
        if not source_reference.strip():
            raise ValueError("source_reference is required")
        normalized = unicodedata.normalize("NFKC", text[:_MAX_INPUT])
        findings: list[InjectionFinding] = []
        for rule_id, severity, pattern in self._RULES:
            match = pattern.search(normalized)
            if match is None:
                continue
            evidence = match.group(0)
            findings.append(
                InjectionFinding(
                    source_reference=source_reference,
                    rule_id=rule_id,
                    severity=severity,  # type: ignore[arg-type]
                    evidence_hash=sha256(evidence.encode("utf-8")).hexdigest(),
                    evidence_excerpt=redact_audit_text(evidence)[:_MAX_EXCERPT],
                )
            )
        rank = {"low": 1, "medium": 2, "high": 3}
        maximum: Severity = max(
            (finding.severity for finding in findings),
            key=lambda value: rank[value],
            default="none",
        )
        return InjectionAssessment("classified", tuple(findings), maximum)

    def detect_safely(self, text: str, *, source_reference: str) -> InjectionAssessment:
        try:
            return self.detect(text, source_reference=source_reference)
        except Exception:
            return InjectionAssessment("unknown", (), "unknown")


class InjectionPolicyGuard:
    def __init__(
        self,
        *,
        audit: InjectionAudit,
        detector: PromptInjectionDetector | None = None,
        policy: ContextualPolicy | None = None,
    ) -> None:
        self._audit = audit
        self._detector = detector or PromptInjectionDetector()
        self._policy = policy or ContextualPolicy()

    async def evaluate(
        self,
        *,
        content: str,
        source_reference: str,
        policy_input: PolicyInput,
        trace_id: str,
    ) -> tuple[InjectionAssessment, ContextualPolicyDecision]:
        if not isinstance(policy_input.tenant_id, UUID):
            raise ValueError("authenticated tenant_id is required")
        assessment = await self.assess(
            content=content,
            source_reference=source_reference,
            tenant_id=policy_input.tenant_id,
            actor=policy_input.request_actor,
            trace_id=trace_id,
        )
        decision = self._policy.evaluate(
            replace(policy_input, injection_severity=assessment.maximum_severity)
        )
        return assessment, decision

    async def assess(
        self,
        *,
        content: str,
        source_reference: str,
        tenant_id: UUID,
        actor: str,
        trace_id: str,
    ) -> InjectionAssessment:
        """Classify one untrusted source and persist bounded evidence."""
        if not isinstance(tenant_id, UUID):
            raise ValueError("authenticated tenant_id is required")
        assessment = self._detector.detect_safely(
            content, source_reference=source_reference
        )
        if assessment.findings or assessment.status == "unknown":
            hashes = ",".join(item.evidence_hash for item in assessment.findings)
            rules = ",".join(item.rule_id for item in assessment.findings) or "unknown"
            await self._audit.record(
                tenant_id=tenant_id,
                actor=actor,
                action="prompt_injection.detect",
                resource_type="untrusted_content",
                resource_id=source_reference,
                decision="detected",
                reason=f"{assessment.maximum_severity};rules={rules};evidence={hashes}",
                trace_id=trace_id,
            )
        return assessment
