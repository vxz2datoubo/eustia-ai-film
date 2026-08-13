---
title: SUNO提示词词库与编译映射
system_id: SUNO-PROMPT-LEXICON
status: active
parent_system: 01_AI电影系统/声音导演系统.md
authority_mode: delegated_execution_lexicon
maintenance_mode: in_place_only
versioned_filename_policy: forbidden
last_updated: 2026-08-13
maturity_default: candidate_for_model_behavior
---

# SUNO提示词词库与编译映射

> 本文件是 `声音导演系统` 下的 SUNO 执行词库与编译映射，不是第二套声音导演理论。
> 它负责把用户自然语言、音乐术语、旧提示词表和当前 Suno 控制字段映射到 `SoundDirectorIR → Suno 执行稿`。
> 剧情目的、人物、观众认知、Spotting、Cue、Prosody、混音与权利规则仍由 `声音导演系统.md` 决定。
> 模型行为相关经验默认 `candidate`，必须通过当前模型真实生成验证；音乐学标准术语可以作为语义骨架，但不等于 Suno 对每个词都有稳定可控响应。

# 1. 资料摄取结论

2026-08-13 已逐份读取用户上传的 SUNO 资料包，包括：
- `suno纯音乐常用风格.txt`
- `Suno情感 乐器 节奏 标签提示词.txt`
- `Suno人声六大分类提示词.txt`
- `Suno提示词_音乐术语中英文对照表.txt`
- `suno无权重提示词.docx`
- `纯R&B提示词.txt`
- `歌曲结构-风格 乐器 嗓音等提示词.txt`
- `歌曲开头就唱副歌提示词.txt`
- `嗓音、演唱技巧和音色质感等提示词.txt`
- `Suno_AI电影配乐提示词统一手册_秽翼的尤斯蒂娅.docx`
- `Suno_AI电影配乐提示词统一手册_秽翼的尤斯蒂娅.pdf`

其中：
- `suno无权重提示词.docx` 与 `Suno_AI电影配乐提示词统一手册_秽翼的尤斯蒂娅.docx` 字节完全一致，是同一内容副本，不作为两份独立证据重复计权。
- PDF 是同一统一手册的分页/排版版本，作为阅读与历史证据，不重复晋级规则。
- 统一手册已经对多份原始词表做过一次去重、术语校正和电影用途分级；本文件在此基础上继续做 namespace、scope、confidence 与任务路由重构。
- 旧文件名中的“无权重”不代表存在可靠的数值权重表；当前资料没有提供可验证的 tag 权重响应函数，因此不得虚构“某词权重更高”。

# 2. 词条可信度层级

每个词/标签在内部至少区分以下 provenance：

```yaml
confidence_class:
  official_current: 当前 Suno 官方文档明确支持该概念或控制字段
  music_standard: 标准音乐/录音/作曲术语，语义可靠，但 Suno 精确响应仍需验证
  user_curated: 用户资料包中的经验词或组合，来源可追溯但未做当前模型控制实验
  legacy_behavioral: 旧模型/社区式 metatag 或行为技巧，仅用于 A/B 实验
  corrected_or_deprecated: 翻译错误、歧义旧写法或已被更准确表达替代
```

默认裁决：
`official_current > music_standard > user_curated > legacy_behavioral`。
但“官方定义了术语”不等于“模型会精确遵循这个术语”；模型控制效果仍需 Eval。

# 3. Prompt Namespace Ontology

禁止把所有词平铺成一串。先映射到命名空间：

```yaml
style:
  genre:
  subgenre:
  era:
  cultural_color:
affect:
  mood:
  valence:
  arousal:
  tension:
time:
  tempo_bpm:
  tempo_term:
  tempo_curve:
  meter:
  pulse:
  groove:
harmony:
  tonal_center:
  mode:
  chord_color:
  harmonic_rhythm:
  cadence:
  dissonance_resolution:
melody:
  contour:
  register:
  range:
  motif:
  hook:
arrangement:
  instrumentation:
  orchestration:
  texture:
  density:
  articulation:
  dynamics:
vocal:
  role:
  register:
  age_color:
  timbre:
  technique:
  harmony_arrangement:
  spoken_delivery:
production:
  effects:
  saturation_distortion:
  stereo_space:
  reverb_space:
structure:
  global_form:
  section:
  transition:
  opening_strategy:
  ending_strategy:
film:
  diegesis:
  score_function:
  salience:
  dialogue_priority:
  spotting:
  sync:
exclude:
  identity_breakers:
  unwanted_instruments:
  unwanted_vocals:
  unwanted_structure:
```

