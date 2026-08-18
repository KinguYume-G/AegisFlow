# Design Note — AF-R09 Production OIDC Sessions and Console Authorization

Status: Approved scope in GitHub Issue #119; implementation design recorded before business code.

## Problem

The local MVP Console authenticates its two server instances with development-only
persona headers. That profile is intentionally rejected in production and cannot
provide a real browser login, logout, short-lived session, CSRF binding, or
production tenant membership experience. The Core already verifies provider-neutral
OIDC bearer tokens and applies database-backed tenant RBAC, but the Console has no
Authorization Code flow and no server-side session boundary.

PR #118 has merged and AF-R04–AF-R08 are complete. The next production-readiness
boundary is therefore identity and Console authorization, not another Agent or
workflow change.

## Objective

Deliver one provider-neutral production-shaped identity path:

```text
Browser
  -> Next.js BFF login route
  -> OIDC Authorization Code + PKCE S256 + state + nonce
  -> trusted IdP (local profile: Keycloak)
  -> Next.js callback validates the protocol response
  -> FastAPI verifies the short-lived access token through existing JWKS logic
  -> PostgreSQL creates a hashed opaque Console session
  -> browser receives only an HttpOnly opaque session cookie
  -> Next.js BFF forwards the opaque session to FastAPI
  -> FastAPI resolves Principal -> tenant membership -> fixed RBAC capability
  -> authorized DTO / mutation result
```

The browser must never receive a provider access token, refresh token, client
secret, local persona token, or database credential. UI visibility is advisory;
FastAPI and PostgreSQL remain the final authorization boundary.

## Non-Goals

- No password database or custom credential login.
- No trust in OIDC groups/roles as direct AegisFlow authorization.
- No UI-only route protection, general ABAC, new Agent role, or workflow change.
- No refresh-token persistence in AF-R09. A short-lived expired session requires a
  new Authorization Code flow; an existing IdP SSO session may make that redirect
  immediate.
- No production deployment, public DNS/TLS change, or real external tool write.
- No removal of the explicitly gated local-MVP persona profile used by regression
  and demo tests.

## Relevant Documents / ADRs

- `docs/DESIGN_BLUEPRINT.md`
- `docs/00_PROJECT_CHARTER.md`
- `docs/02_ARCHITECTURE.md`
- `docs/09_SECURITY_BASELINE.md`
- `docs/19_THREAT_MODEL.md`
- `docs/26_PRODUCTION_READINESS_PLAN.md`
- ADR-0001, ADR-0007 and ADR-0014
- GitHub Issue #119
- Next.js authentication and data-security guides:
  <https://nextjs.org/docs/app/guides/authentication> and
  <https://nextjs.org/docs/app/guides/data-security>
- Keycloak OIDC guide:
  <https://www.keycloak.org/securing-apps/oidc-layers>
- OAuth 2.0 Security Best Current Practice (RFC 9700):
  <https://www.rfc-editor.org/rfc/rfc9700>
- `openid-client` v6 documentation:
  <https://github.com/panva/openid-client>

## Affected Modules

- `web/console/src/lib/`: OIDC client, transient login envelope, server session,
  authorization-aware Core client and safe DTO boundary.
- `web/console/src/app/api/auth/`: login, callback, logout and session routes.
- `web/console/src/app/`: authenticated layout, login/error/session-expiry UX and
  role/capability-aware navigation.
- `src/aegisflow_core/control_plane/identity/`: opaque Console session verifier and
  integration with the existing OIDC verifier.
- `src/aegisflow_core/control_plane/domain/`: revocable hashed Console session fact.
- `src/aegisflow_core/control_plane/migrations/`: additive session schema.
- `src/aegisflow_core/control_plane/bootstrap.py`: development/test-only fixed OIDC
  subject membership bootstrap for the local Keycloak profile.
- `src/aegisflow_core/request_identity.py` and `run_router.py`: session
  authentication and bounded session create/revoke endpoints.
- `settings.py`, environment examples and local Compose overlay.
- Backend, frontend, database, Compose and Playwright tests.

### Dependency decision

The Console should use `openid-client` v6 for discovery, PKCE, state/nonce and
Authorization Code response validation instead of reimplementing OAuth/OIDC. It is
the only proposed new runtime package for AF-R09. Node WebCrypto provides the
short-lived encrypted transaction cookie; provider tokens are discarded after Core
creates the opaque session. The package must be locked and supply-chain checked.

