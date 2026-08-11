---
agent_id: CODEX
---

# GitHub 迁移状态

最后更新：2026-08-11

## 当前系统状态

FULL_GITHUB_CUTOVER / VERIFIED

GitHub 是所有持续成长文字主档的唯一可修改 canonical truth。ChatGPT Library / 外部只读层继续承担图片、视频、音频、游戏母本、PDF、原始证据与历史快照；Memory 只作辅助索引。

## 本次最终切换

已按 SOURCE FOUND → FULL READ → MERGED → WRITTEN → FETCH VERIFY → VERIFIED 完成：

| 主档 | 旧 canonical 完整源 | GitHub 固定路径 | 最终 effective source |
|---|---|---|---|
| AI电影系统.md | F:\aidanao\eustia-migration-source\AI电影系统.md，38855 bytes，1265 lines | 01_AI电影系统/AI电影系统.md | github_verified |
| AI电影项目记忆.md | F:\aidanao\eustia-migration-source\AI电影项目记忆.md，18051 bytes，358 lines | 02_AI电影项目记忆/AI电影项目记忆.md | github_verified |
| 场景与空间设定库.md | F:\aidanao\eustia-migration-source\场景与空间设定库.md，3791 bytes，142 lines | 05_场景与空间/场景与空间设定库.md | github_verified |

场景资产库.md（6561 bytes，193 lines）已作为对账源完整读取。其有效局部场景与资产职责已合并；地图、动线和资产状态的旧表述不恢复为活动权威。

## 关键裁决

- 地图仍是拓扑 SSOT：主街南北向；高架石桥东西向；桥在上、主街在下；钟楼后方为关所入口；关所内部回旋楼梯向上至中层。
- 场景库仅负责局部时代、建筑、材质、装饰、光照、天气、道具、使用痕迹、局部功能、摄影基线、模型约束与关联 Asset ID。
- 当前剧本、角色、地图、资产、连续性和学习主档的 GitHub verified 内容优先于旧源，不被旧文静默覆盖。
- 钟楼正面、左视和右视资产仍保留各自职责；左右视图不覆盖正面资产。

## 迁移 Unknown

U-MIG-001、U-MIG-002、U-SCENE-001 均已 resolved。U-MIG-004 已在 UNKNOWN_REGISTRY 中真实缩小为 Library 外部历史证据边界，不参与 active canonical 裁决。

## 公开仓库边界

迁移文件只包含项目自有导演方法、项目事实、改编索引、场景摘要、Asset ID、File ID 和来源边界。未迁入游戏母本全文、受版权 PDF 全文、媒体二进制、凭证、token、账号或私人数据。

## 验收

11_验收/validate_canonical_cutover.ps1 是本次确定性验收脚本，检查 canonical 路径、Source Authority、legacy 拒绝、地图、资产、剧本、CALC、写回路由和迁移 Unknown 关闭状态。Golden cases 位于 11_验收/director_regression_cases.yaml。