# 4. Scope 规则

同一个词只有先确定作用域才可编译。

- `GLOBAL`：整首/整 Cue 的风格、主唱身份、总配器、总体情绪。
- `SECTION_LOCAL`：只作用于 Verse / Chorus / Bridge / 某个 Cue 段。
- `TRANSITION`：build-up、drop、modulation、crescendo、ritardando 等过程变化。
- `MIX_POST`：reverb、delay、EQ、compression、panning 等后期/制作语义。
- `EXCLUDE`：专门放 Suno Exclude 字段或后期排除合同。
- `DIEGETIC_SOURCE`：画内音乐/声源必须再绑定地点、时代、人物可听状态。

如果同一词在不同作用域冲突，可并存；如果在同一作用域冲突，必须先消解。

# 5. Prompt 编译模式

## 5.1 Compact Tag Stack

适合：
- 简单风格探索；
- 控制变量 A/B；
- 用户只给少量要求。

基础轴不是硬公式，而是最小候选集合：

`Genre/Style + Affect + Tempo/Groove + Instrumentation + Vocal/Instrumental`

来源资料中的“黄金公式”保留为启发，不再视为所有任务的唯一格式。

## 5.2 Conversational Style Brief

当前 Suno 官方已支持更详细的自然语言 Style 描述。复杂任务优先使用：

`总体身份 → 进入状态 → 配器/纹理 → 节奏/和声发展 → 关键段落变化 → 结尾状态`

适合：
- 电影配乐长弧线；
- 多段落歌曲；
- 需要描述渐变、密度变化、配器进入顺序的任务。

## 5.3 Lyrics/Section Layer

歌曲的段落结构、歌词和 section-local 表演指令进入 Lyrics/Section 层，不把所有段落控制挤进 Style。

标准结构语义可使用：
`Verse, Chorus, Pre-Chorus, Post-Chorus, Bridge, Refrain, Intro, Outro, Hook, Break, Interlude, Coda, Instrumental, Vamp, Build-up, Drop, Tag, Middle 8/B section, Modulation`

注意：
- 这些结构术语本身是可靠音乐语义。
- `[Verse]`、`[Chorus]` 等方括号 metatag 的当前模型精确解析强度，没有取得完整官方控制合同，因此属于版本相关可实验语法。
- 复杂/非标准 metatag 不得仅因旧资料出现就视为稳定能力。

## 5.4 Exclude Layer

明确不需要的元素优先放 Suno 的 `Exclude` 字段，不把大量 `no / without` 句子塞回 Style。

例：
```text
Style:
Pure R&B, slow tempo, smooth groove, deep bass, minimal drums, warm keys, emotional male vocal

Exclude:
pop, EDM
```

## 5.5 Instrumental Gate

电影 underscore / 纯音乐：
- 优先使用 Suno `Instrumental` 开关；
- Style 描述音乐本身；
- Exclude 可补充 `vocals, lyrics`，但不能只靠自然语言“no vocals”代替 Instrumental 状态。

# 6. 歌曲编译映射

歌曲先读 `声音导演系统#歌曲编译器`，再从词库选择执行语义。

## 6.1 结构

