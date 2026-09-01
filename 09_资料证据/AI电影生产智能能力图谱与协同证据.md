---
title: AI电影生产智能能力图谱与协同证据
status: candidate_evidence_only
canonical_role: production_intelligence_capability_research_annex
source_issue: 59
last_updated: 2026-08-31
---

# AI电影生产智能能力图谱与协同证据

> 本文件只承担外部研究、专业案例、工业标准、学术证据、项目转译与失败边界职责。它不是第二套导演方法，不覆盖 `01_AI电影系统/AI电影系统.md`，不覆盖剧情、角色、场景、地图、资产、连续性、Learning Application Gate、SOAC、Expected-vs-Observed 或 Targeted Repair authority。
>
> 所有新知识默认 `candidate`。模型、API、软件和平台能力属于版本相关知识；版本变化时进入 `needs_revalidation`。外部论文或大师案例不能单独晋级项目成熟度。

## 1. 研究问题

项目已经拥有大量导演、模型、资产、连续性、学习、验收和修复规则，但随着能力增长出现新的系统问题：

1. 一个制作问题究竟牵涉哪些能力域，缺少统一、机器可读的映射；
2. 不同部门/工具之间应传递哪些最小信息，仍依赖临场组织；
3. 用户明确知识、用户隐性经验、外部专业知识、前沿未知没有统一的 epistemic 路由；
4. 真实生成失败时，何时用 A/B、何时先筛变量、何时怀疑交互、何时检查评价者自身稳定性，尚未形成统一实验选择层；
5. 电影工业标准、认知科学、生成模型 benchmark、AI 协作研究存在可利用知识，但不能机械塞进导演主档。

因此本研究的目标不是“增加更多技巧”，而是寻找一种最小、可组合、可审计的 Production Intelligence Capability Graph，让现有能力知道彼此如何协作。

## 2. 证据等级

- T1：官方文档、正式标准、行业组织、模型官方发布；
- T2：顶会/顶刊同行评审、原作者正式论文；
- T3：专业机构、大师一手访谈、真实工业案例；
- T4：高可信工程复盘；
- E4：本项目真实生成与用户验收；
- candidate synthesis：本项目根据多源证据做出的系统设计候选，不等于来源原文结论。

## 3. 电影工业工作流与跨部门共同语言

### E-PICG-MOVIELABS-001｜MovieLabs Ontology for Media Creation（T1）

来源：MovieLabs, Ontology for Media Creation v2.6。
- https://movielabs.com/ontology-for-media-creation/
- https://mc.movielabs.com/omc/Tasks/ML_Ontology_Pt5_Tasks_v2.6.pdf

来源支持：MovieLabs 为影视制作软件互操作建立共同数据模型，核心概念包括 `Participants / Tasks / Assets / Contexts / Relationships`；Task 可由 Participant 执行，可消费或生成 Assets，也可通过 `Informs / isInformedBy` 传递并非资产化的信息或触发；Context 可从场景级到非常具体的工作说明。

项目转译候选：
- `Context` ↔ Project / WorkItem / Sequence / Scene / Shot；
- `Task` ↔ Analyze / Direct / Previs / Generate / Edit / Evaluate / Repair / Learn / Publish；
- `Participant` ↔ 用户、导演职能、专业部门、AI agent、模型、工具、服务；
- `Asset` ↔ 剧本段、参考图/视频/音频、白模、prompt、生成结果、证据包；
- `Relationship` ↔ DEPENDS_ON / CONSUMES / PRODUCES / INFORMS / VALIDATES / REPAIRS / CONSTRAINS / REFINES / SUPERSEDES。

边界：项目只借鉴工业共同语言与关系设计，不默认实现完整 OMC/RDF/JSON，不允许外部 ontology 成为项目事实 authority。

### E-PICG-OTIO-001｜OpenTimelineIO（T1）

来源：Academy Software Foundation OpenTimelineIO 官方文档。
- https://opentimelineio.readthedocs.io/

来源支持：OTIO 用 `Timeline / Track / Clip / Transition / Marker / RationalTime / TimeRange / metadata` 表达 editorial cut information，并把媒体引用与剪辑时间关系分开。

项目转译候选：
- sequence/shot 的时间身份不应只存在自然语言时间码；
- 当项目真正进入编辑器/DCC 互操作时，`shot_id + source range + timeline range + transition + marker + metadata` 可成为稳定 handoff；
- 当前无需把整个导演系统改写为 OTIO，先保持 compatible concepts。

边界：OTIO 表达剪辑结构，不决定剧情意义、导演意图或资产 authority。

