---
title: AI电影系统
system_id: DIRECTOR-CINEMA-SYSTEM
baseline_version: 1.8.9
status: active
canonical_filename: AI电影系统.md
maintenance_mode: in_place_only
versioned_filename_policy: forbidden
last_updated: 2026-08-28
maintainer: Bob Huang × ChatGPT
language: zh-CN
---

# AI电影系统

> 本文件是导演、分镜、摄影、灯光、表演、剪辑、声音、AI图像与AI视频生产规则的唯一权威主文件。
> 基线固定为 **v1.8.9**。以后不再建立带版本号的新系统总纲，不再建立独立AI视频技能主档，也不再用差异补丁作为长期规则入口。所有有效修改直接写入本文件对应章节，并更新内部变更日志。

> GitHub-first reconcile（2026-08-12）：本文件保留所迁入源文件的全部有效导演知识；每轮活动任务先读取仓库根 `PROJECT_INDEX.yaml`。该索引、`read_sets.yaml`、`write_routes.yaml` 和当前 GitHub verified canonical 决定读取与写回，不得由本文旧路径、Memory 或历史版本说明夺权。

# 0. 唯一入口与维护制度

## 0.1 本文件负责

1. 剧情到电影镜头的分析与编译。
2. 导演意图、人物目标、潜台词、节拍与观众认知。
3. 场面调度、分镜、摄影、灯光、剪辑和声音。
4. DirectorSkills知识域路由与冲突消解。
5. AI图像、关键帧、白模、深度图、多模态参考与局部编辑。
6. Seedream与Seedance双模型生产。
7. 时间码、延长、视频编辑、验收和失败诊断。
8. 系统学习、规则边界和原地写回。

项目事实不在本文件重复维护。先读取根 `PROJECT_INDEX.yaml`，再按 `10_运行时/read_sets.yaml` 的最小读取集合，统一读取：

- `../02_AI电影项目记忆/AI电影项目记忆.md`
- `../03_剧本与改编/当前改编剧本.md`
- `../04_角色与表演/角色与表演设定库.md`
- `../05_场景与空间/场景与空间设定库.md`
- `../05_场景与空间/00_项目地图文件.md`（空间拓扑、方向、高低和可达路线唯一权威）
- `../06_视觉资产/视觉资产登记库.md`
- `../07_连续性与生产状态/连续性与当前生产状态.md`


## 0.1A 用户意图读取接口

在编写提示词、导演方案、资产任务或系统规则前，先读取 `PROJECT_INDEX.yaml`，再读取[AI电影项目记忆](../02_AI电影项目记忆/AI电影项目记忆.md)中的项目专属意图与习惯，以及[反馈反推与系统反哺引擎](../08_系统学习/反馈反推与系统反哺引擎.md)中的相关已验证经验。Memory 只能辅助索引，不能覆盖 GitHub canonical。

- 明确偏好作为默认约束。
- 多次反馈形成的隐性偏好作为高置信度指导。
- 单次要求只在当前任务中生效，除非用户明确要求长期化或后续重复验证。
- 用户实测反馈高于未经验证的理论推断。
- 发现新稳定习惯时，通过[反馈反推与系统反哺引擎](../08_系统学习/反馈反推与系统反哺引擎.md)按 `write_routes.yaml` 写回唯一 GitHub canonical。

## 0.2 固定维护规则

- 文件名永久固定为 `AI电影系统.md`。
- 新规则必须写入所属章节，不能另建第二套主档。
- 不生成带版本号的AI电影系统副本。
- 不生成独立Seedance、Seedream或AI视频长期技能文件。
- 原始官方资料、论文和研究报告可以独立保存，但只承担证据职责。
- 废弃规则在本文内部标注替代关系。
- 用户当前明确要求始终优先。

## 0.3 总执行路由

```text
识别任务
→ 读取项目事实、角色、场景、资产与连续性
→ 诊断剧情和观众认知
→ 选择专业知识域
→ 设计动作线与空间调度
→ 设计镜头、摄影、灯光、声音和剪辑
→ 判断是否需要资产、YAML、深度图或白模
→ 编译为模型执行稿
→ 验收不变量
→ 只修复失败维度
→ 稳定学习原地写回
```

# 1. 核心使命与最高原则

## 1.1 核心使命

把剧情、对白、人物关系、动作和情绪转化为可表演、可调度、可拍摄、可分镜、可剪辑、可生成、可延长、可修复、可验收和可追溯的电影场景。

## 1.2 最高原则

1. 剧情、人物因果和主题优先于技巧。
2. 每个镜头必须承担剧情、心理、情绪、空间、权力、主题、节奏或转场功能。
3. 行动优先于解释，把抽象情绪转成视线、停顿、距离、呼吸、姿态和触碰。
4. 重要动作必须设计预备、发生、结果、反应和余震。
5. 权力通过中心位置、静止权、移动权、遮挡、占幅、距离和发言权表达。
6. 摄影机运动必须在终点提供新信息，否则固定或删除。
7. 模型能力不等于导演意图，模型擅自补镜、降机位或改构图时要使用结构约束。
8. 单场实验、平台限制和临时补救不得自动升级为项目事实。
9. 电影感来自叙事和视听因果，不来自质量词堆叠。
10. 正式执行稿使用最小充分信息，不把导演分析原样倾倒给模型。

## 1.3 镜头必要性测试

每镜回答：

- 观众新知道什么？
- 人物关系或情绪发生了什么变化？
- 空间是否被建立或重定义？
- 为什么在此处切入和切出？
- 删除后损失什么？
- 是否重复上一镜？

回答不出时，删除、合并或重写。

# 2. 规则层级与冲突裁决

## 2.1 五级规则

- L1 通用导演规则
- L2 类型与风格规则
- L3 项目规则
- L4 角色、关系和固定场景规则
- L5 当前镜头一次性方案

## 2.2 优先级

```text
用户当前明确要求
> 安全与平台硬限制
> 当前确认项目事实和改编层
> 角色、场景与连续性
> 本系统通用规则
> 风格偏好
> 单次实验
```

## 2.3 常见冲突

- “反应重于动作”与高速动作连续性冲突时，把反应放到动作前预备或动作后余震。
- 长焦压缩与空间建立冲突时，先短暂建立空间，再进入长焦。
- 延迟揭示与叙事清晰冲突时，不得隐瞒理解当前动作所必需的信息。
- 美学构图与物理空间冲突时，空间和因果优先。
- 模型偏好与相机锁定冲突时，导演合同优先。

# 3. 输入解析

处理前识别：

## 3.1 剧情事实

- 谁在场
- 每个人知道和不知道什么
- 事件顺序
- 前因后果
- 当前空间关系
- 关键道具
- 不可更改事实

## 3.2 人物层

- 表面目标
- 隐藏目标
- 恐惧与欲望
- 伪装
- 权力来源
- 当前关系
- 本场关系变化

## 3.3 戏剧层

- 场景问题
- 冲突来源
- 转折
- 信息差
- 情绪曲线
- 场景结束后的新状态
- 可删除的重复信息

## 3.4 视听层

- 空间结构
- 光源
- 环境声
- 关键动作
- 视线
- 轴线
- 人物动线
- 可作为切点的动作、声音和视线

# 4. 标准导演工作流

## 4.1 场景诊断

判断这场戏为什么存在、开始和结束有何不同、是否只在传递信息、冲突是否被行为承载、最值得观众记住的瞬间是什么。

## 4.2 导演意图

用一句具体句子定义：

> 观众在本场结束时，应当对人物、关系或世界机制产生什么新的感受或判断。

禁止只写“表现紧张”“营造电影感”。

## 4.3 节拍拆分

节拍由目标改变、新信息、权力转移、决策、情绪压抑或失控、空间变化、声音和道具介入、观众解释改写触发。

## 4.4 表演设计

每个主要角色设计：

- 行为任务
- 进入状态
- 眼神落点
- 呼吸和停顿
- 动作前预备
- 动作后的掩饰或余震
- 身体重心
- 距离变化
- 台词表层与潜台词

禁止所有人物使用相同的皱眉、握拳、低头和冷笑。

## 4.5 场面调度

明确初始位置、主要动线、权力中心、前中后景、谁靠近或绕开谁、谁被迫移动、道具如何参与冲突、结尾位置。

## 4.6 镜头组设计

每镜至少记录：

```yaml
shot_id:
dramatic_function:
shot_size:
camera_position:
camera_orientation:
lens_intent:
composition:
foreground:
midground:
background:
blocking:
performance:
camera_motion:
lighting:
sound:
cut_in:
cut_out:
continuity:
final_state:
necessity:
```

## 4.7 摄影与灯光

回答客观还是主观、稳定程度、空间深度、焦段目的、光源动机、主辅轮廓关系、人脸可读度、光比色温、与前后镜头曝光连续。

## 4.8 剪辑与声音

判断动作前切、动作中切或动作后切，是否需要反应镜头、视线匹配、动作匹配、J-cut、L-cut、声音先行、静默或音乐，声音属于客观、主观还是象征层。

# 5. 电影导演分镜知识深度融合

电影制作不是单一导演课，而是编剧、导演、摄影、剪辑、美术、声音、表演和电影史批评的交叉体系。

## 5.1 知识域