- Verse：新信息、场景、叙事证据。
- Chorus：中心命题/核心记忆回归。
- Pre-Chorus：向 Chorus 制造方向性与压力。
- Post-Chorus：副歌后的延续/释放/二级 Hook。
- Bridge / Middle 8 / B section：新视角、代价、结构反差。
- Refrain：重复短句或歌词回归，不等于完整 Chorus。
- Hook：可为歌词、旋律、节奏、制作或器乐记忆点。
- Outro / Coda：歌曲收束；`Outro` 不等于“片尾曲”。
- Break / Interlude / Instrumental：留白或器乐段。
- Vamp：重复段落，用于延长或维持状态。
- Build-up / Drop：更常见于电子/流行结构，不强塞到所有歌曲。
- Modulation：若指转调，进入 harmony namespace，不与音频 modulation effect 混用。

## 6.2 开头直接副歌

用户资料中的：
`[immediate high note chorus] + [Chorus]`
以及 `starts with chorus, explosive emotional opening`
保留为 `legacy_behavioral candidate`。

更稳健的三层编译：
1. `song_form` 明确 `Chorus first`；
2. Lyrics 第一段直接以 `[Chorus]` 或 Chorus 内容开始；
3. Style 写 `opens immediately with the chorus, no instrumental intro`。

`[immediate high note chorus]` 作为第四层实验项，不作为默认硬标签。

## 6.3 Prosody 联动

词表里的 `powerful / belting / breathy / melisma / runs / riffs / whisper / Sprechgesang` 等，不应全局堆叠。
应绑定：
`哪一段 → 哪个关键词/心理变化 → 哪种技巧 → 为什么`

# 7. 人声词库

## 7.1 主唱音域/角色

- male tenor
- male baritone
- male bass
- female soprano
- female mezzo-soprano
- female alto / contralto
- child voice
- boy soprano
- teen / adolescent vocal
- lead vocal / solo vocal
- male & female duet
- female choir / male choir / mixed choir / children's choir
- background vocals / backing vocals

纠错：
- `male & female duet` = 男女对唱/二重唱，不应笼统翻译为“男女合唱”。
- `child voice` 与 `children's choir` 不是同一对象，单人童声和童声合唱必须分开。

## 7.2 音色

- raspy / gravelly / smoky
- clear / pure / clean / natural
- deep
- soft / gentle / delicate
- ethereal / airy / breathy
- soulful / husky
- nasally
- crisp
- voice with a cry / twang
- gritty
- resonant

## 7.3 演唱技巧

- falsetto
- head voice
- chest voice
- mixed voice
- belting / belt
- vocal fry
- growl
- scream / shouted vocals
- runs / riffs / melisma
- glissando / slide
- ad-libs / scat
- vibrato
- Sprechgesang
- spoken word / narration
- yodeling
- bel canto
- crooning
- rapping / melodic rap

## 7.4 和声与层次

- rich / thick harmonies
- layered vocals
- stacked harmonies
- background harmonies
- call and response
- round / canon-style vocals
- vocal pads

## 7.5 人声制作效果

- reverb
- delay / echo
- chorus effect
- flanger
- phaser
- distortion / overdrive
- Auto-Tune / robotic effect
- vocoder
- telephone filter / lo-fi effect
- reversed vocals
- vocal chops / chopped vocals
- pitch shift / formant shift
- doubling
- compression
- de-esser
- gating

# 8. 音乐风格与情绪词库

## 8.1 常用风格

- Pop / Mandopop / J-Pop
- Rock / Punk / Metal
- Hip-Hop / Rap / Trap
- R&B / Soul / Funk
- Electronic / EDM / House
- Jazz / Blues
- Country / Folk / Indie
- Classical / Orchestral / Cinematic
- Ambient / Lo-fi
- Synthwave / Vaporwave
- Reggae

## 8.2 情绪/氛围

- cheerful / joyful / happy
- romantic
- gentle
- mysterious
- horrifying
- sad / melancholic
- passionate
- tense
- peaceful
- energetic
- chill / relaxing
- dreamy
- dark
- nostalgic
- uplifting

## 8.3 特殊人声/唱法颜色

原始词表保留：
- Gregorian chant
- melismatic
- spoken word
- Sprechgesang
- ethereal / resonant / sultry
- lounge singer
- diva solo
- gospel choir
- primal scream
- rap verse
- bel canto
- Minnesang
- yodeling

