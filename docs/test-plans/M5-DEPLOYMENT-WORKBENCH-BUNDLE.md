# M5 Deployment & Personal Workbench Bundle Test Plan — AF-512, AF-513, AF-515

**Status:** Approved v2 — paired with the approved Design Note.

## Required CI

Static and deterministic tests run inside the existing required `test` check:

- parse Chart metadata, values, and rendered templates;
- require `existingSecret` references and prohibit embedded Secret values;
- require digest-pinned third-party images and bounded app resources;
- require default-deny NetworkPolicy, DNS, and explicit dependency flows;
- require non-root/read-only/drop-all application security contexts;
- verify the k3d script is idempotent, bounded, and always supports teardown;
- run all four Personal Workbench fixtures twice and require byte-identical JSONL;
- validate JSONL schema, redaction, unique IDs, citations, and plan completion;
- prove only the six frozen DeliveryPack Agent names are referenced and that the CLI stops before external write execution.

## Hosted k3d and Helm Smoke

The `m5-k3s-demo-smoke` workflow runs on pull requests that change deployment assets and on manual dispatch:

1. install checksum-verified pinned k3d, Helm, and kubectl;
2. build the existing runtime image and create an ephemeral k3d cluster;
3. create the demo namespace and synthetic runtime-only Kubernetes Secret;
4. `helm upgrade --install` the Chart and wait for workloads;
5. verify Core `/health`, Core `/metrics`, Temporal Worker availability, and Prometheus target health;
6. upgrade one observable value and require Helm revision/config change;
7. roll back and require the original value and all health checks;
8. upload bounded status/log evidence;
9. delete the cluster under `if: always()`.

No retry loop may convert a failed assertion into success. Bounded readiness polling is allowed only until the declared timeout.

## Personal Workbench Fixture Matrix

| Scenario | Input | Required result |
|---|---|---|
| XueMai | sanitized local repository fixture | deterministic Plan with citations; fixture classification |
| SynTour | sanitized local repository fixture | deterministic Plan with citations; fixture classification |
| Omni-Assistant | sanitized local repository fixture | deterministic Plan with citations; fixture classification |
| Internship tracking | synthetic non-personal fixture | deterministic Plan with citations; no external write |

The CLI is invoked through `python -m scripts.personal_workbench.seed_requests`. Tests reject request bodies, source excerpts, email/phone patterns, credential signatures, or unexpected fields in output.

## Protected Real-Repository Smoke

The manual workflow uses GitHub Environment `personal-workbench-development`. It fails before checkout when any required variable or Secret is missing. A read-only GitHub App token checks out only the three configured repositories. The CLI reads the checked-out roots locally, emits redacted JSONL to the runner temporary directory, and uploads it as an artifact. The workflow never prints the token, source content, or model output.

This smoke is not part of pull-request Required CI because protected private-repository credentials are unavailable to untrusted PR contexts. Fixture tests are mandatory; the real smoke is required before AF-515 is marked verified.

## Negative and Failure Tests

- missing `existingSecret` or required key prevents rollout;
- mutable/unpinned third-party image fails static validation;
- absent NetworkPolicy or weakened app security context fails static validation;
- image-pull or readiness failure returns non-zero and still tears down the cluster;
- invalid scenario, missing fixture root, unsafe path, malformed JSONL, or output outside the approved path fails closed;
- missing protected GitHub Environment configuration fails without fallback to invented or public data.

## Local Commands

```bash
uv run --locked pytest tests/deploy tests/personal_workbench -q
helm lint deploy/helm/aegisflow
helm template aegisflow deploy/helm/aegisflow --set existingSecret=aegisflow-demo-config
bash scripts/k3d-demo.sh up
bash scripts/k3d-demo.sh verify
bash scripts/k3d-demo.sh upgrade-rollback
bash scripts/k3d-demo.sh down
```

## Acceptance Evidence

- Required CI URL and exact pytest/coverage result;
- k3d/Helm workflow URL and install/upgrade/rollback Job Summary;
- fixture JSONL hash and case count;
- protected real-smoke URL and artifact name, or an explicit external-configuration blocker;
- zero committed Secrets and zero architecture/Accepted ADR changes.
