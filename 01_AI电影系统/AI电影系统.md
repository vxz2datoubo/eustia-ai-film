---
title: AI电影系统
system_id: DIRECTOR-CINEMA-SYSTEM
status: active
canonical_filename: AI电影系统.md
maintenance_mode: in_place_only
versioned_filename_policy: forbidden
last_updated: 2026-08-12
source_migration: file_library_canonical_2026-08-11
public_repository_boundary: project_owned_methods_and_summaries_only
---

# AI电影系统

本文件是《秽翼的尤斯蒂娅》项目中导演、分镜、摄影、灯光、表演、剪辑、声音、AI图像与AI视频方法的唯一可写通用主档。项目事实分别由剧本、角色、地图、场景、资产和连续性主档承担；原始母本、PDF、媒体与证据留在 Library / 外部只读层。

## 1. 启动、权威与运行时路由

每个导演、剧情、分镜、表演、Seedance、Seedream、场景或资产任务先读取 PROJECT_INDEX.yaml，再按 10_运行时/read_sets.yaml 做最小必要读取。不得以旧聊天、Memory、搜索排名、文件修改时间或文件自称 active 取代 Source Authority。

运行顺序：

    PRE-DIRECT
    → PROJECT_INDEX 与 effective source
    → 当前任务 DTRM
    → 必要的剧本、连续性、角色、场景、地图、资产和证据
    → 导演设计与模型编译
    → 验收
    → Final-Delta / 学习分级
    → 唯一目标主档写回并 FETCH VERIFY

默认是 local targeted retrieval；只有路由置信度低、跨域冲突、连续性漂移或复杂失败时才扩大读取。禁止把整个仓库全文注入上下文。

### 1.1 DSRI 与 DTRM

10_运行时/director_route_index.yaml 是长期的 Director Symptom Routing Index（DSRI）：按症状召回检查技能。每轮建立临时 Director Task Routing Manifest（DTRM），不另存为长期版本文件：

    task_class:
    symptom_tags:
    mandatory_reads:
    lead_domain:
    support_domains:
    mandatory_scans:
    candidate_axes:
    reveal_horizon:
    validation_checks:
    recalled_lessons:
    writeback_plan:

每场默认一个主导知识域、一至三个辅助域、至多一个检查域。跳轴、强手持、长焦压迫、延迟揭示、复杂长镜头等不是永久默认效果，须由任务症状触发。

### 1.2 职责与冲突裁决

优先级：

    用户当前明确确认
    → PROJECT_INDEX 与当前 GitHub verified 主档
    → 当前剧本、资产、地图、连续性
    → 本系统通用方法
    → 经验证项目经验
    → 专业研究
    → Memory / 模型推测

Plot layer 锁定必须发生的事件、因果、伏笔、信息顺序、延迟揭示和结尾状态。Character layer 决定人物如何做、如何说、第一冲动、如何自控、走哪条可达路线与行为指纹。美学不得推翻物理空间和因果；模型偏好不得推翻导演合同。

## 2. 核心导演原则

1. 剧情、人物因果和主题高于技巧。
2. 每镜必须承担剧情、心理、情绪、空间、权力、主题、节奏或转场功能。
3. 行动优先于解释：将抽象情绪转译为视线、停顿、距离、呼吸、姿态、触碰、预备、结果与余震。
4. 先设计角色行动线和空间调度，再设计机位、焦段、运镜、灯光与剪辑。
5. 摄影机运动的终点必须提供新人物、新空间、新信息或新心理关系；否则固定或删除。
6. 正式模型执行稿只保留最小充分信息，不倾倒完整导演分析。

每镜都要能回答：观众新知道什么、人物关系改变什么、空间建立或重定义什么、为何在此切入切出、删除后损失什么、是否重复上一镜。回答不出则删除、合并或重写。

### 2.1 场景诊断与编译

导演母版依次确定：剧情事实、人物知道/不知道/误解什么、目标与潜台词、场景问题、转折、信息差、观众认知、空间与声画条件、初始站位、动线、权力中心、镜头组、结尾接口。

镜头卡至少包含：

    shot_id:
    dramatic_function:
    shot_size:
    camera_position_and_orientation:
    lens_intent:
    composition_and_layers:
    blocking_and_performance:
    camera_motion:
    motivated_lighting:
    sound_and_cut:
    continuity:
    final_state:
    necessity:

反应镜头负责脸，关系镜头负责谁在看谁，目标动作镜头负责对方做了什么；一个机位无法兼顾时必须拆镜。非互惠关系不得用错误的正面对视反打。

### 2.2 用户仅提供剧情时的默认完整导演输出

当用户只提供剧情并明确要求完整处理时，默认交付 `DIRECTOR-FULL-OUTPUT-001`，而不是只返回 Seedance 执行稿。除非用户明确豁免某项，输出按以下十五项完整导演合同组织：

1. 母本与连续性核对；
2. 场景诊断；
3. 导演意图；
4. 人物目标与潜台词；
5. 节拍；
6. 表演；
7. 场面调度；
8. 镜头脚本；
9. 摄影与灯光；
10. 剪辑与声音；
11. AI 资产清单；
12. 模型自主权合同；
13. 视频模型执行稿；
14. 验收清单；
15. 结尾接口。