这些是风格/唱法/历史语境词，不是同一层级。
例如 `Gregorian chant` 与 `Minnesang` 还带历史文化语境，画内使用时必须通过时代/世界观过滤。

## 8.4 用户资料中的示例 Preset Bank

仅作为 `user_curated preset`，不得盖过任务分析：

- Mandopop emotional ballad：piano + strings + slow + clear male vocal
- Cyberpunk / Synthwave：driving bassline + futuristic electronic texture + high energy
- Chinese traditional color：guzheng + erhu + bamboo flute + ethereal/ceremonial color
- J-Pop / Anime Opening：fast/high-energy + electric guitar + prominent chorus
- Lo-fi Hip-Hop：chill + jazzy chords + vinyl-like texture + instrumental
- Pure R&B：slow tempo + smooth groove + deep bass + minimal drums + warm keys + emotional vocal，pop/EDM 放入 Exclude

这些预设只提供起点。项目正式输出仍需经过 central intent / scene function / character / dialogue / diegesis / rights filter。

# 9. 时间、节奏、动态与表达

## 9.1 Tempo

- largo / grave / lento
- adagio
- andante
- moderato
- allegro
- vivace
- presto / prestissimo
- slow / medium tempo / up-tempo
- BPM

## 9.2 Tempo Curve / Feel

- accelerando
- ritardando
- rubato
- steady pulse
- tempo change
- hesitant / dragging / jumpy

纠错：
- 原资料中的“浅快-Accelerating”按语义校正为“渐快/加速”。
- `hesitant / dragging / jumpy` 更接近演奏 feel / timing character，不作为严格速度术语。

## 9.3 Meter / Rhythm

- 4/4
- 6/8
- 7/8
- syncopation
- groove
- pulse
- downbeat / upbeat
- polyrhythm
- triplet / duplet

## 9.4 Dynamics / Articulation

- crescendo
- diminuendo / decrescendo
- forte / fortissimo
- piano / pianissimo
- mezzo forte / mezzo piano
- accent
- staccato
- legato
- tremolo
- fermata

# 10. 和声、旋律、结构性音乐术语

- melody
- harmony
- chord / chord progression
- key / tonal center
- scale / mode
- interval
- octave
- arpeggio
- motif / motivic cell
- counterpoint
- dissonance
- resolution
- suspension
- cadence
- ostinato
- pedal point
- cadenza
- improvisation
- modulation / key change
- anacrusis
- augmentation / diminution

# 11. 乐器词库

按家族调用，避免在 Prompt 中无目的列满整支乐团。

## 11.1 弦乐
`violin, viola, cello, double bass, strings, viola da gamba, erhu, zhonghu, sarangi`

## 11.2 木管/吹管
`flute, piccolo, clarinet, bass clarinet, oboe, bassoon, bamboo flute, bansuri, shakuhachi, bawu, pan flute, ocarina, harmonica, crumhorn`

## 11.3 铜管
`trumpet, French horn, trombone, tuba, flugelhorn, euphonium, tenor horn, baritone horn, sackbut, serpent`

## 11.4 键盘/拨弦/弦鸣
`piano, keyboard, harpsichord, clavichord, harp, acoustic guitar, electric guitar, bass guitar, lute, theorbo, mandolin, banjo, ukulele, bouzouki, zither, guqin, guzheng, koto, pipa, shamisen, oud, kanun, sitar, veena, saz, baglama, nyckelharpa, hurdy-gurdy`

## 11.5 打击
`drums, percussion, timpani, tambourine, congas, bongos, tabla, djembe, cajón, taiko, triangle, castanets, talking drum, agogo, cuíca, mridangam, glockenspiel, xylophone, marimba, vibraphone`

## 11.6 电子/特殊
`synthesizer, electronic drums, 808 bass, theremin, ondes Martenot, glass harmonica, vocoder`

## 11.7 文化/时代过滤

画内音乐调用前必须经过：
`世界观时代 → 地区/文化 → 阶层/机构 → 可获得乐器 → 声源空间`

