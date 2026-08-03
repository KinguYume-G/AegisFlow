# M4 Governance & Security Bundle — AF-401 through AF-413

**Status:** Approved v1 — approved by the Project Owner on 2026-08-03

## Objective

Complete Gate 3 without changing AegisFlow's frozen architecture: every request is tenant-bound, externally authenticated, authorized by fixed RBAC and deterministic contextual policy, audited append-only, restricted to registered tool scopes, isolated in the sandbox, and tested against prompt injection and cross-tenant access.

This document is the shared contract for AF-401–AF-413. Approval authorizes implementation in the dependency waves below; each wave remains a separate branch and PR with Human Review.

## Non-Goals

- No generic ABAC engine, policy DSL, user-built roles, or LLM authorization decision.
- No password database, token issuer, OAuth consent UI, or identity-provider administration.
- No production secrets, production tenant onboarding, billing, SCIM, SSO UI, or enterprise directory sync.
- No arbitrary remote MCP discovery or unreviewed third-party MCP server.
- No k3s sandbox, deployment control plane, workflow builder, or frontend console.
- No architecture, state-ownership, Accepted ADR, or DeliveryPack scope changes.

## Authoritative Boundaries

- PostgreSQL owns tenant, membership, role assignment, immutable version, registry, approval, and audit facts.
- OIDC authenticates a subject; it does not directly grant AegisFlow permissions.
- RBAC maps stored tenant roles to fixed capabilities.
- Contextual policy evaluates trusted tenant/repository/environment/risk/approval/tool inputs in deterministic order.
- LLM output, prompts, RAG content, request headers, and tool arguments cannot set trusted identity or policy fields.
- Gateway owns policy, tool, provider, and sandbox boundaries; Temporal/LangGraph ownership remains unchanged.
- Redis and Langfuse never become authorization or business-fact sources.

## Implementation Waves

1. **Foundation — AF-401, AF-410, AF-411**: tenant-scoped data access and immutable prompt/workflow versions.
2. **Identity and execution boundary — AF-402, AF-403, AF-407**: OIDC verification, fixed RBAC, and sandbox hardening.
3. **Decision and tool governance — AF-404, AF-405, AF-406**: contextual policy, audit service, and scoped registry.
4. **Adversarial evidence — AF-408, AF-409**: injection detection and cross-tenant isolation suite.
5. **Gate 3 — AF-412, AF-413**: regression suite, evidence report, and reproducible demo runbook; video is optional supplementary evidence.

Dependencies are satisfied inside each wave in issue order. No downstream wave is marked ready before its required upstream PR is Human Merged.

## AF-401 — Tenant Scope

Introduce an explicit `TenantScope` and tenant-aware session/repository boundary under `control_plane/tenants/`.

- Every tenant-owned ORM read automatically receives tenant criteria.
- Every insert/update/delete verifies the row tenant matches the session tenant.
- Missing tenant scope fails before database access.
- The root `Tenant` catalog is accessed only through explicit bootstrap/admin methods, never through an ordinary tenant session.
- Session state is explicit and transaction-local; no process-global mutable tenant or ambient `ContextVar` is an authority source.
- Raw SQL in application paths is denied unless a reviewed tenant predicate and explicit internal escape hatch are present.
- Existing composite tenant foreign keys remain the database integrity backstop.

Application-level enforcement is the M4 baseline. PostgreSQL RLS is not claimed because the current development connection is also the schema owner; adding a non-owner runtime role/RLS lifecycle requires a separate reviewed deployment decision.

## AF-410 — Immutable Prompt Versions

Add immutable `prompt_versions` and `run_prompt_versions` facts.

- Identity: tenant, prompt name, monotonically increasing version.
- Payload: canonical template, SHA-256 content hash, creation actor/time, optional source-version reference.
- A database trigger rejects update/delete of version rows and run bindings.
- Publishing is concurrency-safe and rejects a reused version with different content.
- Rollback creates a new version from a selected historical version; history is never rewritten.
- A Run binds exact prompt-version IDs before execution and cannot be rebound.
- Prompt content is not treated as a Secret, but all rendering and tracing redaction rules still apply.

## AF-411 — Immutable Workflow Versions

Complete the existing `Workflow` model rather than replacing it.

