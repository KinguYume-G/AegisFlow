# 08 — Test Strategy

## 目标

测试是每个 Issue 的设计输入，不是上线前补充。

## Test Pyramid

### Unit

Domain rules、Policy、Idempotency key、Schema、Prompt rendering、Cost、Error classification。

### Component

Agent node、MCP adapter、Model gateway、Repository、Audit writer、Sandbox controller。

### Integration

Core + PostgreSQL、Redis、Temporal、GitHub test app、Langfuse、OTel 和 Sandbox。

### End-to-End

Gate 1A、1B、Gate 2 recovery、Gate 3 security、Gate 4 evaluation/deployment。

### Fault Injection

Kill worker、model outage、GitHub 429/5xx、Redis interruption、DB lock、duplicate webhook、approval delay、sandbox timeout。

### Security

Cross-tenant、missing scope、role escalation、prompt injection、secret leakage、webhook forgery、replay、path traversal、SSRF、command injection。

### Performance

100 concurrent control-plane users、queue delay、p50/p95/p99、error rate、resource usage、backpressure。

### Evaluation

SWE-bench subset、Delivery Golden Set、Security Injection Set、Historical Set、Single-Agent Baseline。

## Test First

实现 PR 必须先提交失败测试、接口契约测试、状态机测试或无法自动化时的可重复手工 Test Plan。

## Coverage

- Changed-line 目标 ≥ 90%
- Core domain overall 目标 ≥ 80%
- Coverage 不替代行为、安全和可靠性测试
- 不得排除关键文件美化数字

## Flaky Test

Flaky 视为失败，不得长期 retry 掩盖。无法立即修复时隔离并创建 P0/P1 Issue。

## External Integration

使用专用 GitHub 测试仓库；不使用生产 Secret；写操作自动清理；所有资源带幂等 Marker。

## Gate Suites

| Gate | Suite |
|---|---|
| 1A | Demand-to-Plan E2E |
| 1B | Plan-to-Draft-PR E2E |
| 2 | Worker Kill + Duplicate Side Effect |
| 3 | RBAC + Tenant + Injection + Audit |
| 4 | Golden Regression + Load + Deployment |

## Evidence

PR 记录命令、环境、结果、失败数、跳过数、Trace 和限制。“Tests passed”无证据不接受。