### E-PICG-OPENASSETIO-001｜OpenAssetIO（T1）

来源：Academy Software Foundation OpenAssetIO 官方文档。
- https://openassetio.github.io/OpenAssetIO/

来源支持：OpenAssetIO 的核心职责是让 host application 与 asset management system 解耦，通过 entity reference/resolution/publishing/relationships 等接口连接工具与资产系统；它本身不是资产数据库。

项目转译候选：当前 `scene_asset_identity_schema + scene_media_resolver_manifest + asset_retrieval_policy` 的方向与这种“身份/引用 ≠ 存储实现”的分层相容。未来若接 DCC/剪辑/资产工具，应优先做 resolver/adapter，而不是把具体存储路径写进导演规则。

边界：不因此引入新的资产 authority；GitHub formal asset identity 和现有 resolver 仍是项目唯一职责层。

### E-PICG-OPENUSD-001｜OpenUSD composition（T1）

来源：Alliance for OpenUSD / Pixar OpenUSD 官方文档。
- https://openusd.org/release/intro.html

来源支持：USD Stage 由多个 Layer 组合，支持 references、payloads、variants、inherits/specializes 等非破坏式 composition。

项目转译候选：可作为理解项目 `Baseline + accepted deltas - revoked deltas`、reference responsibilities 和 scoped overlays 的结构类比。强 canonical 层与候选局部层应分开，避免每次修改复制整个世界状态。

边界：这是架构类比，不宣称本项目 Constraint Ledger 等同于 USD composition，也不把 USD 术语变成项目 truth semantics。

## 4. 摄影、构图、色彩与后期意图传递

### E-PICG-ASC-FDL-001｜ASC Framing Decision List（T1/T3）

来源：American Society of Cinematographers Motion Imaging Technology Council, Framing Decision List。
- https://theasc.com/society/ascmitc/asc-framing-decision-list

来源支持：FDL 用结构化数据保存从 previs、拍摄到后期的 intended framing，可作为 JSON sidecar 或嵌入其他结构，使 downstream application 能恢复创作者预期画框。

项目转译候选：
- Camera/Framing 不应只存在 prompt 文字里；
- 当机位/画幅是 hard creative decision 时，可输出 `FramingIntentReceipt`：camera anchor、aspect、intended crop/frame、safe/forbidden reveal、source reference、版本；
- 下游 Seedance/Seedream/编辑/裁切不得静默重新解释 locked framing。

边界：FDL 只支持“如何保留 framing decision”这一机制，不证明某种 framing 美学正确。

### E-PICG-ACES-OCIO-001｜ACES / OpenColorIO（T1）

来源：Academy Color Encoding System / Academy Software Foundation OpenColorIO。
- https://docs.acescentral.com/
- https://opencolorio.readthedocs.io/

来源支持：ACES/OCIO 建立跨拍摄、VFX、监看、调色、交付的色彩管理与 transform/view/display 体系；色彩意图与设备/显示变换需要显式区分。

项目转译候选：
- `color_thesis` 应与 `physical_color_sources`、生成模型美术控制、后期 viewing/output transform 分层；
- “暖/冷/电影感”不能把创作色彩意图、场景物理光源、显示变换三个层次糊在一起；
- 正式进入后期链时需要 color metadata/receipt，而不是靠人记忆。

边界：本项目目前不是 ACES mastering pipeline；不得伪称已实现完整 ACES/OCIO。

### E-PICG-C2PA-001｜C2PA provenance（T1）

来源：Coalition for Content Provenance and Authenticity specifications。
- https://c2pa.org/specifications/specifications/2.2/index.html

来源支持：C2PA 用 manifest、assertions、actions、ingredients、content binding 等表达内容来源与变换历史；provenance 本身不应替代对内容价值/真实性的独立判断。

项目转译候选：
- 生成/编辑/拼接/资产引用链应可形成 provenance action history；
- `source asset -> reference derivative -> generation -> edit -> selected final` 的关系可以机器追溯；
- provenance evidence 与 aesthetic/director authority 必须分开。

边界：当前只学习结构，不宣称项目产物已生成 C2PA 签名 manifest。

## 5. Seedance 2.5 官方能力与参考职责

### E-PICG-SEEDANCE25-001｜30秒、多模态参考、白模、编辑（T1，版本绑定）

来源：ByteDance Seed Team，2026-07-31 Seedance 2.5 官方发布与模型页。
- https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5
- https://seed.bytedance.com/en/seedance2_5