可按任务复杂度压缩每项的篇幅，但不得把任一职责静默删去；执行稿只是第十三项，必须服从前十二项的导演裁决，并为第十五项留下可继续制作的状态接口。

## 3. 叙事、认知与信息预算

世界观说明不能冻结画面。优先使用动作、道具、空间、声音、对白与并行动作承载信息；旁白必须明确其功能，不能替代正在发生的戏。

可选择四类信息关系：观众比角色知道得多的悬念、同步发现、感官刺激先于解释的知觉惊异、结果先于原因的回溯重建。延迟揭示可隐藏身份、动机和完整空间，但不得隐藏理解当前动作、方向、物理因果或正确道德归属所必需的信息。

### 3.1 叙事并行与预算

- 叙事并行化：让行动、声音、背景生活和信息在可读范围内同时推进。
- Attention Budget：同一时间只给观众足够可读的主要注意对象；背景不与主线争夺一级权重。
- Reveal Budget：为后续悬念保留尚未该知道的信息；禁止为了短期刺激提前消费回收。
- 长距离叙事预载：以低权重的行动、空间、物件、视线或声音种下可回收线索。
- 反应—视线—目标分离：当三者不能在同一构图中正确表达时，拆成不同镜头。

## 4. CALC、CLCS 与有限理性

CALC（Character Autonomous Life Continuity）是角色自主生命连续性：角色不是为了等镜头才开始活；摄影机只是切到角色原本正在继续的人生。CLCS（Character Life Continuity Scan）是每次角色进入或重入画面前的扫描。

CLCS 至少检查：

    life_before_frame
    current_task
    task_reason_and_urgency
    attention_target
    knowledge_state_and_misunderstanding
    emotional_and_physical_residue
    social_role_and_duty
    relationship_filter
    habit_signature
    interruption_trigger
    first_impulse
    controlled_response
    speech_pattern
    nonoptimal_bias
    resume_or_switch

执行提示可压缩为：

    preexisting_activity
    → attention
    → trigger
    → microreaction
    → response_action
    → speech_style
    → resume_state

角色不是作者的全局最优代理。其行为来自知道、不知道和误解的事实，以及欲望、恐惧、职责、关系、习惯、身体状态、情绪残留与资源约束。允许非最优但人物真实的选择；禁止为了“真实”无因果犯蠢。

必须能通过以下回归：Camera-Off、Swap、Omniscience、Optimizer、Busywork、Uniform-Reaction、Resumption、Background-Independence。即：拿走摄影机角色仍在做合理事情；交换角色后行为不应仍完全成立；角色不能全知或总是最优；背景不能机械忙碌；被打断后应恢复或有理由转向。

## 5. 表演、调度、摄影、剪辑与声音

表演写任务而不是结果。每个重要角色设计行为任务、进入状态、眼神落点、呼吸与停顿、动作预备、余震、重心、距离、台词表层和潜台词。禁止把所有人写成相同的皱眉、握拳、低头或冷笑。

调度应明确初始位置、主要动线、前中后景、遮挡、权力中心、谁靠近或绕开谁、谁被迫移动、道具如何参与冲突和结尾位置。权力可由中心位置、静止权、移动权、占幅、距离、遮挡和发言权承担。威胁可通过渐进侵占、负空间缩小和前景遮挡建立，而不依赖狞笑、吼叫或高密度音乐。

摄影与灯光须说明客观/主观视点、稳定度、空间深度、焦段目的、光源动机、人物可读度、色温光比和前后镜曝光连续。剪辑和声音须判断动作前/中/后切、视线或动作匹配、J/L-cut、声桥、客观/主观/象征声音与静默。声音与画面可以承担不同信息，但必须在同一因果和时长预算内。

## 6. AI资产、模型与多模态职责

### 6.1 通道职责

- 图片：身份、服装、场景、道具、材质、光色与关键帧。
- 视频：动作、节奏、表演、运镜、多人调度、连续时间。
- 音频：对白、音乐、环境声、音效、停顿与同步。
- 白模 / 深度图：空间、机位、景别、轨迹、遮挡、站位、路径和碰撞。

参考素材按身份、几何、动作、摄影机、风格、声音六通道声明唯一职责。生成前检查身份图冲突、几何图与白模冲突、动作参考夹带错误机位、风格图改变时代服装、音频超过动作可承载时长、无关人物被继承等问题。

### 6.2 Seedream 与 Seedance

Seedream 5.0 Pro 优先承担身份锚定、服装道具、场景空间、首尾帧、多图融合、局部替换、人像修复和真实材质；Seedance 2.5 优先承担连续动作、表演、重心、摄影机、时间推进、对白、口型、环境声、延长和视频编辑。复杂多层空间、桥上桥下、精确顶视、多人路径、遮挡与长镜头先做白模。

4–6 秒用于相机、身份、动作或场景单测；8–15 秒用于一个完整事件包；20–30 秒只在资产稳定、阶段清楚、转变有因果且结尾稳定时使用。不得为填满 30 秒增加无意义动作。

