# GitHub Setup Procedure

该目录提供 Labels、Milestones 和 75 个规划 Issue 的权威导入数据。目标仓库已确认为 `KinguYume-G/AegisFlow`，GitHub 写权限已验证，56 个权威 Labels、7 个 Milestones 和 75 个 canonical Issues 已完成导入并逐项核验。

## 已完成的外部输入

- `GITHUB_REPOSITORY=KinguYume-G/AegisFlow`
- 已确认使用现有私有仓库
- 已确认 Labels、Milestones、Issues 写权限

## 推荐顺序

1. [x] 创建或确认私有仓库；
2. [x] 上传 Phase 0 工程文档；
3. [x] 创建 7 个 Milestones；
4. [x] 创建 56 个权威 Labels；
5. [x] 从 CSV 创建 75 个 canonical Issues；
6. [ ] 通过本次 Branch → PR → Human Review → Human Merge 流程完成人工 M0 Review；
7. [ ] 由人工处理 M0 Issues 与 Phase 0 Exit；
8. [ ] 配置 main Branch Protection；
9. [ ] Gate 通过后再决定是否创建 `v0.0.0-docs` Tag；
10. [ ] Phase 0 Exit 后进入 AF-101 Design；AF-101 Ready 前不得开始业务实现。

## 重要

- CSV 是数据源，不是自动执行脚本；
- 不在没有明确仓库和权限时写入 GitHub；
- Issue 导入后，GitHub 状态是实时事实源；
- 规划 ID `AF-xxx` 保留在标题中。
- `817751a` 与 `82c91d7` 是项目所有者批准的一次性 Phase 0 bootstrap exception；不回滚、不重写历史、不补造历史 PR，也不构成未来先例。
- Phase 0 Exit 后所有改动必须遵循 One Issue → One Branch → One PR → Human Review → Human Merge。