## Proposed Flow

### 1. Configuration and discovery

Production requires one complete OIDC client configuration: trusted issuer,
metadata/discovery URL, client ID, client-secret environment reference, callback
URL, post-logout URL, approved algorithm and bounded timeouts. Configuration is
all-or-none and fail-closed.

HTTPS is mandatory in production. A separate explicit development/test switch may
allow HTTP only for an approved `*.localhost` Keycloak issuer. It cannot coexist
with production mode or broaden to arbitrary hosts. Callback and return URLs use
an exact allowlist; request input never selects the issuer, metadata endpoint or
client credentials.

### 2. Start login

`GET /api/auth/login` validates a relative post-login path, then generates fresh
cryptographic `state`, `nonce` and PKCE verifier/challenge values. A compact
transaction envelope is AES-GCM encrypted with a server-only key reference and set
in a short-lived HttpOnly, SameSite=Lax cookie. Production cookies use Secure and
the `__Host-` prefix. The route redirects only to the authorization endpoint from
trusted discovery metadata.

The transaction cookie contains no provider token or user data and expires within
ten minutes. A new login replaces the previous transaction.

### 3. Callback and session creation

`GET /api/auth/callback` consumes the authorization response once. `openid-client`
checks the exact callback URL, PKCE verifier, state, nonce, issuer, audience,
signature and required ID-token claims. Error descriptions from the provider are
not returned to the user or logs.

The BFF sends the resulting short-lived access token once to
`POST /v1/auth/sessions`. FastAPI re-verifies it using the existing `OidcVerifier`,
looks up the issuer/subject membership, and rejects users with no active tenant
membership. OIDC group/role claims do not create roles and never override the
database capability matrix.

Core generates a high-entropy opaque session token, stores only its SHA-256 digest,
and binds the row to issuer, subject, creation/expiry timestamps and a revocation
state. The expiry cannot exceed the verified access-token expiry or the configured
maximum session lifetime. The raw token is returned once to the BFF and set as the
only long-lived HttpOnly browser cookie. The transaction and any provider token
material are then cleared from the BFF process.

### 4. Authenticated BFF request

Every server component and Route Handler calls one `server-only` Data Access Layer.
It reads the opaque cookie and sends `Authorization: AegisSession <token>` to Core.
Core hashes the token, locks/loads the active session, verifies expiry/revocation,
builds the existing `Principal`, and performs tenant membership plus fixed RBAC
authorization for the requested operation.

Core returns only existing bounded session/Run DTOs. The Console derives navigation
and approval presentation from returned capabilities, but hiding a control is
never treated as authorization. The Reviewer decision endpoint remains protected
by Core capability checks and the separate-human rule.

### 5. CSRF and mutations

All state-changing BFF routes retain exact Origin, host, JSON content type and
`Sec-Fetch-Site` checks. AF-R09 additionally binds a random CSRF value to the
server session. The safe session DTO may expose that non-credential value to the
same-origin UI; mutation requests must return it in `X-AegisFlow-CSRF`. Core does
not accept browser cookies directly and therefore remains outside ambient-cookie
CSRF scope.

Login CSRF is blocked by the state/nonce/PKCE transaction. Logout is POST-only,
same-origin, CSRF-bound and idempotent.

### 6. Logout and expiry

Logout revokes the PostgreSQL session before any provider redirect and clears the
browser cookie even if the provider is unavailable. If trusted discovery exposes
an RP-initiated logout endpoint, the BFF redirects to that exact endpoint with an
allowlisted post-logout URI. No arbitrary return URL is accepted.

Expired, revoked, missing or malformed sessions return stable 401 codes. Pages
redirect to `/login?reason=session_expired`; mutations return bounded JSON and do
not silently retry the original side effect after reauthentication.

### 7. Local Keycloak profile

A new development/test-only Compose overlay starts a digest-pinned Keycloak image
on a loopback-bound port. A versioned realm/client template contains no reusable
password or client Secret. Bootstrap reads local values from an ignored environment
file and creates deterministic Developer, Reviewer and Admin subject identifiers.

Core may bootstrap those exact subjects into one local tenant only when the local
OIDC bootstrap switch is enabled in development/test. Production rejects that
switch. Role authority remains PostgreSQL, not Keycloak group claims.

The authenticated profile uses one Console: users sign in as distinct accounts or
browser sessions. The two-instance local Persona overlay remains available only for
the existing dry-run regression path.