| 知识域 | 核心问题 | 对应输出 |
|---|---|---|
| 编剧与叙事 | 场景为什么存在 | 事件、冲突、节拍、信息顺序 |
| 导演思想 | 观众如何理解人物 | 导演意图、权力、视点 |
| 分镜与调度 | 三维行动如何变成二维画面 | 站位、动线、轴线、构图 |
| 摄影与灯光 | 从哪里看，光从哪里来 | 景别、机位、焦段、曝光 |
| 表演指导 | 心理任务如何变成行为 | 行为动词、微动作、停顿 |
| 剪辑与转场 | 为什么此刻切 | 切点、视线、动作匹配、声桥 |
| 声音设计 | 画外空间和主观经验 | 环境声、静默、对白、音效 |
| 美术与调色 | 空间如何承载社会结构 | 材质、色彩、层级、连续性 |

## 5.2 研究转译链

```text
来源资料
→ 关键观点
→ 可执行规则
→ 适用场景
→ 禁用条件
→ 错误示例
→ 高级示例
→ 检查清单
→ AI执行字段
```

禁止把书名、导演名和课程术语直接塞入提示词。

## 5.3 先设计动作线，再设计镜头

先问：

- 谁控制场面？
- 谁想逃、靠近、隐藏、试探或打断？
- 谁知道更多？
- 空间中有什么门、窗、桌、楼梯、桥、前景和遮挡？
- 人物从A点到B点的动机是什么？
- 这个移动改变了什么权力关系？

再决定景别、角度和运镜。

## 5.4 分镜是剪辑计划

每张分镜必须说明从上一镜继承什么、向下一镜提出什么问题、观众看哪里、轴线与视线如何连续、是否需要把反应、关系确认和目标动作拆开。

## 5.5 视觉变量

可控制：

- 空间开合
- 线条方向
- 形状秩序
- 明暗
- 色温与饱和
- 运动速度
- 遮挡比例
- 稳定度
- 剪辑密度
- 声音密度

视觉强度应随剧情强度变化，不从第一秒把所有通道推到最大。

## 5.6 表演不写结果，写任务

错误：

```text
她悲伤地说。
他愤怒地看着。
```

可执行：

```text
她想把哭意压回去，低头整理袖口，指尖反复捏住同一处线头。
他想迫使对方先退让，所以不提高音量，视线保持不动，说话速度反而变慢。
```

## 5.7 运镜必要性

摄影机运动终点必须揭示新人物、新空间、新信息或新的心理关系。没有新信息则改为固定镜头。

# 6. 观众认知与镜头职责

## 6.1 四种信息关系

1. 观众比角色知道得多：悬念。
2. 观众和角色同步发现：共同发现。
3. 感官刺激先于解释：知觉惊异。
4. 结果先出现，原因和身份后补：好奇与回溯重建。

## 6.2 延迟揭示边界

可以延迟行动者身份、动机和完整空间关系。不能延迟理解当前动作所必需的信息、人物方向、关键物理因果和会造成错误道德归属的事实。

## 6.3 三镜职责

- 反应镜头负责脸。
- 关系镜头负责谁在看谁。
- 目标动作镜头负责对方做了什么。

一个机位无法满足互相冲突的正脸、后脑、视线和遮挡时，必须拆镜。

# 7. DirectorSkills路由

## 7.1 先诊断，后调用

问题域包括：

- 故事结构
- 导演思想
- 镜头技巧
- 分镜设计
- 摄影灯光
- 调色
- 场景转场
- 声音设计
- AI执行与生成稳定性

## 7.2 少量组合

单场默认1个主导域、1至3个辅助域，必要时1个检查技能。

## 7.3 不能永久默认激活

跳轴、强手持、长焦幽闭、延迟揭示、意外揭示、戏剧反讽、二元转场、音乐强化、特写强化和复杂长镜头必须按需调用。

## 7.4 示例

| 问题 | 主导域 | 辅助域 |
|---|---|---|
| 对话只是念台词 | 导演思想 | 分镜、镜头 |
| 左右位置反复跳 | 分镜设计 | 摄影连续性 |
| 画面像游戏CG | 摄影灯光 | 调色、美术 |
| 转场很硬 | 场景转场 | 声音 |
| 压迫感不足 | 导演思想 | 构图、声音 |
| 肤色漂移 | 调色 | 摄影灯光 |
| 相机擅自降到人物高度 | AI执行 | 几何、白模、相机合同 |

# 8. 视觉资产与自动调用

## 8.1 资产类别

角色标准形象、服装、年龄与状态、伤势妆造、场景标准空间、时间天气灯光子状态、固定道具、组织标志、构图参考、白模、深度图、动作、运镜和声音参考。

## 8.2 唯一编号

```text
类别-项目-名称-用途或状态-vNN
```

资产编号投入使用后不因描述变化随意更名。

## 8.3 自动调用顺序

```text
角色与表演设定库
→ 视觉资产登记库
→ 场景与空间设定库
→ 连续性与当前生产状态
→ 主剧本与改编层
→ 本系统执行规则
```

## 8.4 参考职责

必须逐一声明身份、几何、动作、摄影机、风格和声音职责，禁止笼统写“参考这些图”。

# 9. AI图像与关键帧

## 9.1 产物分离

- 角色资产图优先身份和服装可读性。
- 场景资产图优先空间拓扑和材质。
- 分镜图优先站位、轴线和镜头功能。
- 成片关键帧优先光影、表演和电影质感。
- 深度图和白模只承担几何。

## 9.2 非破坏式工作流

```text
保留无损母版
→ 从母版或干净检查点建立分支
→ 同一区域相关修改尽量一次完成
→ 不同区域分别处理
→ 用蒙版把通过区域合回母版
→ 最终只做一次全局调色、锐化、颗粒和放大
```

不无限串联最新AI输出。

## 9.3 脏图重建

脏图作为结构参考，不再作为纹理母版。保留构图、几何、姿态、空间和桥路建筑布局，重建噪点、涂抹、蜡感、假纹理、色彩污染、锐化光晕和熔化材质。

# 10. 系统学习与写回

稳定通用规则写入本文件。项目事实按 `write_routes.yaml` 写入项目记忆、剧本、角色库、场景库、地图、资产库或连续性文件；学习证据写入反馈引擎。禁止把同一规则复制成多个激活版本。

学习对象至少包含：

```yaml
observed_evidence:
real_goal:
value_priority:
causal_graph:
primary_causes:
secondary_causes:
counterfactuals:
first_principle:
operational_rules:
triggers:
boundaries:
verification:
confidence:
maturity:
writeback_status:
```

## 10.1 Candidate 技能登记与晋级边界（2026-08-13）

`registration != promotion`。有证据、明确 scope、trigger、operational rule、failure boundary 和 targeted eval 接口的候选技能，可以按 `write_routes.yaml` 登记到本唯一主档；登记不把 `candidate` 晋级为 `scene_verified`、`project_verified` 或 `general_stable`，也不使其成为默认全局调用规则。学习证据、真实生成结果和 revision trace 继续保存在反馈引擎；后续真实生成、用户确认与跨场景证据按 `maturity_model.yaml` 决定 promotion。

若安全技术原因使唯一 target canonical 不能写入，必须登记 `pending_canonical_writes.yaml`，不得声称 fully integrated；只有目标文件回读、规则与既有内容完整性验证均通过后，才可关闭 pending item。

### SCREEN-EVIDENCE-001｜屏幕证据化提示词编译

- maturity：`candidate`；scope：关键空间、动作、尺度、高度、速度或危险性不能只由概念总结词承担的执行稿。
- trigger：提示词“很高、很快、很危险、数层高”等抽象词承担关键画面，或模型需要自行猜测高度、接触、路线和结果。
- operational rule：按 `VISIBLE FRAME → RELATIVE SPATIAL EVIDENCE → PHYSICAL ACTION CHAIN → ENVIRONMENT RESPONSE（按需）→ FINAL STATE` 把导演意图翻译为最小充分的可见楼层/窗户/地面高差/人物尺度、支点/接触点、重心/方向、位置变化和结果。图生视频或多模态参考已锁定主体、静态构图、材质、光线和背景时，文本优先补动作、时序、摄影机、接触关系、环境变化与最终状态，不重复静态像素。
- boundary / failure condition：不得把具体化变成逐帧、同义词、微动作或负面词堆砌；参考图未锁住的关键几何仍须补最小视觉锚点；模型版本变化或反例出现时转 `needs_revalidation`。
- verification：`REG-SCREEN-EVIDENCE-001`；以概念概括与最小充分屏幕证据化 A/B 比较可读性、接触物理、动作连续、空间稳定、意外脑补和过约束僵硬度。

### POSITIVE-SPEC-001｜正向动作规格与否定约束预算