- A version service publishes canonical definitions, verifies `definition_hash`, and serializes concurrent version allocation.
- Definition payloads are stored immutably for newly published versions; legacy hash-only bootstrap rows remain explicit legacy records and are never fabricated.
- Publishing a new version supersedes the previous active version without mutating its definition.
- Rollback publishes a new version derived from a historical definition.
- Runs continue to bind exact `workflow_id` and `workflow_version`; in-flight Temporal inputs retain their original version.
- Replay resolves the bound definition and fails honestly when a legacy payload is unavailable.
- Temporal workflow type/version changes remain code changes and are not dynamically generated from database content.

## AF-402 — OIDC Authentication

Add a provider-neutral bearer-token verifier under `control_plane/identity/`.

- Configuration is all-or-none: issuer, audience/client ID, allowed asymmetric algorithm, JWKS URL/discovery, and bounded cache/timeout values.
- Validate signature, issuer, audience, expiry, not-before, subject, and key ID.
- Reject `none`, symmetric confusion, missing claims, stale tokens, unknown keys, and malformed headers.
- JWKS resolution is injectable for deterministic tests, cached with a bound, and refreshed once for legitimate key rotation.
- Authentication yields an immutable `Principal(issuer, subject)` only; tenant and role authority are loaded from PostgreSQL.
- The service validates tokens only. It never stores passwords, issues tokens, performs refresh-token exchange, or logs bearer values.

Before protected real-provider evidence, the Project Owner must provide outside chat the non-secret development issuer/audience and configure any required GitHub Environment Secret. Unit and integration implementation uses generated test keys and makes no external call.

## AF-403 — Fixed RBAC

Store tenant memberships and role assignments in PostgreSQL. Roles are fixed:

`Admin`, `Developer`, `Reviewer`, `Security`, `DevOps`, and `Viewer`.

Capabilities are a code-owned enum and matrix covering tenant administration, run read/execute, approval decisions, audit/security read, scoped tool invocation, sandbox execution, and deployment operations.

- A subject may hold multiple roles per tenant; permissions are the union within that tenant only.
- Role assignment changes are audited and require an authorized Admin path.
- Unknown roles/capabilities and missing membership default to deny.
- API and tool authorization share the same evaluator and reason codes.
- No role can authorize AI self-approval or bypass required Human Review.

## AF-404 — Deterministic Contextual Policy

Extend the existing `gateway/policy` boundary with a versioned `PolicyInput` and explainable `PolicyDecision`.

Trusted inputs: authenticated principal, tenant membership, RBAC capabilities, repository allowlist, environment, risk, approval evidence, registered tool/version, and requested scope.

Evaluation order:

1. tenant/membership;
2. RBAC capability;
3. repository and environment boundary;
4. tool registration and scope;
5. risk ceiling and injection findings;
6. approval evidence and actor separation.

Outcomes are `allow`, `deny`, or `require_approval`, with stable rule/reason codes. Missing or contradictory evidence denies. LLM text cannot override the result.

## AF-405 — Append-Only Audit

Reuse the existing `audit_events` table and mutation trigger; add the production audit writer/query ports required by M4.

- Required fields: tenant, actor, action, resource type/id, decision, reason, trace, and created time.
- Authentication, authorization, policy, role assignment, tool invocation, sandbox, injection, and approval decisions emit bounded events.
- Secret values, bearer tokens, raw prompts, model responses, and unrestricted tool arguments are prohibited.
- Writes are transactionally coupled to the business decision when both are PostgreSQL facts.
- Tenant-scoped readers cannot access another tenant; no application delete/update API exists.
- Audit failure on a security-relevant state change fails closed rather than silently dropping evidence.

## AF-406 — MCP Registry and Scopes

Add immutable tool registrations under `control_plane/registries/` and an invocation gate under `gateway/mcp/`.

A registration contains tenant/owner scope, canonical tool name, version, adapter identifier, input/output schema hashes, allowed capability scopes, risk level, and enabled state. Version facts are immutable; disabling is a separate audited control fact.

Invocation order is authentication → RBAC → policy → registry/schema validation → adapter → redacted audit. Unknown, disabled, mismatched-version, out-of-scope, and schema-invalid tools deny before adapter execution. Credentials are resolved by reference inside the adapter and never accepted in model/tool arguments.

M4 registers reviewed internal adapters only; arbitrary network MCP discovery and OAuth/token forwarding are out of scope.

## AF-407 — Sandbox Hardening

Extend the existing narrow broker rather than giving Core Docker access.

