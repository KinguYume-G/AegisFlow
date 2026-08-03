# Gate 3 Governance and Security Report

**Milestone:** M4 Governance & Security

**Issues:** AF-412 and AF-413

**Evidence status:** CI verified — requires Human Review and Human Merge

## Result

Gate 3 consolidates the implemented M4 controls into one deterministic regression gate inside the existing required `test` CI job. The gate fails closed and produces a 30-day evidence artifact containing JUnit results, the complete bounded test log, the tested commit and tool versions, and a tracked-file credential-signature scan.

The gate covers:

| Control | Executable evidence |
|---|---|
| Missing, invalid, expired, or malformed identity | `tests/control_plane/test_oidc.py` |
| Tenant-local roles, denial, and self-approval prevention | `tests/control_plane/test_rbac.py` |
| Complete, redacted, append-only audit records | `tests/control_plane/test_audit_service.py` |
| Tenant-scoped tool registration and invocation | `tests/control_plane/test_registry_service.py`, `tests/gateway/mcp/test_registry_gate.py` |
| Default-deny policy and separate approval | `tests/gateway/policy/test_contextual.py` |
| Deterministic injection detection and high-risk denial | `tests/gateway/policy/test_injection.py` |
| Bounded sandbox execution and cleanup | `tests/gateway/sandbox/test_runner.py` |
| API, retrieval, trace, and concurrent cross-tenant isolation | `tests/control_plane/test_tenant_scope.py`, `tests/security/test_cross_tenant_isolation.py` |

## Required Evidence

For the reviewed commit, the required GitHub Actions `test` job must provide:

- a successful `Run Gate 3 security regression` step with no retry;
- `junit.xml` with exact pass, fail, error, and skip counts;
- `security-gate.log` with the invoked cases and bounded failures;
- `secret-scan.log` showing no tracked credential signature;
- `environment.txt` containing the commit, runner, Python, and uv versions;
- the immutable Actions run URL and `gate3-security-evidence-<run-id>` artifact name.

## Verified CI Evidence

| Evidence | Result |
|---|---|
| Draft PR | [PR #108](https://github.com/KinguYume-G/AegisFlow/pull/108) |
| Evidence-producing implementation commit | `8b79531ef7ecf0df2fbad19f2a23ea20638ad90f` |
| Required CI | [Actions run 30831661867](https://github.com/KinguYume-G/AegisFlow/actions/runs/30831661867), passed in 2m15s |
| Gate 3 matrix | 83 passed in 2.36s; 0 failed, 0 errored, 0 skipped |
| Full repository suite | 526 passed, 1 protected-environment skip |
| Coverage | 90.86%; required 90% gate passed |
| Credential-signature scan | 0 findings in scanned tracked files |
| Evidence artifact | `gate3-security-evidence-30831661867`, artifact ID `8863182478`, 3,060 bytes, not expired at report update |

These results apply to the evidence-producing implementation commit. The PR's final head must also pass Required CI; its current status is authoritative and avoids a self-referential documentation-only commit SHA.

## Security Properties

- Authorization decisions are deterministic; no LLM grants authority.
- Denials use bounded reason codes and do not reveal credentials or cross-tenant resource contents.
- Audit assertions prove correlation and redaction without publishing production data.
- CI uses synthetic test identities, tenants, resources, and placeholder database credentials only.
- The credential scan examines tracked repository content and does not read GitHub Secrets.

## Limitations

1. This is deterministic regression evidence, not a penetration test or proof that prompt injection is completely detectable.
2. OIDC tests use controlled keys and resolvers; live identity-provider availability is outside this gate.
3. Sandbox tests verify the broker contract and bounded Docker command construction; production cluster isolation remains deployment evidence.
4. The scan detects defined credential signatures, not every possible sensitive-data format. Two explicit redaction-test files containing inert credential-shaped fixtures are allowlisted; their redaction behavior remains covered by pytest.
5. The GitHub artifact expires after 30 days; the immutable run URL and reviewed commit remain the evidence locator.
6. Video is optional supplementary evidence and is not a Gate 3 acceptance requirement.

## Acceptance

Gate 3 may be accepted only after a Human Reviewer confirms the required CI passed on the reviewed commit, the evidence artifact is complete, the limitations are accurate, and the runbook is reproducible. AI does not approve or merge the PR.