总时长、镜头边界、事件顺序和最后状态可以由导演指定；但 Seedance 2.5 擅长自动分配镜头时长时，默认让模型自然安排各镜头时长，不为每镜硬写具体秒数。时间码（timecode）是按需控制工具，只在以下情况使用：对白或口型同步、定点视频编辑、延长接口、明确节拍控制，或必须锁定因果时序。时间码不是所有长视频的默认格式。

每个镜头先确立一个单一主导变化律，其他元素只能辅助。编译分三层：

    导演母版
    → 资产与控制层
    → 最小充分模型执行稿

模型自主权按 camera / actor / environment / edit / sound 分别设为 LOCKED、GUIDED 或 FREE。角色身份、空间拓扑、关键道具、严格机位与最后状态常为 LOCKED；自然呼吸、布料与低显著度背景可 GUIDED/FREE。

### 6.3 质量与失败修复

默认目标是真人电影截图质感：真实摄影机成像、物理正确光照、自然皮肤布料、石木金属旧化、稳定空间、干净高频细节、可靠中间调和柔和高光。避免塑料皮、游戏CG、插画感、数字绘画感、无逻辑材质、噪点伪细节与过度HDR。

失败时先定位单一维度：机位漂移、变脸、场景搬家、动作主语错配、提示词失控或图像累积脏化。只修失败维度：锁六自由度或做无人物相机测试；减少身份源并拆段；用地图/YAML/白模锁几何；为动作加人物位置和时序；重建最小提示；回到干净母版、分区修复和最终一次全局合成。不得无限串联最新AI输出。

### 6.4 执行模板与几何约束

正式镜头在导演母版、资产控制层和模型执行层之间编译。执行层应只保留：任务、画幅、总时长、镜头目的、主导变化律、参考职责、不变量、模型自主权、事件顺序、必要时的时间码、最后一帧和少量高风险禁止项。

任务域提示词编译器按任务选字段、优先级与验收，不能把一种模板套给所有任务：影视剧情型优先镜头目的、人物/空间、动作因果、反应、摄影机、声音与结束状态；几何空间型优先投影、摄影机自由度、拓扑、轨迹、不变量、材质与光线；产品/材质型优先资产身份、不可变结构、材料反馈、主导变化律、光线、摄影机与品牌信息；平面/海报/Logo 型优先文字/Logo、版式、可运动图层、层级、转场与结束版式；教育/科普型优先事实关系、过程、变化顺序、标签/图形、摄影机与美学；IP/创意反差型优先清楚反差、主体、主动作、背景第二事件、揭示时机与结果。DTRM 只召回当前任务域需要的字段；不相关任务域不得默认激活。

复杂几何镜头应使用 YAML、白模或深度图描述投影、固定机位、可见域、对象层级、路径、遮挡和不变量。纯顶视或正交镜头属于几何空间任务：先生成干净场景，再做无人物相机单测，锁定 six degrees of freedom（camera height、pitch、yaw、roll、focal length、zoom）、cut/reframe 与 XY 轨迹，最后加入小人物；人物近景应另做镜头。

首帧与尾帧可分别锁定身份、构图和最后状态；视频延长与局部视频编辑必须继承已验证的最后状态、身份、服装、空间、声音和动作接口。镜头自动调用资产时，按用户本次明确指定、当前连续性绑定、正式默认资产、合法备选、明确报告缺失的顺序执行。

## 7. 证据、学习与成熟度

EDCM（Epistemic Director Coverage Matrix）管理认知边界：

- K0：用户明确确认、正式主档与一手证据；
- K1：有证据、置信度和适用边界的稳定隐含规律；
- K2：能提升制作的邻接专业知识，先作为 candidate；
- K3：重复失败、漏召回、模型变化、技能冲突或旧理论无法解释的 unknown-unknown，先入 Unknown Registry。

技能成熟度为：

    candidate → scene_verified → project_verified → general_stable

旁路状态为 conflicted、needs_revalidation、deprecated。单次成功不是通用定律；模型、工具或版本变化会使依赖型经验进入 needs_revalidation。

稳定通用方法写本文件；项目事实写项目记忆；剧情写剧本；人物写角色库；局部场景属性写场景库；拓扑写地图；资产写资产库；当前生产状态写连续性；证据写证据索引；无法裁决问题写 Unknown Registry。正式写回统一为：

    FETCH CURRENT → EDIT → COMMIT → FETCH VERIFY

## 8. 迁移与废弃边界

本文件在 2026-08-11 完整迁移旧 AI电影系统.md 的有效内容，并与 GitHub-first、PRE-DIRECT、DSRI/DTRM、CALC/CLCS、EDCM、成熟度和当前项目验证规则合并。历史 AI电影化系统总纲_v*.md、旧总纲、补丁、旧 Seedance 独立技能与版本副本只能作 historical / migration evidence / comparison source，不得成为活动依赖。

原始官方网页、MHTML、PDF、游戏母本和其他受版权材料不复制到 public GitHub；本文件只保留项目自有方法、短摘要、来源边界与可执行结论。
