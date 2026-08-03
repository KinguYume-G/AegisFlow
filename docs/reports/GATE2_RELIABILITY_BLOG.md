# Recovering Without Repeating: AegisFlow Gate 2

Reliable agent execution is not demonstrated by a happy-path demo. It is demonstrated when a worker disappears at an inconvenient moment and the system resumes without losing intent or repeating an external effect.

For AegisFlow Gate 2, we tested that boundary directly. A GitHub-hosted campaign terminated and restarted Temporal workers across four failure points, five times each. All 20 executions reached their terminal state. The campaign recorded zero duplicate external effects and zero lost durable Signals. Recovery measured 2.05 seconds at p50 and 2.97 seconds at p95, comfortably inside the 5-second and 15-second Gate targets.

## Why duplicate effects matter

Retrying code is easy. Retrying safely is not.

An agent workflow may create a pull request, submit an approval, or call an external tool. If a worker dies after the external system accepted the operation but before the workflow recorded success, a naive retry can perform the action twice.

AegisFlow separates durable orchestration from external-effect ownership. Temporal owns workflow progress and replay. PostgreSQL owns the idempotency ledger and business evidence. Every effect is claimed through a stable scope and key before execution, and compensation uses a separate fenced claim. The workflow can replay; the external effect cannot silently duplicate.

## Compensation is evidence, not cleanup magic

Gate 2 also adds reverse-order Saga compensation. Each completed action yields a typed receipt. If a later action fails, compensations execute in reverse order, record retryable and final outcomes, and escalate explicitly when automation cannot restore the intended state.

The important property is visibility. A failed compensation is not converted into success, and audit evidence is append-only.

## Models fail differently

The model gateway treats availability failures differently from configuration, authentication, and budget errors. Availability may move to a bounded fallback route. Invalid configuration and failed authorization stop immediately. A PostgreSQL-backed circuit breaker shares Closed/Open/Half-Open state between workers and permits only one fenced recovery probe.

We also ran a protected request against `deepseek/deepseek-v4-flash`. It returned measured token usage and provider-reported cost without logging the response body or API Key. The configured Gemini fallback was not called because the primary request succeeded. Fallback behavior is covered by deterministic tests; we do not describe that as a live provider outage.

## What Gate 2 proves—and what it does not

Gate 2 proves recovery for a defined 20-run worker-loss matrix, deterministic compensation and fallback behavior, and one protected real-provider request. It does not prove multi-region availability, provider SLA, long-duration chaos, tenant isolation, or production readiness.

That distinction is intentional. Evidence is useful only when its boundary is visible.

The next milestone applies the same discipline to tenant isolation, OIDC, RBAC, contextual policy, audit, sandbox hardening, and prompt-injection defense.

## Reproduce the evidence

The implementation is in [PR #100](https://github.com/KinguYume-G/AegisFlow/pull/100). The hosted [fault campaign](https://github.com/KinguYume-G/AegisFlow/actions/runs/30801262477) and [provider smoke](https://github.com/KinguYume-G/AegisFlow/actions/runs/30804037539) remain linked from the engineering report. Operators can reproduce the safe sequence using the accompanying [Gate 2 Demo Runbook](GATE2_DEMO_RUNBOOK.md).
