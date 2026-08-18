# ADR-0014 — Development-Only Local MVP Execution Profile

- **Status**: Accepted
- **Date**: 2026-08-17
- **Decision owner**: Project Owner
- **Issues**: AF-R04, AF-R05, AF-R06 (#113–#115)

## Context

AegisFlow already contains the domain model, six fixed DeliveryPack agents,
LangGraph graphs, a Temporal workflow, PostgreSQL persistence, policy and approval
gates, a sandbox broker, model routing, and GitHub adapters. The production
assembly is intentionally fail-closed: the API has no local identity, the Worker
starts with `UnconfiguredGraphPort`, and the model gateway requires two hosted
routes before its optional vLLM fallback.

The next milestone must prove one honest local business loop without requiring
real OIDC, hosted-model, or GitHub App Secrets. The local machine has Docker
Desktop and Ollama available. A development convenience must not weaken the
production boundary or claim a real GitHub write that did not occur.

## Decision

1. Add one explicit, default-off **local MVP profile** for `development` and
   `test` only. Production configuration rejects every local-profile option.
2. The profile uses two synthetic, server-side tokens representing separate
   Developer and Reviewer principals. The browser never receives either token.
   Self-approval remains forbidden and no “always allow” authority is introduced.
3. The profile bootstraps one local tenant, the immutable Delivery workflow, one
   Developer membership, and one Reviewer membership idempotently.
4. Ollama is allowed as the sole route only inside this profile. It remains behind
   the existing `ModelGateway` and LiteLLM adapter, is bounded by output-token and
   timeout limits, and uses `qwen3:8b` by default. Accepted endpoints are exact
   loopback hosts for host execution or `host.docker.internal` for Docker Desktop.
   URLs with credentials, query strings, fragments, or non-HTTP schemes fail.
5. Temporal remains the owner of Run lifetime, retry, timeout, and Human Signal
   waits. LangGraph remains the owner of agent computation and checkpoint/resume.
   PostgreSQL remains the source of business facts and UI read models.
6. Local GitHub execution is an explicit **dry-run Draft PR candidate**. It is
   still protected by the run-level Policy Gate, exact action preview, separate
   Reviewer decision, content digest, idempotency ledger, and audit trail. It
   performs no GitHub mutation and never emits a fake GitHub URL.
7. Docker Sandbox Broker remains the only Docker boundary. The Worker receives a
   controlled per-run workspace under the shared broker-owned volume; it never
   modifies the checked-out AegisFlow repository.
8. The management console will use same-origin Next.js route handlers as a local
   backend-for-frontend. Those server handlers inject the selected synthetic
   persona token. Direct browser access to Core does not expose local tokens.

## Relationship to ADR-0013

ADR-0013 remains valid for its optional third vLLM fallback. This ADR adds a
narrower local-MVP exception: Ollama may be the only configured model route only
when the development/test local profile is explicitly enabled. It does not replace
or weaken the normal hosted primary/fallback production configuration.

## Alternatives

- Rejected: disabling authorization for localhost.
- Rejected: using one local principal for both creation and approval.
- Rejected: calling Ollama directly from individual agents outside ModelGateway.
- Rejected: reporting a local artifact as a real GitHub Draft PR.
- Rejected: moving workflow ownership from Temporal into LangGraph.
- Rejected: letting Core or the Worker access the Docker socket directly.

## Consequences

- A new contributor can run the complete governed business loop without real
  Secrets or external writes.
- Local execution remains visibly different from production in API metadata,
  audit evidence, and the future UI banner.
- The Worker needs a production assembly function rather than a placeholder port.
- Run request, human request, trace, event, result, and evaluation projections must
  be persisted so restart and UI reconstruction do not depend on process memory.

## Security Impact

- Local tokens are synthetic development credentials, compared in constant time,
  never logged, never returned by an API, and rejected in production.
- Repository identifiers, paths, prompt fields, model output, and tool arguments
  remain bounded and schema validated.
- Approval is bound to an exact repository scope, base revision, changed-file
  digest, and one pending decision. Reject/cancel is the safe UI default.
- Secrets, `.env` files, credentials, and raw provider errors are excluded from
  workspaces, prompts, traces, events, and sandbox archives.

## Migration / Rollback

Disable the local profile and Ollama route, stop the local console, and run the
database downgrade for the new read-model tables if complete removal is required.
Existing production routes, M1–M5 facts, and ADR-0013 behavior remain intact.

## Revisit Conditions

- Production self-hosted model serving is approved separately.
- A real OIDC provider and GitHub Fixture repository are configured for the demo.
- The local BFF is replaced with the production authentication deployment.
