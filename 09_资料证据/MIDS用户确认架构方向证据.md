---
title: MIDS 用户确认架构方向证据
status: candidate_evidence
source_issue: 76
source_session_date: 2026-09-01
scope: user_confirmed_architecture_direction_only
---

# MIDS 用户确认架构方向证据

> 本文件保存本次 MIDS 发现会话中用户明确确认的架构方向及其 provenance。它不是新的导演、剧情、地图、资产、学习或跨项目用户画像 authority。

## 1. 原始确认

MIDS 提出三个高影响架构问题后，用户原始回答为：

```text
C B C
```

本项目将其解释为以下 **USER_EXPLICIT_CONFIRMED** 决策。

## 2. DEC-MIDS-ARCH-001｜执行导演型自治

- user_choice: `C`
- decision: `EXECUTION_DIRECTOR_AUTONOMY`
- meaning:
  - 在不触碰高影响红线的前提下，AI 可以自主发现问题、研究、提出方案、实施、Eval、修复并继续推进；
  - 用户不需要为低风险、可逆、已授权的确定性步骤反复发“继续”命令；
  - 高影响、不可逆、authority-changing 操作仍必须经过现有人工门与治理流程。
- does_not_mean:
  - AI 可以静默改核心剧情、世界观、角色身份；
  - AI 可以静默改 canonical 地图拓扑；
  - AI 可以静默替换正式默认资产；
  - AI 可以绕过独立 review / write_routes / maturity gate。
- implementation_boundary_after_independent_attack:
  - 当前 `proactive_execution_opportunity_router.yaml` 已经由 PROJECT_INDEX / read_sets 接入 ordinary directing path，因此不得把尚未验收的自治语义直接写进该 active-path 文件；
  - `EXECUTION_DIRECTOR_C` 当前只能存在于独立 `execution_director_autonomy_candidate.yaml` sidecar；
  - sidecar 当前不得出现在 PROJECT_INDEX、directing always-read set 或 write_routes；
  - 文件存在不等于 activation；未来正式启用必须通过独立 reviewed activation slice 显式接线。

## 3. DEC-MIDS-ARCH-002｜Persistent Film World Model

- user_choice: `B`
- decision: `PERSISTENT_FILM_WORLD_MODEL`
- meaning:
  - 长期目标不是每个镜头重新用文字描述世界；
  - 角色、对象、空间、摄影机、事件、持续实体与场景运行状态应拥有跨镜持续状态；
  - 新镜头默认继承上一个合法世界状态，只有显式状态变化、出场、移除、遮挡、相机排除或 canonical change event 才改变相关状态；
  - 生成模型应被视为这个持续电影世界状态的渲染/执行端之一，而不是世界事实来源。
- anti_duplication:
  - 不建立第二地图；
  - 不建立第二连续性主档；
  - 复用现有 `WorldStateIR + EventGraphIR + BlockingIR + TransitionContract + map + continuity`。

## 4. DEC-MIDS-ARCH-003｜跨项目长期 Creator Model

- user_choice: `C`
- decision: `CROSS_PROJECT_CREATOR_MODEL`
- meaning:
  - 系统长期应学习用户跨项目的叙事、镜头、表演、节奏、光影、AI味敏感点、创新接受边界等稳定创作偏好；
  - 当前项目仍拥有自己的项目局部风格与例外；
  - 当前 work item 的临时实验偏好不得自动升级成长期 Creator preference。
- authority_boundary:
  - 当前用户明确指令永远高于 Creator Model；
  - 本项目 screenplay / character / scene / map / asset / continuity canonical 永远高于 Creator Model；
  - Creator Model 只提供 preference signal，不提供项目事实；
  - 本仓库不作为跨项目 Creator Profile 数据库，真实跨项目 profile 应由独立长期记忆/第二大脑层承载；
  - 本仓库只允许消费带 provenance / scope / confidence / evidence 的 preference projection。

## 5. 架构翻译

```text
USER_EXPLICIT_CONFIRMED
        ↓
DEC-MIDS-ARCH-001 → unregistered execution_director_autonomy_candidate sidecar
DEC-MIDS-ARCH-002 → existing WorldStateIR persistent-state adapter
DEC-MIDS-ARCH-003 → non-authoritative creator-preference projection adapter
        ↓
exact-head eval
        ↓
independent architecture review
        ↓
separate bounded activation if accepted
```

当前 active Opportunity Router 保持 canonical main 内容不变；DEC-MIDS-ARCH-001 的方向确认不自动产生 runtime activation。

## 6. 当前成熟度

- decisions: `USER_EXPLICIT_CONFIRMED`
- implementation: `candidate`
- architecture_activation: `not_active`
- one_success_auto_promotion: forbidden
- PROJECT_INDEX_registration: absent

本次用户确认解决“方向是否要做”的问题，不等于所有具体实现细节均已确认。实现细节仍需通过 regression、真实生产试验和独立 review 收敛。