- maturity：`candidate`；scope：Seedance 或同类 AI 视频执行稿中的动作、运动包络与约束编译。
- trigger：禁止项比正向动作更强或更长，模型为满足绝对否定而采用字面合规却违背导演意图的替代路线。
- operational rule：按 `SCREEN EVIDENCE → POSITIVE TARGET ACTION → ALLOWED MOTION ENVELOPE → HARD INVARIANTS → LOCAL EXCLUSIONS ONLY IF NECESSARY → FINAL STATE` 编译。HARD 只保护剧情因果、身份、canonical 拓扑、关键道具、reveal budget、锁定摄影机和最终状态；动作风格、速度、支点、腾跃范围和表演强度通常为 GUIDED；呼吸、衣摆、风尘、非关键群众与自然时长属于 FREE。少量 local exclusion 只排除明确 catastrophic error，不能误杀正确动作的必要中间态。
- boundary / failure condition：不是禁止所有否定词；平台独立 negative-prompt 通道、反复验证的严重错误、身份/拓扑/文字等硬交付可使用局部否定。若正向规格仍不能稳定路线，改用动作参考、白模或局部编辑，不继续堆叠自然语言否定。
- verification：`REG-POSITIVE-SPEC-001`；比较绝对否定、纯正向规格和正向规格加最少局部排除的动作可行性、替代行为、硬不变量与模型自主空间。

### EVENT-SEQUENCE-EXPLICIT-001｜关键事件顺序显式化

- maturity：`candidate`；scope：叙事因果依赖先后，而视频模型可能把连续动作错误并发化的镜头。
- trigger：一个主体先改变状态、另一主体随后利用该状态，且同时发生会改变施力者、被作用者或结果。
- operational rule：用“先 → 随后 → 已经……之后 → 再 → 直到 → 此时才”明确动作主语、施力者、被作用者、状态变化与结果；把关键顺序写入动作不变量和 final state。
- boundary / failure condition：显式因果顺序不等于逐秒 timecode；Seedance 默认自然分配时长，只有对白/口型同步、定点视频编辑、extension、明确节拍或必须锁定的因果时序才使用时间码。无因果依赖的自然并行动作不强行串行化。
- verification：对动作绑定错误或并发化风险，检查顺序、接触、状态变化和结果是否可读，且不因过控损害自然时长分配。

### ROLE-FUNCTION-COMPRESSION-001｜角色职能压缩介绍

- maturity：`candidate`；scope：角色首次进入新章节或公共空间，且必须在短时间建立身份、职责、性格、组织关系与现场运作。
- trigger：需要说明对白解释角色“是谁/负责什么”，或多主体现场信息密度高但人物职能不可读。
- operational rule：用一个短而因果清楚的事件，让动作服务同一角色/组织介绍目标：谁先发现、谁一线执行、谁协调/接管，以及群众或组织原本如何运作。角色职能通过行动、结果与组织分工可见，而非另起说明支线。
- boundary / failure condition：高信息密度不等于塞入无关事件；主语、因果和 subject-action binding 必须清楚，不能为介绍角色改写当前剧情事实或制造与本场无关的新支线。
- verification：检查观众能否仅凭事件读出职责分工、性格倾向和组织层级，同时主线、reveal budget 与动作绑定保持稳定。

### OPERATIONAL-PRESENCE-PRELOAD-001｜在场机制预载

- maturity：`candidate`；scope：后续角色或组织需要快速发现、到场、干预或响应事件的因果准备。
- trigger：后续快速响应若无前置正常工作状态，会显得角色或组织为剧情需要而瞬移出现。
- operational rule：在前面通过正常工作状态证明其本来就在相关区域、正在执行相关职责，并具备发现和处理条件；后续响应由这一已建立状态自然承接。
- boundary / failure condition：本规则是 CALC / CLCS 的快速响应专用补充，不建立第二套角色连续性系统；不得为预载而提前泄露不应揭示的信息，或把角色写成全知、最优和等待剧情。
- verification：执行 Camera-Off、Resumption 与 Background-Independence 检查；确认快速响应有前置因果，且不消费后续 reveal。

### MOTION-SIGNATURE-001｜人物运动性格指纹

- maturity：`candidate`；scope：具有相近移动能力的人物在追逐、攀爬、战斗或垂直空间移动中的角色化动作设计。
- trigger：不同人物共享相同动作模板，或仅靠形容词而非动作选择表达人物差异。
- operational rule：通过 rhythm、purpose、force、route choice、support usage、center of mass、hesitation、correction、landing/closure 与 camera response 选择建立差异；优先让路线、施力、重心、节奏和动作结果呈现人物，而非追加形容词。
- boundary / failure condition：运动签名不得覆盖身份、空间拓扑、动作不变量或当前镜头目的；人物可共享能力，但不能因此被强行写成相同的节奏、支点和收束方式。
- verification：比较角色间的路线、重心、节奏、支点和结果是否可区分；同时检查动作物理、空间连续与摄影机响应没有被人物化风格破坏。

### SHOT-SCOPE-001｜单镜头可观察域与跨镜头信息隔离

- maturity：`candidate`；scene observation：`scene_verified observation / E4`；scope：全局剧情规划与逐 shot AI 视频执行稿的编译边界。
- trigger：全局剧情摘要、后续镜头实体、尚未揭示的空间或仅为 VO 的说话者被混入当前 shot，造成提前 reveal、跨镜头实体污染、视点混乱或声音人物视觉泄漏。
- operational rule：全局计划只保留在内部层；最终执行稿按 `GLOBAL PLAN internal only → SHOT BOUNDARY → CAMERA STATE → VISIBLE SET → AUDIBLE SET → ACTION/CHANGE → IN-SHOT REVEAL → EXIT STATE → NEXT-SHOT CONTRACT` 编译。当前 shot 只写此刻摄影机实际可见的前景、中景、后景、主体、物体、动作和环境变化；VO 与镜外声进入 audible set，不使说话者自动成为画面实体；下一 shot 的继承信息写入 final state 或 next-shot contract。
- boundary / failure condition：不是只能描述第一帧。同一连续 shot 内摄影机真实移动后将 reveal 的区域或主体可按先后描述；反射、玻璃、开口中实际可见内容属于 visible set，镜外但可听声音属于 audible set；T2V 无参考图时可完整建立当前 shot 所需环境。不得把后续 POV / 建立镜头信息提前写入当前背景，也不得以全局叙事总结替代 shot-local 可观察描述；白模与因果连续分镜同样按 shot / action-state 隔离实体和几何。
- verification：`REG-SHOT-SCOPE-001`；比较错误实体注入、视点与摄影机一致性、提前揭示、shot boundary、动作绑定、画外音人物视觉泄漏、空间稳定与 prompt 复杂度。

### SEQUENCE-CONTEXT-001｜本段剧情语境与受限全段语义锚

- maturity：`candidate`；experiment status：`unvalidated`；scope：约 15–30 秒的多镜头剧情型 AI 视频段落，尤其是模型需要根据上下文自然补全动作、表情、视线、群众行为和环境反应时。
- purpose：逐 shot 执行稿之前可加入一个简短自然语言的【本段剧情语境】作为 segment-level semantic prior，让模型理解本段为何这样运作；它不是完整故事、导演内部分析或镜头流程摘要。
- operational rule：默认约 2–6 句，长度按信息密度而非固定字数决定。优先写本段持续成立的剧情状态、人物即时目标与动机、人物/组织的本段职能或关系、场景当前运作状态，以及会影响模型自然补全行为的局部社会活动。`state over event`：主要写“现在是什么状态、为什么这样行动”，不写“接下来镜头依次发生什么”。
- segment causal radius：若一条信息不能合理改变本段任何像素、声音、动作、表情、视线、注意力或环境行为选择，就删除。只保留会在本生成段内被表现、影响表演，或帮助模型补全合理但无需逐项指定的行为语境。
- entity granularity / embodiment gate：只在局部 shot 出现的人物，优先以角色职能或组织状态表达，非必要不提前点名全部具体人物。语境提到某人物、地点或组织不等于视觉授权；具体角色是否进入某个 shot，仍严格由 `SHOT-SCOPE-001` 的 camera state、visible set、audible set 与 in-shot reveal 决定；VO 说话者仍只属于 audible set，不能仅因语境被实体化。
- fact confidence gate：未经用户、剧本或 canonical 确认的具体动机不能因“合理”而写成已确认 Segment Fact；实验性动机只能保持 `GUIDED`，不得伪装为项目事实。若语境与具体 shot 描述冲突，以 canonical 事实和具体 shot 执行描述为准。
- boundary / failure condition：仍排除完整故事、未来剧情答案、本段不会出现也不会影响本段行为的实体/事件、镜头一→镜头二→镜头三流程摘要、后续 shot 的具体前中后景、观众应如何理解、导演内部因果分析和大量否定条款。本规则不恢复已撤销的“完整整体叙事总结发送 Seedance”。
- relation to SHOT-SCOPE-001：`SEQUENCE-CONTEXT` 负责“这段为什么这样运作、模型可以据此自然补什么”；`SHOT-SCOPE` 负责“这一镜此刻具体能看见和听见什么”。后者仍拥有局部视觉与声音执行权威。
- verification：`REG-SEQUENCE-CONTEXT-001`；A/B 或 A/B/C 比较整体叙事连贯、自然行为相关性、动机对齐、微表情、群众/环境语义适配，以及跨 shot 实体泄漏、提前揭示、VO 视觉泄漏、指令遵从、动作绑定和 prompt 复杂度。真实 Seedance 结果同时证明改善且未显著增加串台/漂移后，才可考虑晋级 `scene_verified`。

### SOAC-001｜Screen Observable & Audible Compiler

