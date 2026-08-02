# ADR-0008 — Split LLM and System Observability

- **Status**: Accepted
- **Decision**:
  - Langfuse：Prompt、LLM、Token、Cost、Agent Eval。
  - OpenTelemetry：API、Temporal、DB、MCP、Sandbox。
  - Prometheus/Grafana：指标和 Dashboard。
- **Correlation**: tenant_id、run_id、trace_id、workflow_version。
