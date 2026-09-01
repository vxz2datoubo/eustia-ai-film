---
title: AI电影生产认知与迭代优化证据
status: candidate_evidence_only
canonical_role: production_cognition_iteration_research_annex
source_issue: 59
last_updated: 2026-08-31
---

# AI电影生产认知与迭代优化证据

> 本文件补充 Production Intelligence Capability Atlas 的两个高价值但不同于导演技巧的领域：**隐性专业判断如何被提取**，以及**跨部门迭代/返工/验证周期如何被组织**。它只承担证据与候选转译，不是用户偏好 authority，不是第二套 Learning Gate，不是项目管理真相源。

## 1. 为什么 K2“我知道但没说”不能只靠模型猜

用户可能能稳定识别“高级/低级”“自然/假”“像角色/不像角色”，但在当下未必能完整解释判断线索。直接把模型推断写成“用户偏好”会产生两个问题：

1. 把一次性情境误学成稳定价值；
2. 只学表面结果词，没学到导致判断的 cue、expectation、tradeoff 和 exception。

因此 K2 应有专门的 **Tacit Knowledge Elicitation** 路径：从真实决策与对比中提取结构化判断，但始终保留 `inferred` 身份，直到用户确认或多次跨场景验证。

## 2. Cognitive Task Analysis / ACTA

### E-PICG-ACTA-001｜Applied Cognitive Task Analysis（T2）

来源：Militello & Hutton, Ergonomics 41(11), 1998, DOI 10.1080/001401398186108。
- https://pubmed.ncbi.nlm.nih.gov/9819578/

来源支持：CTA 用于识别熟练任务所需的认知技能/心理需求；ACTA 提供三种更易落地的方法：
1. `Task Diagram Interview`：先找任务中认知要求最高的部分；
2. `Knowledge Audit`：系统追问 cue、策略、异常、典型性、预测等专业知识；
3. `Task Simulation Interview`：在具体情境里追踪专家如何判断、预期和行动。

项目转译候选：对用户长期导演判断，不进行泛泛“你喜欢什么风格”的问卷；只在真实高价值 revision/golden case 上，从具体选择反推：

```text
事件 / 版本对比
→ 用户选择或否决
→ 关键 cue
→ 用户预期
→ 识别出的异常/风险
→ 选择理由
→ tradeoff
→ 哪些近似情况不适用
→ K2 inference
→ 后续 pairwise / production 验证
```

边界：ACTA 是知识提取方法，不保证被访者所有解释都是真实因果；仍需行为/生成结果/反事实交叉验证。

### E-PICG-CDM-001｜Critical Decision Method（T2/T3）

来源：Klein, Calderwood & MacGregor, IEEE Transactions on Systems, Man, and Cybernetics 19(3), 1989, DOI 10.1109/21.31053；Hoffman, Crandall & Shadbolt, Human Factors 40(2), 1998。
- https://doi.org/10.1109/21.31053
- https://doi.org/10.1518/001872098779480442

来源支持：CDM 通过对真实关键事件做多轮 retrospection，并用 probes 提取 perceptual discrimination、conceptual discrimination、typicality judgment、critical cues 等专家知识；产物可以是 timeline、decision requirements、situation assessment records。

项目转译候选：当用户指出一个关键版本“为什么这版明显高级/低级”，系统可以在不打断正常制作的前提下，优先从已发生 revision series 自动构造少量 CDM-style probes：
- 最早在哪个画面证据上判断它不对？
- 如果只改一件事，哪件最重要？
- 什么版本看起来相似但其实你会接受？
- 当时预期观众先注意哪里？
- 哪个错误最致命、哪个只是瑕疵？

若这些问题可由既有用户反馈和版本差异直接推断，则不重复询问；只在 materially ambiguous 时提出最小问题。

边界：不得把“用户事后解释”自动当因果真理；保持 observation / user explanation / system inference / controlled evidence 分层。

## 3. Pairwise Preference Learning：把隐性审美从“打分”变成“选择”

### E-PICG-PREF-001｜Preference Learning / Pairwise Comparison（T2/T3）