来源支持：
- 单次最长 30 秒并支持多轮延长；
- 单次可输入大量图像、视频、音频参考；
- 官方强调 clay render/white model 可负责空间结构、人物姿势、运动路径、摄影机角度；
- 官方示例明确把 white model 用于 `camera movement / pacing / shot-size transitions / trajectory / blocking`，把另一图像用于 `character / scene / materials / lighting / color / atmosphere`；
- 官方仍承认复杂运动物理合理性和多主体稳定性存在改进空间。

项目转译候选：本项目已有的 `reference responsibility split`、低纹理白模、高动态动作 geometry/contact 参考职责有强 T1 支撑，应把“参考媒体负责什么”和“提示文本负责什么”作为 handoff contract 的一等字段。

边界：这不是白模必然提高所有任务质量的证明。不同模式、版本、场景、参考信号冲突仍需真实生成验证；模型升级触发 `needs_revalidation`。

## 6. 生成视频验收不能压成一个“好看分”

### E-PICG-VBENCH-001｜VBench（T2，CVPR 2024）

来源：VBench: Comprehensive Benchmark Suite for Video Generative Models。
- https://openaccess.thecvf.com/content/CVPR2024/html/Huang_VBench_Comprehensive_Benchmark_Suite_for_Video_Generative_Models_CVPR_2024_paper.html

来源支持：把视频生成质量拆成 16 个相对解耦维度，并区分视频自身质量与条件一致性。

项目转译候选：Expected-vs-Observed 应继续坚持维度化验收。一个镜头可以视觉质感 PASS，但空间关系/动作/身份 FAIL，不能平均成“总体还不错”。

### E-PICG-T2VCOMP-001｜T2V-CompBench（T2，CVPR 2025）

来源：T2V-CompBench。
- https://openaccess.thecvf.com/content/CVPR2025/html/Sun_T2V-CompBench_A_Comprehensive_Benchmark_for_Compositional_Text-to-video_Generation_CVPR_2025_paper.html

来源支持：显式评测 attribute binding、dynamic attribute、spatial relationship、motion binding、action binding、object interaction、numeracy，并用人工评测验证指标相关性。

项目转译候选：增加/保留 `identity attribute / spatial relation / motion binding / action binding / object interaction` 等可分离维度，特别适合多人、多物体、道具接触与群体调度。

### E-PICG-PHYSICAL-001｜PAI-Bench 与 physics benchmarks（T2，CVPR 2026）

来源：PAI-Bench: A Comprehensive Benchmark For Physical AI。
- https://openaccess.thecvf.com/content/CVPR2026/html/Zhou_PAI-Bench_A_Comprehensive_Benchmark_For_Physical_AI_CVPR_2026_paper.html

来源支持：2,808 个真实世界案例表明，视频生成模型即使有强视觉逼真度，仍经常无法保持物理动力学一致。

补充来源：Physical Simulator In-the-Loop Video Generation, CVPR 2026。
- https://openaccess.thecvf.com/content/CVPR2026/html/Foo_Physical_Simulator_In-the-Loop_Video_Generation_CVPR_2026_paper.html

来源支持：当前生成模型对 gravity/inertia/collision 等基础物理仍是困难；显式物理 simulation 可作为某些任务的增强路径。

项目转译候选：
- `visual fidelity` 与 `physical plausibility` 永久分维度；
- 支撑、接触、惯性、碰撞、承重等镜头应进入 physics/contact eval；
- prompt escalation 不是唯一修复工具；若失败机制确实来自几何/动力学，可以升级白模、轨迹、4D/模拟/关键帧表示；
- 当前项目不能因为论文存在就声称已有 simulator pipeline。

### E-PICG-VABENCH-001｜音视频联合验收（T2，CVPR 2026）

来源：VABench: A Comprehensive Benchmark for Audio-Video Generation。
- https://openaccess.thecvf.com/content/CVPR2026/html/Hua_VABench_A_Comprehensive_Benchmark_for_Audio-Video_Generation_CVPR_2026_paper.html

来源支持：把同步音视频生成拆成 text-video、text-audio、video-audio similarity、A/V synchronization、lip-speech consistency 等 15 个维度。

项目转译候选：AudibleIR 与 VisibleIR 的并列结构是合理方向；对白 lipsync、物理事件音同步、环境声、音乐与视觉语义不能混成一个“声音好不好”。

## 7. 观众认知、事件边界与剪辑

### E-PICG-EVENT-SEG-001｜Event Segmentation Theory（T2）

来源：Zacks & Swallow, 2007；Zacks et al., Event perception: a mind-brain perspective。
- https://doi.org/10.1111/j.1467-8721.2007.00480.x
- https://pubmed.ncbi.nlm.nih.gov/17338600/

