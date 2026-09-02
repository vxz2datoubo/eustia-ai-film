---
title: 声音导演与SUNO证据索引
status: active
canonical_role: sound_domain_evidence_annex
last_updated: 2026-09-01
---

# 声音导演与 SUNO 证据索引

> 本文件是 `09_资料证据/官方资料与证据索引.md` 下的声音专业域证据附录。只保存来源、证据等级、版本边界与可支持的主张，不作为第二套导演规则入口。可执行规则写入 `01_AI电影系统/声音导演系统.md`。

## 1. 证据等级

沿用项目主证据索引：E1 官方文档/机构一手；E2 大师或专业机构一手案例；E3 同行评议/大学研究/经典专业理论；E4 本项目真实生成与用户验收；E5 候选推断或尚未复验的迁移知识。

## 2. 用户已有资料与迁移证据

### E-SOUND-LEGACY-001｜旧版长段落电影配乐协议
- 来源：ChatGPT File Library `00_项目长期外部记忆与系统演化总文档_v1.0.35_更新补丁.md`。
- 身份：历史迁移证据；不得作为当前 canonical 规则、active source 或运行时 authority 使用。
- 支持内容：underscore / incidental music / background score；Spotting 与 Cue；低显著度、dialogue-safe underscore；4–15 秒视频生成与约 1–3 分钟长 Cue 分层；少量同步点；Suno Style/Exclude；后期 Crop/Extend/Replace/Stem/Automation。
- 边界：旧文件自称“最高优先级”不能覆盖 GitHub `PROJECT_INDEX.yaml`；其中模型特定能力必须按当前 Suno 版本重验。
- 当前处置：保留有效概念作为候选迁移输入，与专业资料及当前 Suno 官方能力重新对齐。

## 3. Suno 官方能力与版本证据（E1）

### E-SUNO-V55-001｜v5.5 当前模型族
- 来源：Suno Help `What’s New in v5.5`；Suno 官方博客 `Suno v5.5: More Expressive. More You.`。
- 日期：2026-03-26。
- 支持：v5.5 引入/支撑 Voices、Custom Models、My Taste；官方将其描述为当前更具表现力和个性化的模型。
- 版本边界：模型能力属于 `needs_revalidation_on_version_change`。

### E-SUNO-CUSTOM-001｜Custom Models
- 来源：Suno Help `Custom Models in v5.5`。
- 支持：Pro/Premier 可建立最多 3 个自定义模型；至少 6 首拥有权利的歌曲可创建模型；模型私有。
- 项目含义：可用于建立项目/角色/系列的稳定声音语言，但训练素材必须有权利且必须通过跨 Cue 一致性实测。

### E-SUNO-VOICE-001｜Voices
- 来源：Suno Help `Voices: Use Your Voice in Suno`、`Voices FAQ`。
- 支持：v5.5 可建立自己的 Voice；干净 acapella 更有利；Audio Influence 可调参考影响。
- 权利边界：当前条款要求只能为自己的声音建立 Voice Model；项目不得把第三方角色声优/演员声音默认当作可建模素材。

### E-SUNO-CONTROL-001｜Custom / Exclude / Creative Sliders
- 来源：Suno Help `How do I exclude elements of a song?`、`How to Use: Creative Sliders`。
- 支持：Custom Mode 可使用 Exclude；Weirdness、Style Influence，以及 Audio Upload 时的 Audio Influence 提供生成控制。
- 边界：滑杆与提示词的精确因果响应没有官方量化映射，必须通过项目 A/B 测试校准。

### E-SUNO-EDITOR-001｜局部重写与编辑
- 来源：Suno Help Song Editor / Reuse Prompt / Extend 相关官方文档与 2026 Release Notes。
- 支持：可进行 section 级编辑、Replace/Extend/Crop/Fade、歌词重写和版本复用；2026-07 Web 增加 Duration slider 与歌词编辑/结构标签改进。
- 项目含义：生成不再等于一次性成品，应采用“候选 → 局部修复 → 结构重写 → 后期 conform”的非破坏式迭代。

### E-SUNO-STEMS-001｜Advanced Stem Separation
- 来源：Suno Help `Advanced Stem Separation`，2026-06-12。
- 支持：Auto Split 最多约 12 stems；Split from Mix 可抽单一乐器/人声及其 complement；Premier Advanced Split 可从更细的乐器列表定制拆分。
- 边界：官方明确检测/标签仍可能错误；stem 质量必须实际听检。

### E-SUNO-SOUNDS-001｜Suno Sounds
- 来源：Suno Help `Suno Sounds: Generate Custom Audio Samples`，2026-02-18。
- 支持：实验性生成 one-shot / loop，可用于 SFX、环境声、乐器 sample 等。
- 边界：官方标注 experimental/beta；不得直接替代项目 Foley/物理音效验收，先作为 candidate 工具。

