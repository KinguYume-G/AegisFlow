# Post-MVP Roadmap Bundle — AF-R01, AF-R02, AF-R03

Status: Approved by Project Owner on 2026-08-04.

## Objective

Deliver the three approved optional roadmap items without changing DeliveryPack,
the modular-monolith boundary, or any M1–M5 acceptance claim.

## Design

### AF-R01 — OpsPilot simulation

- Add `packs/opspilot` with immutable input/output contracts and one deterministic
  simulated CI failure classifier.
- Accept simulation data only. The result contains evidence, a bounded diagnosis,
  remediation steps, and `human_approval_required=true`.
- No network, persistence, command execution, new Agent name, or external effect.

### AF-R02 — optional vLLM route

- Extend `ModelRoute` with an optional `api_base` and extend `ModelGateway` with an
  optional third `local_fallback` route after the two existing routes.
- `MODEL_LOCAL_FALLBACK_ENABLED` defaults to false. Enabling is allowed only in
  development/test and requires a loopback HTTP base URL, model name, and API-key
  environment reference. The validation model is `openai/Qwen/Qwen3-0.6B`.
- LiteLLM receives `api_base` only for this route. Existing calls remain byte-for-
  byte equivalent at the adapter boundary. Route metrics use a bounded
  `local_fallback` label. Missing provider cost remains explicitly unavailable.
- A bounded smoke command records latency, token availability, and honest cost
  availability; it never invents self-hosting cost.
- Every model request carries a hard `max_output_tokens` bound (default 512; smoke
  16). The validated Windows/WSL image is `vllm/vllm-openai:v0.18.0` at manifest
  digest `sha256:c32358ebfc115d56ade2acfdbcd00df5b115417dbd6006547c88f07e2b39de06`.

### AF-R03 — GitHub Actions read-only MCP tool

- Add a bounded GitHub REST read for one workflow run plus jobs and artifact
  metadata. Pagination and item counts are bounded and preserve truncation.
- Add adapter `internal.github.actions.read`, scope `actions:read`, risk L1, using
  existing MCP policy/registry/audit/idempotency gates.
- Output excludes logs, artifact contents, credentials, and raw upstream errors.
- No dispatch, rerun, cancel, delete, download, or other write-capable method.

## Security and failure behavior

- Configuration is fail-closed; local model mode cannot be enabled in production.
- GitHub responses are size bounded and schema validated; authentication and
  upstream failures use existing redacted error categories.
- All MCP authorization, repository allowlisting, scope checks, and audit evidence
  occur before the adapter is invoked.

## Non-goals

No new service, database table, migration, UI, production deployment, model
training, generic MCP framework, GitHub write, or change to the six DeliveryPack
Agents.

## Rollback

Disable the local route (the default), unregister the MCP tool, and remove the
OpsPilot pack. No persisted business state or external effect needs migration.
