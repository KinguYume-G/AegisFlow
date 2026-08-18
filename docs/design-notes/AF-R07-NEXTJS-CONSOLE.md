# AF-R07 — Governed Next.js Local MVP Console

Status: Approved for implementation by the Project Owner on 2026-08-17.

## Problem

The backend can complete the local governed delivery loop, but operators currently
need raw HTTP calls to create a Run, answer clarification questions, inspect
evidence, make a separate approval decision, and verify the final result. This is
not a usable product demonstration and hides the control-plane value.

## Objective

Add one production-shaped Next.js 16.3.1 console (the npm security-audit fix
available on 2026-08-17) that makes the existing backend
truth visible and lets the two local actors complete the same workflow safely:

```text
Developer Console :3000                 Reviewer Console :3001
        | create / clarify / read               | review / decide / read
        +--------------------+------------------+
                             |
                    server-only BFF client
                             |
                    FastAPI tenant Run API
```

The two consoles use the same image and source tree but receive distinct server-side
persona/token configuration. Browser JavaScript never receives either token.

## Non-goals

- Workflow Builder, arbitrary agent creation, chat UI, real GitHub mutation, merge,
  deployment, OIDC replacement, or production authorization design.
- Copying Paperclip or OpenHands branding/code. They are interaction references only.
- Client-owned business state, client-side policy decisions, or browser-stored secrets.
- Adding a second business backend inside Next.js.

## References

- GitHub Issue #116 and dependencies #114–#115.
- `docs/DESIGN_BLUEPRINT.md`, `docs/02_ARCHITECTURE.md`, ADR-0014.
- `docs/19_SECURITY_STANDARD.md`, `docs/08_TEST_STRATEGY.md`.
- Next.js App Router, Server/Client Components, BFF and production guidance.
- Paperclip task/trace/cost/governance information hierarchy.
- OpenHands task/session and execution-event interaction patterns.

## Affected modules

- New `web/console` TypeScript application.
- Local Compose profile and frontend runtime image.
- Repository tests, documentation, environment template and manifest.
- No Core domain or state-ownership change.

## Information architecture

1. `/` — command-center overview, current profile, actor/role, status totals, recent
   Runs, pending attention, measured tokens/cost.
2. `/runs/new` — bounded PRD/Issue/Bug form with repository/base identity and an
   explicit statement that GitHub effects are dry-run.
3. `/runs/[runId]` — ten-step timeline plus request, pending Human action, exact
   approval preview/digest, artifacts, traces, evaluation and audit tabs.
4. `/api/*` — thin Route Handlers for browser polling and mutations. They validate
   same-origin state-changing requests and attach only the configured server persona.

## Rendering and data flow

- Server Components call FastAPI directly for initial session/list/detail data.
- One small Client Component polls the Run detail endpoint while status is active or
  waiting and refreshes the route when the representation changes.
- Client forms call same-origin Route Handlers. Route Handlers validate bounded JSON,
  generate a fresh idempotency key, and forward to FastAPI.
- FastAPI/PostgreSQL remain the only source of business truth. The BFF stores no Run
  state and Next.js caching is disabled for mutable control-plane reads.

## Consent and approval UX

- Every screen shows the active actor and capabilities.
- Developer console renders approvals read-only and links to the isolated Reviewer
  console; it never offers an approve button.
- Reviewer console presents purpose, repository/base scope, exact changed paths,
  digest, risk, effect mode and reversibility before decision controls.
- Reject is visually safe and available without a reason; approve requires an
  explicit acknowledgement bound to the displayed digest.
- Completion says “Draft PR candidate recorded (dry-run)”, never “GitHub PR created”.

## Security

- `server-only` guards protect the backend client and token resolver.
- Local tokens exist only as container/server environment variables and redacted
  diagnostics never echo them.
- No localStorage/sessionStorage/token cookie is used.
- Mutation handlers require JSON, same-origin/Fetch-Metadata checks, schema bounds,
  and no client-supplied tenant/persona override.
- Content is rendered as text; no arbitrary HTML, Markdown execution, or raw prompt is
  displayed. Digests and identifiers are line-wrapped.
- Security headers deny framing and broad browser capabilities.

## Failure behavior

- Backend unavailable: retain the application shell and render a retryable operational
  error without exception/secret detail.
- Invalid input or backend conflict: return a stable problem code and preserve form
  values.
- Poll failure: back off and show stale-state notice; never invent progress.
- Missing tenant/capability: fail closed with a role-specific empty state.
- Already-decided approval: refresh authoritative Run state rather than replaying it.

## Testing

See `docs/test-plans/AF-R07-NEXTJS-CONSOLE.md`. Tests cover server-only identity,
same-origin enforcement, contracts, status presentation, consent copy, accessibility,
responsive rendering, production build and a browser-driven backend integration.

## Rollback

Remove the two local console services and `web/console`. FastAPI remains independently
usable and no database migration or business-state rollback is required.