来源：Fürnkranz & Hüllermeier, Preference Learning, 2010；Bradley–Terry paired comparison family。
- https://link.springer.com/book/10.1007/978-3-642-14125-6

来源支持：偏好可以从成对比较中学习，而不要求用户为每个对象给出绝对评分；pairwise preference 可以构造相对排序/latent preference。

项目转译候选：
- 对难以语言化的审美，不默认要求“1–10分”；
- 在自然出现的 A/B、版本修订、Golden Case 对比中记录 `A > B / B > A / tie / context-dependent`；
- 同时记录差异维度、scene context、model/version、用户理由（若有）；
- 后续只在相近 context 中召回该 preference evidence。

重要边界：Bradley–Terry 类模型常隐含可排序/相对稳定偏好假设，而电影审美可能非传递、情境依赖、目标依赖。因此本项目不得把 pairwise 结果强行压成一个全局“审美分数”。出现 `A>B, B>C, C>A` 并不自动说明用户矛盾，可能代表多目标 tradeoff 或 context shift。

### E-PICG-ACTIVE-PREF-001｜信息量驱动的偏好询问（T2，candidate）

来源：2025 Artificial Intelligence journal, `On preference learning based on sequential Bayesian optimization with pairwise comparison`。
- DOI 10.1016/j.artint.2025.104400

来源支持：偏好学习可主动选择更有信息量的比较，而不是穷举所有 pair。

项目转译候选：K2 不应通过不断问用户问题来“补全人格”。只有当某个偏好不确定性会真正改变当前高价值导演决策，且存在两个能最大区分假设的可用版本时，才提出一次高信息量 pairwise comparison。

边界：不直接部署该论文算法；只采用 `ask the comparison with high expected information gain` 的设计原则，真实实现前需项目验证。

## 4. K1–K4 与 L0–L5 必须是正交坐标

现有 `learning_application_gate.yaml` 已定义 L0–L5：Observation → Surface Tactic → Director Intent → Causal Mechanism → Contextual Policy → Transferable Principle。

Production Intelligence 新增的 K1–K4 表示“知识是怎样进入当前问题的”：
- K1 用户明确说；
- K2 从行为/反馈推断；
- K3 外部专业知识；
- K4 尚未知/前沿。

二者不能合并。例如：

| 示例 | Epistemic Zone | Abstraction | Maturity/Status |
|---|---|---|---|
| 用户说“这版画面太脏” | K1 | L0 observation | confirmed user feedback |
| 推断用户真正反感的是非权威参考把高频纹理带入成片 | K2 | L2/L3 hypothesis | candidate |
| ASC FDL 的 framing intent preservation | K3 | L4 mechanism/policy candidate | candidate research-supported |
| 当前 Seedance 某模式是否会稳定服从特定负向控制 | K4 | unresolved mechanism | Unknown / needs experiment |

再加第三轴 `maturity_model`：candidate / scene_verified / project_verified / general_stable / conflicted / needs_revalidation / deprecated。

因此项目知识不是一条线，而是至少三轴：

```text
Epistemic Source/Relationship (K1-K4)
× Knowledge Abstraction (L0-L5)
× Validation Maturity
```

任何系统都不得把这三轴压成一个“可信度分”。

## 5. Design Structure Matrix：跨部门耦合与返工不是异常，而是结构

### E-PICG-DSM-001｜Design Structure Matrix（T2/T3）

来源：Eppinger et al., `A Model-Based Method for Organizing Tasks in Product Development`, Research in Engineering Design 6, 1994；Eppinger & Browning, MIT Press `Design Structure Matrix Methods and Applications`。
- https://stuff.mit.edu/people/eppinger/pdf/Eppinger_RED1994.pdf
- https://mitpress.mit.edu/9780262528887/design-structure-matrix-methods-and-applications/

来源支持：复杂开发由大量互相依赖的任务组成，iteration 是内在特征。DSM 用任务/组件间信息依赖矩阵暴露耦合；关键改进包括重新排序任务、让必要信息更早可得、紧耦合任务形成迭代块、可并行任务并行、删除低价值耦合，从而减少浪费性返工。

