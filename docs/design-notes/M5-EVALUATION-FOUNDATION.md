# M5 Evaluation Foundation — AF-501–AF-505

## Objective

Implement the accepted ADR-0010 mixed-dataset foundation and a controlled single-agent comparison without changing runtime ownership, model routing, or DeliveryPack behavior.

## Scope

- Immutable Pydantic contracts for dataset manifests, cases, expected outcomes, runs, and metric observations.
- Canonical JSON hashing and strict JSON/JSONL loaders with duplicate, provenance, and secret checks.
- A 12-case metadata-only SWE-bench Verified subset pinned to an immutable public dataset revision.
- A 15-case deterministic security set covering prompt override, credential/token exfiltration, SQL injection, and tenant/authority escalation.
- A single-agent baseline runner that requires the same model, token/cost budget, timeout, and case input used by the full-system subject.

## Boundaries

- Evaluation owns datasets, runners, and comparison evidence only; it does not own workflow state or external side effects.
- Dataset text is untrusted input and cannot grant tools or authorization.
- No real credentials, private issue content, gold patch bodies, repository clones, provider calls, or benchmark execution are included.
- Historical XueMai/SynTour completion remains blocked until 5–10 real sanitized source records are provided. The importer must reject synthetic records mislabeled as historical evidence.

## External Data Decision

`princeton-nlp/SWE-bench_Verified` is pinned at revision `c104f840cc67f8b6eec6f759ebc8b2693d585d4a`. The local subset stores only public identifiers, repository names, base commits, versions, difficulty, and row indexes. Dataset-level license metadata is not declared by the source card; downstream use must also respect each referenced repository's license.

## Security

- Secret-shaped non-placeholder content fails loading.
- Historical cases require source system, immutable source reference, sanitization statement, and ground-truth fix reference.
- Baseline tool access is supplied by a reviewed runner port, never by case text.
- Results distinguish unavailable measurements from zero.

## Completion

AF-501, AF-502, AF-503, and AF-505 can complete in this batch. AF-504 remains open until the required real sanitized historical cases exist.
