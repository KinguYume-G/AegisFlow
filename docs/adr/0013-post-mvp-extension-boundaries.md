# ADR-0013 — Bound Post-MVP Extensions to Existing Control-Plane Ports

- **Status**: Accepted
- **Date**: 2026-08-04
- **Decision owner**: Project Owner

## Context

M1–M5 is complete. The optional Post-MVP roadmap contains one OpsPilot experiment,
one local-model route, and one MCP integration. Implementing these as new services,
new autonomous agents, or new policy paths would weaken the frozen modular-monolith
and governance boundaries.

## Decision

1. **OpsPilot** is a separate application pack containing one deterministic,
   simulated GitHub Actions incident. It diagnoses fixture evidence and proposes a
   remediation that always requires human approval. It performs no external reads
   or writes and adds no new Agent role to DeliveryPack.
2. **vLLM** is an optional third route on the existing Model Gateway. It is disabled
   by default, forbidden in production configuration, restricted to a loopback
   OpenAI-compatible endpoint, and validated with `Qwen/Qwen3-0.6B`. Primary and
   fallback behavior remains unchanged when it is disabled.
3. **MCP** adds only a GitHub Actions read-only adapter for the observed dogfooding
   need: inspecting run, job, and artifact metadata. It uses the existing registry,
   contextual policy, credential, idempotency, injection, and audit gates. It cannot
   dispatch, rerun, cancel, download artifacts, read logs, or mutate GitHub.

## Consequences

- The three features remain optional and cannot block the core product.
- Secrets stay behind existing resolvers and are never included in tool output.
- All outputs are bounded, schema-validated, attributable, and testable without an
  external provider.
- A real vLLM smoke is environment evidence, not a required application startup
  dependency or a production-capacity claim.

## Rejected alternatives

- A new OpsPilot microservice or additional fixed Agent.
- Replacing either hosted model route with vLLM.
- A generic GitHub MCP client or any GitHub Actions write operation.
