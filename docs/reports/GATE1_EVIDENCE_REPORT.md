# Gate 1 Evidence Report / Gate 1 证据报告

Status: Candidate for Human Review / 等待人工验收

Evidence commit: `af74b419cc73e8975beb9bedd4419db0a37e2793` (`main`, 2026-08-04)

## Verified evidence / 已验证证据

| Capability / 能力 | Evidence / 证据 | Result / 结果 |
|---|---|---|
| Real GitHub Draft PR boundary | [Gate 1B run 30879275468](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879275468) | 1 selected real-GitHub test passed; Draft PR creation, deduplication, marker cleanup, migrations |
| Full deterministic Gate 1B contracts | [main CI run 30878829835](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878829835) | CI passed on the same evidence commit |
| Real model route and cost provenance | [Model Gateway run 30879285171](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879285171) | primary `deepseek-v4-flash` succeeded; `token_status=measured`; `cost_source=provider_reported` |
| Trace write/read | [Langfuse run 30879289869](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879289869) | attempt 1 timed out; attempt 2 succeeded with redacted trace ID `8ae3d43445d62e5aa765510fcab15514` |

## Honest boundary / 真实性边界

- The real GitHub workflow proves the external Draft PR boundary and idempotent cleanup. It does not execute the entire Intake → Reviewer graph in one live run.
- The provider smoke reports measured token/cost provenance but intentionally does not publish monetary or token values in repository documentation.
- The successful primary route does not prove live fallback. Fallback and circuit behavior remain deterministic test evidence.
- Video is optional by Project Owner decision. Immutable Actions logs, trace identity, test evidence, and this repeatable report are the formal AF-211 evidence.

## AF-211 assessment / AF-211 结论

The evidence package is complete for Human Review, with limitations explicitly retained. AF-211 must not be closed or marked verified until the documentation PR is human-reviewed and merged.