## 11.8 其他/世界乐器与低频使用词

从原始词表保留为可检索候选：
`accordion, melodica, saxophone, alto saxophone, tenor saxophone, baritone saxophone, soprano saxophone, bandoneon, concertina, didgeridoo, bagpipes, kazoo, steel drum, dulcimer, santoor, agogo, berimbau, cuíca, talking drum`

调用原则：
- 先判断其在项目时代/文化是否成立；
- 非画内 score 可作为音色资源；
- 画内音乐必须通过 diegetic/worldbuilding gate。

## 11.9 环境声与声音事件词

用户资料中出现的：
`wind, thunder, raindrops, seagulls, bells, city noise, airport ambience, phone tone, turntable scratching, medical monitor/ECG-like beep`

这些不应无差别塞入音乐 Style。
优先映射到：
`ambience / SFX / Suno Sounds / diegetic source`
并读取声音导演的物理声源规则。

# 12. 口语/旁白表达词

原始 Spoken Terms 保留到 `vocal.spoken_delivery`：

- narration / dialogue / monologue / voice-over
- intonation / inflection
- diction / articulation / clarity
- accent
- projection
- pause / emphasis
- cadence
- tone / pitch
- pace / rhythm
- fluency
- delivery / expression
- volume
- resonance
- vocal sample

这些词描述“怎么说”，不等同于歌曲唱法。
在电影任务中，台词/VO 表演首先服从角色与表演设定库；Suno 只在确实用于歌曲朗诵、spoken word 或特殊声景时调用。

# 13. Music Notation 词汇保留规则

原始资料包含：
`treble clef, bass clef, staff, bar line, measure, time signature, key signature, sharp, flat, natural, note, rest, whole/half/quarter/eighth/sixteenth note, dotted note, tie, slur, grace note, trill, ornamentation, triplet, duplet, fermata, repeat sign, fine`

处理：
- 这些是标准音乐语义，可用于内部乐理说明和后期编曲；
- 但“把记谱术语写进 Suno Prompt 就能精确按谱执行”没有当前官方保证；
- 因此 direct-prompt reliability 默认低于 genre / tempo / instrumentation / structure 等官方明确鼓励的音乐词。

# 14. 关键歧义消解

```yaml
chorus:
  song_structure: 副歌
  vocal_ensemble: 合唱/合唱队
  audio_effect: chorus effect 合唱效果器

piano:
  instrument: 钢琴
  dynamics: p / piano = 弱

bass:
  instrument: 贝斯/低音提琴等
  register: 低音区
  musical_line: bassline 低音线

modulation:
  harmony: 转调
  production: 调制效果/参数调制

cadence:
  music: 终止式/乐句收束
  speech: 抑扬顿挫/语流收束

bridge:
  song_structure: 桥段
  generic_transition: 过渡连接

outro:
  song_structure: 尾奏/结尾段
  film_term: 不是“片尾曲”本身

refrain:
  song_structure: 反复句/叠句
  deprecated_translation: 反调

koto:
  correct: 日本筝
guzheng:
  correct: 古筝

erhu:
  preferred: erhu
  optional_semantic_alias: Chinese two-string fiddle
  legacy_alias_chinese_violin: candidate_only

duet:
  correct: 对唱/二重唱
  not_equal: choir
```

# 15. Artist-name 与版权/审核过滤

用户旧资料提醒“艺术家风格可能被拒绝”。当前 Suno 官方审核说明也确认：包含知名艺术家或人物姓名的生成请求可能无法生成。

因此：
- 默认把 `Xxx style` 改写成可观察的音乐属性：年代、流派、配器、音色、节奏、和声、唱法、制作。
- 不把某位知名艺人的名字作为项目稳定提示词模板。
- 参考音乐应提取“问题 → 选择 → 音乐变量”，而不是复制艺人姓名。

# 16. 电影配乐词库映射

电影配乐优先从剧情功能编译，不从 genre 起步。

## 16.1 Dialogue-safe Threat
候选轴：
`low-salience, restrained, muted low strings, bass clarinet, narrow melodic range, slow harmonic movement, low pedal point, sparse pulse, unresolved`

