# 15 — Release & Versioning

## 软件版本

MVP 前使用 `0.x.y`，Minor 对应 Gate，Patch 对应修复。

## Workflow / Prompt

- Immutable
- Run 固定版本
- 在途 Run 不受新版本影响
- 支持回滚和旧版本重放
- Prompt 关联内容 hash、模型和评测
- 未通过 Regression 不可 active

## Tool Version

记录 server_id、tool_name、schema_version、implementation_version、required_scope 和 risk_level。

## Release Evidence

Release Notes、Test、Security、Limitations、Evaluation、Demo 和 Rollback。

## Rollback

软件用 Helm；Workflow/Prompt/Model route 切 previous active；Tool 可禁用 registry entry。
