---
title: Cinematic Visual Grammar外部研究与融合证据
status: candidate_evidence
canonical_filename: Cinematic Visual Grammar外部研究与融合证据.md
scope: cinematic_visual_grammar_external_skill_professional_research_and_runtime_integration
last_updated: 2026-08-28
---

# Cinematic Visual Grammar 外部研究与融合证据

> 本文件只承担来源、证据等级、冲突、适用边界与 targeted eval 设计，不是第二套导演系统。可执行导演方法唯一写入 `01_AI电影系统/AI电影系统.md`；运行时字段与静态检查写入 `10_运行时/screen_observable_audible_ir_schema.yaml`。外部资料不能直接把 candidate 晋级为项目稳定技能。

## 1. 摄取目标

本轮不是把“高级电影感”包装成质量词，也不是复制外部 Skill，而是回答：

1. 哪些视觉导演机制能补强当前 AI电影系统？
2. 哪些机制已经存在，只需要形式化为可传递的 IR？
3. 哪些外部规则与项目多模态、资产、Source Authority 或学习架构冲突？
4. 如何让自然语言导演任务能够经 Director Feature Compiler → Hard Route → AI电影系统 / SOAC 执行，而不是只停留在研究文档？
5. 如何用真实生成、targeted eval 与 regression 决定是否晋级？

## 2. 外部 Skill 固定来源

### Cinema DNA 21:9 × 3

- repository: `dacnay816y62-hub/cinema-dna-21x9x3`
- upstream commit: `4e3ec03b0a2ac5ebf5ceb9f4bfac12ec60f54ef1`
- `SKILL.md` blob: `4d2f0871f492ffed3a9a8babf0e1641eed10e0d8`
- source path: `SKILL.md`
- repository license status at ingestion: no `LICENSE` detected; GitHub repository metadata reported `license: null`
- evidence class: external community Skill / engineering artifact; useful as hypothesis and workflow evidence, not professional-standard authority
- repository URL: https://github.com/dacnay816y62-hub/cinema-dna-21x9x3

### 可迁移机制摘要

经查重后值得进入 candidate 研究的机制：

- unresolved state before aesthetic decoration
- relation / spatial pressure before composition choice
- planned viewer attention flow and cross-cut attention handoff
- color as narrative/physical-source decision rather than global filter
- visual information / texture / highlight density budget
- motivated capture substrate rather than generic film-stock tokens
- anti-template composition review
- reference-signal decoupling: reference role should be isolated not only by prose but, when feasible, by reducing unwanted signals in the reference itself

### 明确不摄取

- 不采用其“参考图只能分析、不得作为生成输入”的全局规则。本项目 Seedance/Seedream 工作流需要身份、场景、白模、动作、摄影机、风格等分通道参考。
- 不采用 21:9 × 3 作为项目正式影片默认结构；仅可作为 concept / visual exploration 的候选输出形式。
- 不采用其 82/100 评分作为项目硬门槛；该评分是该 Skill 自定义 rubric，不是行业标准。
- 不复制其完整 SKILL / references 到本仓库；当前无明确再分发许可证。
- 不把大量绝对 negative bans 迁移为项目全局提示规则；项目已有约束过载与字面合规失败证据。

## 3. T1 / T2 专业机构与一手制作证据

### AFI Conservatory｜Directing Curriculum

- source: American Film Institute Conservatory
- URL: https://conservatory.afi.com/directing-curriculum/
- evidence tier: T3专业机构 / E1机构课程资料
- relevant claim: 导演训练把文本/潜台词转为 visual storytelling and blocking，并要求镜头、移动与剪辑具有可解释的导演理由，而不是任意装饰。
- project translation: `RELATION-PRESSURE-COMPOSITION-001` 不把低机位、负空间、门框、前景虚焦当模板；先从角色目标、关系、信息与空间压力得到摄影机理由。
- boundary: 课程原则支持“有动机的导演决定”，不证明本项目某个具体构图自动优于另一构图。