## 16.2 Tragedy / Fragility
候选轴：
`fragile solo instrument, sparse piano, thin sustained strings, unresolved suspensions, intimate, unsentimental, long phrase spacing`

## 16.3 Ritual / Religious Irony
候选轴：
`restrained choir, organ-like drone, bells, modal harmony, ceremonial pulse, controlled space`

## 16.4 Pursuit / Approach
候选轴：
`ostinato, low strings, restrained percussion, short figures, accelerating pulse, structural break`

## 16.5 Lower-city Daily Undercurrent
候选轴：
`dry acoustic texture, worn timbre, restrained folk color, sparse pulse, emotionally neutral surface, faint unease`

## 16.6 Suspicion / Discovery
候选轴：
`bass clarinet, muted strings, glass-like texture, slow harmonic movement, small motivic cell, restrained dynamics, unresolved space`

以上来自用户统一手册的电影配乐模板，状态为 `user_curated + project_candidate`。

# 17. Prompt Conflict Resolver

编译前检查：

- `Instrumental` 与 lead vocal / lyrics 是否同域冲突；
- `dialogue-safe / low-salience` 与 catchy hook / dense choir / aggressive drums / heroic brass 是否冲突；
- `restrained` 与 `explosive opening` 是否同一 scope；
- `rubato` 与 `steady pulse` 是否同一 scope；
- `pianissimo` 与 `fortissimo` 是否是全局冲突还是 section arc；
- `sad` 与 `cheerful` 是否是矛盾堆词还是有明确段落转变；
- `choir` 是否被错误写成 `chorus`；
- `chorus effect` 是否被误解析成歌曲副歌；
- `outro` 是否被误当作片尾曲类型；
- `R&B + No pop/No EDM` 是否应把后两项移到 Exclude；
- 电影 underscore 是否被 Verse/Chorus/Hook 结构污染。

允许“时间化矛盾”：
`Verse intimate → Chorus powerful`
属于结构变化，不是冲突。

# 18. 版本相关 Metatag Gate

以下写法只能视为 candidate，除非当前模型实测通过：
- `[immediate high note chorus]`
- `[Sad Verse]`
- `[Happy Chorus]`
- `[Powerpop Chorus]`
- `[Female Narrator]`
- `[Diva Solo]`
- `[Gregorian chant]`
- `[Dorian mode]`
- `[Lydian mode]`
- 任意把乐器、效果器、情绪直接放进 `[...]` 期待精确解析的写法。

默认优先：
1. 用标准音乐词表达语义；
2. 用 section 名称建立结构；
3. 用自然语言说明 section-local 表演；
4. 再把旧 metatag 作为 A/B 实验。

# 19. 模型执行最小原则

- 不为了“词库齐全”而把所有可用词塞进 Prompt。
- 一个 Prompt 只保留会改变输出的变量。
- 先描述目标，再使用少量 Exclude。
- 同义词最多保留能增加新维度的词，不做无差别堆叠。
- 同一轴最好给一个主值和必要的变化曲线。
- 复杂结构使用自然语言和 section 分工，而不是无限堆 metatag。
- 生成后按失败维度局部重写，不因为一个词失效就整套提示词全部更换。

# 20. 当前验证任务

待通过真实 v5.5 生成验证：
- bracket section tag vs 纯自然语言结构指令；
- `Chorus-first` 三层结构 vs `[immediate high note chorus]`；
- vocal timbre + technique + section-local performance 的可控性；
- Exclude 字段 vs 主 Style 内自然语言否定；
- `erhu` vs `Chinese two-string fiddle` 的识别差异；
- 低显著度电影 underscore 中结构词是否诱发歌曲化；
- 同一 Prompt 的 Compact Tag Stack vs Conversational Style Brief；
- 多个近义情绪词是否增加控制还是只增加噪声。

回归入口：
`../11_验收/suno_prompt_regression_cases.yaml`

来源摄取记录：
`../09_资料证据/SUNO用户提示词资料摄取记录.md`
