# 17 — Evaluation Plan

## 目标

证明 AegisFlow 相比“单 Agent + 直接工具”在可靠性、安全、可控性和交付质量上的改进。

## Dataset

| Dataset | Size | Purpose |
|---|---:|---|
| SWE-bench Verified Python subset | 10–15 | 真实 Issue-Patch |
| Delivery Golden Set | 25–30 | 功能、Bug、重构、测试、文档 |
| Security Injection Set | 15–20 | 漏洞和 Prompt Injection |
| Historical Set | 5–10 | XueMai / SynTour |

## Baseline

Single Agent + direct tools；可选无 RAG / 无 Policy ablation。

## Metrics

Task Completion、Tool Success、Defect Detection、False Positive、Patch Applicability、Test Pass、Unauthorized Tool Rate、Injection Block、Token Cost、p95、Human Intervention、Recovery、Duplicate Side Effects。

## Reporting

小样本显示 `24/30 = 80%`，不能只写 `80%`。

## LLM-as-Judge

只辅助 deterministic tests、human sample、multiple judges、order swap 和 consistency。

## CI Regression

固定数据集和模型版本；比较阈值；退化阻止发布并生成报告。

任何 README 或简历数字必须链接固定 commit 的报告。
