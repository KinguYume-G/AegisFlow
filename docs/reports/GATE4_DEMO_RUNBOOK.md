# Gate 4 Evidence Runbook / Gate 4 证据复现手册

Use protected GitHub Environments. Never paste credentials into commands, logs, Issues, or PRs. / 使用受保护的 GitHub Environment，禁止在命令、日志、Issue 或 PR 中粘贴凭据。

## Preconditions / 前置条件

- Run from protected `main`; record the full commit SHA.
- Required environments and secrets already exist for real GitHub, model, Langfuse, and Personal Workbench smokes.
- Video is optional; Actions logs, artifacts, trace/cost metadata, and this runbook are the formal evidence.

## Reproduce / 复现

1. Run **CI** and retain the Gate 3 JUnit/secret-scan and evaluation-regression artifacts.
2. Dispatch **Gate 1B real GitHub E2E**. Confirm the marked Draft PR is created, deduplicated, and cleaned up.
3. Dispatch **Gate 2 fault injection**. Download JSONL and verify 20/20 completion, zero duplicate effects, and zero lost signals.
4. Dispatch **Model gateway smoke**. Confirm the redacted route chain, token status, and cost source. A primary success is not a fallback demonstration.
5. Dispatch **Langfuse smoke**. Record the redacted trace ID. If the read path times out, retry once and record both attempts.
6. Dispatch **M5 control-plane load test** and retain Locust CSV/HTML plus resource usage.
7. Dispatch **M5 k3s demo smoke** and retain Helm status/history, pod state, events, and logs.
8. Dispatch **Personal Workbench smoke** and retain the sanitized artifact; never archive private source bodies.
9. Review [`GATE4_FINAL_ACCEPTANCE.md`](GATE4_FINAL_ACCEPTANCE.md). A Human Reviewer decides final acceptance.

## Four required demonstrations / 四项必做演示

| Demo | Automated evidence route | Required statement |
|---|---|---|
| Normal closure | CI contracts + Gate 1B + Model + Langfuse | Component-composed evidence; not a single live six-Agent run |
| Worker recovery | Gate 2 JSONL | Publish measured recovery and duplicate-effect counts |
| Model fallback | deterministic CI + provider smoke | Do not claim live fallback unless primary is deliberately failed in a protected run |
| Injection rejection | Gate 3 JUnit/audit evidence | Deterministic security evidence; no unsafe live attack required |
| Prompt regression (promoted) | evaluation decision artifact | Label as `deterministic_gate_fixture` unless provider-measured |

## Stop conditions / 停止条件

Stop on a secret leak, mutable or unknown commit, missing artifact, non-zero duplicate effect, unresolved smoke failure, or unsupported claim. Do not bypass protection or silently rerun until green.
