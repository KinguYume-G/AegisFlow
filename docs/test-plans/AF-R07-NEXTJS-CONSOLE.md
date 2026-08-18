# AF-R07 — Governed Next.js Console Test Plan

Status: Approved for implementation by the Project Owner on 2026-08-17.

## Unit and contract tests

1. Runtime environment accepts only `developer` or `reviewer`, requires one matching
   server token, validates the Core URL, and never serializes token material.
2. FastAPI response parsers reject malformed session, Run list/detail, pending action,
   trace and evaluation shapes instead of rendering invented values.
3. Status, duration, token/cost, effect-mode and digest formatters are deterministic.
4. Mutation request schemas bound all text, repository/ref/SHA and answer fields.
5. Same-origin guard rejects cross-site, absent browser metadata, non-JSON and
   client-supplied persona/tenant attempts.

## Component tests

1. Application shell exposes product identity, active actor, local-only warning and
   keyboard-visible navigation.
2. Run cards and the ten-step timeline distinguish pending, running, waiting,
   completed and failed truthfully.
3. Clarification form renders every question with stable labels and submits exact
   keyed answers.
4. Developer view cannot render approval controls.
5. Reviewer view renders exact action scope/digest and requires acknowledgement before
   enabling approval; rejection remains the safer default.
6. Artifacts, traces, evaluation, cost and audit have loading/empty/error/value states.

## Integration tests

1. Mock FastAPI responses prove BFF authentication headers are server-generated and
   tokens are absent from returned JSON/HTML.
2. Create Run returns a canonical Run link and idempotent replay remains one Run.
3. Clarification and approval handlers forward only validated fields and preserve
   backend 403/409/503 problem codes.
4. `next build` succeeds with no live Core dependency at build time.

## Browser smoke

Against the local Compose profile:

1. Open Developer console, create a bounded PRD Run and observe progress.
2. If clarification is requested, submit answers and verify the same Run resumes.
3. Verify Developer cannot approve; open Reviewer console and inspect exact scope.
4. Reject path is covered with a fixture or isolated Run; approve the primary Run.
5. Observe ten completed steps, sandbox evidence, dry-run candidate, trace/token/cost,
   evaluation and audit without any real GitHub write.
6. Check 1440 px and 390 px layouts, keyboard focus, labels, contrast and no console
   errors.

## Quality gates

- `npm run lint`
- `npm run typecheck`
- `npm test -- --run`
- `npm run build`
- Playwright browser smoke against Compose
- Python suite remains at or above the verified `633 passed / 1 protected-environment skip` baseline and the 90% coverage gate.

## Evidence and limits

Record dependency versions, test totals, build routes, container health, screenshots
and one browser-created Run ID. This proves local functional integration, not
production identity, capacity, model quality or GitHub write readiness.

### Verified 2026-08-18

- Vitest: 17/17 passed, including failed-Run nullable usage evidence and HTML UnicodeSets pattern compatibility.
- ESLint, TypeScript `--noEmit` and Next.js production build passed.
- Fresh Playwright execution created Run `56e35374-fd5d-4229-b8fd-23e168ab4e4a`, reached 10/10, Sandbox PASS and separate Reviewer approval; it exposed and drove the HTML pattern fix. Final resume-based Playwright verification: 2 passed, 2 project-specific skips.
- Developer Console, Reviewer Console and Core were exercised through the Compose network; local tokens stayed server-side.