### DGA｜Mimi Leder interview

- source: Directors Guild of America
- URL: https://www.dga.org/craft/dgaq/issues/1802-spring-2018/dga-interview-mimi-leder
- evidence tier: T3专业机构 / E2导演一手实践
- relevant claim: 复杂长镜头准备按演员 blocking、摄影机、声音、extras、props 等逐层合成。
- project translation: 支持 department overlay / staged integration，而不是所有部门同时改同一份最终 Prompt。
- boundary: 大师案例学习“问题→选择→原因→代价→成立条件”，不机械复制长镜头风格。

### ASC｜Roger Deakins production interviews

- source: American Society of Cinematographers
- URLs:
  - https://theasc.com/article/roger-deakins-asc-bsc-six-favorite-films/
  - https://theasc.com/articles/deakins-blade-runner-2049
- evidence tier: T3专业机构 / E2摄影师一手实践
- project translation: 图像与声音首先服务故事；光色应尽量从场景、建筑、实际光源与摄影选择产生，而不是依赖泛化“电影滤镜”。支持 `COLOR-THESIS-001` 与 `MOTIVATED-CAPTURE-SUBSTRATE-001`。
- boundary: 不以摄影师姓名作为 Prompt 风格魔法词，也不复制具体影片镜头。

## 4. T2 / T3 观众注意与剪辑研究

### Tim J. Smith｜Attentional Theory of Cinematic Continuity / Edit Blindness

- sources:
  - Tim J. Smith, attentional continuity research
  - edit blindness / gaze and continuity studies
- URL: https://bop.unibe.ch/JEMR/article/view/2264
- DOI/background: https://doi.org/10.3167/proj.2012.060102
- evidence tier: E3学术研究
- transferable mechanism:
  - 电影剪辑可利用运动、显著性与连续性组织观众注意，而非假定观众自由均匀扫描整幅画面。
  - 切镜处的运动和注意同步可影响切换是否被察觉以及下一镜搜索位置。
- project translation: `ATTENTIONAL-FLOW-001` / `attention_handoff` 可以记录 entry ROI、attention modulator、decisive ROI、withheld info、exit ROI 与跨切镜目标。
- terminology boundary: `attention flow / attentional flow` 在本项目作为工程字段；Cinema DNA 的“视线流量”不是宣称为行业固定标准术语。
- causal boundary: 眼动研究不能直接证明某个 AI 生成 Prompt 会稳定控制人眼；需要项目成片和观众/导演验收。

## 5. T1 制作互操作与部门信息传递

### OpenUSD｜Layer composition

- source: OpenUSD official documentation
- URL: https://openusd.org/release/intro.html
- evidence tier: E1/T4专业工程标准生态
- relevant mechanism: 多个部门/艺术家可在独立 Layer 工作，再通过明确组合规则叠加，不要求互相破坏源数据，并保留修改来源。
- project translation: 借用“Department Overlay”治理思想：Story/Director → Performance → Blocking → Cinematography → Look → Editorial → Sound → Model Adapter，各层只能补充自身职责；不能用下游审美改写上游 canonical 世界事实。
- boundary: 本项目不因此要求把所有导演数据迁移到 USD，也不实现 USD scene graph runtime。

### OpenTimelineIO｜Timeline metadata and external media references

- source: OpenTimelineIO official docs
- URL: https://opentimelineio.readthedocs.io/en/latest/index.html
- evidence tier: E1/T4专业工程
- relevant mechanism: timeline 保存 clips/timing/tracks/transitions/markers/metadata，媒体本体可保持外部引用。
- project translation: 支持当前 GitHub 保存 Shot/Transition/attention handoff/metadata，而 ChatGPT Library / Project 保存媒体本体的职责分离；不需要建立第二份视频二进制数据库。

### ACES Metadata File (AMF)

