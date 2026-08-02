# 03 — Roadmap

## 原则

- 12 周主线不变；
- Gate 未通过时冻结新功能；
- 文档和图表时间不超过实现时间 20%；
- OpsPilot 只在 Gate 1–4 通过后启动；
- Personal Workbench 只做最薄 Dogfooding；
- 不为技术栈完整度引入被否决组件。

## M0 — Engineering System

交付 Charter、Architecture、ADR、Roadmap、Milestones、Issue Backlog、Developer Guide、AI Protocol、质量基线和 GitHub Templates。退出时无业务代码。

## Week 1–3 — Gate 1

### Gate 1A：需求到方案

```text
Issue / PRD → Intake → Clarifier → Context → Planner → Evidence-based Plan
```

### Gate 1B：方案到 Draft PR

```text
Plan → Policy Gate → Executor → Docker Sandbox → Reviewer → Approval → Draft PR
```

必须有 PostgreSQL、Redis、Docker Compose、GitHub App/MCP、LangGraph 六 Agent、Langfuse Trace/Cost 和一个真实需求。

止损：Gate 1A 不过不开始 Executor；Gate 1B 不过冻结治理和模型高级能力，先补齐 Draft PR。

## Week 4–6 — Gate 2

Temporal、durable signal、PostgresSaver、Idempotency Ledger、Retry/Timeout/Saga、Kill Worker、LiteLLM、熔断和降级。

演示目标：恢复 p50 < 5 秒、p95 < 15 秒；重复外部副作用为 0。目标必须通过真实测试验证。

## Week 7–9 — Gate 3

Tenant、OIDC、RBAC、Contextual Policy、Audit、MCP Scope、Sandbox Hardening、Prompt Injection、Cross-Tenant Test、Prompt/Workflow Version。

## Week 10–12 — Gate 4

Golden Dataset、Single-Agent Baseline、Prompt Regression CI、OTel、Prometheus/Grafana、100 并发、k3s、Helm、Personal Workbench 薄版、README/Demo/Reports。

## Post-MVP

OpsPilot 单场景模拟；有 GPU 时可选 vLLM；更多 MCP 只按真实 Dogfooding 需求增加。