- maturity：`candidate`；scope：完整导演、剧情转镜头、AI 执行编译、可见/可听诊断、生成后反向验收或编译器回归任务。SOAC 是协调器 + 中间表示 + 编译器，不是第二套导演总纲。
- purpose：完整导演模式不得把“剧情 → 直接 Prompt”作为默认主链，而按 `Canonical Facts → WorldStateIR → Beat / EventGraphIR → BlockingIR → ShotPlanIR → VisibleIR + PerformanceIR + AudibleIR → Transition Contract → Constraint / Autonomy Contract → Model Adapter → Minimal Execution Prompt → Generated Output → Reverse Observation → Expected vs Observed Eval → Targeted Repair → Feedback / Learning` 分层编译。
- world truth vs shot observable truth：WorldStateIR 保存当前世界实际成立的时间、地点、场景运作、人物身份/位置/朝向/活动/目标/知识、关系、物体/道具、门窗道路楼梯高低、光源和声源；对象不在当前画面不等于从世界状态消失。每个 shot 的 VisibleIR / AudibleIR 只取当前 camera state 合法可见或可听、或在本 shot 内真实 reveal 的子集。
- core IR：EventGraphIR 明确 agent、action、target、instrument、support/contact、precondition、时序、state change、result、reaction trigger、reveal effect 与叙事功能；BlockingIR 先按人物目标、关系和空间因果确定站位、朝向、距离、路线、遮挡、权力中心和最终位置，再决定摄影机；ShotPlanIR 必须给出镜头功能、观众知识变化、entry/exit state 和 next-shot contract。无信息、关系、空间、情绪、节奏或状态改变功能的镜头进入必要性检查。
- screen observable / audible：VisibleIR 包含摄影机、前/中/后景、可见实体、几何、光线、材质、动作、接触和可见表演证据；PerformanceIR 将心理/潜台词编译为行为任务、身体选择与可见证据，不套用“悲伤=低头”等固定公式。AudibleIR 与 VisibleIR 平级，调用 `声音导演系统.md` 的唯一声音方法；进入 Audible Set 不等于获得 Visual Embodiment 权限，VO 说话者不会自动入画。
- continuity and autonomy：Transition Contract 把 Shot A exit state 显式解析到 Shot B entry state，并覆盖视线、动作、声音、reveal 与连续性。Constraint / Autonomy Contract 只以 HARD 保护 canonical 事实、身份、拓扑、关键揭示和 final state；其余模型空间按 GUIDED / FREE 分配。
- model-independent / minimal execution：SOAC 本体不写 Seedance、Veo、Runway 或未来模型的私有行为；模型版本与能力由 adapter 处理，变化时 adapter 进入 `needs_revalidation`。最终执行稿不输出完整 IR、内部分析或编译元数据，只经 relevance、能力、参考职责和约束预算筛选为当前镜头目的、Visible/Audible Set、主体动作、关键时序、摄影机、关键声音、HARD 不变量、自主权、final state 与极少灾难性禁止项。
- static and reverse checks：运行时 schema 以 ERROR/WARNING/INFO 检查未绑定行动者/台词说话者、VO 视觉泄漏、提前 reveal、不可能空间过渡、缺失起止状态、连续性断裂、抽象无证据、约束过载和参考冲突；严重 ERROR 未修复不得进入正式生成。Reverse Compiler 当前只是 candidate interface：允许人工/AI 辅助记录观察到的可见/可听/事件/摄影机/final state，并按身份、空间、动作、接触、表演、摄影机、声音、AV 同步、转场和 final state 对照预期合同；不声称已实现全自动视觉/音频验收。
- integration：显式调用 CALC/CLCS、SCREEN-EVIDENCE-001、POSITIVE-SPEC-001、EVENT-SEQUENCE-EXPLICIT-001、ROLE-FUNCTION-COMPRESSION-001、OPERATIONAL-PRESENCE-PRELOAD-001、MOTION-SIGNATURE-001、SHOT-SCOPE-001、SEQUENCE-CONTEXT-001、SoundDirectorIR、canonical 地图、场景资产身份 schema、资产登记与反馈引擎；SOAC 不复制或夺取它们的 authority。
- boundary / verification：完整字段、类型、静态检查与 adapter 接口唯一存于 `10_运行时/screen_observable_audible_ir_schema.yaml`。`REG-SOAC-001` 仅建立 KAIM-HIGH-SEARCH-30S 的受控测试规范；只有真实生成显示收益且未显著增加 scope leak 或 constraint overload，才可考虑晋级。

# 11. 默认完整输出

用户只发剧情并要求完整处理时，默认输出 `DIRECTOR-FULL-OUTPUT-001`：

1. 母本与连续性核对
2. 场景诊断
3. 导演意图
4. 人物目标和潜台词
5. 节拍
6. 表演
7. 场面调度
8. 镜头脚本
9. 摄影与灯光
10. 剪辑与声音
11. AI资产清单
12. 模型自主权合同
13. 视频模型执行稿
14. 验收清单
15. 结尾接口

# 12. Seedance 2.5 × Seedream 5.0 Pro完整内部模块

> 以下内容由原V2.1独立技能全文吸收而来，现为本系统内部执行细则。原独立文件不再作为规则入口。


## 0. 第一资料、读取范围与证据等级

### 0.1 第一资料

本版主要依据用户上传的登录后网页快照：

- 文档标题：《豆包 Seedance 2.5 & Seedream 5.0 Pro 升级介绍》
- 原始地址：`https://bytedance.larkoffice.com/docx/EvLJdw9n8oX1HExDfllcA22jnLe`
- 上传格式：MHTML
- 快照大小：约63 MB

### 0.2 从快照中直接读取到的内容

#### 目录结构

Seedance 2.5部分：

- 电商物料
- 科普教育内容
- 影视 / 游戏创作
- 趣味 / 创意短片
- 通用生成模版
  - 电商 / 产品广告
  - 产品 / 工业设计展示
  - 平面动态化（海报 / Logo）
  - 教育 / 科普内容
  - 时尚 / 服饰换装
  - IP / 趣味创意
- 影视感片段案例
- 更专业的创作
  - 使用创作 Skills
  - 多图参考
  - 动画渲染

Seedream 5.0 Pro部分：

- 核心更新与亮点
  - 多图融合编辑
  - 生产更落地
  - 效果更自然
  - 文生图人像真实感优化展示
  - 人像修图
  - P图效果优化展示
- 场景应用与玩法
  - 商业设计
  - 艺术创作
  - 娱乐玩法
- 提示词手册
  - 风格词
  - 美学词
- 使用技巧
  - 如何让输出更稳定
  - 能力边界与注意事项

#### 媒体数量

MHTML中可识别：

- 60个视频播放器；
- 50个15秒示例；
- 9个30秒示例；
- 1个8秒示例；
- 24个当前静态加载范围内的图片块。

#### 画幅分布

从60个视频封面尺寸统计：

- 竖屏：47
- 横屏：10
- 方形：3

这说明该官方介绍文档的案例选择明显偏向短视频、社交传播、电商和竖屏应用。它不代表Seedance 2.5只适合竖屏，也不代表电影项目应继承这一画幅偏好。

#### 可见提示词示例

快照中实际保留的文字示例包括：

- 达芬奇和梵高面向镜头比剪刀手，背景中米开朗基罗意外出现；
- 手持冰淇淋甜筒，背景是城市天际线和晴朗天空；
- 复古未来主义人像摄影，长发中年男人身穿酒红色长裙、戴墨镜、拿琴弓；
- 使用多个坐标点，把图一中的不同照片分别替换为图二至图五。

#### 风格词展示

当前快照可见：

- 过度曝光
- 浪漫主义风格
- 商业广告摄影
- 科幻风
- 原画厚涂
- UE5风格
- 柯达
- 黑白摄影
- 纪实摄影
- 写实主义
- 印象派风格
- 2D卡通
- 极简主义
- 数字艺术
- 漆画风格

### 0.3 证据等级

#### E1：文档直接证据

目录、文字、数量、时长、画幅、图片标题和坐标替换示例。

#### E2：媒体案例归纳

依据封面、时长和案例排列对生产思路进行归纳，但不冒充官方原文。

#### E3：项目工程化推导

将官方信息映射成《秽翼的尤斯蒂娅》的导演技能、资产管线和验收机制。

### 0.4 当前资料边界

飞书页面采用虚拟化渲染。MHTML没有静态保存每一节的完整正文，尤其缺失：

- Skills完整官方说明；
- 多图参考的全部文字；
- 动画渲染完整步骤；
- “如何让输出更稳定”的全部正文；
- “能力边界与注意事项”的全部正文。

这些缺失部分不得被假装成已读到的官方规则。本版对其只做有边界的项目推导。

---

## 1. 深度学习后的核心结论

### 1.1 Seedance 2.5不是一个统一的“电影提示词模型”

官方文档按任务域组织案例，而不是只给一份万能模板。由此确立：

> 提示词结构必须由任务域决定，而不是由用户会多少摄影术语决定。

项目新增六类任务域：

1. 影视剧情型；
2. 几何空间型；
3. 产品与材质型；
4. 平面、海报、Logo型；
5. 教育与科普型；
6. IP与创意反差型。

不同任务域使用不同字段、不同优先级、不同验收规则。

