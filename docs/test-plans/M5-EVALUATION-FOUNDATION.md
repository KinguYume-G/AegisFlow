# M5 Evaluation Foundation Test Plan — AF-501–AF-505

- Canonical hashes are stable across mapping order and change when semantic content changes.
- Contracts reject invalid versions, duplicate IDs, malformed commits/hashes, unknown fields, inconsistent measurements, and mutable inputs.
- Loaders enforce declared count, dataset identity, unique cases, provenance, and no real-secret patterns.
- SWE-bench selection contains exactly 12 unique Python cases across at least 10 repositories and is pinned to the approved revision.
- Security selection contains 15–20 unique truth cases and covers SQL injection, secret, token, authorization/tenant escalation, and prompt injection.
- Historical imports reject missing sanitization, source, ground truth, or synthetic provenance.
- Baseline runner passes identical controls and case input to the injected agent, enforces budget/time bounds, rejects mismatched results, and has no implicit provider or tool implementation.
- Existing module-boundary, full test, coverage, manifest, and secret checks remain green.
