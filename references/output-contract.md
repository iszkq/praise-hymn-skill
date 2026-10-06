# 机器可读交付合同

企业批处理或需要复核的任务，使用 JSON 记录；字段命名保持稳定，便于导入数据库、检索和版本比较。完整示例见 `hymn-record.schema.json`。

```json
{
  "schema_version": "1.2",
  "record_id": "praise-hymn-001",
  "status": "review",
  "processing": {
    "skill_version": "1.4.2",
    "mode": "transcribe",
    "processed_at": "2026-10-06T00:00:00Z",
    "operator": null,
    "model": null
  },
  "source": {
    "path": "1 这一生最美的祝福.png",
    "sha256": "...",
    "page": 1,
    "title_as_seen": "这一生最美的祝福",
    "catalog_number": "1"
  },
  "metadata": {
    "key": "C",
    "meter": "4/4",
    "tempo": null,
    "language": "zh-CN"
  },
  "transcription": {
    "raw": "",
    "normalized": "",
    "notation_system": "jianpu"
  },
  "sections": [],
  "analysis": {
    "themes": [],
    "worship_use": [],
    "melodic_notes": "",
    "confidence": "medium",
    "lyric_craft": {
      "function": "安静敬拜",
      "core_question": null,
      "structure": [],
      "line_char_counts": [],
      "congregational_hook": null,
      "lyric_issues": [],
      "originality_note": null
    }
  },
  "quality": {
    "confidence": "medium",
    "issues": [],
    "field_confidence": {
      "source": "high",
      "metadata": "medium",
      "transcription": "medium",
      "lyrics": "medium"
    },
    "image_audit": null
  },
  "uncertain_items": [],
  "rights": {
    "source_provided_by_user": true,
    "reuse_permission": "unknown",
    "publication_allowed": false
  },
  "review": {
    "reviewers": [],
    "decision": "pending",
    "last_reviewed_at": null,
    "closed_issue_ids": []
  },
  "change_log": []
}
```

必填字段：`schema_version`、`record_id`、`status`、`processing`、`source`、`metadata`、`transcription`、`sections`、`analysis`、`quality`、`uncertain_items`、`rights`、`review`、`change_log`。`approved` 记录必须有来源哈希、非空的 `sections`、非低置信度、`review.decision=approved`、至少一名审核人、审核时间和已关闭的问题清单。若已有本地来源目录，使用验证脚本的 `--source-root` 实际比对哈希。

`sections[].melody` 保存按小节分组的原始或标准化简谱；`sections[].lyrics` 保存与旋律对齐的歌词行；`sections[].label` 使用 `intro`、`verse`、`chorus`、`bridge`、`coda`、`repeat` 等稳定标签。不要把编曲建议写进原谱字段。

分析型回答仍可只输出 Markdown，但应沿用同一字段顺序，并在结尾列出来源、置信度、未决项和版权状态。
