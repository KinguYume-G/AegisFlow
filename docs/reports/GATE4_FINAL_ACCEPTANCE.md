# Gate 4 Final Acceptance / Gate 4 最终验收

Status: **Candidate — Human Review and Merge required / 候选状态，等待人工审查与合并**

Evidence commit: `af74b419cc73e8975beb9bedd4419db0a37e2793`

Evidence date: 2026-08-04

## Evidence ledger / 证据台账

| Gate | Immutable evidence | Measured result | Assessment |
|---|---|---|---|
| Main CI | [run 30878829835](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878829835) | CI passed; Gate 3 artifact `8880512436`; evaluation artifact `8880500442` | Pass |
| Gate 1B | [run 30879275468](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879275468) | real GitHub Draft PR test: 1 passed | Pass for external boundary |
| Gate 2 | [run 30879280701](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879280701), artifact `8880681687` | 20/20 completed; duplicates 0; lost signals 0; p50 2269.19 ms; p95 2972.42 ms; max 2976.35 ms | Pass |
| Gate 3 | [artifact 8880512436](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878829835/artifacts/8880512436) | 83 security tests passed; tracked credential signatures 0 | Pass |
| Evaluation | [artifact 8880500442](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878829835/artifacts/8880500442) | decision passed; scope=`deterministic_gate_fixture`; correctness regression 0%; cost/p95 within 10% fixture thresholds | Pass as gate validation, not production quality |
| Load | [run 30878614820](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878614820), artifact `8880424564` | 100-user profile; 1906 requests; 0 failures; 100.07 req/s; aggregate p95 140 ms | Pass in CI runner scope |
| k3s + Helm | [run 30878614801](https://github.com/KinguYume-G/AegisFlow/actions/runs/30878614801), artifact `8880460026` | Helm revision 3 deployed; eight workloads Ready/Running; upgrade/rollback smoke passed | Pass |
| Model provider | [run 30879285171](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879285171) | primary route succeeded; measured tokens; provider-reported cost provenance | Pass for primary smoke only |
| Langfuse | [run 30879289869](https://github.com/KinguYume-G/AegisFlow/actions/runs/30879289869) | attempt 1 read timeout; attempt 2 success; trace `8ae3d43445d62e5aa765510fcab15514` | Pass with transient warning |
| Personal Workbench | [run 30876654196](https://github.com/KinguYume-G/AegisFlow/actions/runs/30876654196) | protected read-only private-repository smoke succeeded | Pass |

## Artifact integrity / Artifact 完整性

| File | SHA-256 |
|---|---|
| Gate 2 `gate2-fault-evidence.jsonl` | `4714527149E5580C4F7B48B1870317D0E3C9DED0E8A9C141AB38D6CC805BC674` |
| Gate 3 `junit.xml` | `7096437D47D0E2190F491ED5819654046539C3C35CDBD1113ABED52D62716907` |
| Evaluation `regression-decision.json` | `4BD05B73FAEC12F8AD776A26BE55BBE5663624DED47DF530993BF2DE657E2B14` |
| Load `load-results_stats.csv` | `5E0DDA8F82A8178030C03ED7A04D037E35A3055BB804316323266CB010083B63` |

## Required package / 必备材料

- Product and bilingual entry point: [`../../README.md`](../../README.md)
- Architecture: [`../02_ARCHITECTURE.md`](../02_ARCHITECTURE.md)
- Accepted decisions: [`../adr/`](../adr/)
- Evaluation: [`../17_EVALUATION_PLAN.md`](../17_EVALUATION_PLAN.md) and the ledger above
- Reliability: [`GATE2_RELIABILITY_REPORT.md`](GATE2_RELIABILITY_REPORT.md)
- Load: artifact `8880424564` and the measured row above
- Threat model: [`../19_THREAT_MODEL.md`](../19_THREAT_MODEL.md)
- Repeatable demonstrations: [`GATE4_DEMO_RUNBOOK.md`](GATE4_DEMO_RUNBOOK.md)

## Limitations and warnings / 限制与警告

1. Normal closure is supported by composed automated evidence, not one live six-Agent execution recording.
2. Live primary-provider success was observed; live forced fallback was not. Fallback remains deterministically tested.
3. Injection blocking and prompt regression are deterministic CI evidence, not production traffic measurements.
4. Load results describe an ephemeral GitHub-hosted runner, not a capacity commitment or SLO.
5. Langfuse attempt 1 timed out and attempt 2 succeeded. This transient is retained, not erased.
6. Artifact retention follows GitHub policy; the SHA-256 values allow downloaded evidence to be rechecked.
7. GitHub emitted a Node.js 20 deprecation warning for the SHA-pinned `actions/upload-artifact` release while forcing Node.js 24. The run succeeded; dependency maintenance should address the warning separately without weakening pinning.

## Human decision / 人工结论

- [ ] Human Reviewer confirms AF-211 evidence is sufficient.
- [ ] Human Reviewer confirms AF-516 package completeness.
- [ ] Human Reviewer reproduces or reviews all AF-517 evidence and accepts the stated limitations.
- [ ] Human Reviewer merges the documentation PR.
- [ ] Project Owner marks AF-211, AF-516, and AF-517 verified/closed and declares M5 exit.

Until every box above is completed, AegisFlow is **Gate 4 Candidate**, not a completed or production-certified system.
