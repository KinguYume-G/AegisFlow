# 20 — Decision Log

## Accepted

| ADR | Decision |
|---|---|
| ADR-0001 | Modular Monolith |
| ADR-0002 | LangGraph / Temporal State Ownership |
| ADR-0003 | No Kafka |
| ADR-0004 | No Terraform |
| ADR-0005 | No SFT / LoRA |
| ADR-0006 | No CrewAI |
| ADR-0007 | RBAC + Contextual Policy |
| ADR-0008 | Langfuse / OTel Split |
| ADR-0009 | Phased Sandbox |
| ADR-0010 | Mixed Evaluation Dataset |
| ADR-0011 | No Workflow Builder |
| ADR-0012 | OpsPilot Roadmap Only |

## Repository Governance Decisions

### Phase 0 bootstrap exception

- 项目所有者确认提交 `817751a932f16c025bfd80be73d7a57c2783497b` 与 `82c91d73867bafb7873011275abe970fb2fcd908` 是 Phase 0 初始化期间直接推送 `main` 的一次性 bootstrap exception。
- 既有提交不回滚、不重写历史，也不补造历史 PR；该例外不构成任何未来工作的先例。
- 从 Phase 0 Exit 开始，所有改动必须执行 One Issue → One Branch → One PR → Human Review → Human Merge。
- AI 不得批准或 Merge 自己创建的 PR，也不得以该 bootstrap exception 为依据绕过未来治理流程。

## Open

Python/Node 精确版本、ORM/migration、OIDC provider、Policy representation、Object storage、Langfuse hosting、k3s environment 和 Model providers 必须通过 Issue/ADR 决定。
