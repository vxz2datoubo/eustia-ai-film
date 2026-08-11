# GitHub 迁移状态

最后更新：2026-08-11

## 原则

- 不采用“大爆炸切换”。
- 每个 canonical 文件只有在“完整读取旧权威源 → 写入 GitHub → 回读核验”后，才把 effective_source 切到 GitHub。
- 尚未完成完整迁移的文件继续以 File Library 当前 canonical 为权威，避免静默丢内容。
- 旧 `AI电影化系统总纲_v*.md` 永久不得恢复为活动主档。

## POC

- GitHub 仓库连接：PASS
- ChatGPT create file：PASS
- ChatGPT fetch file：PASS
- ChatGPT update file：PASS
- ChatGPT fetch verify：PASS

## 已切换为 GitHub 权威

| 文件 | 状态 | 当前有效来源 | 说明 |
|---|---|---|---|
| PROJECT_INDEX.yaml | verified | GitHub | Source Authority Registry；每次导演前必读 |
| 项目入口.md | verified | GitHub | GitHub-first 架构和每轮 P0 已回读核验 |
| 反馈反推与系统反哺引擎.md | verified | GitHub | 已加入 EDCM、成熟度、Final-Delta 和正式写回事务 |
| 连续性与当前生产状态.md | verified | GitHub | 已合并 2026-08-11 菲奥奈巡查+插队事件最新锁定 |
| 官方资料与证据索引.md | verified | GitHub | 已迁移证据等级并记录 CALC 研究来源边界 |
| source_authority.yaml | verified | GitHub | 旧主档拒绝规则 |
| read_sets.yaml | verified | GitHub | 每任务最小必要读取集合 |
| write_routes.yaml | verified | GitHub | 唯一写回路由与回读验证 |
| maturity_model.yaml | verified | GitHub | candidate → stable 生命周期 |
| director_route_index.yaml | verified | GitHub | 症状到技能/扫描路由 |
| director_regression_cases.yaml | verified | GitHub | 首批 Golden Cases |
| UNKNOWN_REGISTRY.yaml | verified | GitHub | 未知项与安全默认 |

## 尚未切换

| 文件 | 状态 | 当前有效来源 | 原因 |
|---|---|---|---|
| AI电影系统.md | pending_full_export | File Library | 文件很长；必须拿到完整 canonical 再迁移，不能从截断摘要重建 |
| AI电影项目记忆.md | pending_full_export | File Library | 文件很长；必须完整迁移后切换 |
| 当前改编剧本.md | pending_full_export | File Library | 必须拿到完整当前稿，不依据摘要重建 |
| 角色与表演设定库.md | pending_reconcile | File Library | 文字主体可迁，但默认视觉指针需先和 CURRENT_v5 对账 |
| 场景与空间设定库 / 场景资产库 | pending_reconcile | File Library | 必须统一职责，避免新双权威 |
| 视觉资产登记 | pending_reconcile | File Library + CURRENT_v5 | 先对账 CURRENT_v5 后迁移；钟楼左右图待正式入库 |
| 00_项目地图文件.md | pending_full_export | File Library | 保留空间拓扑唯一主档职责，需完整迁移 |

## 完成定义

单文件只有满足以下全部条件才标 `verified`：

1. 找到旧体系当前 canonical；
2. 完整读取；
3. 明确旧文件中的 legacy 引用；
4. 写入固定 GitHub 路径；
5. 回读 GitHub；
6. 核对关键头信息、核心段落、记录数量或结构；
7. PROJECT_INDEX 的 effective_source 改为 GitHub。

## 当前系统状态

`PARTIAL_CUTOVER / SAFE_MIXED_SOURCE`

导演任务已经可以把 GitHub 作为**第一入口和路由权威**，但遇到尚未迁移的 AI电影系统、项目记忆、当前剧本、角色/场景/资产/地图时，必须根据 `PROJECT_INDEX.yaml` 继续读取 File Library 当前 canonical，直到对应文件验证迁移完成。