### E-SUNO-API-001｜官方 Suno Platform API
- 来源：`platform.suno.com` 官方登录页。
- 支持：官方公开存在 REST API 平台，可从 prompt 生成原创歌曲、cover、mashup。
- 未确认：当前公开抓取只能看到登录入口，未取得可核验的 endpoint schema、鉴权细节、速率限制、异步任务合同等完整开发文档。
- 安全边界：在正式 API 文档可读前不猜测/复制非官方接口。

## 4. 专业电影配乐与声音工作流（E1/E2）

### E-FILM-BERKLEE-SPOTTING-001｜Spotting / writing to picture
- 来源：Berklee Online `Film Scoring 101`、`Film Score Analysis`。
- 支持：从剧情结构、叙事 signpost 与情绪节奏决定音乐；Spotting 决定何处进出音乐及 Cue 功能；学习 timecode、DAW、tempo/meter map、underscore、theme adaptation、dialogue scene。
- 项目转译：声音导演必须先回答“为什么此刻需要音乐”，再回答风格与提示词。

### E-FILM-BERKLEE-SYNC-001｜Sync points / cue anatomy
- 来源：Berklee Online `Film Scoring Concepts You Need to Know`。
- 支持：tempo map、sync point、乐句完整性、主题类别与主题重复/变奏；同步点通常与新音乐段落发生关系。
- 项目边界：不机械要求 Suno 原始生成精确命中帧；用于 Cue 设计和后期 conform。

### E-FILM-BERKLEE-MUSIC-EDITOR-001｜Music Editor / picture reconform
- 来源：Berklee Online `Music Editor`。
- 支持：spotting session、cue notes、timecode/duration/style、temp soundtrack、picture re-edit 同步更新、最终 dub 与 cue sheet。
- 项目转译：建立 Music Tracker/Cue Matrix，将音乐先绑定剧情功能与工作段，picture lock 后再做精确 conform，降低反复剪辑造成的重做成本。

### E-FILM-BERKLEE-CANVAS-001｜完整声音画布
- 来源：Berklee Online `Professional Film Scoring Skills 1`、`Audio/Music Production for Visual Media`。
- 支持：音乐需与 dialogue、SFX、source music/songs 协作；最终交付 stems 并进入 dub/final mix；Foley、backgrounds、dialogue、score 共同构成声音画布。
- 项目转译：声音导演不仅是“配乐部门”，还负责声音层级、音乐让位与最终交付接口。

### E-BAFTA-MUSIC-TRACKER-001｜Music Tracker / Cue Sheet
- 来源：BAFTA Film Rules（2027 awards cycle current rules）。
- 支持：Original Score 类别要求 music tracker 记录 original / sourced / pre-existing / unknown music 时长，并提交标注原创 Cue 的 cue sheet。
- 项目转译：建立 provenance-aware music tracker，记录 Cue 身份、来源、版本、时长、权利、生成工具与使用位置。

### E-BAFTA-COMPOSERS-001｜大师案例入口
- 来源：BAFTA Guru `Conversations with Screen Composers`。
- 覆盖：Hans Zimmer、John Powell、Daniel Pemberton、Anne Dudley、Clint Mansell、Cliff Martinez 等创作者一手访谈。
- 用法：作为问题导向案例池，提取“问题 → 选择 → 原因 → 代价 → 成立条件”，禁止复制某位作曲家的表面风格当通用规则。

## 5. 歌曲创作专业知识（E1/E3）

### E-SONG-BERKLEE-PROSODY-001｜Prosody
- 来源：Pat Pattison / Berklee Online `Prosody in Music and Songwriting`、`Songwriting Tools and Techniques`。
- 支持：歌词、旋律、和声、节奏等元素应共同服务歌曲的 central intent/emotion；stable/unstable 可作为统一分析轴之一。
- 项目转译：歌曲分支先定义“歌曲真正想表达什么”，再设计歌词、旋律、和声、节奏和制作，不从 genre tag 开始。

### E-SONG-BERKLEE-LYRIC-001｜歌词结构与唱词适配
- 来源：Berklee `Lyric Writing: Tools and Strategies`、`Writing Lyrics to Music`。
- 支持：rhyme、rhythm、line length、verse/chorus/bridge contrast；lyric stress、rhythm、phrasing 与 melody 对齐；hook/focal point 放置。
- 项目转译：歌曲验收增加 prosody、可唱性、重音、段落功能、hook、歌词可懂度，而不是只评“好不好听”。

### E-SONG-BERKLEE-HARMONY-001｜歌曲和声与段落对比
- 来源：Berklee `Songwriting: Harmony`。
- 支持：groove/chord color、harmonic rhythm、cadence、modal color、modulation 与 section contrast。
- 项目转译：Style Prompt 中的和声语言应服务段落与叙事功能，不把“minor=悲伤”等单变量映射当硬规则。

## 6. 声音量化与可懂度（E1/E3）

