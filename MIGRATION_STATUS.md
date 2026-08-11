---
agent_id: CODEX
---

# GitHub 迁移状态

最后更新：2026-08-12

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

## GPT 二次审查修复与 semantic coverage audit

本审计重新逐项对照旧 AI电影系统.md（38855 bytes，1265 lines）。压缩只允许删除重复、过时路径和不适合公开仓库的原始资料描述；下列仍有效能力均有唯一当前承载位置。

| 旧 canonical 能力 | 分类 | 当前承载或原因 |
|---|---|---|
| 导演执行流程、场景诊断、动作线优先 | migrated | AI电影系统，第2、3、5节 |
| 镜头卡、导演母版和执行提示模板 | migrated | AI电影系统，第2.1与6.4节 |
| DirectorSkills 症状路由与按需组合 | moved_to_other_canonical | 10_运行时/director_route_index.yaml 与 read_sets.yaml；系统第1.1节保留 DTRM 接口 |
| 摄影机合同与 six degrees of freedom | migrated | AI电影系统，第6.3–6.4节 |
| 顶视、正交及特殊机位 | migrated | AI电影系统，第6.4节 |
| YAML、白模、深度图与空间几何 | migrated | AI电影系统，第6.1与6.4节；地图是拓扑 SSOT |
| Seedream 职责 | migrated | AI电影系统，第6.2节 |
| Seedance 职责 | migrated | AI电影系统，第6.2节 |
| 身份、几何、动作、摄影机、风格、声音六通道 | migrated | AI电影系统，第6.1节 |
| 首尾帧连续性 | migrated | AI电影系统，第6.2与6.4节 |
| 视频延长与定点视频编辑 | migrated | AI电影系统，第6.2与6.4节 |
| 镜头时长自动分配与按需时间码 | migrated | AI电影系统，第6.2节；项目记忆 AIP-001 |
| AI 视频失败诊断矩阵 | migrated | AI电影系统，第6.3节 |
| 人物变脸修复 | migrated | AI电影系统，第6.3节 |
| 场景搬家修复 | migrated | AI电影系统，第6.3节 |
| 动作绑定错误修复 | migrated | AI电影系统，第6.3节 |
| 非破坏式图像工作流 | migrated | AI电影系统，第6.3节 |
| 脏图重建 | migrated | AI电影系统，第6.3节 |
| 资产自动调用 | moved_to_other_canonical | 视觉资产登记库与 write_routes；系统第6.1、6.4节保留接口 |
| 连续性约束 | moved_to_other_canonical | 07_连续性与生产状态 canonical；系统第4、6.4节读取并执行 |
| 声音、剪辑、表演与调度 | migrated | AI电影系统，第5节 |
| 质量验收与生成前单测 | migrated | AI电影系统，第6.3节 |
| 模型自主权 LOCKED / GUIDED / FREE | migrated | AI电影系统，第6.2节 |
| 三层编译、单一主导变化律、风格冲突检查和证据边界 | migrated | AI电影系统，第2、6、7节 |
| 官方 MHTML/PDF 原文、游戏母本与媒体二进制 | deprecated_with_reason | public GitHub 只保留项目自有方法和来源边界；原始资料继续在 Library / 证据层 |
| 旧外部记忆路径、版本基线和补丁链 | deprecated_with_reason | PROJECT_INDEX GitHub-first 路由及固定文件名已取代旧路径和版本文件 |

本轮已合并 origin/main 的 `ab9f88df9a39c38d1a5a11685f6ba33fab20a38a`，保留唯一的 U-ASSET-RETRIEVAL-001，且 status: open。它是资产像素检索接口缺口，不改变 Asset Registry 的 Source Authority。最终树重新通过 Source Authority、地图、资产、剧本、CALC 与新会话恢复回归。

## 公开仓库边界

迁移文件只包含项目自有导演方法、项目事实、改编索引、场景摘要、Asset ID、File ID 和来源边界。未迁入游戏母本全文、受版权 PDF 全文、媒体二进制、凭证、token、账号或私人数据。

## 验收

11_验收/validate_canonical_cutover.ps1 是本次确定性验收脚本，检查 canonical 路径、Source Authority、legacy 拒绝、地图、资产、剧本、CALC、写回路由和迁移 Unknown 关闭状态。Golden cases 位于 11_验收/director_regression_cases.yaml。