项目转译候选：Capability Graph 可导出一个 shot/work-item 临时 DSM：
- 节点 = 当前 materially active capabilities/tasks；
- 边 = consumes / informs / constrains / validates / handoff；
- 强双向耦合 = 应在同一 micro-cycle 内联合设计，例如 `Blocking ↔ Camera ↔ Previs`；
- 单向稳定依赖 = 上游先锁定后下游执行，例如 `Formal Asset Identity -> Model Adapter`；
- 不相关节点 = 不应被扩进当前任务。

这为 `sparse dependency expansion` 提供理论支持：大师级协同不是把所有部门都叫进来，而是识别真正紧耦合块。

边界：不要求每个普通镜头生成完整 DSM 图；只有复杂跨部门反复返工、接口频繁漂移或成本高时启用。

## 6. Verification ≠ Validation：技术合规与导演成功分开

### E-PICG-NASA-VV-001｜NASA Systems Engineering V&V（T1）

来源：NASA Systems Engineering Handbook Rev 2。
- https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf

来源支持：Verification 检查产品是否满足规定要求/设计；Validation 检查最终产品是否满足 stakeholder expectations 和 intended use/environment。NASA 也强调从低层组件到集成系统分层 V&V。

项目转译候选：AI 电影必须显式区分：

**Verification（做对规格了吗）**
- work-item identity 对不对；
- 人物/资产是不是正确版本；
- 机位、时长、事件顺序、接触拓扑、参考职责是否执行；
- prompt/adapter/packet 是否满足合同。

**Validation（这镜头真的成立吗）**
- 戏剧功能是否实现；
- 观众知道/感受是否按导演意图改变；
- 表演是否可信；
- 节奏、审美、情绪、信息是否成立；
- 用户/导演是否愿意把它留下。

一个镜头可以 Verification 全绿但 Validation 失败，例如严格按提示词生成了一个无聊的镜头；也可以局部技术偏差但导演效果很好，需要由 Creative Authority 判断是否接受 deviation。

边界：借鉴 V&V 区分，不把电影创作变成航空航天 requirement compliance。

## 7. 多层生产周期：避免 micro-fix 改坏 macro truth

Production Intelligence 候选周期模型：

### C0 Perceptual / moment loop（秒级）
表演微变化、动作接触、观众注意力、声画同步。

### C1 Shot production loop（分钟到单轮生成）
Director packet → reference/previs → model execution → reverse observation → Expected-vs-Observed → Targeted Repair。

### C2 Revision / sequence loop（多轮）
Constraint Ledger → revision series → continuity → edit/attention handoff → checkpoint → Final-Delta。

### C3 Scene / project loop（跨场景）
资产、角色、场景、地图、重复问题、Golden/Regression Cases、maturity promotion。

### C4 Tool/model lifecycle loop（版本周期）
模型/API/软件版本变化 → capability refresh → needs_revalidation → bounded re-test。

### C5 Project architecture loop（较慢）
Source Authority、runtime contracts、department interfaces、schemas、governance。

约束：内层 cycle 可以快速迭代，但不得静默修改外层 authority。例如 C1 为了让模型容易生成，不得改 C3 canonical map；C4 模型能力更新不得改剧情；C2 的一次成功不得直接晋级 C3 general rule。

## 8. Multi-fidelity：便宜模型/短时长测试的理论升级

### E-PICG-MULTIFIDELITY-001｜Multi-fidelity Bayesian Optimisation（T2，ICML 2017）

来源：Kandasamy et al., `Multi-fidelity Bayesian Optimisation with Continuous Approximations`, ICML 2017。
- https://proceedings.mlr.press/v70/kandasamy17a.html

来源支持：昂贵 black-box evaluation 可利用便宜近似 fidelity 提高优化效率，但近似与最终目标之间的关系必须被建模，不能把 cheap approximation 当 exact truth。

