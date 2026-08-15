---
title: AI视频高动态动作提示证据索引
status: active
canonical_filename: AI视频高动态动作提示证据索引.md
last_updated: 2026-08-15
scope: high_dynamic_human_motion_prompting_motion_reference_and_action_cinematography_evidence
---

# AI视频高动态动作提示证据索引

> 本文件只承担高动态人体动作、跑酷、攀爬、武打、竞技运动等 AI 视频生成的外部证据职责。它不替代 `01_AI电影系统/AI电影系统.md`，也不把任何单一模型的私有提示语法提升为通用导演规则。

# 1. 当前项目触发

## OBS-KAIM-H3-MOTION-20260815

- work item：`KAIM-HIGH-SEARCH-30S`，凯姆外立面高手式纵向跑酷。
- 用户连续多轮 MiniMax H3 真实测试反馈：即使提示词加入“一手高抓、点墙改向、转体、左右横移”等大量微动作描述，生成结果仍倾向普通人式持续贴墙攀爬，高手感很弱。
- 真实画面共同特征：多肢体长时间贴墙、接触持续过久、横向位移更像横向爬而非横向弹射、明显腾空/释放阶段不足。
- 同轮已验证：简化窗口交互并使用互斥状态后，凯姆先经过、妇女紧接开窗的时序明显更稳定；因此当前主要失败维度已收敛到 `motion_signature / dynamic_vitality`。
- 证据等级：E4，项目真实生成 + 用户明确反馈。
- 当前可复用规则成熟度：`candidate`。

# 2. ByteDance Seedance 官方动作案例｜E1

## 2.1 Seedance 2.0 正式发布

来源：ByteDance Seed Team，`Seedance 2.0 Official Launch`，2026-02-12。

官方案例呈现出稳定的动作描述结构：

- 双人花滑：先给竞技/花滑动作身份，再写同步起跳、空中旋转、精准落冰等少数高辨识动作节点，并用轴线偏移、重心调整、空中姿态、落地结果等物理证据保证动作可读。
- 武侠对决：蓄势 → 同时冲锋 → 泥水被脚步带起 → 兵器碰撞 → 瞬间超慢动作展示雨水冲击波与竹叶 → 恢复正常速度 → 背对背落地。重点是动作阶段、速度变化、环境响应和落地，而不是逐关节控制。
- 结论边界：这些是 Seedance 2.0 官方案例，不证明 Seedance 2.5 或 MiniMax H3 会逐字采用同一行为；可迁移的是高动态动作提示的结构思想。

项目提取：

```text
动作身份 / 技术类别
→ 少量标志性动作节点
→ 动量、重心或姿态证据
→ 环境响应 / 接触结果
→ 摄影机响应
→ 收束状态
```

# 3. Runway Gen-4 官方提示指南｜E1 / 跨模型工程证据

来源：Runway Help Center，`Gen-4 Video Prompting Guide`。

官方明确建议：

- 从最简单、最基础的 motion prompt 开始；
- 一次只增加一个新元素，便于判断哪个变量真正改善结果；
- 图生视频时文本重点描述 `motion`，不要重复输入图已经提供的主体、构图、色彩、灯光和风格；
- 使用直接、简单、易理解的物理动作；
- 避免过度复杂的 prompt；
- 省略非必要元素会给模型留下创造空间。

项目用途：支持“该详细的地方详细、可自由发挥的地方不要微控”，以及“动作失败时先压缩变量，不继续无限追加手脚细节”。

# 4. Google Veo 官方提示指南｜E1 / 跨模型工程证据

来源：Google Cloud / Vertex AI Veo video generation prompt guide。

相关结构：

- 把 action 视为视频核心“动词”；
- 可用 pacing / rhythm / direction 补充动作节奏；
- 图生视频优先描述画面如何运动，而不是重新描述静态首帧；
- 不要求每次把所有 prompt 元素写满。

项目用途：支持把“高手感”落到动作轨迹、节奏、方向、接触-释放关系，而不是只写抽象的“高手、轻盈、很快”。

# 5. MiniMax 官方视频资料｜E1 / 版本绑定

## 5.1 MiniMax H3

MiniMax H3 官方页面显示其支持自然语言多模态生成，并强调 V2V motion transfer / 复杂意图理解等能力。当前公开资料尚未给出 H3 专属的“跑酷提示语法”或逐关节动作 DSL。

项目边界：

- H3 最终 prompt 继续使用自然语言动作描述；
- 不把 Hailuo 旧模型的 camera command 私有语法无证据迁移到 H3；
- 若精确高手动作仅靠文本连续失败，应优先评估 H3 的视频动作参考 / V2V，而不是继续堆叠文字。

## 5.2 Hailuo 02 / 2.3

MiniMax 官方资料曾以 parkour、gymnastics 等作为复杂动作连续性能力示例，并使用简洁动作链描述主体行为。该资料只承担 MiniMax 系列邻接证据，不覆盖 H3 当前实测。

# 6. 动作参考 / 轨迹控制研究｜E3

`Motion Prompting` 等原始研究指出，纯文本对动态动作和时间构成的细微差异表达能力有限，显式时空运动轨迹或运动参考可以提供更直接的运动控制。

项目用途：

- 当一个非普通、高辨识、强身体力学的动作在 1–2 次文本定向 probe 后仍持续退化为泛化动作，进入 `reference_escalation`；
- 优先考虑 motion reference、V2V、绿幕动作、白模/动作 blocking 或关键帧轨迹；
- 这不是“文本永远做不到”，而是避免在文本控制已经饱和时继续增加自然语言约束。

# 7. 当前候选结论

当前足以形成但仍需项目继续验证的 candidate：

1. 高动态动作提示优先采用 `ACTION CLASS → TRAJECTORY → 2–4 SIGNATURE BEATS → IMPULSE/RELEASE/AIRBORNE/CATCH → ENVIRONMENT RESPONSE AS NEEDED → CAMERA RESPONSE → FINAL STATE`。
2. 只详细写会决定动作身份、叙事因果或物理成立的接触与动作节点；左右手脚的非关键微选择保持 GUIDED / FREE。
3. “高手感”不能仅依赖高手、敏捷、跑酷等抽象词，需要至少一组可见的运动证据，例如短接触、明确爆发、释放、腾空、改向、下一次抓点/落点。
4. 连续高动态动作不应让模型同时满足大量可替换的微动作菜单；“例如A或B或C”过多时可能被模型平均成安全、泛化运动，本项目已观察到类似失败，但因果仍为 candidate。
5. 环境响应只选 1–2 个最能证明力量/速度的信号，例如鞋底撞击、石灰尘、木梁轻颤、衣摆瞬间甩开；不是所有接触都要写反应。
6. 摄影机应让完整身体轨迹和下一关键支点可读，同时保留导演构图，不因动作可读性退化成无美学的 coverage。
7. 若 1–2 次简化文本 probe 仍不能建立目标 motion signature，升级到 motion reference / V2V / 白模动作参考，不继续无限追加自然语言。
8. H3 与 C-DANCE 的模型私有行为分别验证；低成本 H3 可先筛运动结构，但 H3 成功不等于 C-DANCE 2.5 正式成片一定成功。

maturity: candidate
