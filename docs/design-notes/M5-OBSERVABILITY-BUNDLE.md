# M5 Observability Bundle — AF-508, AF-509, AF-511, AF-514

## Decision

- OpenTelemetry owns API, SQLAlchemy, Temporal, MCP, and Sandbox system spans; span attributes contain only correlation IDs and bounded technical values.
- Prometheus exposes success/failure, latency, model cost, queue depth, and resource gauges with code-owned low-cardinality labels.
- Locust supplies a reproducible 100-user control-plane profile; measured claims require an attached run report.
- The run graph is a read-only Core API backed by PostgreSQL facts and protected by OIDC plus tenant-local `run:read` RBAC. It exposes node status, duration, trace ID, and persisted failure reason.

## Non-goals

No Grafana dashboard, deployment cluster, write UI, new business state, raw prompt telemetry, user-controlled metric labels, or real credentials.

## Rollback

Remove the instrumentation composition and routes. PostgreSQL schema and business facts are unchanged.