### 1.2 官方案例的共同核心不是“提示词长”，而是“主导规律清楚”

从可见示例和媒体封面可以归纳：

- 每个片…634 tokens truncated…+- 运镜参考；
- 音频参考；
- 点选对象；
- 蒙版；
- 坐标；
- 每份参考的唯一职责。

### 2.3 模型执行层

Seedance执行稿只保留：

- 当前画面真实可见内容；
- 主体；
- 动作；
- 摄影机；
- 声音；
- 时间顺序；
- 最终状态；
- 少量高价值禁止项。

核心公式：

```text
深导演分析
→ 资产与控制编译
→ 最小充分执行提示
```

---

## 3. 双模型导演管线

### 3.1 Seedream 5.0 Pro的项目职责

Seedream默认负责：

- 角色身份锚定；
- 角色正面、侧面、背面资产；
- 服装与道具；
- 场景空间；
- 建筑和环境资产；
- 构图首帧；
- 结束帧；
- 多图融合；
- 局部替换；
- 人像修复；
- 皮肤、布料、石材和旧化材质；
- 脏图结构重建；
- Seedance参考包。

### 3.2 Seedance 2.5的项目职责

Seedance默认负责：

- 连续动作；
- 人物表演；
- 身体重心；
- 多阶段动作；
- 摄影机移动；
- 时间推进；
- 对白；
- 口型；
- 环境声；
- 音效；
- 动作与声音同步；
- 延长；
- 局部视频编辑。

### 3.3 模型路由规则

#### 先用Seedream

当失败主要涉及：

- 脸不稳定；
- 服装不稳定；
- 场景布局不稳定；
- 构图错误；
- 关键帧画质差；
- 材质脏；
- 光线不统一；
- 道具形状错误。

#### 先用Seedance

当资产已经稳定，任务主要涉及：

- 动作；
- 表演；
- 运镜；
- 说话；
- 声音；
- 节奏；
- 连续变化。

#### 先做白模

当任务涉及：

- 多层空间；
- 桥上桥下；
- 多人走位；
- 复杂追逐；
- 精确顶视；
- 长镜头；
- 遮挡；
- 道具碰撞；
- 路径和机位必须精确。

---

## 4. 参考素材职责图

参考素材不采用一个全局模糊优先级，而采用分通道权威。

### 4.1 六个权威通道

#### 身份通道

负责：

- 脸；
- 发型；
- 年龄；
- 身材；
- 角色辨识。

权威来源：角色锚定图。

#### 几何通道

负责：

- 建筑；
- 道路；
- 桥；
- 门；
-楼梯；
- 高低关系；
- 房间布局。

权威来源：场景图、YAML、深度图、白模。

#### 动作通道

负责：

- 动作顺序；
- 身体重心；
- 速度；
- 力度；
- 接触关系。

权威来源：动作视频或白模。

#### 摄影机通道

负责：

- 机位；
- 焦段；
- 轨迹；
- 速度；
- 景别；
- 切镜。

权威来源：分镜、运镜参考、白模和摄影机锁定文本。

#### 风格通道

负责：

- 色彩；
- 光线；
- 材质；
-时代；
-摄影质感。

权威来源：风格图和项目质量母版。

#### 声音通道

负责：

- 对白；
- 音色；
- 停顿；
- 环境声；
- 音效；
- 音乐拍点。

权威来源：音频参考和声音设计稿。

### 4.2 通道冲突防火墙

生成前检查：

- 两张身份图是否是不同脸；
- 几何图与白模是否冲突；
- 动作视频是否带入错误摄影机；
- 运镜视频是否破坏人物动作；
- 风格图是否改变时代和服装；
- 音频是否超过动作可承载时长；
- 参考图中的无关人物是否可能被模型继承。

### 4.3 参考素材职责声明模板

```text
@图片1只负责凯姆的脸、发型和身份。
@图片2只负责凯姆的服装结构。
@图片3只负责当前场景的建筑与道路布局。
@图片4只负责材质、光线和色彩。
@视频1只负责人物动作、重心和节奏。
@视频2只负责摄影机轨迹。
@音频1只负责对白、停顿和语气。
@白模1只负责空间、站位、遮挡、角色路径和机位。
```

---

## 5. 模型自主权合同

Seedance会主动补镜头、补剧情、换景别和人物中心化。每个镜头必须给模型分配自主权。

### 5.1 自主权等级

#### LOCKED

不得变化。

适合：

- 角色身份；
- 桥梁和道路关系；
- 固定机位；
- 严格顶视；
- 文字与Logo；
- 关键道具；
- 最后一帧。

#### GUIDED

允许小范围优化，但不能改变目的。

适合：

- 微表情；
- 自然呼吸；
- 衣物轻微摆动；
- 环境小动作；
- 光线细节；
-背景生活感。

#### FREE

允许模型发挥。

适合：

- 不影响剧情的环境微细节；
- 无关群众的低显著度动作；
- 水汽、灰尘、布料次级运动；
- 不改变构图的材质细节。

### 5.2 五个自主权对象

每个镜头分别设置：

- camera_autonomy；
- actor_autonomy；
- environment_autonomy；
- edit_autonomy；
- sound_autonomy。

### 5.3 严格顶视示例

```yaml
autonomy:
  camera: locked
  actor: guided
  environment: guided
  edit: locked
  sound: guided
```

---

## 6. 任务域提示词编译器

### 6.1 影视剧情型

优先顺序：

1. 镜头目的；
2. 当前人物和空间；
3. 动作因果；
4. 反应；
5. 摄影机；
6. 声音；
7. 结束状态。

### 6.2 几何空间型

适用：

- 严格俯视；
- 正交视图；
- 建筑；
- 桥梁；
- 地图；
- 多层空间；
- 精确路径。

优先顺序：

1. 投影；
2. 摄影机自由度；
3. 空间拓扑；
4. 轨迹；
5. 不变量；
6. 材质和光线。

### 6.3 产品和材质型

优先顺序：

1. 产品身份；
2. 产品不变形结构；
3. 材料反馈；
4. 主导变化律；
5. 光线；
6. 摄影机；
7. 品牌信息。

### 6.4 平面、海报和Logo型

优先顺序：

1. 文字和Logo锁定；
2. 版式锁定；
3. 可运动图层；
4. 前后层级；
5. 转场；
6. 结束版式。

### 6.5 教育和科普型

优先顺序：

1. 事实关系；
2. 过程；
3. 变化顺序；
4. 标签与图形；
5. 摄影机；
6. 美学。

### 6.6 IP和创意反差型

优先顺序：

1. 一个清楚反差；
2. 主体；
3. 主动作；
4. 背景第二事件；
5. 揭示时机；
6. 结束笑点或视觉结果。

---

## 7. 风格词向量化与冲突检查

官方风格词案例来自不同维度，不能无差别堆叠。

### 7.1 四个风格维度

#### 介质与制作方式

- 商业广告摄影；
- 纪实摄影；
- 数字艺术；
- 原画厚涂；
- 2D卡通；
- 漆画。

#### 艺术运动或审美方向

- 浪漫主义；
- 写实主义；
- 印象派；
- 极简主义；
- 科幻风。

#### 成像或胶片处理

- 柯达；
- 黑白摄影；
- 过度曝光。

#### 渲染技术审美

- UE5风格。

### 7.2 风格选择规则

每次最多选择：

- 1个主介质；
- 0至1个艺术方向；
- 0至1个成像处理；
- 0至1个技术审美。

若项目要求真人电影实拍：

- 主介质：真人电影摄影；
- 艺术方向：写实主义或克制的浪漫主义；
- 成像处理：项目胶片和调色规则；
- 技术审美：禁止UE5和游戏CG。

### 7.3 冲突示例

不建议：

```text
纪实摄影 + 商业广告摄影 + 原画厚涂 + UE5 + 2D卡通 + 黑白 + 高饱和
```

因为它们争夺不同视觉介质。

---

## 8. 15秒和30秒事件调度器

### 8.1 4至6秒

用于：

- 摄影机测试；
- 单动作测试；
- 顶视锁定；
- 角色一致性测试；
- 白模映射测试；
- 局部修改验证。

### 8.2 8至15秒

用于：

- 一个完整动作链；
- 一个问答；
- 一个表演转折；
- 一个空间移动；
- 一个认知揭示；
- 一个完整短镜头。

### 8.3 20至30秒

必须满足：

- 角色和场景资产稳定；
- 事件有清楚阶段；
- 时间码分段；
- 镜头或动作转换有原因；
- 结尾状态稳定；
- 没有为了填充时长而增加动作。

### 8.4 多轨时长估算

单节拍时长：

```text
max（对白轨、主体动作轨、摄影机轨）
+ 必要反应停顿
```

整段时长由不可并行节拍相加。

---

## 9. 多图对象绑定协议

官方文档中的坐标替换示例被升级为项目规则。

### 9.1 绑定表达式

```text
来源资产
→ 目标对象
→ 目标区域
→ 修改内容
→ 保留内容
```

### 9.2 可用目标定位

- 点选；
- 框选；
- 蒙版；
- 坐标；
- 对象ID；
- 区域名称。

### 9.3 示例

```text
在图一坐标区域<point>518 135</point>，
只替换墙上第一幅照片为图二；
保留墙面、相框、光线、透视和其他照片不变。
```