- source: ACES Central specification
- URL: https://docs.acescentral.com/amf/specification/
- evidence tier: E1/T3专业色彩规范
- relevant mechanism: 通过 sidecar metadata 让输入、look、输出等颜色处理意图在 dailies/editorial/VFX/color 之间可复现传递。
- project translation: 支持 `LookIntent` / `color_thesis` / physical source / exposure continuity 作为部门交接字段，而不是只写“电影级调色”。
- boundary: 当前项目不实现完整 ACES/AMF 管线；只借鉴“创意意图随镜头传递”的接口思想。

## 6. T1 Seedance 2.5 官方多模态证据

### ByteDance Seedance 2.5

- sources:
  - https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
  - https://seed.bytedance.com/en/seedance2_5
- evidence tier: E1官方
- relevant mechanisms:
  - 多参考输入会综合理解 composition、scene、style、character、props 等视觉信号。
  - Clay Render / white-model workflow 可用无纹理或低材质 3D/previs 表达空间结构、人物姿态、运动路径与摄影机角度，再由模型恢复真实视觉。
- project translation:
  - 参考职责不能只靠文字声明；若动作/几何参考带有强烈错误纹理、光线、色彩或风格，模型仍可能继承这些信号。
  - `REFERENCE-SIGNAL-DECOUPLING-002`：动作/几何参考优先低纹理、可读明暗、明确接触/路径；身份和风格由各自 authority reference 提供。
- boundary: 具体污染强度与哪种 white-model 最优属于模型/版本相关知识，必须由 C-DANCE/Seedance 2.5 项目实测验证，升级版本后进入 revalidation。

## 7. T2/T3 AI电影与长视频研究

### MovieBench｜CVPR 2025

- URL: https://openaccess.thecvf.com/content/CVPR2025/html/Wu_MovieBench_A_Hierarchical_Movie_Level_Dataset_for_Long_Video_Generation_CVPR_2025_paper.html
- evidence tier: E3同行评议
- transferable mechanism: movie-level / scene-level / shot-level hierarchical representation。
- project translation: 支持 Project/Episode Context → Scene Context → Shot Contract 分层，避免完整全局剧情反复灌入每个 shot。

### ShotDirector｜CVPR 2026

- URL: https://openaccess.thecvf.com/content/CVPR2026/html/Wu_ShotDirector_Directorially_Controllable_Multi-Shot_Video_Generation_with_Cinematographic_Transitions_CVPR_2026_paper.html
- evidence tier: E3同行评议
- transferable mechanism: parameter-level camera control 与 hierarchical editing-pattern-aware prompting 分层。
- project translation: 支持导演计划/IR 与 Model Adapter/执行控制分离；不把复杂导演分析全部塞进最终模型 Prompt。

### ShotVerse｜2026 preprint

- URL: https://arxiv.org/abs/2603.11421
- evidence tier: E3-preprint / candidate
- transferable mechanism: Plan-then-Control，将 planner 与 controllable video generation 分开。
- boundary: 作为架构邻接证据，不等于其模型效果可直接迁移到 Seedance。

### FilmBench｜2026 preprint

- URL: https://arxiv.org/abs/2607.24241
- evidence tier: E3-preprint + film-professional benchmark design
- relevant mechanism: 电影级视频不能只评“好看/清晰”，而需要 instruction following、temporal continuity、aesthetic/cinematic dimensions 等多轴评估。
- project translation: 当前 Expected vs Observed Eval 应继续分 instruction, identity, blocking, camera, performance, continuity, cinematic aesthetics, sound, reference fidelity/contamination 等维度。
- boundary: FilmBench 的具体 scorer 或权重不直接成为本项目硬门槛。

### CineTechBench｜2025 preprint

- URL: https://arxiv.org/abs/2505.15145
- evidence tier: E3-preprint
- relevant mechanism: 专业摄影维度包括 shot scale、angle、composition、camera movement、lighting、color、focal length 等。
- project translation: 支持把 cinematic compliance 拆成可检查字段而非“电影感总分”。