- Preserve digest-pinned image, non-root user, read-only root, no network, no-new-privileges, dropped capabilities, resource/PID limits, bounded timeout, and tmpfs.
- Bound workspace file count, per-file size, archive size, output size, and extraction path.
- Reject symlinks, devices, FIFOs, absolute/traversal paths, sensitive filenames, and detected credential material before container creation.
- Do not inject host environment or Secret values into the workspace/container.
- Remove the owned container on success, failure, and timeout; bounded startup cleanup handles orphaned containers with AegisFlow ownership labels.
- Sanitize Docker errors and never expose socket paths or daemon details to an Agent.
- Mocked negative tests are mandatory; an optional Docker-marked live smoke runs only where a daemon exists.

## AF-408 — Prompt Injection Detection

Add deterministic classification at the untrusted Context/RAG-to-Policy boundary.

- `InjectionFinding` records source reference, rule ID, severity, bounded evidence hash/excerpt, and detector version.
- v1 rules identify explicit instruction override, credential/tool exfiltration requests, authority impersonation, and encoded-command indicators.
- Findings annotate content; they never execute, rewrite, or promote it to trusted instructions.
- High-severity untrusted findings deny write/high-risk tools and emit audit evidence.
- Detection failure or unknown classification cannot increase permission.
- No LLM classifier, autonomous remediation, or claim of complete injection detection.

## AF-409 — Cross-Tenant Isolation Suite

Use two synthetic tenants with intentionally colliding names and resource shapes. Cover:

- tenant-aware ORM reads/writes and composite foreign keys;
- FastAPI authentication/tenant dependency behavior;
- RAG ingestion and retrieval namespaces;
- trace metadata/query adapters;
- role/policy decisions and MCP tool invocation;
- audit read boundaries and immutable prompt/workflow bindings.

Tests must prove missing tenant, mismatched tenant, forged tenant input, reused IDs, and cross-tenant references are denied without leaking existence or content.

## AF-412 — Security Regression Suite

Create a deterministic `security_gate` suite covering positive, negative, escalation, replay, injection, sandbox, and cross-tenant paths. It runs inside the existing required `test` check so branch protection remains stable. Flaky retries are prohibited; failures produce bounded reason codes and no credentials.

Gate evidence reports cases, environment, commands, pass/fail/skip counts, limitations, and immutable Actions links.

## AF-413 — Gate 3 Demo

Publish a governance report and demo runbook that demonstrates:

- missing/invalid identity rejection;
- tenant A denied from tenant B;
- insufficient role denied;
- injection finding blocks a high-risk tool;
- authorized, approved path succeeds;
- audit correlation reconstructs the decision.

CI logs, JUnit, security audit evidence, limitations, and the reproducible runbook are the formal Gate 3 acceptance evidence. A Human-operated video is optional because recording a private repository UI can expose unrelated content; AI neither requires nor fabricates a recording.

## Migration and Rollback Rules

- One forward Alembic revision per implementation wave when schema changes are required.
- Every revision must downgrade/reapply in CI and preserve existing M1–M3 facts.
- Security triggers and immutable rows are removed only by explicit downgrade during rollback, never application cleanup.
- Each wave is revertible without requiring later-wave code.

## External Inputs

No external input is required for Wave 1.

Before AF-402 protected evidence:

- development OIDC issuer;
- audience/client ID;
- expected asymmetric signing algorithm;
- GitHub Environment holding any provider credential by Secret reference.

AF-413 requires no external input beyond Human Review of the protected CI evidence and runbook. A Project Owner may optionally perform or delegate a redacted recording using the approved runbook.

## Stop Conditions

Stop on architecture/ADR conflict, unclear tenant ownership, missing acceptance criteria, an unreviewed external MCP server, real Secret requirements in code/tests, unsafe Docker access, inability to test denial paths, or a request to let AI authorize/approve/merge its own protected action.

## Definition of Done

Each Issue satisfies its canonical acceptance criteria, tests precede implementation, migrations and rollback pass, changed-line coverage remains at least 90%, Security and cross-tenant negatives pass, documentation/traceability are synchronized, CI is green, and a Human merges the applicable wave PR.

## Open Questions for One-Time Approval

1. Approve the five-wave batching and one PR per wave.
2. Approve application-enforced tenant sessions for M4, with PostgreSQL RLS explicitly deferred rather than falsely claimed.
3. Approve immutable rollback-by-new-version for prompts and workflows.
4. Approve fixed code-owned roles/capabilities and no general ABAC/role builder.
5. Approve deterministic injection rules and policy denial; no LLM detector.
6. Confirm OIDC provider details may be supplied later, before Wave 2 protected evidence.
7. Resolved 2026-08-04: the Project Owner made video optional and accepted CI logs, JUnit, security audit evidence, limitations, and a reproducible runbook as the formal Gate 3 evidence.