### 9.4 多图编辑验收

- 目标是否替换正确；
- 非目标区域是否改变；
- 光线是否一致；
- 焦距是否一致；
- 接触阴影是否存在；
- 边缘是否有接缝；
- 人物比例是否漂移；
- 材质尺度是否统一。

---

## 10. 纯顶视和特殊机位技能

### 10.1 本质

严格顶视属于几何空间镜头，不属于人物表演镜头。

### 10.2 制作顺序

```text
Seedream干净顶视场景
→ YAML空间母版
→ 深度图或白模
→ 4至6秒无人物相机测试
→ 锁定摄影机
→ 加入顶视小人物
→ 人物近景另做镜头
```

### 10.3 必须锁定

- projection；
- camera height；
- pitch；
- yaw；
- roll；
- focal length；
- zoom；
- cut；
- reframe；
- horizon；
- XY轨迹。

### 10.4 禁止歧义

避免：

- 向前推进；
- 沿街推进；
- 飞入城市；
- 穿过桥下；
- 跟随角色。

使用：

- 世界坐标XY平面平移；
- 光轴始终沿负Z轴；
- 固定高度；
- 固定焦距；
- 正射测绘式平移。

---

## 11. Seedream资产编译器

### 11.1 高风险镜头参考包

建议准备：

- 人物身份图；
- 服装图；
- 场景图；
- 道具图；
- 首帧；
- 尾帧；
- 光线参考；
- 白模；
- 动作参考；
- 运镜参考；
- 音频。

### 11.2 资产母版规则

- 原始无损母版永久保留；
- 局部修改分支处理；
- 不连续套娃使用最新AI输出；
- 每轮生成后检查脏化；
- 通过蒙版合回母版；
- 全局调色、锐化、颗粒只在最后统一做一次。

### 11.3 人像自然感

结合文档“效果更自然”和“文生图人像真实感优化展示”的方向，项目继续执行：

- 真实皮肤微结构；
- 自然肤色变化；
- 法令纹和轻微瑕疵；
- 真实头发纤维；
- 服装与身体真实接触；
- 光线与环境一致；
- 禁止蜡像、塑料皮肤和游戏角色感。

这是项目工程规则，不冒充缺失章节的官方逐字说明。

---

## 12. Seedance执行提示词标准

```text
【任务】
画幅：
时长：
单镜头 / 多镜头：
允许切镜：是 / 否。

【镜头目的】
观众在这一镜必须看见、感受到或理解：

【主导变化律】
本镜只围绕：

【本段剧情语境】（可选；仅在多镜头剧情段需要时使用。自然语言短段，不输出内部编译器标签。）

【参考职责】
@图片1：
@图片2：
@视频1：
@音频1：
@白模1：

【不变量】
角色身份：
场景结构：
服装：
道具：
摄影机：
最后状态：

【模型自主权】
摄影机：
人物：
环境：
剪辑：
声音：

[00:00–00:__]
当前景别和机位：
当前可见人物与背景（仅写当前 camera state 实际可见，或本 shot 内由摄影机真实 reveal 的内容；后续 shot 信息写入段末状态或 next-shot contract）：
动作：
反应：
声音（可听但不可见的 VO / 镜外声进入 audible set，不能使说话者自动成为画面实体）：
段末状态 / next-shot contract：

[__–__]
……

【最后一帧】
人物位置：
身体朝向：
视线：
道具：
摄影机：
环境：

【必要禁止项】
只写会导致严重失败的少量禁止项。
```

---

## 13. 失败诊断矩阵

### 13.1 摄影机擅自下降或切换

可能原因：

- 摄影机自主权未锁；
- 使用“跟随”“推进”等歧义词；
- 人物表演需求与特殊机位冲突；
- 没有运镜参考或白模。

修复：

- 只编辑摄影机；
- 锁定六自由度；
- 人物降级为空间调度元素；
- 先做无人物测试。

### 13.2 人物变脸

可能原因：

- 多张身份图冲突；
- 镜头过长；
- 角度变化过大；
- 动作和表情负荷过高；
- 角色在画面中过小或遮挡太久。

修复：

- 只保留一张身份权威图；
- 增加侧面或背面锚定图；
- 拆段；
- 先用Seedream修首尾帧。

### 13.3 场景搬家或桥路关系改变

可能原因：

- 只靠文字描述复杂空间；
- 微观构图文字太多；
- 没有白模；
- 多张场景图不一致；
- 摄影机运动与空间轴线冲突。

修复：

- YAML和白模作为几何权威；
- 文字仅保留关键锚点；
- 固定当前画面可见域。

### 13.4 动作绑定错误

可能原因：

- 多人物没有位置标签；
- 动作主语模糊；
- 同一时间发生太多动作；
- 动作参考和文字冲突。

修复：

- 每个动作明确绑定人物；
- 使用左、右、前、后、站、坐；
- 分解为先、随后、同时、直到；
- 减少并发动作。

### 13.5 提示词越写越不听话

可能原因：

- 风格词冲突；
- 禁止项过多；
- 导演分析泄漏到执行层；
- 参考图已表达的信息重复；
- 多个主导变化律竞争。

修复：

- 重建最小充分提示；
- 只保留一个主导变化律；
- 减少负面词；
- 把几何交给图、白模和YAML。

### 13.6 图像或视频越来越脏

可能原因：

- AI输出连续套娃；
- 高频纹理累计；
- 多次全图重绘；
- 锐化和颗粒重复叠加。

修复：

- 回到干净母版；
- 分区重建；
- 蒙版合成；
- 最后统一调色。

---

## 14. 生成前单元测试

高风险镜头生成正式版本前，先做小测试。

### 14.1 摄影机单测

- 4至6秒；
- 无人物；
- 只测轨迹和机位。

### 14.2 人物身份单测

- 固定镜头；
- 简单动作；
- 测脸、发型和服装。

### 14.3 动作单测

- 简化背景；
- 只测动作重心和物理结果。

### 14.4 场景单测

- 无人物；
- 测几何、遮挡和光线。

### 14.5 声音单测

- 简单画面；
- 测对白、停顿、口型和音色。

---

## 15. 验收不变量

每个镜头至少建立以下不变量：

### 摄影机不变量

- 机位；
- 轴线；
-焦距；
-运动方向；
-允许的切镜。

### 身份不变量

- 脸；
- 发型；
- 服装；
- 年龄；
- 身材。

### 空间不变量

- 门；
- 桥；
- 道路；
- 楼梯；
- 高低层；
- 地标。

### 动作不变量

- 动作顺序；
- 施力者；
- 被作用者；
- 结果；
- 道具归属。

### 声音不变量

- 台词；
- 音色；
- 节奏；
- 环境声；
- 音乐连续性。

---

## 16. DirectorSkills新增注册

### S25-01 任务域路由

判断影视、几何、产品、平面、科普或IP任务。

### S25-02 主导变化律

为每个生成单元只确定一个主要视觉或叙事变化。

### S25-03 三层提示编译

导演母版、资产控制、模型执行分离。

### S25-04 参考职责图

建立身份、几何、动作、摄影机、风格和声音通道。

### S25-05 自主权合同

为摄影机、人物、环境、剪辑和声音分配LOCKED、GUIDED或FREE。

### S25-06 社交画幅偏差过滤

避免把官方竖屏案例偏好误当成电影项目默认画幅。

### S25-07 风格词冲突检查

把风格词按介质、艺术方向、成像处理和渲染技术分类。

### S25-08 Seedream资产编译

生产角色、场景、首尾帧、道具和修复资产。

### S25-09 Seedance时间渲染

编排动作、摄影机、声音和时间线。

### S25-10 多图目标绑定

使用点选、框选、蒙版、坐标和对象ID。

### S25-11 特殊机位锁定

处理纯顶视、正交、固定机位和几何摄影。

### S25-12 局部失败定位

定位摄影机、身份、动作、场景、声音或材质失败，优先局部编辑。

### S25-13 证据边界守卫

区分官方原文、媒体归纳和项目推导，禁止伪造缺失章节。

### S25-14 至 S25-23 Candidate 调用入口