### FilmOps

- URL: https://github.com/Neo-yk/FilmOps
- evidence tier: T4工程实现 / candidate tool source
- relevant mechanism: 可从视频自动提取多类电影技术标签，为未来 `Expected CinematicIntentIR vs Observed Output` 提供 PoC 方向。
- boundary: 本 slice 不建立 FilmOps 生产依赖。其 checkpoint、资源成本、第三方模型许可证与项目收益需独立验证；当前 reverse observation 仍是 manual_or_AI_assisted。

## 8. 综合机制图

```text
Canonical story / character / map / assets
→ EventGraph / Blocking
→ CinematicIntentIR
   - unresolved state
   - viewer position
   - relation pressure
   - attention flow / handoff
   - composition reason
   - color thesis + physical sources
   - visual density budget
   - motivated capture substrate
   - reference signal roles
   - anti-template signature
→ ShotPlan / VisibleIR / PerformanceIR / AudibleIR
→ TransitionContract
→ ConstraintAutonomyContract
→ Model Adapter
→ Minimal Prompt
→ Generated Output
→ Expected vs Observed Eval
→ Feedback Learning
```

关键治理：`CinematicIntentIR` 不能覆盖 BlockingIR、canonical topology、角色身份或剧情因果；它只解释“这些事实已经成立以后，为什么摄影机、注意力、光色和视觉层级这样组织”。

## 9. Candidate 技能与边界

### UNRESOLVED-STATE-VISUALIZATION-001

- hypothesis: 重要画面先明确人物/关系当前无法立刻解决的状态，可降低“只摆情绪/只摆造型”的空镜头。
- boundary: 并非每个过渡镜头都要制造悬念或不可逆冲突；功能性空间/节奏镜头可保持普通。

### RELATION-PRESSURE-COMPOSITION-001

- hypothesis: 重要构图优先由人物目标、权力、信息差和空间压力推出，再选焦段/角度/遮挡。
- boundary: 不禁止形式主义构图；当对称、极端角度或重复构图本身就是主题/节奏策略时可以明确采用。

### ATTENTIONAL-FLOW-001

- hypothesis: 对关键揭示、遮挡、意外、absence reveal 和跨镜头搜索，记录 attention entry/modulator/decisive target/handoff 可改善信息控制。
- boundary: 不要求每个镜头画眼动箭头；普通动作镜头只在注意力冲突风险存在时调用。

### COLOR-THESIS-001

- hypothesis: 将综合色/强调色绑定到场景、服装、天气、材质和 practical light，可减少“滤镜染全画面”的低级感。
- boundary: 后期 look 仍可作为创作工具；规则要求的是来源/目的可解释，不要求颜色必须完全来自现场原始光谱。

### VISUAL-DENSITY-BUDGET-001

- hypothesis: 一主线索、一副线索，非关键区域允许普通、软、暗、遮挡或低细节，可改善层级并降低 AI 纹理油腻。
- boundary: 群像、史诗建立镜头、production design 展示等可以需要高信息量，但仍需主次层级；不能机械限制“每镜只能2–3个物件”。

### MOTIVATED-CAPTURE-SUBSTRATE-001

- hypothesis: 胶片、MiniDV、监控、鱼眼、旧广播转拍等成像介质只有在改变观众理解、角色感知或生产目的时才提高权重。
- boundary: 不禁止摄影师审美选择；只是防止把介质名当成通用“高级感 token”。

### ANTI-TEMPLATE-COMPOSITION-001

- hypothesis: 最近镜头重复同一构图压力/注意流/机位且没有新信息、升级、对比或主题回声时，应触发 necessity review。
- boundary: 连续性、视觉母题、仪式重复或故意压迫节奏可合法重复。

### REFERENCE-SIGNAL-DECOUPLING-002

