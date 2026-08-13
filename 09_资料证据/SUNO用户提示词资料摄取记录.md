---
title: SUNO用户提示词资料摄取记录
status: active
canonical_role: sound_prompt_source_evidence
last_updated: 2026-08-13
---

# SUNO 用户提示词资料摄取记录｜2026-08-13

> 本文件记录用户本次上传资料的来源、重复关系、可支持主张、纠错与当前 Suno 官方核验。
> 它不是第二套提示词规则入口；可执行词库写入 `../01_AI电影系统/SUNO提示词词库与编译映射.md`。

# 1. 本次文件清单与哈希

| 文件 | SHA-256 | 角色 |
|---|---|---|
| suno纯音乐常用风格.txt | 5410409edaa6c2b69c10d6842906feb60e25ce2b9f5719a51d3a94a0777c8659 | 通用风格组合、黄金公式、示例 |
| Suno情感 乐器 节奏 标签提示词.txt | ac2f32f61e638d62541df7c6ce80c1df4cd3d7b91459e89e913f5e499c645ddd | 情感/乐器/节奏基础词 |
| Suno人声六大分类提示词.txt | 7543bb008d8532da2b5dca4962f6b4f4e6fe9a5f7ddecb55176dd91bee1c08dd | 主唱、童声、合唱、风格化人声 |
| Suno提示词_音乐术语中英文对照表.txt | 19c18d6fe54dfe7fca3e7892374aceccf1de5cceab6114c15872f84137a75b88 | 大型音乐/人声/速度/乐器/结构/metatag词表 |
| suno无权重提示词.docx | a7950b8030b461ef417b2e2b56dba5b4457983fa27f82934cc993499a3e7f453 | 与统一手册 DOCX 完全重复 |
| 纯R&B提示词.txt | fbf6bb604839d3d262e749423e1227cbabc1b5a451ecd2ea65568e09bdc8a61e | 单一 R&B 配方与排除项 |
| 歌曲结构-风格 乐器 嗓音等提示词.txt | 6675225d5033c36790e9d6a58e5d4d8cc0e17d3e434b72dc0289602ca1360242 | 歌曲结构、风格、乐器、人声、情绪 |
| 歌曲开头就唱副歌提示词.txt | 3643650f33d499888544dac749575e6fdbd5059311c70ffb9e21596368a4c825 | chorus-first 旧经验 |
| 嗓音、演唱技巧和音色质感等提示词.txt | a26a1ca3be7601576a182b83334d4d7e9fe19d600213251efd8626cfb21afa21 | 音色、唱法、和声、FX |
| Suno_AI电影配乐提示词统一手册_秽翼的尤斯蒂娅.docx | a7950b8030b461ef417b2e2b56dba5b4457983fa27f82934cc993499a3e7f453 | 用户已整理的电影配乐优先统一手册 |
| Suno_AI电影配乐提示词统一手册_秽翼的尤斯蒂娅.pdf | 22f9a60ba2f8182d5e2efda58c5c2a41055cf58c6ba79d50b8fef70699966dfe | 同一手册的 PDF 排版/分页版本 |

核验：
- 两份 DOCX SHA 完全一致，因此 `suno无权重提示词.docx` 不是额外独立知识源。
- DOCX 统一手册 24 页；PDF 排版版本 29 页，核心内容一致，分页不同。
- PDF 与 DOCX 已完成视觉渲染检查，未发现“文件名相同但内容完全不同”的情况。

# 2. 用户资料直接支持的知识

## 2.1 电影配乐
统一手册明确建立：
- 4–15 秒视频单元与较长 Cue 分层；
- 先判断是否需要配乐；
- underscore / source music / hybrid / no score 分流；
- dialogue-safe / low-salience；
- Spotting；
- 少量同步点；
- 长情绪弧线由 Suno 承担，逐帧卡点交后期；
- 电影 Cue 的功能模板：冷静威胁、悲剧脆弱、宗教仪式/讽刺、追逐逼近、底层日常暗流、悬疑发现。

这些与现有 `声音导演系统.md` 大体一致，本次主要新增“词库映射层、namespace、scope 与 Prompt Conflict Resolver”，而不是复制第二套配乐理论。

## 2.2 歌曲
原始文件提供：
- Verse / Chorus / Pre-Chorus / Bridge / Hook / Intro / Interlude / Outro 等结构语义；
- 歌曲开头直接副歌的旧经验；
- R&B、Pop、Rock、Hip-Hop、Electronic、Jazz、Folk、Ambient 等风格；
- vocal register / timbre / technique / harmony / production effects；
- section-local 表演变化，如 Verse breathy → Chorus powerful；
- 人声与制作效果词。

## 2.3 术语
大型中英词表覆盖：
- tempo / dynamics / articulation；
- melody / harmony / motif / cadence / modulation；
- instruments；
- spoken delivery；
- vocal effects；
- notation；
- structural tags / performance tags / vocal metatags。

# 3. 本次发现的纠错与歧义

以下不能原样进入 canonical：

