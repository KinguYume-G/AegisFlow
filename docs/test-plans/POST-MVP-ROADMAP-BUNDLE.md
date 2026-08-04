# Post-MVP Roadmap Bundle Test Plan — AF-R01, AF-R02, AF-R03

Status: Approved by Project Owner on 2026-08-04.

## AF-R01

1. Parse only the frozen synthetic fixture and reject malformed/non-simulated data.
2. Assert deterministic diagnosis, bounded evidence, and mandatory human approval.
3. Assert there is no network, persistence, command execution, or DeliveryPack
   Agent change.

## AF-R02

1. Prove the disabled default preserves the existing two-route chain.
2. Reject partial, production, non-loopback, credential-bearing, or malformed local
   configuration.
3. Prove third-route ordering, distinct route names, circuit behavior, and bounded
   metrics.
4. Prove LiteLLM receives the local `api_base` and no SDK retries.
5. Run a bounded official vLLM container smoke with `Qwen/Qwen3-0.6B` when the local
   Docker/GPU environment permits; report any environment limitation truthfully.

## AF-R03

1. Validate run/job/artifact schemas, pagination, item bounds, and truncation.
2. Prove only GET requests are emitted and logs/artifact content are not exposed.
3. Prove malformed, permission, timeout, and upstream failures remain redacted.
4. Invoke through the existing MCP gate and verify tenant, repository, scope,
   registry, policy, idempotency, schema, and audit enforcement before the adapter.

## Regression gate

Run targeted tests, then the complete locked test suite with branch coverage at or
above 90%. Scan the diff for secrets and confirm Architecture and ADR-0001–0012 are
unchanged.

## Execution evidence — 2026-08-04

- Targeted tests: 61 passed, 1 PostgreSQL environment skip; final full local suite:
  540 passed, 27 environment-gated skips, 0 failures.
- Official v0.23.0 image initialized the model but failed under Docker Desktop/WSL
  because Model Runner V2 requires unavailable UVA. This result is retained as a
  compatibility limitation, not reported as success.
- Official `vllm/vllm-openai:v0.18.0` with `--enforce-eager`, loopback-only port,
  and `Qwen/Qwen3-0.6B` passed `/health` and the AegisFlow LiteLLM smoke:
  `latency_ms=953.0`, `total_tokens=33`, `cost_source=not_available`. This is a
  single local functional measurement, not a production performance claim.