- hypothesis: 多模态参考除声明职责外，还应尽量降低其非职责强信号；例如动作/几何白模保留清楚明暗与空间，但去除错误高频纹理、材质和风格污染。
- boundary: 不要求所有参考变白模；身份/材质/风格任务反而需要高质量像素。只在非职责信号足以竞争 authority 时处理。
- version binding: Seedance/C-DANCE 2.5 reference behavior requires ongoing revalidation.

## 10. Targeted Eval 设计

### REG-CINEMATIC-PRESSURE-001

A：先选漂亮构图/焦段，再把人物放进去。
B：同剧情、同空间、同资产下先定义人物/空间/信息压力，再选择构图。
比较：剧情可读、空间关系、摄影机理由、记忆点、模板感、生成稳定性。

### REG-ATTENTION-FLOW-001

目标场景优先使用“遮挡→镜外离场→回原 master 发现人物缺席”的 absence reveal。
A：只写事件结果“回来时人物已离开”。
B：显式定义 cut on action、reaction cutaway、offscreen exit、return to same master 与 attention target。
比较：揭示是否成立、人物是否被提前看见、观众搜索位置、剪辑自然度、约束僵硬度。

### REG-COLOR-THESIS-001

A：用统一电影滤镜/综合色形容词。
B：同目标色彩拆成 physical source + practical light + accent role。
比较：局部色彩差异、材质可信、肤色、滤镜感、连续性。

### REG-VISUAL-DENSITY-001

A：全画面高锐、高细节、高对比。
B：保持剧情线索不变，仅降低非关键区纹理/锐度/高光竞争。
比较：主信息可读、噪点/伪纹理、电影层级、材质自然度、细节损失。

### REG-REFERENCE-DECOUPLING-001

当前天然生产机会：凯姆市集滑绳。

A：使用原高频、强材质/强风格的动作构图参考。
B：使用相同核心几何/身体/绳索/围巾/摄影关系的 clean white-model / clay previs，保留可读明暗但去掉非职责高频纹理；人物身份和最终风格仍由各自 authority reference 提供。

必须尽量控制：同剧情、同 Prompt、同模型/版本、同画幅/时长、同 identity/style refs、同摄影目的、同生成设置。

比较：
- 围巾/绳索/身体拓扑
- 横向运动与摄影机几何
- identity fidelity
- environment/style fidelity
- unwanted texture/light/style inheritance
- microcontrast/noise
- overall naturalness
- prompt complexity

当前状态：`candidate_planned_AB`。在 B 未真实生成并和 A 对照前，不得把“白模一定改善画质”晋级为 scene_verified。

### REG-ANTI-TEMPLATE-001

用三个不同戏剧功能场景测试同一导演系统是否仍机械输出同种背影、中心透视、门框、眼部特写等套路。合法母题重复应允许通过。

### REG-CAPTURE-SUBSTRATE-001

A：无剧情理由加入 film stock / grain / fisheye 等“电影感”词。
B：仅在记忆、监控、媒介内嵌、角色主观感知等有明确功能时启用成像介质。
比较：风格适配、叙事功能、视觉污染、模板感。

## 11. 晋级规则

所有上述方法在本轮研究后最多为 `candidate`。

- 外部 Skill 受欢迎、专业机构资料、论文或 benchmark 不能替代本项目真实生成。
- 单场 A/B 清楚支持某一机制时最多进入 `scene_verified`，且只能在已验证 scope 内。
- 跨不同剧情功能、场景、角色和生成条件重复成立后，才考虑 `project_verified`。
- 模型/reference 行为必须记录 model/version；版本变化进入 `needs_revalidation`。
- 若新证据与既有正向规格、最小充分信息、SHOT-SCOPE、SOAC 或摄影构图保护规则冲突，按 Learning Application Gate 做 contextual coexistence / contradiction 裁决，不静默覆盖。