## State Ownership

| State | Owner | Persistence / recovery |
|---|---|---|
| IdP login and SSO | OIDC provider | Provider-owned |
| Login state/nonce/PKCE | Next.js BFF | Short-lived encrypted HttpOnly cookie |
| Opaque Console session | AegisFlow Core | PostgreSQL, digest only, revocable |
| Tenant membership and roles | AegisFlow Core | PostgreSQL, authoritative |
| Capability decision | Fixed RBAC code + membership | Recomputed for every sensitive request |
| UI presentation | Next.js | Derived DTO only; never authoritative |
| Agent/workflow/business facts | Existing owners | Unchanged |

Redis is not involved in AF-R09 identity truth. Later caching may only accelerate
negative/expiry lookups and must tolerate total loss.

## External Side Effects

- Browser redirect to the configured authorization and logout endpoints.
- Server-to-server discovery and Authorization Code token exchange with the
  configured IdP.
- PostgreSQL session create/revoke/audit writes.

AF-R09 performs no GitHub, model, MCP, sandbox or deployment write.

## Idempotency

- Authorization codes and transaction cookies are single-use and short-lived.
- Session creation uses a unique random token digest and one verified callback.
- Repeating logout produces the same revoked/absent outcome.
- Session revocation is monotonic and never reactivates a row.
- Reauthentication creates a new token; it does not reuse or extend an old row.

## Failure Modes

- Missing/partial/unsafe configuration: startup or auth route fails closed.
- Discovery/JWKS/token endpoint unavailable: bounded timeout and sanitized login
  failure; no session is created.
- State/nonce/PKCE mismatch, replay or callback error: transaction is cleared and
  audited without provider details.
- Valid identity without membership: 403 and no Console session.
- Expired/revoked session: 401, cookie cleared, explicit login UX.
- Database unavailable during session creation: no cookie/session is reported.
- Provider logout unavailable: local session remains revoked; a sanitized warning
  is recorded.
- Clock skew: bounded configuration only; no disabled expiry validation.

### Deployment integrity boundary

The authenticated local Compose profile supplies the DeliveryPack Worker with its
complete development-only Ollama, governed Sandbox Broker, workspace and GitHub
dry-run contract. Outside that explicitly enabled profile, the worker retains the
original fail-closed `UnconfiguredGraphPort`: it can prove Temporal registration and
readiness for the accepted M5 install/upgrade/rollback gate, but rejects any Agent
task rather than constructing a partially configured execution adapter. AF-R11 owns
packaging the complete Kubernetes execution plane; AF-R09 does not claim it.

## Security Impact

High. The implementation must preserve least privilege, short-lived identity,
fixed RBAC, tenant isolation, separate-human approval, Secret-by-reference and
append-only audit. Session tokens and provider tokens are credential material and
must be covered by existing redaction/scanning patterns. Authentication failures
must not reveal token, claim, discovery response or upstream exception content.

## Test Plan

See `docs/test-plans/AF-R09-OIDC-CONSOLE-AUTH.md`. Tests are added or updated before
each implementation slice. No check may be skipped or threshold lowered to make the
Issue pass.

## Observability

Record sanitized authentication event type, outcome, issuer identifier, subject
hash/reference, session ID hash prefix, tenant, trace ID, latency and stable reason
code. Never record codes, tokens, cookies, nonce, PKCE verifier, client Secret,
provider response body or raw claims. Authentication telemetry is not an
authorization source.

## Documentation Updates

- Synchronize README, START_HERE, docs index, architecture, production-readiness
  status and the AF-R04–AF-R08 Handoff with merged PR #118.
- Update configuration reference, environment templates, Compose/runbook,
  traceability, repository layout, manifest and final AF-R09 Handoff.
- Record the one new locked dependency and the reason it is safer than custom
  protocol code.

## Rollback

Disable the authenticated Console profile, stop the local Keycloak overlay, revoke
active Console sessions, and restore the previous Console image. Downgrade the
additive session migration only after all rows are expired/revoked and the rollback
runbook authorizes removal. The existing local Persona profile remains default-off
and available for development regression; production never falls back to it.

## Open Questions

- Project Owner approval is required before adding and locking the proposed
  `openid-client` runtime dependency.
- Hosted production IdP, domain and TLS ownership remain AF-R16 external inputs;
  the AF-R09 implementation is provider-neutral and uses local Keycloak only as a
  reproducible test provider.
