# 01 — Master Task Book

## 目的

把冻结产品方案转化为 Work Breakdown Structure。所有开发工作必须映射到本文件、Milestone 和 GitHub Issue。

## Workstreams

| ID | Workstream | 核心产物 | Milestone |
|---|---|---|---|
| WS-00 | Governance & Documentation | Charter、ADR、Guides、Issue System | M0 |
| WS-01 | Repository Foundation | 模块化单体骨架、配置、质量工具 | M1 |
| WS-02 | DeliveryPack Agent Flow | 六 Agent 闭环 | M1–M2 |
| WS-03 | RAG & Context | 代码/文档/ADR/历史 PR 检索 | M1–M2 |
| WS-04 | GitHub & MCP | GitHub App、MCP Tool、Draft PR | M2 |
| WS-05 | Sandbox | Docker 沙箱到 k3s Job | M2–M5 |
| WS-06 | Durable Workflow | Temporal、Signal、Retry、Saga | M3 |
| WS-07 | State & Idempotency | Checkpoint、Ledger、零重复副作用 | M3 |
| WS-08 | Model Gateway | LiteLLM、熔断、降级 | M3 |
| WS-09 | Governance & Security | Tenant、OIDC、RBAC、Policy、Audit | M4 |
| WS-10 | Evaluation | Golden、Baseline、Regression | M5 |
| WS-11 | Observability | Langfuse、OTel、Prometheus、Grafana | M1–M5 |
| WS-12 | Deployment | Docker Compose、k3s、Helm | M1–M5 |
| WS-13 | Dogfooding | 三个个人项目 + 实习跟踪薄流 | M5 |
| WS-14 | Packaging | README、Demo、Blog、Reports | M3–M5 |
| WS-R1 | OpsPilot Roadmap | 单场景模拟 | Post-MVP |

## Dependency Spine

```text
WS-00
  ↓
WS-01
  ↓
WS-02 ── WS-03 ── WS-04 ── WS-05
  ↓
WS-06 ── WS-07 ── WS-08
  ↓
WS-09
  ↓
WS-10 ── WS-11 ── WS-12
  ↓
WS-13 ── WS-14
```

## 任务层级

- Epic：跨多个 Issue 的能力；
- Issue：一个 PR 可以交付；
- Task：Issue 内一天内完成；
- Checklist：验收或操作步骤。

Issue 预计超过 3 个工作日或改动超过两个核心模块时必须拆分。

## 主要交付物

### M0

Charter、Master Task Book、Architecture、Roadmap、Milestones、Issue Backlog、Developer Guide、AI Protocol、Test/Security/Reliability/Evaluation Plans、ADRs、GitHub Templates。

### M1–M2

六 Agent、RAG、GitHub App、GitHub MCP、Docker Sandbox、Policy Gate、Draft PR、Trace 和 Cost。

### M3

Temporal、Signal、Checkpoint、Idempotency Ledger、Retry/Timeout/Saga、Worker Kill Test、LiteLLM、Circuit Breaker。

### M4

Tenant、OIDC、RBAC、Contextual Policy、Audit、Tool Scope、Prompt Injection、Cross-Tenant Test、Versioning。

### M5

Golden Dataset、Baseline、Regression CI、OTel、Prometheus/Grafana、Locust、k3s、Helm、Dogfooding、Final Demo。

## 项目节奏

- 每日只推进一个主 Issue；
- 每个 PR 一个明确目标；
- 每周 Milestone Review；
- Gate 未过冻结新功能；
- 架构变化必须 ADR；
- 失败必须写入 Risk、Decision 或 Evaluation。

## 完成标准

所有 P0/P1 Issue 关闭、Gate 1–4 通过、文档与实现一致、演示可复现，MVP 才完成。
