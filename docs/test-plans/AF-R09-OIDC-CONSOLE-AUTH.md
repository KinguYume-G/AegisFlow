# Test Plan — AF-R09 Production OIDC Sessions and Console Authorization

Status: Defined before AF-R09 business implementation.

## Scope

Verify provider-neutral Authorization Code + PKCE login, strict OIDC/JWKS access
token verification, hashed opaque PostgreSQL sessions, tenant membership, fixed
RBAC, separate-human approval, CSRF, logout/expiry, local Keycloak composition and
the authenticated Next.js user experience. Preserve the complete local-MVP
regression path and the repository 90% backend coverage gate.

## Unit Tests

### Core identity and session

1. Opaque token generation has the required entropy and only its SHA-256 digest is
   persisted.
2. Session expiry cannot exceed verified token expiry or configured maximum.
3. Missing, malformed, oversized, unknown, expired and revoked session tokens return
   stable credential-free errors.
4. Session revocation is idempotent and monotonic.
5. OIDC group/role claims cannot create membership or grant capability.
6. HTTPS remains mandatory in production; explicit local HTTP accepts only approved
   `*.localhost` development/test endpoints.
7. Partial OIDC client/session configuration, weak keys, unsafe callback/logout URLs
   and enabled production bootstrap fail configuration loading.

### Console OIDC and cookies

1. Login creates fresh state, nonce and PKCE S256 values and an encrypted transient
   cookie with a bounded lifetime.
2. Callback validates exact state, nonce, issuer, audience, callback URL and PKCE;
   mismatch/replay/error clears the transaction and creates no session cookie.
3. Return paths accept only bounded same-origin relative paths; protocol-relative,
   absolute, encoded and control-character redirects are rejected.
4. Production session cookie is `__Host-`, Secure, HttpOnly, SameSite=Lax and Path=/;
   local exceptions cannot be selected in production.
5. Provider/client/session credentials are absent from public context, component
   props, HTML, JavaScript bundles, browser storage and error bodies.
6. The server-only Core client sends only `AegisSession` after login and removes the
   local Persona headers from the authenticated profile.
7. A rejected OIDC discovery promise is evicted so a transient provider outage can
   recover on the next bounded request; successful discovery remains cached.
8. Failed Core session revocation returns a sanitized failure and retains the
   browser cookie so the user cannot be told that an active server session ended.

## Component Tests

1. `POST /v1/auth/sessions` re-verifies a signed access token, requires active
   membership, creates one session and returns the raw opaque token once.
2. Session authentication reconstructs the same issuer/subject Principal and
   re-evaluates database roles for each request.
3. Role revocation takes effect on the next request without issuing a new session.
4. Developer, Reviewer, Admin, missing membership and cross-tenant identities see
   only authorized session/Run DTOs.
5. Developer self-approval remains denied; Reviewer approval remains bound to the
   exact Run action digest.
6. Logout revokes the row and emits sanitized audit evidence; repeated logout is
   safe.
7. Database errors during create/revoke produce no false success or partial cookie.

## Integration Tests

1. Apply the additive session migration to clean and populated PostgreSQL, validate
   digest uniqueness, expiry/revocation constraints and downgrade/upgrade behavior.
2. Start local Keycloak, Core and Console from the authenticated Compose profile;
   validate discovery, authorization redirect, callback and `/v1/session`.
3. Authenticate deterministic Developer and Reviewer users provisioned from ignored
   local environment inputs; verify PostgreSQL, not IdP groups, owns roles.
4. Run one PRD through clarification and Reviewer approval using two browser
   contexts and reach the existing dry-run Draft PR candidate.
5. Restart Console and Core while preserving PostgreSQL; the opaque session remains
   valid until expiry/revocation.
6. Stop Keycloak after login: existing Core session behavior is explicit, new login
   fails boundedly, and logout still revokes locally.
7. Render the merged OIDC Compose profile and verify the Worker receives the
   Ollama, Sandbox Broker, workspace, Temporal and dry-run DeliveryPack contract.

