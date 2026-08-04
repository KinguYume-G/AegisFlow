# M5 Evaluation Gates Test Plan — AF-504, AF-506, AF-507, AF-510

Status: Approved by Project Owner on 2026-08-04.

- Validate exactly five unique historical cases, approved source systems, immutable SHAs, sanitization, ground truth, and absence of secret-shaped content.
- Aggregate every required metric; verify ratios retain numerator/denominator, p95 is deterministic, and unavailable metrics are not represented as zero.
- Exercise green and red regression decisions, zero baselines, missing metrics, incompatible units, 0% correctness tolerance, and 10% cost/latency tolerance.
- Run the regression CLI in CI, retain its JSON decision artifact on success or failure, and prove a deliberately degraded fixture exits non-zero.
- Parse the Grafana dashboard and assert all six required panels use bounded AegisFlow Prometheus metrics.
- Verify human-intervention labels reject unknown values and `/metrics` exports accepted observations.
- Run the complete repository test and coverage gates plus the tracked-file credential scan.