来源支持：人会自动把持续活动分割为层级事件；分割同时受运动等底层特征和人物目标等高层特征影响；预测误差与事件边界有关，事件分割影响注意和记忆。

项目转译候选：beat/cut analysis 可增加 `event_model_change`：目标改变、行动阶段改变、预测失配、新因果状态等都是潜在 cut/beat 候选。但不能把认知论文机械变成“这里必须切镜”。

### E-PICG-ATOCC-001｜Attentional Theory of Cinematic Continuity（T2）

来源：Tim J. Smith, 2012。
- https://doi.org/10.3167/proj.2012.060102

来源支持：连续性剪辑的若干规则可从视觉注意与切点前后 perceptual expectations 理解，包括 match-action、entrance/exit、shot/reverse-shot、180°和 POV。

项目转译候选：`attention_handoff` 不应只写“观众看哪儿”，还可记录：cut 前 salient ROI、运动向量/动作阶段、预期存在对象、cut 后 target ROI、声音桥、是否故意打破 expectation。它用于诊断 continuity/reveal，不是声称眼动可以完全决定剪辑艺术。

## 8. Human-AI mixed initiative 与用户主导权

### E-PICG-HUMAN-AI-001｜Guidelines for Human-AI Interaction（T2/T3）

来源：Amershi et al., CHI 2019, Microsoft Research。
- https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/

来源支持：18 条 Human-AI Interaction 指南经多轮验证，强调在适当上下文提供服务、表达能力边界、支持高效调用/撤销/纠错、在不确定时限制服务范围、解释原因、支持反馈和持续学习、保留控制。

项目转译候选：现有 proactive router 可以进一步引入 `expected information gain / interruption cost / reversibility / user effort saved / confidence / consequence`，但不能频繁为了“主动”打断创作。

边界：HCI 原则决定协作方式，不决定导演内容。

## 9. 实验设计与测量系统

### E-PICG-NIST-DOE-001｜Design of Experiments（T1/T2）

来源：NIST/SEMATECH Engineering Statistics Handbook。
- https://www.itl.nist.gov/div898/handbook/pri/section3/pri33.htm
- https://www.nist.gov/programs-projects/nistsematech-engineering-statistics-handbook

来源支持：实验设计应根据目标与因素数量选择。比较性问题、screening、多因素建模/优化需要不同设计；高因素全因子成本迅速上升，工程上常采用顺序小实验逐步缩小问题。

项目转译候选：
- 已知单一关键变量 → A/B comparative；
- 多个可能原因 → screening，先找主效应候选；
- 怀疑变量相互作用 → bounded factorial/foldover；
- 连续参数优化 → 小范围 response-surface/迭代搜索；
- 高成本模型 → sequential probe，便宜阶段只测试有迁移证据的维度。

边界：电影创作样本通常小，不能滥用显著性检验或用 DOE 名词制造虚假精确度；目标是降低混杂与生成成本。

### E-PICG-NIST-GRR-001｜Gauge R&R / measurement variability（T1/T2）

来源：NIST Gauge R&R。
- https://www.itl.nist.gov/div898/handbook/mpc/section4/mpc4.htm

来源支持：测量系统本身存在 repeatability、reproducibility、stability、bias 等误差；应区分被测过程变化与测量系统变化。

项目转译候选：
- 若不同 reviewer、不同抽帧策略、不同自动指标对同一视频结论不稳定，先标记 `measurement_system_uncertainty`；
- 不得把评价器抖动直接归因于生成模型；
- 对关键维度可建立少量重复评价/跨 reviewer 检查。

边界：不要求每个导演判断都做统计 Gauge R&R；只在结论高度依赖测量且 reviewer disagreement 会改变生产决策时启用。

## 10. 大师案例：学习机制，不抄招式

### E-PICG-DEAKINS-PRISONERS-001｜地点、灯光、调度共同演化（T3）

来源：American Cinematographer, Roger Deakins on Prisoners。
- https://theasc.com/articles/beyond-the-law-prisoners

案例机制：Deakins 描述夜景 RV 场景时，避免凭空制造“月光”，而是选择能提供可信光源的加油站环境；地点选择改变了光源与画面深度，继而改变人物调度和最终照明。这里不是“多用 practical lights”的风格秘方，而是 `story need -> location affordance -> motivated light -> staging -> frame` 的跨部门共设计。

项目转译：当灯光需求总靠 prompt 补救时，Capability Graph 应允许回溯 Production Design/Location/Blocking，而不是把所有失败都扔给 Lighting/Model Adapter。

