# 16 — Observability Plan

## 分工

### Langfuse

Prompt version、LLM I/O、Agent step、Token、Cost、Dataset experiment、Agent evaluation。

### OpenTelemetry

FastAPI、Temporal、PostgreSQL/Redis、MCP、Sandbox、External API、系统延迟和错误。

### Prometheus/Grafana

业务和系统指标、Gate Dashboard、Alert。

## Correlation

```text
tenant_id
workflow_id
workflow_version
run_id
step_id
trace_id
```

## Business Metrics

Task completion、Tool success、Human intervention、Model fallback、Cost per task、Duplicate side effect、Recovery time、Prompt version performance。

## System Metrics

API latency、error rate、Temporal backlog、DB pool、Redis、Sandbox duration、CPU/memory、provider latency。

## Cardinality

raw user id、prompt text、issue title、stack trace、repository path 不得直接作为 Prometheus Label。

## Redaction

Secret、token、private key、Authorization、PII 和按配置的源代码必须脱敏。
