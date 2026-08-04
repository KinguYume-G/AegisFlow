# M5 Deployment & Personal Workbench Bundle — AF-512, AF-513, AF-515

**Status:** Approved v2 — Project Owner directed Codex to apply the reviewed corrections and implement on 2026-08-04.

## Objective

Deliver one dependency-closed batch that proves the existing AegisFlow modular monolith can be installed, upgraded, and rolled back on an ephemeral k3s-compatible cluster and can run four thin Personal Workbench planning flows without adding an Agent, application service, state owner, or general-assistant direction.

The dependency order remains `AF-512 -> AF-513 -> AF-515`; AF-413 and AF-514 are already verified. The Project Owner's approved batch rule permits these three Issues in one branch and one PR while preserving separate acceptance evidence.

## Scope

### AF-512 and AF-513

- Use k3d as the ephemeral local/CI distribution of k3s.
- Build the existing Dockerfile `runtime` image once and import it into k3d.
- Install the final `deploy/helm/aegisflow` chart directly. Do not create disposable bare manifests that AF-513 immediately deletes.
- Deploy Core, Temporal Worker, PostgreSQL/pgvector, Redis, Temporal, Temporal PostgreSQL, and Prometheus.
- Run Alembic migrations before Core starts.
- Prove `/health`, `/metrics`, worker readiness, and Prometheus scraping.
- Prove Helm install, upgrade, and rollback against real Kubernetes objects.
- Use digest-pinned third-party images and pinned CI tooling.
- Keep credentials out of Chart values and templates. The Chart accepts one `existingSecret` reference; the ephemeral smoke creates synthetic runtime-only values.
- Apply least-privilege ServiceAccounts, disabled token automount, app-container security contexts, resource bounds, and default-deny NetworkPolicies with explicit DNS and service flows.

### AF-515

- Provide a thin CLI that invokes the existing in-process Gate 1A DeliveryPack graph and contracts.
- Do not claim a DeliveryPack REST submission API exists; the current Core exposes health, metrics, GitHub webhook, and read-only Run Graph only.
- Run four sanitized scenarios: XueMai, SynTour, Omni-Assistant, and internship tracking.
- Use deterministic repository fixtures in Required CI and emit canonical JSONL evidence.
- Support a protected, manually triggered real-repository smoke that checks out exactly the three approved private repositories with a read-only GitHub App. Secrets stay in the GitHub Environment and output is uploaded as a redacted artifact.
- Add no new Agent role, generic assistant behavior, external write tool, or business state.

## Non-Goals

- No EKS, GKE, AKS, Terraform, production HA, autoscaling, ingress controller, certificate manager, or persistent object storage.
- No Grafana dashboard (AF-510), Gate 4 report (AF-516/517), UI, or new REST write endpoint.
- No production credential embedded in Git, Helm values, Kubernetes manifests, logs, or artifacts.
- No claim that fixture evidence is a successful private-repository smoke.
- No k3s sandbox execution migration in this batch. ADR-0009's M5 Ephemeral Job backend requires a separately authorized AF-518 Issue and must complete before Gate 4; the Issue has not been created because changing the governed backlog requires explicit Project Owner authorization.

## Deployment Contract

`deploy/helm/aegisflow/values.yaml` contains operational defaults and image references only. Sensitive configuration is loaded from `.Values.existingSecret`, which must provide:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `DATABASE_URL`
- `LANGGRAPH_DATABASE_URL`

The demo script creates that Secret from explicitly synthetic values after cluster creation. Non-demo environments must supply an externally managed Secret.

The Chart does not create the sandbox broker. Core receives no `SANDBOX_BROKER_URL`; therefore the deployment cannot execute code and must not be presented as the final ADR-0009 sandbox architecture.

## Personal Workbench Evidence Contract

JSONL is the only canonical usage-log format. Each record contains schema version, scenario ID, fixture/real source classification, deterministic run and trace IDs, normalized request ID, completion status, plan risk, task count, citation count, and input receipt timestamp. It contains no request body, repository file content, Secret, token, email address, or personal identifier.

Fixture mode proves deterministic platform integration. Real-repository mode is a protected manual smoke and requires GitHub Environment `personal-workbench-development` with:

- variable `PERSONAL_WORKBENCH_APP_ID`;
- variable `PERSONAL_WORKBENCH_OWNER` and variables `XUEMAI_REPOSITORY`, `SYNTOUR_REPOSITORY`, `OMNI_ASSISTANT_REPOSITORY` containing repository names without an owner prefix;
- Secret `PERSONAL_WORKBENCH_APP_PRIVATE_KEY`;
- a GitHub App installed only on those repositories with read-only Contents and Metadata permissions.

## Security and Architecture

- PostgreSQL remains the business fact source; Temporal and LangGraph ownership do not change.
- Kubernetes and Helm release state are deployment state, not AegisFlow business state.
- All application images come from the existing Dockerfile; no new service boundary is introduced.
- NetworkPolicy is default-deny and allows only DNS and declared application dependency flows.
- The Personal Workbench cannot call write tools and does not reach Executor or Reviewer; it stops at a deterministic Plan.
- R-017 mitigation is updated with sanitized fixtures, redacted JSONL, and protected real-input handling. R-005 remains open until AF-518 replaces the Docker-socket sandbox backend.

## Rollback

- `scripts/k3d-demo.sh down` deletes the ephemeral cluster.
- Helm rollback restores the prior release revision and is verified before teardown.
- Reverting this batch removes only deployment assets, smoke tooling, and the thin CLI; it does not migrate or mutate production data.

## Stop Conditions

Stop on an architecture/ADR conflict, unpinned external binary or image, real Secret requirement in tracked files, private repository outside the approved allowlist, cross-tenant or personal-data leakage, inability to prove rollback, or any attempt to treat fixture evidence as a real private-repository result.

## Definition of Done

- AF-512: ephemeral k3d cluster is repeatable; Core, Worker, dependencies, and Prometheus become Ready; health and scrape checks pass; teardown is unconditional.
- AF-513: Chart lint/template security tests pass; install, upgrade, rollback, and post-rollback health all pass.
- AF-515: four deterministic sanitized scenarios generate schema-valid redacted JSONL; no new Agent roles or writes exist; protected real smoke is available and honestly reports missing configuration.
- Required CI, manifest, link, Secret, and architecture-boundary checks pass.
- One Draft PR links all three Issues and waits for Human Review/Human Merge.