- `koto = 古筝`：错误。koto 是日本筝；古筝使用 guzheng。
- `refrain = 反调`：错误。应为反复句/叠句。
- `Outro = 片尾曲`：错误。Outro 是歌曲尾奏/结尾段；片尾曲是 ending theme / end credits song 等使用场景。
- `Fade to End = 淡入结束`：错误/误导，应理解为朝结束收束或渐弱至结束，具体以编辑行为为准。
- `male & female duet = 男女合唱`：不精确，应为男女对唱/二重唱。
- `浅快 = accelerating`：中文标注错误，应为渐快/加速。
- `femalealto`：应规范化为 `female alto / contralto`。
- `chorus` 至少有副歌、合唱、chorus effect 三个 namespace。
- `piano` 既可指钢琴，也可指弱力度标记。
- `modulation` 既可指转调，也可指音频/参数调制。
- `cadence` 在音乐与口语中语义不同。
- `erhu = Chinese violin` 是旧兼容式说法，当前未取得 Suno 官方精确别名合同，只作为 candidate alias。

# 4. 当前 Suno 官方核验｜2026-08-13

## E1｜Music Glossary
来源：
https://help.suno.com/en/articles/9010177

支持：
- Suno 官方明确鼓励使用更具体的音乐词汇；
- 官方词汇包含 tempo/rhythm、dynamics/expression、song structure、melody/harmony、genres、instrumentation/texture、vocal techniques、production/effects、advanced concepts；
- Verse / Chorus / Bridge / Pre-Chorus / Intro / Outro / Hook / Refrain / Break / Drop 等结构概念有官方解释；
- ostinato、pedal point、cadence、modulation、counterpoint、dissonance/resolution 等是当前官方建议可尝试的音乐词。

边界：
- “官方词汇可用于 prompt”不等于每个词都有稳定可量化的控制强度。

## E1｜Detailed Style Instructions
来源：
https://help.suno.com/en/articles/5782849

支持：
- v4.5 起官方明确支持比短 tag stack 更详细、更自然语言化的 Style 指令；
- 因此用户资料的 `Genre + Mood + Instrument + Tempo + Vocal` 应保留为最小启发，不应成为唯一 Prompt 格式；
- 当前系统增加 `Compact Tag Stack` 与 `Conversational Style Brief` 双模式。

## E1｜Custom Mode / Instrumental
来源：
https://help.suno.com/en/articles/3726721
https://help.suno.com/en/articles/3197377

支持：
- Custom Mode 分离 Lyrics、Styles、Advanced options；
- 纯器乐可使用 Instrumental toggle；
- 因此电影配乐不再只依赖 `no vocals` 文本。

## E1｜Exclude
来源：
https://help.suno.com/en/articles/3161921

支持：
- Advanced Options 有独立 Exclude 字段；
- 用户资料中的 `No pop, no EDM`、`vocals, lyrics` 等排除语义应优先编译到 Exclude。

## E1｜Creative Sliders
来源：
https://help.suno.com/en/articles/6141377

支持：
- Weirdness、Style Influence、Audio Influence；
- 精确最优数值未被官方给出，继续保留 A/B 校准。

## E1｜v5.5
来源：
https://help.suno.com/en/articles/11362305

支持：
- 当前 v5.5 与 Voices、Custom Models、My Taste 等能力；
- 所有模型行为性 prompt 经验必须绑定版本。

## E1｜Artist/person moderation
来源：
https://help.suno.com/en/articles/3198209

支持：
- 生成请求包含知名艺术家或人物姓名时可能无法生成；
- 用户旧资料中“艺术家风格可能被拒绝”的提醒获得当前官方支持；
- 项目应把艺人名改写为可观察音乐变量，不建立 `Xxx style` 稳定模板。

# 5. 当前未被官方完整确认的部分

没有找到当前 Suno 官方 Help Center 对以下内容给出完整稳定解析合同：
- `[immediate high note chorus]`；
- `[Sad Verse]` / `[Happy Chorus]` / `[Powerpop Chorus]` 等组合 metatag；
- 把 `[Dorian mode]`、`[Lydian mode]` 等任意音乐词放进方括号后的精确作用；
- `[End]`、`[Fade to End]` 等旧模型标签在 v5.5 的稳定终止行为；
- `erhu` 与 `Chinese violin` 的当前识别差异；
- 大量 notation 词是否能提供可重复的精确演奏控制。

因此这些进入 `legacy_behavioral / candidate`，而不是稳定规则。

# 6. 学习落地

本批资料不是“整表复制成 Prompt”，而是转化为：

1. `Prompt Namespace Ontology`
2. `GLOBAL / SECTION_LOCAL / TRANSITION / MIX_POST / EXCLUDE` 作用域
3. `Compact Tag Stack / Conversational Style Brief / Lyrics-Section / Exclude` 编译模式
4. 人声五层映射：role / register / timbre / technique / production
5. 术语歧义消解
6. 歌曲与电影配乐 Prompt 分流
7. Artist-name 改写
8. Prompt Conflict Resolver
9. Metatag 版本验证门
10. targeted regression

可执行词库：
`../01_AI电影系统/SUNO提示词词库与编译映射.md`

回归：
`../11_验收/suno_prompt_regression_cases.yaml`
