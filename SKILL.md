---
name: praise-hymn
description: "以可审计、可复核的流程分析、转写、编排、选歌和创作中文基督教赞美诗歌与数字简谱；适用于歌谱图片、歌本批处理、敬拜歌单和原创会众诗歌。"
metadata:
  version: "1.8.0"
---

# 企业级赞美诗歌与数字简谱

把歌谱当作需要来源追踪、视觉复核、音乐校验和版权/神学审阅的资料项目处理。默认在本地工作，不把用户歌谱上传到外部服务；不把 OCR、推测或风格惯例当作原谱事实。

## 任务路由

先把请求归入一个或多个模式，并在输出中声明模式：

- `transcribe`：从图片逐小节转写，保留原始符号和歌词对齐。
- `analyze`：分析曲式、旋律、节奏、歌词主题和敬拜用途。
- `arrange`：在不改动主旋律的前提下给出移调、和声、乐器层次和现场提示。
- `create`：写全新的、可会众传唱的中文赞美诗及数字简谱草稿。
- `curate`：按主题、聚会环节、音域、速度或乐队条件选歌并说明证据。
- `batch`：对歌本进行登记、分批处理、错误隔离和汇总。

复杂任务采用 [references/enterprise-workflow.md](references/enterprise-workflow.md) 的 G0–G4 门禁；需要机器可读交付时采用 [references/output-contract.md](references/output-contract.md) 和 [references/hymn-record.schema.json](references/hymn-record.schema.json)。签核前执行 [references/review-checklist.md](references/review-checklist.md)，涉及文件或版权时执行 [references/data-governance.md](references/data-governance.md)。读谱细节见 [references/notation-conventions.md](references/notation-conventions.md)，风格判断见 [references/style-profile.md](references/style-profile.md)。`create` 模式必须先读 [references/lyric-craft.md](references/lyric-craft.md)，再决定歌词功能、句长、结构和跟唱测试。

## 企业级最小工作流

### G0：范围与权限

记录任务模式、来源范围、目标听众、交付格式、是否允许改写现成歌词、是否只做本地处理。来源或授权不清时标记 `needs-input`，不要假定用户拥有出版权。

### G1：来源登记

对每张图片登记相对路径、文件名、扩展名、大小、SHA-256、页序和可见曲号/歌名。批量任务先运行：

```text
python scripts/catalog_hymns.py <歌本目录> -o manifest.json
```

脚本只使用标准库，输出稳定排序的 manifest，并标记缺少数字前缀、曲号冲突或内容哈希重复的文件。不要一次把全部图片加载进上下文；按 manifest 分批，单曲失败写入错误清单并继续。

来源登记后运行图片审计，检查头部、尺寸和疑似截断：

```text
python scripts/audit_images.py <歌本目录> -o image-audit.json
```

审计结果只提供结构性警告，不能替代逐张视觉判断。

### G2：视觉转写

逐张查看原图，再用 OCR/脚本辅助。先读页眉：曲号、歌名、`1=` 调、拍号、速度/表情、转调和结束提示；再按小节从左到右转写数字、`0` 休止、`-` 延音、八度点、时值线、连音弧、小节线、三连音和重复标记。每个音符/延音单位都要与歌词字对齐。

保留两层结果：`transcription.raw` 尽量贴近原图，`transcription.normalized` 只统一空格、标点和段落。看不清的符号放入 `uncertain_items`，包括稳定 ID、位置、候选读法、置信度和复核原因；不要凭“常见旋律”补齐。

### G3：校验与审阅

- **音乐**：逐小节核对拍值、延音、附点、音域、句法、终止、重复和歌词/音符数量。
- **语言**：核对汉字、断句、重音、普通话可唱性和多节歌词对应。
- **神学**：区分经文原意、教会常用表达、作者观点和祷告愿望；不伪造经文出处，不把个人愿望写成无条件应许。
- **原创性**：`create` 模式只写新歌词和新旋律；不得把样本中的连续句子或可识别旋律片段拼接成“新歌”。

置信度使用 `high / medium / low`，写入 `quality.confidence`；质量问题写入 `quality.issues`。P0（身份/调号/关键旋律）或 P1（节拍/歌词对齐）问题未关闭时，状态不能为 `approved`。具体签核项见 `references/review-checklist.md`。

### G4：交付

普通任务输出 Markdown；批量或需要复核的任务同时输出 JSON 记录、manifest、错误清单和汇总。每份交付标明 `draft / review / approved / rejected / needs-input`，列出来源、哈希、技能版本、处理模式、处理时间、未决项和变更记录。用脚本检查记录：

```text
python scripts/validate_hymn_record.py <record.json> --strict --source-root <歌本目录>
```

正式谱面、出版、公开发布或录音定稿必须由用户明确要求并经过人工复核；默认交付分析稿或草稿。涉及来源图片、版权或公开发布时遵循 `references/data-governance.md`。

## 默认输出合同

### 读谱/分析

1. **任务与来源**：模式、文件路径/页码、哈希、处理状态。
2. **曲目卡**：曲名、编号、调、拍号、速度、版本和置信度。
3. **可核对转写**：按小节分行的简谱与逐字歌词；保留 `|`、`||`、`-` 和八度/时值标记。
4. **音乐分析**：音域、动机、节奏密度、段落、高潮、终止和会众/领唱/和声建议。
5. **歌词与敬拜功能**：主题、祷告方向、适合环节和经文依据（仅列有把握者）。
6. **问题清单**：不确定项、等级、置信度、需要谁复核以及下一步。

### 原创/编曲

先读 `references/lyric-craft.md`，确定敬拜用途、中心问题/核心真理、情绪曲线、音域和可用乐器，再输出：歌名、主题、调、拍号、速度、段落结构、完整原创歌词、带小节线的数字简谱草稿、和声/编曲建议和已知限制。把“原谱事实”“创作决定”“可选建议”分开；歌词必须报告行字数、会众记忆句和未解决的可唱性问题。深度应通过“看见—承认—求光照—回转—回应”的短句推进，不能用长段解释替代会众可唱的回应。

## 风格与边界

这套歌本以简洁、直接、可会众传唱的华语敬拜歌为主，常见主/耶稣/耶和华/圣灵/十字架/恩典/跟随/呼求/感恩等主题，旋律多用级进、重复动机和清楚终止。可以借鉴这些可观察特征，但不复制任何曲目的独特歌词、标题或旋律。用户提供的受版权保护文本只用于其要求的分析、转写或获授权改编。

如果用户只问普通乐理、与赞美诗无关，或要求制作无关的图片/音频，不要自动套用本技能。
