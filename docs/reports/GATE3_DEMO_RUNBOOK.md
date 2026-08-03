# Gate 3 Governance and Security Runbook

## Purpose

Reproduce the AF-412/AF-413 security evidence without real credentials, production writes, or mandatory screen recording.

## Preconditions

- Use the reviewed PR commit or a protected `main` commit.
- Do not enter, print, download, or copy any real Secret.
- Use the required GitHub Actions `test` job; local output is useful for diagnosis but is not protected evidence.

## Automated Run

1. Open the PR's required `test` check.
2. Confirm the run SHA matches the reviewed commit.
3. Confirm `Run Gate 3 security regression` passes without retry.
4. Confirm `Scan tracked files for credential signatures` reports no match.
5. Download `gate3-security-evidence-<run-id>` only when detailed review is required.
6. Verify the artifact contains `junit.xml`, `security-gate.log`, `secret-scan.log`, and `environment.txt`.
7. Record the Actions URL, commit SHA, artifact name, and JUnit pass/fail/error/skip counts in the PR review.

Local reproduction uses the same locked command:

```bash
uv sync --locked
uv run --locked alembic upgrade head
uv run --locked python -m pytest -q \
  tests/control_plane/test_oidc.py \
  tests/control_plane/test_rbac.py \
  tests/control_plane/test_audit_service.py \
  tests/control_plane/test_registry_service.py \
  tests/control_plane/test_tenant_scope.py \
  tests/gateway/mcp/test_registry_gate.py \
  tests/gateway/policy/test_contextual.py \
  tests/gateway/policy/test_injection.py \
  tests/gateway/sandbox/test_runner.py \
  tests/security/test_cross_tenant_isolation.py \
  tests/security/test_gate3_contract.py
```

## Review Scenarios

- Invalid identity is rejected by the OIDC cases.
- Tenant A cannot access tenant B through the scope and isolation cases.
- Insufficient role and self-approval are denied by the RBAC cases.
- Untrusted injected instructions cannot invoke write/high-risk tools.
- A registered, authorized, policy-approved path reaches its adapter once.
- Audit events correlate actor, tenant, action, target, decision, and reason while redacting credentials.

## Human Review Checklist

- [ ] Reviewed commit equals workflow commit.
- [ ] Required `test` check passed with no retry masking.
- [ ] JUnit has zero failures and errors; skips are explained.
- [ ] Secret scan passed and logs contain no credential value.
- [ ] Denial and approved-path cases are both present.
- [ ] Audit and cross-tenant assertions are present.
- [ ] Report limitations remain accurate.
- [ ] Human Reviewer accepts or rejects Gate 3 explicitly.

## Optional Video

A Human Reviewer may record the run for presentation purposes, but video is not required for Gate 3. If recorded, show only the approved fixture and redacted evidence; hide browser identity, private repository content outside scope, tokens, keys, environment values, and personal data.

## Stop Conditions

Stop and report instead of retrying or weakening the gate when the commit differs, any test fails, a credential signature is found, evidence is incomplete, a denial leaks another tenant's data, or the result conflicts with the report. Never approve, merge, rotate Secrets, or change branch protection from this runbook.
