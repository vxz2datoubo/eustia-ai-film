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

## 迁移批次

| 文件 | 状态 | 当前有效来源 | 说明 |
|---|---|---|---|
| PROJECT_INDEX.yaml | verified | GitHub | Source Authority Registry 已建立 |
| 项目入口.md | migrating | File Library | 本轮迁移 |
| 反馈反推与系统反哺引擎.md | migrating | File Library | 本轮迁移 |
| 角色与表演设定库.md | migrating | File Library | 本轮迁移 |
| 连续性与当前生产状态.md | migrating | File Library | 本轮迁移 |
| 官方资料与证据索引.md | migrating | File Library | 本轮迁移 |
| AI电影系统.md | pending_full_export | File Library | 文件较长，必须完整迁移后再切换 |
| AI电影项目记忆.md | pending_full_export | File Library | 文件较长，必须完整迁移后再切换 |
| 当前改编剧本.md | pending_full_export | File Library | 必须拿到完整当前稿，不依据摘要重建 |
| 场景与空间设定库/场景资产库 | pending_reconcile | File Library | 需要裁决当前最终文件职责 |
| 视觉资产登记 | pending_reconcile | File Library + CURRENT_v5 | 先对账 CURRENT_v5 后再迁移 |
| 00_项目地图文件 | pending_full_export | File Library | 保留空间唯一主档职责 |

## 完成定义

单文件只有满足以下全部条件才标 `verified`：

1. 找到旧体系当前 canonical；
2. 完整读取；
3. 明确旧文件中的 legacy 引用；
4. 写入固定 GitHub 路径；
5. 回读 GitHub；
6. 核对关键头信息、核心段落、记录数量或结构；
7. PROJECT_INDEX 的 effective_source 改为 GitHub。
