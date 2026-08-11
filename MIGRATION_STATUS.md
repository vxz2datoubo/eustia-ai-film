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
| 当前改编剧本.md | verified | GitHub | 已读取旧 canonical 全文，并合并 8/11 凯姆攀爬 + 菲奥奈巡查/插队事件 |
| 角色与表演设定库.md | verified | GitHub | 已绑定最新 Asset ID，并合并菲奥奈当前职责/CALC行为状态 |
| 00_项目地图文件.md | verified | GitHub | 已纠正钟楼/关所关系、主街南北轴与桥东西轴 |
| 视觉资产登记库.md | verified | GitHub | 已从 CURRENT_v5 对账迁移视觉资产，并正式登记钟楼左右侧视图 |
| 连续性与当前生产状态.md | verified | GitHub | 已合并菲奥奈巡查+插队事件，并绑定 GitHub 资产库 |
| 反馈反推与系统反哺引擎.md | verified | GitHub | 已加入 EDCM、成熟度、Final-Delta 和正式写回事务 |
| 官方资料与证据索引.md | verified | GitHub | 已迁移证据等级并记录 CALC 研究来源边界 |
| source_authority.yaml | verified | GitHub | 旧主档拒绝规则 |
| read_sets.yaml | verified | GitHub | 每任务最小必要读取；空间任务强制读取地图 |
| write_routes.yaml | verified | GitHub | 唯一写回路由与回读验证 |
| maturity_model.yaml | verified | GitHub | candidate → stable 生命周期 |
| director_route_index.yaml | verified | GitHub | 症状到技能/扫描路由 |
| director_regression_cases.yaml | verified | GitHub | 首批 Golden Cases |
| UNKNOWN_REGISTRY.yaml | verified | GitHub | 未知项与安全默认 |

## 本轮资产迁移结果

- `SCN-CHURCH-BELLTOWER-LEFT-001`：**active / 左视职责默认**，File ID `file_000000005ef481fd986ebe6946d669f5`。
- `SCN-CHURCH-BELLTOWER-RIGHT-001`：**active / 右视职责默认**，File ID `file_00000000d40881fdbf84fc376df37d00`。
- 钟楼正面继续由 `SCN-CHURCH-BELLTOWER-SOUTH-001` 承担，不被左右视图覆盖。
- File Library 的 `秽翼AI电影资产总表_CURRENT_v5.xlsx` 保留为迁移前快照/对账证据；后续视觉资产状态与默认指针写 GitHub `视觉资产登记库.md`。

## 本轮空间迁移结果

- 主街锁定为南北向。
- 高架石桥锁定为东西向，桥在上、主街在下。
- 北侧链：蔷薇酒馆 / 绯灯街。
- 南侧链：市集 / 布道施粥广场 → 教堂钟楼 → 钟楼后方关所底层入口。
- 关所内部通过长距离四方回旋楼梯向上到中层。
- 钟楼不再与关所合并；旧“通天楼”只作兼容旧称，不再默认解释为另一栋独立上层通道建筑。

## 尚未切换

| 文件 | 状态 | 当前有效来源 | 原因 |
|---|---|---|---|
| AI电影系统.md | pending_full_export | File Library | 文件约 41.5KB；当前接口读取会截断，不能从摘要重建后冒充完整迁移 |
| AI电影项目记忆.md | pending_full_export | File Library | 文件较长；必须完整迁移后切换 |
| 场景与空间设定库.md | pending_reconcile | File Library | 地图权威已切 GitHub；仍需迁移各场景节点材质/功能/资产关系，避免和地图重复 |

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

导演任务现在把 GitHub 作为**第一入口、路由权威、当前改编剧本权威、角色权威、空间地图权威、视觉资产文字权威、连续性权威和学习权威**。目前只剩 AI电影系统、AI电影项目记忆和局部场景设定库仍按 `PROJECT_INDEX.yaml` 从 File Library 读取，直到完整验证迁移完成。
