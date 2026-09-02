---
title: MIDS 混合主动式共创发现与规格化外部证据索引
status: candidate_evidence
source_issue: 67
scope: upstream_discovery_question_selection_design_rationale_examples_and_multi_turn_eval
---

# MIDS 混合主动式共创发现与规格化外部证据索引

> 本文件只承担候选外部证据与项目翻译职责，不是新的导演、剧情、学习、规格或用户意图权威。项目事实仍服从 `PROJECT_INDEX.yaml` 与对应 canonical。

## 1. 研究问题

MIDS 需要解决的不是“怎样写一个更长的澄清 Prompt”，而是：当用户只有模糊方向、感觉、例子或局部想法时，系统如何在不过度打断、不抢创作控制权的前提下，主动发现最值得问的未知、扩展有价值的设计空间，并把共同决策收敛为可追溯且可交给现有生产运行时的规格候选。

## 2. 证据与项目翻译

### E-MIDS-001｜Mixed-Initiative Interaction

- source: Eric Horvitz, *Principles of Mixed-Initiative User Interfaces*, CHI 1999.
- URL: https://www.microsoft.com/en-us/research/publication/principles-mixed-initiative-user-interfaces/
- evidence tier: T2/T3 professional peer-reviewed HCI source
- useful idea: 自动服务与用户直接控制应协同；系统应考虑用户目标的不确定性、行动收益/成本与介入时机。
- project translation:
  - MIDS 可以主动提出问题和方案，但不能因为推断概率高就把方案当用户决定；
  - question selection 同时计算信息价值与 interruption/cognitive cost；
  - 当 canonical 已经可靠知道答案时，不应打断用户重复提问。
- boundary: 不复制具体概率模型；本项目只采用 ordinal heuristic。

### E-MIDS-002｜Human-AI Interaction Guidelines

- source: Amershi et al., *Guidelines for Human-AI Interaction*, CHI 2019.
- URL: https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/
- evidence tier: T2 peer-reviewed HCI
- useful idea: 人机协作需要围绕不确定性、可控性、纠错与随时间学习等行为设计；研究通过多轮评估形成18条通用 guideline。
- project translation:
  - AI proposal 必须可被接受、修改或拒绝；
  - 被拒方向不得通过后续推断偷偷回来；
  - inference、proposal 与 user-confirmed decision 必须可见地区分。
- boundary: 不把18条 guideline 机械复制成项目运行规则。

### E-MIDS-003｜Double Diamond

- source: Design Council, *The Double Diamond* / Framework for Innovation.
- URL: https://www.designcouncil.org.uk/resources/the-double-diamond/
- evidence tier: T3 professional design institution
- useful idea: Discover/Define 先理解问题而不是假设，Develop 保持多个答案并共创，Deliver 小规模测试、拒绝和改进方案；发散与收敛可以迭代往返。
- project translation:
  - 高创意问题先允许 divergence，不在第一个 plausible idea 上过早锁定；
  - handoff readiness 是一次 convergence gate，不代表不可回到 discovery；
  - rejected alternatives 保留最小 rationale 以防设计回退/泄漏。
- boundary: MIDS 不是项目管理版 Double Diamond，也不建立四阶段第二导演流程。

### E-MIDS-004｜Critical Decision Method / Cognitive Task Analysis

- source: Klein, Calderwood & MacGregor, *Critical decision method for eliciting knowledge*, IEEE Transactions on Systems, Man, and Cybernetics, 1989.
- evidence locator: DOI/publication metadata and abstract indexed externally.
- evidence tier: T2 peer-reviewed knowledge-elicitation method
- useful idea: 通过具体关键事件和 probes 引出专家用于判断的关键线索、区分依据和决策策略。
- project translation:
  - USER_TACIT_CANDIDATE 不通过抽象“你喜欢什么风格”硬猜；优先问具体场景、以前哪个版本更对、关键转折、如果反过来会怎样；
  - 用 critical incident / contrast / counterfactual 把隐性标准变成可判断的 outcome。
- boundary: 不声称用户是被访谈专家，不复制完整 CDM interview protocol。

### E-MIDS-005｜QOC Design Rationale

- source: MacLean, Young, Bellotti & Moran, *Questions, Options, and Criteria: Elements of Design Space Analysis*, Human-Computer Interaction 6(3-4), 1991.
- URL: https://www.tandfonline.com/doi/abs/10.1080/07370024.1991.9667168
- evidence tier: T2 peer-reviewed HCI/design rationale
- useful idea: 用 Questions 表示关键设计问题、Options 表示可能答案、Criteria 比较方案，并保留 justification、analogies、data/theory 等设计理由。
- project translation:
  - MIDS session 用轻量 Q/O/C 记录真正 material 的设计空间；
  - 不保存完整谈话流水账，只保存对后续决策有价值的 rationale；
  - question 必须能结构化 design space，而不是泛泛“还有什么要求吗”。