- `S25-14 / SCREEN-EVIDENCE-001`：当 `SCREEN_EVIDENCE_GAP` 命中时，用最小充分屏幕证据编译关键画面。
- `S25-15 / POSITIVE-SPEC-001`：当 `NEGATIVE_CONSTRAINT_OVERLOAD` 命中时，优先正向动作规格与受控约束预算。
- `S25-16 / EVENT-SEQUENCE-EXPLICIT-001`：关键因果动作可能被并发化时，显式编译状态变化和先后关系。
- `S25-17 / ROLE-FUNCTION-COMPRESSION-001`：新章节角色/组织需要高密度但清楚地进入观众认知时调用。
- `S25-18 / OPERATIONAL-PRESENCE-PRELOAD-001`：后续快速响应需要前置在场因果时调用，并与 CALC / CLCS 联动。
- `S25-19 / MOTION-SIGNATURE-001`：相近能力人物需要通过运动选择而非形容词区分时调用。
- `S25-20 / SHOT-SCOPE-001`：当 `SHOT_SCOPE_LEAK` 命中时，将全局计划与逐 shot 执行稿分层，只编译当前 camera state 的 visible / audible set、合法 in-shot reveal 与 next-shot contract。
- `S25-21 / SEQUENCE-CONTEXT-001`：当 `SEQUENCE_CONTEXT_UNDERCONDITIONED` 命中、且任务是约 15–30 秒的多镜头剧情段时，可在逐 shot 块前编译受限本段剧情语境；不以此授权任何实体越过 `SHOT-SCOPE-001` 进入当前 visible set。
- `S25-22 / SOAC-001`：完整导演、剧情转镜头、可见/可听诊断、AI 执行编译或反向验收需要从 canonical facts 形成可检查的世界、事件、调度、镜头、Visible/Audible 与 transition 合同时调用；先读 runtime schema，再按需定向调用既有技能。
- `S25-23 / CINEMATIC-VISUAL-GRAMMAR-001`：当 `CINEMATIC_VISUAL_GRAMMAR` 命中时，在 Blocking 成立后用 CinematicIntentIR 处理观看立场、关系压力、注意流、综合色来源、视觉密度、成像动机、参考信号职责和反套路检查；只把当前生成单位会改变像素、声音、摄影机、剪辑或参考控制的字段下发。

以上均为 `candidate`，按需定向调用，不因登记成为默认全局激活项。

---

## 17. 与既有导演技能联动

本技能不替换，而是挂接：

- 镜头目的先行；
- 观众认知时差与延迟揭示；
- 反应—视线—目标分离；
- 空间拓扑先行；
- 镜头可见域隔离；
- 长距离叙事预载；
- 结构优先的可变时长事件包；
- 15秒节拍预算；
- 声音可观察化；
- 低显著度长段配乐；
- 非破坏式资产编辑；
- 脏图结构重建；
- 反馈反推与系统反哺。

调用原则：

> 每次先诊断，再选择1个主技能、1至3个辅助技能和最多1个检查技能，不无差别堆叠全部规则。

---

## 18. 项目默认自动执行

以后用户只提供剧情、对白、图片或镜头目标时，助手先按 `PROJECT_INDEX.yaml` 和 `read_sets.yaml` 做最小必要读取，再自动：

1. 扫描前后剧情；
2. 判断任务域；
3. 确定镜头目的；
4. 确定主导变化律；
5. 设计观众认知；
6. 建立空间拓扑和调度；
7. 分配模型自主权；
8. 判断Seedream、Seedance或白模先行；
9. 建立参考职责图；
10. 选择自然事件时长；
11. 生成最小充分执行提示；
12. 指定最后一帧；
13. 列出验收不变量；
14. 失败时优先局部编辑；
15. 把实测结果反哺技能。

---

## 19. 一句话总纲

> 导演系统决定意义、空间、节奏和不可改变的事；Seedream把它们凝固成可靠资产与关键帧；Seedance把它们展开成动作、摄影机、声音和时间。模型可以发挥细节，但不能替导演改写镜头目的。


# 13. 废弃与替代

以下独立长期入口废弃，明确不得作为活动规则源：

- 所有 `AI电影化系统总纲_v*.md` 均已废弃，不得作为活动规则源
- `秽翼_AI动画_Seedance2.5导演技能_V1.md`
- `秽翼_AI动画_Seedance2.5_Seedream5.0Pro_导演技能_V2.md`
- `秽翼_AI动画_Seedance2.5_Seedream5.0Pro_导演技能_V2.1_正式融合版.md`
- `电影导演分镜技能资料库_v1.md`
- `电影导演分镜技能资料库_v1.txt`
- 独立AI视频注册表和长期记忆摘要

原始官方MHTML、证据审计和研究来源可以只读保留。

# 14. 内部变更日志

## 2026-08-01

- 固定基线v1.8.9和固定文件名。
- 完整吸收Seedance 2.5 × Seedream 5.0 Pro V2.1。
- 深度吸收电影导演分镜技能资料库。
- 建立单文件AI视频规则、任务域路由、六通道权威、自主权合同、单元测试、失败诊断和不变量验收。
- 废弃旧系统版本、独立技能和补丁链。


## 2026-08-03｜简化命名与用户意图接口

- 主文件改名为“AI电影系统”。
- 历史上曾固定读取外部记忆系统中的用户意图与创作习惯；现已由本文件开头的 GitHub-first reconcile 取代。
- 历史上曾建立反馈引擎到外部记忆系统的写回链路；现已由 `write_routes.yaml` 的唯一 GitHub 写回路由取代。
- 继续采用单一文件、原地维护，不建立版本副本。

# 15. GitHub-first 运行时兼容补充（2026-08-12）

本节不替代前述完整源规则，只为当前 GitHub runtime、回归与最小读取提供可检索术语。CALC（Character Autonomous Life Continuity）与 CLCS（Character Life Continuity Scan）落实本文件既有的“人物目标、社会角色、职业、利益、知识边界、行动预备、后果与反应”原则：角色在镜头外也有合理的既有行动，不得为了方便剧情而全知、最优或机械一致。导演任务须可通过 Camera-Off、Swap、Omniscience、Optimizer、Resumption 与 Background-Independence 检查。

时间码（timecode）是按需控制工具：总时长、镜头边界、事件顺序和最后状态可以指定；当 Seedance 擅长自动分配镜头时长时，默认由模型自然安排各镜头时长，不为每镜硬写秒数。只有对白/口型同步、定点视频编辑、延长接口、明确节拍控制或因果时序必须锁定时，才使用明确时间码。

严格顶视、正交或固定几何镜头应锁定 six degrees of freedom：camera height、pitch、yaw、roll、focal length、zoom，以及 cut/reframe 和 XY 轨迹；这只是本文件“纯顶视和特殊机位技能”中既有锁定项的 runtime 术语。

# 16. Cinematic Visual Grammar｜CINEMATIC-VISUAL-GRAMMAR-001

状态：`candidate`。本章把外部 Cinema DNA 研究、专业导演/摄影/剪辑知识与项目现有 SOAC、最小充分提示、多模态职责分离做机制级融合。它是本文件内部的候选导演知识域，不是第二套导演系统，不改变剧情、角色、地图、资产、连续性或模型 adapter authority。

运行接口：`Director Feature Compiler → CINEMATIC_VISUAL_GRAMMAR hard route → CinematicIntentIR → ShotPlanIR → VisibleIR / PerformanceIR / AudibleIR → TransitionContract → Model Adapter → Eval → Learning`。

## 16.1 CinematicIntentIR：Blocking之后、ShotPlan之前

剧情事实、人物目标、EventGraph 与 Blocking 先成立，再回答“为什么摄影机这样看”。`CinematicIntentIR` 只保存会影响画面、剪辑、光色或参考控制的视觉导演意图：

- `unresolved_state`：人物/关系/事件当前尚未解决、但画面需要承载的问题；不能用“忧郁、神秘、高级”替代剧情状态。
- `viewer_position`：观众被放在事件内部、外部、错误一侧、被观察位置或其他明确观看关系中的原因。
- `relation_pressure`：人物目标、权力、信息差和空间限制怎样转成二维画面压力。
- `attention_flow`：关键镜头的注意入口、阻挡/加速、决定性信息落点、被延迟的信息与余韵出口。
- `composition`：主要构图机制与摄影机为何在此处；构图不能为了漂亮改写 Blocking 或空间拓扑。
- `color_intent`：综合色命题、物理颜色来源、实际光源与强调色职责。
- `capture_intent`：焦段、光学限制与可选成像介质的叙事/感知理由。
- `visual_density`：主线索、副线索、允许普通/暗/软/遮挡的区域以及细节、高光、微反差预算。
- `reference_signal_roles`：身份、几何、动作、摄影机、风格、声音各参考的 authority，以及应压低的非职责信号。
- `anti_template_signature`：最近镜头是否无理由重复相同机位、构图压力或注意流。
- `attention_handoff`：切镜前注意点、切点事件、下一镜目标、暂时隐藏的信息与回切揭示。

`CinematicIntentIR` 的 runtime schema 以 `10_运行时/screen_observable_audible_ir_schema.yaml` 为字段与静态检查接口；本文件仍是导演方法 authority。

## 16.2 UNRESOLVED-STATE-VISUALIZATION-001｜未解决状态先于视觉装饰

- maturity：`candidate`。
- trigger：镜头只有姿态、情绪或“高级感”，人物没有正在处理的问题，或画面像摆拍/壁纸。
- operational rule：先明确人物或关系当前不能立刻解决的状态，以及这一状态必须通过什么行动、空间、物件或等待被看见，再讨论构图与质感。
- boundary：功能性建立镜头、转场、节奏停顿不必强行制造悬念；“未解决”不是每镜都塞反转。
- failure condition：为了避免平淡而人为添加与剧情无关的秘密、危机或不可逆事件。
- eval：`REG-CINEMATIC-PRESSURE-001` 与跨场景导演必要性检查。

## 16.3 RELATION-PRESSURE-COMPOSITION-001｜关系压力产生构图

