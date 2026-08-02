# 18 — Reliability Plan

## 目标

Workflow 可恢复、外部副作用不重复、模型可降级、审批不丢失、Retry 不放大风险、Saga 可补偿、失败可重放。

## Failure Taxonomy

| Category | Example | Response |
|---|---|---|
| Transient | timeout, 5xx | retry |
| Rate Limit | 429 | Retry-After |
| Permanent | invalid input | fail |
| Authorization | missing scope | deny |
| Agent Quality | bad plan | HITL / rework |
| Tool Failure | tests failed | Executor rework |
| Security | injection | block + audit |
| Partial Side Effect | branch created, PR failed | resume / compensate |

## Recovery Measurement

Worker Recovery Time、Completion After Recovery、Duplicate Side-Effect Count、Lost Signal Count、Compensation Success 分开测量。

## Idempotency Ledger

```text
PENDING
EXECUTING
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
COMPENSATED
```

唯一约束或锁保证一个执行者。

## Retry Ownership

Temporal Activity 处理外部副作用；LangGraph Node 处理纯计算；Model Gateway 处理 provider retry/fallback。禁止三层无界重试。

## Chaos

kill worker、restart Core、model outage、GitHub timeout、duplicate webhook、delayed approval、DB transient error、sandbox timeout。

## Gate 2 Report

记录环境、版本、20 次运行、p50/p95、duplicate count、failure、limitations 和 raw evidence。