- boundary: QOC 是 rationale representation，不成为项目事实 authority。

### E-MIDS-006｜Example Mapping / Specification by Example

- source: Cucumber, *Example Mapping* and *Examples*.
- URLs:
  - https://cucumber.io/docs/bdd/example-mapping/
  - https://cucumber.io/docs/bdd/examples/
- evidence tier: T4 high-quality engineering practice
- useful idea: 用具体 examples 探索规则与验收，未知结果应保留为 question；好的例子具体并避免技术细节。
- project translation:
  - 用户不需要说焦段、latent、conditioning 等实现词；可以说“这一版里我想看到什么 / 哪种情况算失败”；
  - READY_FOR_FEATURE_COMPILER 前对 material ambiguity 至少保留正例和反例/非目标；
  - unanswered material outcome 保留 unknown/question，不能伪造成 acceptance rule。
- boundary: MIDS 不生成 Gherkin，也不把电影创作简化为软件业务规则。

### E-MIDS-007｜Jobs To Be Done / generative causal interviewing

- source: Christensen, Hall, Dillon & Duncan, *Know Your Customers’ Jobs to Be Done*, Harvard Business Review, 2016.
- URL: https://hbr.org/2016/09/know-your-customers-jobs-to-be-done
- evidence tier: T3/T4 established management/design practice
- useful idea: 比起表面画像，更关注人在具体情境中真正想取得的 progress / job 与选择背后的因果。
- project translation:
  - 对“我想要更电影感/更自然”先追问观众或故事结果究竟要发生什么；
  - 可用“上次哪个结果让你觉得更对、为什么”之类对比暴露价值排序。
- boundary: 不把创作问题商业化，不使用客户画像替代导演意图。

### E-MIDS-008｜Preference Elicitation / Value of Information

- source: Guo & Sanner, *Real-time Multiattribute Bayesian Preference Elicitation with Pairwise Comparison Queries*, AISTATS/PMLR 2010.
- URL: https://proceedings.mlr.press/v9/guo10b.html
- evidence tier: T2 peer-reviewed ML/HCI-adjacent decision support
- useful idea: 真实 preference elicitation 要兼顾 real-time、multiattribute、low cognitive load、noise robustness、scalability，并可用 VOI 思路挑选问题。
- supporting source: Lin et al., *Preference Exploration for Efficient Bayesian Optimization with Multiple Outcomes*, AISTATS/PMLR 2022, https://proceedings.mlr.press/v151/jerry-lin22a.html
- project translation:
  - 每轮通常只问1–3题；
  - 优先问会改变多个下游决定的高信息价值问题；
  - A/B outcome comparison 可用于 USER_TACIT_CANDIDATE，但不把一次偏好判断直接晋级稳定规则。
- boundary: 不引入 Bayesian utility model；MIDS v0.1 只用可审计 ordinal priority heuristic。

### E-MIDS-009｜Evaluator-Optimizer / multi-turn agent eval

- source: Anthropic, *Building Effective AI Agents*.
- URL: https://www.anthropic.com/engineering/building-effective-agents
- supporting source: Anthropic, *Demystifying evals for AI agents*, 2026.
- URL: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- evidence tier: T1/T4 vendor engineering guidance for current agent practice
- useful idea: 只有当额外复杂度带来可测价值时才增加 agent/workflow；evaluator-optimizer 适合有清晰评价标准且迭代可测改善的任务；多轮 agent 需要 multi-turn/end-to-end eval 而不只单轮 prompt 测试。
- project translation:
  - MIDS 先 SHADOW/CANDIDATE，不直接成为 mandatory director runtime；
  - 用历史 replay + live pilot 测“问得是否有用”和“是否减少返工”，而不是只看回答看起来聪明；
  - complexity budget 本身是 architecture cost。
- boundary: 不复制 Anthropic agent architecture，不建立第二 evaluator authority。

### E-MIDS-010｜Requirements Elicitation / Traceability

- source: ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*.
- URLs:
  - https://www.iso.org/standard/72089.html
  - https://www.iso.org/obp/ui#iso:std:iso-iec-ieee:29148:ed-2:v1:en
- evidence tier: T1 international standard
- version note: 2018 edition remains published/current while a 2026 Edition 3 DIS is under development; MIDS uses only stable elicitation/traceability concepts, not draft-specific changes.
- useful idea: requirements elicitation is the proactive use of systematic techniques to identify and document user/customer needs; requirements engineering includes discovering, eliciting, developing, analyzing, validating, communicating, documenting and managing requirements; traceability preserves derivation and flow-down paths.
- project translation:
  - MIDS discovery receipt must retain provenance from raw intent to confirmed decision to downstream spec candidate;
  - “用户没说清楚”不是许可去猜，而是触发有边界的 elicitation；
  - elicitation 与 final authority 分离：发现出来的内容仍须按用户确认和项目 source authority 裁决。
