# M5 Observability Bundle Test Plan

- Verify correlation fields propagate while secret-shaped inputs never become span attributes.
- Verify API and SQLAlchemy instrumentation is optional and exporter-free by default.
- Verify Prometheus names and labels are bounded; unknown components/outcomes fail closed.
- Verify `/metrics` exposes success/failure and latency observations.
- Verify Run Graph orders nodes, computes durations, exposes trace/failure evidence, and filters by tenant.
- Verify the HTTP endpoint denies missing identity, invalid tokens, missing membership, and cross-tenant reads.
- Verify the Locust profile defines bounded `/health` and `/metrics` scenarios and supports 100 users without embedding credentials.