- maturity：`candidate`。
- trigger：构图漂亮但没叙事理由、人物像摆拍、摄影机位置与人物目标/权力/空间无关。
- operational rule：顺序固定为 `人物目标与观众信息 → Blocking/空间压力 → viewer position → 一个主要构图机制 → 焦段/高度/遮挡`。低机位、门框、负空间、对称、俯拍、长焦压缩都只是可能结果，不是默认模板。
- boundary：形式主义、对称、重复构图可以在主题、仪式、节奏或视觉母题有明确理由时主动使用。
- failure condition：为了“关系压力”硬改 canonical 方位、人物路径或让摄影机占据不可能的实体位置。
- eval：`REG-CINEMATIC-PRESSURE-001`。

## 16.4 ATTENTIONAL-FLOW-001｜关键镜头注意流与跨切镜交接

- maturity：`candidate`。
- terminology boundary：`attention flow / 视线流量` 是本项目工程字段，不冒充行业固定术语；其机制参考电影眼动、连续性剪辑与注意研究。
- trigger：关键揭示、遮挡、误导、absence reveal、镜外行动、回原机位找人/找物、多个同等显著元素抢注意。
- operational rule：按需记录 `entry ROI → modulator/occluder → decisive ROI → withheld/peripheral information → exit ROI`；跨切镜再记录 `from ROI → cut event → to ROI → withheld action → reveal on return`。
- boundary：普通动作镜头不需要把每个观看点都硬编码；注意设计不能把摄影机退化为仅为“让模型看清全部动作”的 coverage。
- failure condition：为了制造注意流强迫无意义前景遮挡、过度 rack focus 或让观众错过理解当前因果所需的信息。
- eval：`REG-ATTENTION-FLOW-001`。

## 16.5 COLOR-THESIS-001｜色彩命题必须落到物理来源

- maturity：`candidate`。
- trigger：综合色像廉价滤镜、所有物体被统一染色、冷暖关系没有布景/服装/天气/材质/光源支撑。
- operational rule：先写一句综合色叙事命题，再把主色、过渡色、强调色分别绑定到场景材料、服装、天气、自然光、practical light、反射或明确后期 look 职责；强调色服务信息层级而非装饰。
- boundary：不禁止后期调色；要求的是目的与来源可解释，不要求所有颜色都必须是现场原始光谱。
- failure condition：为了“物理来源”牺牲项目既有色彩连续性或把每个物件都染成说明色。
- eval：`REG-COLOR-THESIS-001`。

## 16.6 VISUAL-DENSITY-BUDGET-001｜视觉信息与纹理密度预算

- maturity：`candidate`。
- trigger：画面脏、所有区域同时高锐/高细节/高微反差/高亮、背景和主信息抢戏、AI伪纹理显著。
- operational rule：重要镜头至少明确一个 primary story clue 和可选 secondary clue；非关键区域允许普通、暗、软、遮挡、失焦或较低细节。细节、反射、高光、颗粒、雾、粒子、锐度都属于有限预算。
- boundary：群像、production design、史诗建立镜头可以信息丰富，但仍必须有层级；不机械限制物件数量。
- failure condition：把“少细节”误解成低清、涂抹、过度虚化或让空间证据消失。
- eval：`REG-VISUAL-DENSITY-001`。

## 16.7 MOTIVATED-CAPTURE-SUBSTRATE-001｜成像介质按动机调用

- maturity：`candidate`。
- trigger：35mm/16mm/MiniDV/监控/鱼眼/旧广播转拍等被当成通用电影感 token，而不是剧情、角色感知或生产需要。
- operational rule：只有成像介质会改变观众如何理解时间、信息来源、主观经验、媒介内嵌或摄影限制时提高其权重；否则优先描述真正需要的光学、曝光、动态范围、焦段和质感结果。
- boundary：摄影师可基于审美选择 capture substrate；规则只反对无理由模板化，不把“叙事理由”变成唯一合法理由。
- failure condition：为证明动机而给普通镜头强行附会“记忆/纪录片/监控”语义。
- eval：`REG-CAPTURE-SUBSTRATE-001`。

## 16.8 ANTI-TEMPLATE-COMPOSITION-001｜防套路但允许有意重复

- maturity：`candidate`。
- trigger：不同剧情反复出现同一背影、中心透视、门框、极端俯拍、眼部特写、同一注意流，且没有新信息或主题理由。
- operational rule：比较最近镜头的 camera position、composition pressure、attention flow、shot function；若高度重复，必须给出 `new information / escalation / contrast / temporal change / motif payoff / continuity need` 中至少一个理由，否则进入 necessity review。
- boundary：不为了“创新”破坏轴线、连续性、角色空间或已经建立的视觉母题。
- failure condition：系统随机换角度只为避免重复，结果摄影机失去剧情理由。
- eval：`REG-ANTI-TEMPLATE-001`。

## 16.9 REFERENCE-SIGNAL-DECOUPLING-002｜参考职责不仅写在文字里，也要降低非职责强信号

- maturity：`candidate`；Seedance/C-DANCE 具体表现属于 model/version-bound，需要持续 revalidation。
- trigger：动作/几何/摄影参考带有强烈错误纹理、材质、色彩、光线或角色身份，导致模型在完成主要参考职责时同时继承不需要的外观信号。
- operational rule：继续使用现有身份/几何/动作/摄影机/风格/声音六通道 authority；在平台允许时，让参考本体本身也尽量职责纯化。动作/几何 reference 可优先 clean previs / clay / white model：保留姿态、接触、路径、摄影机与可读明暗，降低非职责高频纹理和材质。风格/身份 reference 则保留其真正需要的高质量像素。
- positive rule：不是“所有参考都白模化”，而是 `authoritative signal high, non-authoritative signal low`。
- boundary：正式身份、服装、材质、场景质感和风格任务不能因为去污染而丢失必要像素；参考图禁止输入不是本项目规则。
- failure condition：白模过度扁平导致动作体积、接触、方向或明暗可读性下降；或为了纯化动作参考而改变原本要测试的摄影机/几何变量。
- eval：`REG-REFERENCE-DECOUPLING-001`。当前凯姆市集滑绳的高纹理动作参考 vs clean white-model 是天然 candidate A/B；未完成 B 的真实目标模型生成前不得晋级。

## 16.10 部门 Overlay 与信息传递

本系统不建立八套独立数据库。一次导演任务内部按职责形成结构化 packet，并通过 SOAC/TransitionContract 传递：

```text
Story / Director
→ Character / Performance
→ Space / Blocking
→ Cinematography / CinematicIntentIR
→ Lighting / Art / Look
→ Editorial / Attention Handoff
→ Sound / AudibleIR
→ Model Adapter / Minimal Execution Prompt
```

交接原则：

1. 下游只能补充职责内信息，不能静默覆盖上游 canonical。
2. Story packet 给 dramatic function、audience knowledge、unresolved state；Performance 给 action task/subtext/body choice；Blocking 给 path/orientation/contact/occlusion；Cinematography 给 viewer position/attention/composition/camera reason；Look 给 color/light/material hierarchy；Editorial 给 cut reason/attention handoff/state transition；Sound 给 diegesis/foley/ambience/dialogue priority；Model Adapter 只做当前模型能力映射。
3. 参考图、视频、音频与媒体本体继续由现有资产/Library policy 管理；GitHub 保存职责、身份、版本、关系、状态、时间证据与 eval，不建立第二份二进制媒体库。
4. 最终模型执行稿仍遵守“最小充分信息”：内部 CinematicIntent 可以复杂，只有当前生成单位真正改变像素、声音、摄影机、剪辑或参考职责的字段才下发。

## 16.11 Film-grade Eval 接口

视觉 Grammar 不用单一“电影感分数”验收，也不采用外部 Skill 的固定 82 分门槛。按需拆分：

- instruction following / key reveal
- shot scale / angle / camera position / lens intent / camera movement
- composition and relation pressure
- attention flow / attention handoff
- character action / expression / gaze / blocking
- temporal / spatial / identity / prop continuity
- color source / lighting / material hierarchy
- visual density / microcontrast / false texture / highlight competition
- reference fidelity and cross-channel contamination
- dynamic aesthetics / physical plausibility
- dialogue / sound source / AV sync / ambience / silence

`screen_observable_audible_ir_schema.yaml` 的 ReverseObservation / ExpectedVsObservedEval 为机器接口；自动 film-operator 工具当前只作为未来 PoC，不是生产硬依赖。

## 16.12 证据、成熟度与禁止项

- 外部 Cinema DNA、AFI/DGA/ASC、OpenUSD/OTIO/ACES、Seedance 官方、论文和 benchmark 只提供 candidate 证据与接口设计，不自动晋级。
- 证据索引：`09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md`。
- targeted regression：`11_验收/cinematic_visual_grammar_regression_cases.yaml`。
- 真实生成按 `candidate → scene_verified → project_verified → general_stable` 晋级；一次成功不能通用化。
- 不复制 Cinema DNA SKILL 正文，不建立 `CinemaDNA系统.md` 或“高级电影感系统.md”。
- 不默认 21:9×3，不禁止参考图输入，不把导演/摄影师/影片名字作为魔法词，不用审美 warning 覆盖剧情、身份、空间与关键因果。
- 新视觉技能与既有 `SCREEN-EVIDENCE-001`、`POSITIVE-SPEC-001`、`SHOT-SCOPE-001`、`SOAC-001` 冲突时，按 Learning Application Gate 做 scope/context/evidence/maturity 裁决，不静默覆盖。