### E-AUDIO-ITU-1770-001｜Loudness / True Peak
- 来源：ITU-R BS.1770-5（11/2023，在有效状态）。
- 支持：节目响度与 true-peak 的标准测量算法。
- 项目边界：只作为测量基础，不把某个固定 LUFS 数值当电影、流媒体、社媒全部发行场景的统一目标；最终目标由交付平台规范决定。

### E-AUDIO-AES-DIALOGUE-001｜Dialogue Intelligibility
- 来源：AES Technical Documents，TD1009 `Improving Dialogue Intelligibility in Media`。
- 支持：对白可懂度是独立的专业声音问题，应在媒体混音中单独控制与验收。
- 项目转译：dialogue-safe 不只是一组配器词，还要在最终混音中检查频谱遮蔽、动态竞争、时序竞争和声场优先级。

## 7. 学术研究（E3 / 部分 candidate）

### E-ACADEMIC-BOLTZ-001｜音乐与电影认知整合
- 来源：Marilyn G. Boltz, Memory & Cognition 32 (2004), DOI 10.3758/BF03196892。
- 支持：音乐可影响影片信息的解释、情绪影响和记忆；情绪一致/不一致条件呈现不同编码行为。
- 项目转译：音乐与画面的关系不等于永远“同情绪”；一致与反差都必须明确服务观众认知目标，并通过成片测试。

### E-ACADEMIC-EMSYNC-001｜情绪与时间边界对齐
- 来源：`Video Soundtrack Generation by Aligning Emotions and Temporal Boundaries` (2025 arXiv)。
- 状态：E3-preprint / candidate。
- 支持线索：把 valence-arousal 与视频时间边界共同用于音乐条件控制，并通过 boundary offset 对齐音乐和场景切点。
- 项目转译：可用于设计“情绪曲线 + 边界事件”两轴 Cue IR，但不是 Suno 内部机制证据。

### E-ACADEMIC-EMORSION-001｜电影声音参数与沉浸
- 来源：EMORSION (2026 arXiv preprint)。
- 状态：E3-preprint / candidate。
- 支持线索：对 frequency/pitch、dynamics/loudness、directionality 做受控变化并测量主观/生理/运动响应。
- 项目转译：为未来声音 A/B Eval 提供实验设计启发，不直接形成稳定审美规则。

### E-ACADEMIC-DIALOGUE-V2M-001｜Dialogue-aware video-to-music
- 来源：`Dialogue-Aware Video-to-Music Generation Using Public Domain Film Collections` (2026-08-12 arXiv)。
- 状态：最新预印本 / candidate。
- 支持线索：把 dialogue track 作为视频到音乐生成的时间条件之一，并强调可复现、版权友好的公共领域电影语料。
- 项目转译：加强“对白不是配乐之外的障碍，而是音乐条件信号”的研究方向；需等待更多同行评议/复现。

## 8. 权利、版权与来源治理（E1）

### E-SUNO-RIGHTS-001｜商业使用权
- 来源：Suno Help `What rights do I have with a paid subscription?`、`free plan`、`Does Suno own the music I make?`、`If I subscribe... before subscribing?`。
- 支持：Pro/Premier 订阅期间生成的歌曲获商业使用权，可用于 film/TV/games 等；Basic/free 主要限非商业；后续订阅默认不追溯赋予旧免费歌曲商业权利。
- 边界：商业使用权不等于版权资格。

### E-SUNO-TOS-001｜Submission / Voice / 非唯一输出
- 来源：Suno Terms of Service，last revised 2026-03-26。
- 支持：上传者须拥有所提交素材必要权利；Voice Model 只能建立自己的声音；服务可产生相同/相似输出；条款对 Content/Voice Model 许可范围较广。
- 项目转译：任何上传音频、歌词、Voice、Custom Model 训练集都必须有 provenance 与权利状态，不把“能上传”当作“可商用”。

### E-USCO-AI-001｜美国 AI 版权报告 Part 2
- 来源：U.S. Copyright Office，2025-01-29。
- 支持：生成式 AI 输出只有在存在足够人类创作表达时才可能获得版权保护；单纯 prompt 本身不足；人类的创作安排或修改可能构成可保护贡献。
- 项目转译：建立 Human Authorship Ledger，记录用户写作歌词、旋律/结构决策、选择、重写、编曲/剪辑/混音等真实人类贡献。此记录不构成法律结论。

## 9. 研究到项目规则的晋级门

所有外部研究默认只产生 `candidate`：

```text
source claim
→ scope / version / failure boundary
→ SoundDirectorIR operational rule
→ same-work-item A/B or controlled revision
→ user / objective acceptance
→ scene_verified
→ cross-scene replication
→ project_verified
```

Suno 模型/功能更新时，所有依赖具体模型行为的条目转 `needs_revalidation`；电影叙事、Spotting、Prosody、声音层级等稳定专业原则不因模型换代自动失效，但若项目出现反例仍应重验。
