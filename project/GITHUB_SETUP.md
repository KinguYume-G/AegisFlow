# GitHub Setup Procedure

该目录提供 Labels、Milestones 和 75 个规划 Issue 的导入数据。当前没有仓库 URL，因此未执行任何 GitHub 写操作。

## 需要项目所有者提供

- `GITHUB_REPOSITORY=<OWNER/REPO>`
- 确认使用现有仓库或新仓库
- 允许创建 Labels、Milestones、Issues 和 Branch Protection 的权限

## 推荐顺序

1. 创建或确认私有/公开仓库；
2. 上传本工程文档；
3. 创建 Milestones；
4. 创建 Labels；
5. 从 CSV 创建 Issues；
6. 把 M0 Issues 标记为完成；
7. 只把下一个满足依赖的 Issue 改成 `status:ready`；
8. 配置 main Branch Protection；
9. 打 `v0.0.0-docs` Tag；
10. 开始 AF-101。

## 重要

- CSV 是数据源，不是自动执行脚本；
- 不在没有明确仓库和权限时写入 GitHub；
- Issue 导入后，GitHub 状态是实时事实源；
- 规划 ID `AF-xxx` 保留在标题中。
