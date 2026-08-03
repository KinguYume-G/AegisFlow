# Test Plan — M4 Governance & Security Bundle

**Status:** Approved v1 — approved by the Project Owner on 2026-08-03

## Scope

Verify AF-401–AF-413 tenant isolation, OIDC authentication, RBAC, deterministic policy, append-only audit, scoped tool registry, sandbox hardening, prompt-injection handling, immutable versioning, and Gate 3 evidence.

## Wave 1 — AF-401, AF-410, AF-411

### Tenant scope

- Missing tenant scope rejects before SQL execution.
- Reads automatically include tenant criteria for every tenant-owned mapped type.
- Insert/update/delete with a mismatched tenant rejects before flush.
- Tenant A cannot read, infer, update, or delete Tenant B rows, including reused UUID inputs.
- Admin/bootstrap tenant catalog access requires its distinct explicit path.
- Application raw SQL without reviewed tenant scope is rejected.

### Prompt versions

- Concurrent first/next publication produces one ordered sequence.
- Same version/same content is idempotent; same version/different content conflicts.
- Update/delete triggers reject version and run-binding mutation.
- Rollback publishes a new version with the historical content/hash and audit reference.
- A Run cannot be rebound to a different prompt version.
- Cross-tenant version/run binding fails at the database boundary.

### Workflow versions

- Canonical definition hash matches persisted definition.
- Concurrent version allocation is ordered without duplicates.
- Existing immutable trigger still rejects definition mutation/deletion.
- New publication supersedes only the previous active row.
- Rollback publishes a new version; historical rows remain unchanged.
- In-flight Run and Temporal identity retain their original workflow version.
- Replay resolves the exact payload; legacy hash-only rows fail explicitly rather than inventing content.

## Wave 2 — AF-402, AF-403, AF-407

### OIDC

- Valid generated asymmetric token authenticates with expected issuer/audience/subject.
- Reject bad signature, wrong issuer/audience, expired/not-yet-valid token, missing subject/kid, `none`, algorithm confusion, malformed bearer header, and oversized token.
- JWKS cache is bounded; unknown key causes at most one refresh and supports rotation.
- Network timeout/configuration errors fail closed and logs contain no token.

### RBAC

- Every fixed role has an explicit positive and negative capability matrix.
- Multi-role union is tenant-local; no role crosses tenants.
- Missing membership, unknown role/capability, escalation attempt, and self-approval deny.
- API and tool paths return the same decision/reason for the same principal and capability.
- Role assignment changes require Admin authorization and append audit evidence.

### Sandbox

- Broker preserves every required Docker hardening option.
- Reject mutable images, symlinks, path traversal, devices/FIFOs, oversized files/count/archive/output, sensitive filenames, and credential patterns.
- No host environment/Secret is passed to container creation.
- Success, exception, timeout, extraction failure, and client disconnect remove owned containers.
- Orphan cleanup affects only labeled, expired AegisFlow containers.
- Optional live Docker smoke verifies no network, non-root, read-only root, resource cap, and cleanup; absence of a daemon is declared, not disguised.

## Wave 3 — AF-404, AF-405, AF-406

### Contextual policy

- Table-driven cases cover every evaluation rule and stable reason code.
- Missing/contradictory trusted context denies.
- Repository, environment, risk, approval, scope, injection, and actor-separation boundaries cover allow/deny/require-approval outcomes.
- Prompt/model/tool text cannot override policy fields or decisions.

### Audit

- Required fields and bounds are enforced.
- Security-relevant state change and audit write commit/rollback together.
- Update/delete trigger and application API reject mutation.
- Tenant-scoped queries cannot return another tenant's events.
- Secret/token/prompt/tool-argument redaction tests include representative credential shapes.
- Audit failure prevents the corresponding protected mutation.

### Registry and invocation

- Registered enabled version with exact schema/scope can reach a fake adapter.
- Unknown, disabled, stale/mismatched version, schema mismatch, missing capability/scope, high risk without approval, and tenant mismatch never invoke the adapter.
- Credential references resolve only inside adapters; values never enter request schemas, audit, prompt, or error output.
- Duplicate invocation remains subject to the existing idempotency ledger.

## Wave 4 — AF-408, AF-409

### Prompt injection

- Fixed multilingual fixtures cover instruction override, exfiltration, impersonation, encoded command, benign security discussion, and ambiguous content.
- Findings are deterministic, bounded, source-linked, versioned, and contain no full secret.
- High-severity untrusted finding denies high-risk/write tools and emits audit evidence.
- Detector exception/unknown state cannot increase authorization.
- False-positive limitations are recorded; no completeness claim.

### Cross-tenant suite

- Two tenants with colliding names/resources cover API, ORM/DB, RAG, trace, RBAC/policy, registry/tool, audit, prompt, and workflow version boundaries.
- Test missing, forged, stale, and mismatched tenant identifiers.
- Denials do not reveal resource existence or content.
- Parallel requests prove no session/context leakage.

## Wave 5 — AF-412, AF-413

- `security_gate` runs deterministically inside required CI with no retry masking.
- Record exact case/pass/fail/skip counts, environment, command, commit, Actions URL, limitations, and Secret scan.
- Demo runbook reproduces denied cross-tenant, denied role escalation, blocked injection, approved path, and correlated audit.
- Video is optional supplementary evidence. If a Human records one, the redaction checklist prohibits tokens, keys, private repository content outside the approved fixture, and personal data.
- Gate 3 is accepted only after Human Review of the protected CI logs, JUnit, security audit evidence, report, reproducible runbook, and limitations.

## Migration Matrix

For every schema wave:

1. upgrade from current head;
2. verify constraints/triggers and expected data;
3. run upgrade again for deployment idempotency expectations;
4. downgrade one revision;
5. re-upgrade to head;
6. run `alembic check`;
7. confirm existing M1–M3 rows remain valid.

## Security and Secret Checks

- Scan staged diff, fixtures, workflow logs, audit rows, exception text, and sandbox archives.
- Never use production credentials or customer data.
- Test keys are generated at runtime and never committed.
- External provider tests use protected GitHub Environment references only.
- Any credential-shaped output fails the test rather than being approved as a fixture.

## Quality Gates

- Tests precede production implementation in every wave.
- Changed-line coverage ≥90%; repository threshold remains ≥90%.
- No excluded security-critical file to improve coverage.
- Full existing suite, PostgreSQL migrations, Compose configuration, relevant container build, module boundaries, Markdown links, MANIFEST, and dependency compatibility pass.
- Flaky retry count is zero.

## Evidence Required Per PR

- Exact commands and environment.
- Test counts and failures/skips.
- Migration head and downgrade/reapply result.
- Security negative-case summary.
- Secret-scan result.
- Changed-file scope and rollback method.
- Honest external-input limitations.

## Stop Conditions

Stop if tenant isolation cannot be enforced without an architecture change, OIDC authority is unavailable for its protected evidence, Docker tests require unsafe host access, a real Secret would enter code/tests/logs, a security test is flaky, an unregistered tool would execute, or Human Review/Gate evidence is unavailable.

## External Inputs

- Wave 1: none.
- Wave 2 OIDC protected evidence: development issuer, audience/client ID, algorithm, and protected GitHub Environment configuration.
- Wave 2 sandbox live smoke: Docker-capable runner; mocked tests remain mandatory.
- Wave 5: no external runtime input; an optional Human-operated redacted demo recording is not an acceptance dependency.
