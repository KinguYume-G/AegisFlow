# 13 — Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---:|---:|---|
| R-001 | Scope creep | High | High | Gate freeze、ADR |
| R-002 | Temporal/LangGraph 双重状态 | Medium | Critical | State Ownership |
| R-003 | 重复 GitHub 副作用 | High | Critical | Ledger + Marker |
| R-004 | Prompt Injection 越权 | High | Critical | Policy + Scope + Approval |
| R-005 | Sandbox escape | Low | Critical | Isolation and negative tests |
| R-006 | Cross-tenant leak | Medium | Critical | tenant filter and tests |
| R-007 | Secret leakage | Medium | Critical | references and redaction |
| R-008 | Evaluation overclaim | High | High | denominator and fixed environment |
| R-009 | Too much documentation | Medium | Medium | 20% cap |
| R-010 | Too many dependencies | Medium | High | modular monolith |
| R-011 | GPU unavailable | High | Low | vLLM optional |
| R-012 | GitHub API limit | Medium | Medium | Retry-After and budget |
| R-013 | Model outage | High | High | fallback and human pause |
| R-014 | Flaky evaluation | Medium | High | deterministic metrics |
| R-015 | AI loses context | High | High | AGENTS and Handoff |
| R-016 | Unauthorized AI merge | Medium | High | branch protection |
| R-017 | Personal data in demo | Medium | High | sanitized fixtures, tenant separation, redacted JSONL, protected read-only private-input smoke |
| R-018 | Gate target missed | Medium | High | stop-loss and freeze |

Critical 风险未关闭时不得通过 Gate。