### E-PICG-DEAKINS-BR2049-001｜角色/情绪先于视觉系统（T3）

来源：ASC Roger Deakins / Blade Runner 2049 discussion。
- https://theasc.com/articles/deakins-blade-runner-2049

案例机制：Deakins 强调复杂大制作仍保持简单，先聚焦角色与情绪，让 lighting/framing 随之服务；摄影、美术和建筑共同形成 silhouette、移动光线等视觉行为。

项目转译：视觉机制必须回到 `dramatic reason`，不能因为能力图谱知识更多就让镜头变成技术展示。

### E-PICG-CUARON-LUBEZKI-001｜长镜不是“不剪辑”，而是高密度协同（T3）

来源：ASC Children of Men production gallery / making-of material。
- https://theasc.com/articles/ac-gallery-children-of-men

案例机制：车内长镜与战斗长镜依赖专用 rig、演员 cue、摄影机运动、光线、车辆/场景、特效与排练的高度同步。它提醒项目：复杂 one-take 的难度不是一句“长镜头电影感”，而是跨部门时序和空间 constraint orchestration。

项目转译：当用户要求复杂一镜到底，Capability Graph 应自动扩展 Camera/Blocking/Performance/Previs/Lighting/Sound/Physics/Transition 的依赖扫描，并检查是否需要 white-model/trajectory，而不是只增加运镜形容词。

## 11. 研究综合：Production Intelligence 的核心原则

### PI-PRINCIPLE-001｜能力图谱只做“谁负责什么、什么依赖什么”

完整知识留在唯一 domain canonical；Capability Graph 只保存 compact routing metadata、authority refs、handoff contract、eval dimensions、experiment strategy 和 boundaries。

### PI-PRINCIPLE-002｜Epistemic zone 与 truth authority 分离

用户“知道/不知道”的状态不能决定事实真假。K1/K2/K3/K4 只决定系统如何解释、询问、研究、验证和呈现，不得绕过 Source Authority。

### PI-PRINCIPLE-003｜Department handoff 传递 invariant + intent + evidence，不传整份脑内分析

每个交接包只携带下游做出正确决策所需的最小充分信息：Context、Task、Asset refs、creative intent、hard/guided/free、reference roles、expected observables、acceptance dimensions、unknowns、provenance、next owner。

### PI-PRINCIPLE-004｜验收维度按镜头目的激活，不做全局总分

不同镜头激活不同 material dimensions。视觉质感 PASS 不能覆盖 topology FAIL；物理 PASS 也不能覆盖剧情功能 FAIL。

### PI-PRINCIPLE-005｜Experiment routing 是生产成本控制，不是学术装饰

实验方法根据未知结构选择。遇到多变量失败时，先减少混杂，不继续给 prompt 加同义词。代理模型只验证有项目证据支持可迁移的维度。

### PI-PRINCIPLE-006｜测量系统也必须被怀疑

生成结果、观察方式、评价者、抽帧策略、自动指标都可能带来变化。高影响分歧必须区分 generator variance 与 evaluator variance。

### PI-PRINCIPLE-007｜大师能力体现为跨域约束整合

高水平导演/摄影并不是掌握更多“招式”，而是能让剧情、表演、空间、摄影、光线、声音、剪辑、生产条件互相成为因果条件。能力图谱的终点不是规则越多，而是跨域决策更少冲突、更有原因、更易传递和验证。

## 12. 不确定性与待验证项

1. Capability Graph 是否会增加上下文负担，需要实际 runtime profiling；
2. K2 tacit inference 的 false-positive 率需要真实用户交互验证；
3. K3 专业知识主动解释的粒度需要避免打断创作；
4. K4 Unknown 自动生成过多可能造成研究膨胀，必须有 materiality/cost gate；
5. department expansion 不能变成“每个镜头调用所有部门”；需要 sparse dependency routing；
6. experiment strategy 需要至少三个不同生产任务验证成本收益；
7. Dimension Registry 是否遗漏动画/角色表演特有指标，需要后续 Golden/Regression Cases 反推；
8. 外部工业标准的 interoperability 只有在真实 DCC/editor/API 对接出现时才值得进一步实现。

## 13. 当前成熟度

- 外部证据索引：`candidate / research_supported`
- Production Intelligence Capability Graph：`candidate_unvalidated`
- Production Handoff Packet：`candidate_unvalidated`
- Epistemic Router：`candidate_unvalidated`
- Experiment Strategy Router：`candidate_research_supported`
- Dimension Registry：`candidate_research_supported`

任何一项不得因本研究文件写入而升级 `scene_verified`。