- boundary: 不把电影创作规格化成软件 shall-statements，也不要求用户填写正式 requirements document。

### E-MIDS-011｜Continuous Discovery / Opportunity-Solution Separation

- source: Teresa Torres / Product Talk, *Opportunity Solution Trees: Visualize Your Discovery to Stay Aligned and Drive Outcomes* and Opportunity Solution Tree glossary.
- URLs:
  - https://www.producttalk.org/2016/08/opportunity-solution-tree/
  - https://www.producttalk.org/glossary-discovery-opportunity-solution-tree/
- evidence tier: T3/T4 established product discovery practice
- useful idea: desired outcome、opportunity space、solution space、assumption tests 应保持可区分；新证据或失败实验到来时可以回到上游重新审视 opportunity/solution，而不是只在既有方案上打补丁。
- project translation:
  - MIDS 先问“要让故事/观众/角色/成片发生什么”，再提出具体导演或生产方案；
  - AI_DISCOVERABLE_OPTION 属于可探索 solution space，不得反向伪造成用户原始 need；
  - failed prototype 可以触发重新打开 discovery，而不是自动把当前方案继续修到死。
- boundary: 不建立 Opportunity Solution Tree 第二知识库；只吸收 outcome/opportunity/solution/assumption 的分离原则。

### E-MIDS-012｜Spec-Driven Development / Intent Before Implementation

- source: GitHub Spec Kit official repository and documentation.
- URLs:
  - https://github.com/github/spec-kit
  - https://github.github.com/spec-kit/
- evidence tier: T1 official current tooling/documentation
- useful idea: Spec-Driven Development 强调先定义 what / intent，再进入 plan → tasks → implement，并使用结构化 artifacts / quality checks 给 agent 提供稳定上下文，而不是让 implementation 从临时自然语言直接漂移出来。
- project translation:
  - MIDS handoff 的价值不是形成另一份长期 spec 主档，而是在需要时把 discovery 收敛成 minimum-sufficient `DiscoverySpecCandidate`；
  - director/execution/engineering 下游只消费已经达到 readiness gate 的候选，并继续服从各自 canonical authority；
  - spec candidate 可以被后续反馈重新打开，不把一次收敛当不可逆真理。
- boundary: 不采用 Spec Kit 的命令体系，不把 `DiscoverySpecCandidate` 设为 screenplay/director canonical，也不让 spec 直接绕过现有 Feature Compiler / review / write routes。

## 3. 与当前项目已有知识的融合

MIDS 不新增第二 Epistemic authority。现有 `反馈反推与系统反哺引擎.md` 已定义 EDCM：

- K0 明确已知；
- K1 隐含已知；
- K2 邻接未知；
- K3 unknown-unknown。

Pilot 使用用户要求的四个交互标签作为 discovery-facing projection：

```text
USER_EXPLICIT_CONFIRMED -> EDCM K0
USER_TACIT_CANDIDATE    -> EDCM K1
AI_DISCOVERABLE_OPTION  -> EDCM K2
EXPERT_BLIND_ZONE       -> EDCM K2/K3（按证据与可解释性）
```

这四类只描述当前 discovery 的知识关系，不改变 Learning Application Gate 的 maturity / scope / conflict authority。

## 4. 当前候选结论

1. **少问而不是多问。** 问题数量不是 discovery 质量，information value / dependency / irreversibility / novelty 与用户负担的组合才是。
2. **具体 outcome 优先于技术参数。** 用户说画面、故事、角色、声音、风险与成本，AI 翻译为摄影/模型/工程约束。
3. **发散与收敛分离但可往返。** 过早锁定一个方案会损失 AI_DISCOVERABLE_OPTION；一直发散则无法 handoff。
4. **例子和反例是规格边界。** 关键行为只写抽象词会在后续 Feature Compiler / prompt compilation 中重新产生歧义。
5. **拒绝必须是一等状态。** 没有 reject ledger，LLM 很容易在后续总结里把曾提议但被否决的方向重新混入。
6. **MIDS 的成功指标不是“用户回答了多少问题”，而是更早发现 critical unknown、降低重复提问和 post-spec rework，同时不越权。**
7. **需求、机会与方案必须分层。** 用户想达成的效果不等于 AI 提出的实现手段；两者混在一起会让后续拒绝/替换方案时误伤真实需求。
8. **真正 hidden-answer replay 必须由未见答案的独立上下文执行。** 当前机器 fixture 可以验证问题筛选、守门和评分管线，但不能把同一实现上下文中预置的候选问题冒充“未知答案下的自主发现能力”。

以上全部 maturity=`candidate`，需要 replay 与真实项目 SHADOW pilot 后再判断是否值得激活。
