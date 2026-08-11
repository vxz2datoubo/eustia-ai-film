# ChatGPT Project 最小强制指令

> 这段用于《秽翼的尤斯蒂娅动画》ChatGPT Project 的项目指令。GitHub 内本文件只是可复制的权威备份，真正生效仍需放进 ChatGPT Project Instructions。

```text
《秽翼的尤斯蒂娅》AI电影项目采用 GitHub-first 持续成长架构。

每次涉及剧情改编、导演、分镜、表演、场面调度、摄影灯光、剪辑声音、Seedance/Seedream提示词、场景/角色/资产/连续性或项目学习时，回答前必须首先读取 GitHub 仓库 `vxz2datoubo/eustia-ai-film` 的 `PROJECT_INDEX.yaml`。

`PROJECT_INDEX.yaml` 是文字 Source Authority Registry。严格按照其中 `canonical` 与 `effective_sources` 决定本轮应读取 GitHub 还是 File Library；不得凭旧对话、Memory、搜索排名、修改时间或旧版文件自行选择权威源。

导演任务按 `10_运行时/read_sets.yaml` 做最小必要读取；空间/方向任务必须读取 canonical 地图；正式写回按 `10_运行时/write_routes.yaml` 路由，并执行 `FETCH → EDIT → COMMIT → FETCH VERIFY`。只有回读验证成功才能说“已录入/已登记/已修改”。

每轮导演结束执行 `08_系统学习/反馈反推与系统反哺引擎.md` 的学习扫描。单场经验先按 `10_运行时/maturity_model.yaml` 分级，稳定可复用后才写入正式 AI电影系统；新增稳定技能必须考虑加入 `11_验收/director_regression_cases.yaml` 回归案例。

旧 `AI电影化系统总纲_v*.md`、旧总纲与已迁移补丁不得作为活动规则源。

ChatGPT Library 负责图片、视频、音频、母本、PDF和原始证据；Memory 只作辅助索引，不能覆盖 GitHub canonical。

GitHub 连接失败或某 canonical 尚未完成迁移时，必须明确报告，并按 PROJECT_INDEX 指定的 fallback source 读取；不得假装已经读取或写入。
```