## Negative / Security Tests

1. Forged/expired/wrong-audience/wrong-issuer/wrong-algorithm JWT and unknown JWKS
   key.
2. State, nonce and PKCE mismatch; authorization-code replay; missing transaction;
   callback mix-up; untrusted discovery/redirect/logout host.
3. Session fixation, token replay after revoke, digest collision fixture, oversized
   cookie/header and concurrent revoke/use.
4. Missing/wrong Origin, cross-site fetch, missing/wrong CSRF value, non-JSON
   mutation and login/logout CSRF.
5. Cross-tenant read/write, role escalation, IdP group injection, inactive
   membership and self-approval.
6. Provider access/refresh/ID token, client Secret, code, nonce, PKCE verifier,
   session token and cookie signature scans across logs, traces, responses, bundles
   and committed files.
7. Production cannot enable local Persona auth, local HTTP OIDC or OIDC subject
   bootstrap.

## Fault Injection

- OIDC discovery unavailable, slow, oversized or malformed.
- Token endpoint timeout, 4xx/5xx, malformed response and incorrect content type.
- JWKS key rotation and unavailable refresh.
- PostgreSQL unavailable before and after access-token verification.
- Console restart between login redirect and callback.
- Core restart before session use and during logout.
- Clock skew around token/session expiry.

## Fixtures

- Deterministic RSA/EC test keys and bounded OIDC discovery/JWKS/token responses.
- Synthetic Developer, Reviewer, Admin and no-membership subjects.
- Local Keycloak realm/client template without credentials.
- Ignored `.env.auth-local` values for local users, client Secret and transaction
  encryption key; examples contain placeholders only.
- Existing local MVP PRD and controlled Sandbox workspace.
- Existing `KinguYume-G/AegisFlow-Gate1B-Fixture` is not written by AF-R09.

## Expected Results

- No unauthenticated or unauthorized browser request reaches a tenant operation.
- Browser JavaScript/storage/HTML contains no provider or local Persona token.
- Database stores no raw opaque session token and no provider token.
- Provider claims identify a Principal; PostgreSQL membership and fixed RBAC alone
  authorize AegisFlow operations.
- Role revocation and session revocation take effect immediately.
- One authenticated local Run can complete through separate Human Approval without
  weakening any existing Policy or dry-run boundary.
- Complete Python coverage remains at or above 90%; frontend test/lint/type/build
  and required browser suites pass.

## Commands

```powershell
uv run pytest -q -p no:cacheprovider
uv run pytest -q -m database
docker compose --env-file .env.auth-local -f compose.yaml -f compose.auth-local.yaml config
docker compose --env-file .env.auth-local -f compose.yaml -f compose.auth-local.yaml up -d --build
npm.cmd --prefix web/console run test:run
npm.cmd --prefix web/console run lint
npm.cmd --prefix web/console run typecheck
npm.cmd --prefix web/console run build
npm.cmd --prefix web/console run test:e2e
```

Run the repository credential-signature scan, local Markdown target validation,
Compose static guards and `git diff --check` before PR publication.

## Evidence

Record exact commands, pass/fail/skip counts, coverage, Alembic head, container
health, Keycloak version/image digest, sanitized issuer/audience, login/session/logout
outcomes, Developer/Reviewer subject references, one completed Run ID, approval
receipt, dry-run candidate reference and credential-scan result. Never record any
password, client Secret, token, cookie, code, nonce or PKCE value.

## Limitations

- Local Keycloak proves protocol and authorization integration, not hosted IdP
  availability or production TLS.
- AF-R09 intentionally uses short-lived sessions and reauthentication rather than
  storing provider refresh tokens. Provider SSO may make reauthentication silent,
  but that is provider behavior rather than an AegisFlow availability guarantee.
- Real GitHub and hosted model writes remain separately protected under AF-R12.
- Production deployment and operational certification remain AF-R11–AF-R16 work.