项目转译候选：现有“MiniMax H3/短5秒 probe → C-DANCE 2.5 final”可以从单纯 `cheapest-first` 升级成 **multi-fidelity evidence routing**：
- fidelity 不只等于模型价格，还可以是时长、分辨率、参考复杂度、镜头数量、预览/白模程度；
- 每种 fidelity 必须记录能可靠测试哪些 dimension；
- 只有存在跨 fidelity transfer evidence 的维度才能在低 fidelity 提前筛；
- 视觉最终质感、模型专属 reference behavior 等仍需 final fidelity 验证。

边界：不直接部署 Bayesian Optimisation；短期只实现 fidelity-role ledger 与真实跨模型相关性学习。

## 9. Expected Value of Information：不是最便宜的测试，而是最值钱的测试

### E-PICG-EVI-001｜Expected Value of Information / sequential research（T2/T3）

来源：Griffin, Welton & Claxton, Medical Decision Making 30(2), 2010。
- https://doi.org/10.1177/0272989X09344746

来源支持：进一步研究的价值取决于它能减少多少决策不确定性以及成本；不同参数对决策价值贡献不同，顺序研究设计可先获取最有价值的信息再决定下一步。

项目转译候选：主动 probe 的目标函数不应只是 `cost_min`，而应接近：

```text
Priority ≈ Expected Decision-Relevant Information Gain
           × Future Reuse Value
           × Failure Cost Avoided
           / (Generation Cost + User Effort + Delay + Interruption)
```

这里只作为排序启发，不输出伪精确数值。例：一个 5 秒测试如果能决定“以后所有复杂接触是否要上白模”，价值可能远大于另一个便宜但只验证画质的小样。

## 10. 迭代不是越少越好：区分 learning iteration 与 avoidable rework

Eppinger/MIT 的 product-development literature 强调，复杂耦合任务的 iteration 是内生的；目标不是把 iteration 清零，而是组织 iteration：让高价值反馈更早出现，紧耦合任务一起迭代，低价值耦合拆掉。

项目转译：
- `productive_iteration`：每轮改变一个清晰变量、产生新证据、缩小不确定性；
- `rework`：因为遗漏 authority、错误 handoff、参考版本错、旧 work-item 串入、无控制变量 prompt pile-up 而重复劳动；
- 系统优化 KPI 应优先降低 rework，不是机械降低 revision count。

## 11. 候选新能力：TACIT-ELICITATION-001

目标：从真实制作选择中提取用户难以完整口述的导演判断机制。

Trigger：
- 用户明确比较两个版本并稳定偏好其中一个；
- 多轮 revision 中反复出现相同“更高级/自然/不对”的判断，但原因尚未结构化；
- 该隐性判断未来有高复用价值。

Pipeline：
```text
Real Decision Event
→ Existing Revision / Media Evidence
→ Difference Set
→ Critical Cue Candidates
→ User Explanation if already available
→ Alternative Explanations
→ Minimal High-Information Probe only if needed
→ K2 Tacit Preference Candidate
→ Context/Boundary
→ Pairwise/Production Validation
→ Existing Learning Gate / maturity
```

输出字段候选：
- decision_event_ref
- compared_variants
- selected_variant
- rejected_variant
- observed_differences
- inferred_critical_cues
- inferred_value_priority
- tradeoff
- negative_example
- context
- confidence_vector
- what_would_falsify
- user_confirmation_status

Anti-pattern：
- 每次反馈都追问“为什么”；
- 把“更好看”自动总结为固定风格；
- 从一次 A/B 推出全局偏好；
- 把用户没说过的话写成用户原话；
- 为了建立模型而打断真实制作。

## 12. 当前成熟度

- CTA/CDM 在本项目 K2 提取上的应用：candidate_research_supported
- Pairwise preference memory：candidate_research_supported
- K×L×Maturity 三轴知识坐标：candidate_architecture
- DSM temporary dependency graph：candidate_research_supported
- Verification/Validation split：candidate_research_supported
- nested production cycles：candidate_architecture
- multi-fidelity role ledger：candidate_research_supported
- information-value probe ranking：candidate_research_supported
- TACIT-ELICITATION-001：candidate_unvalidated
