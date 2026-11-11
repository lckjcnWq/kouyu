# Workbench data

The workbench is a local, user-owned archive. Default to `english-speaking-workbench` in the learner's home directory. Pass the same explicit `--data-dir` to archive and serve only when another location is requested. Resolve scripts relative to this installed skill, not the learner's current workspace.

## Session object and backward compatibility

The state container is version `2`; version `1` containers remain readable. Saving upgrades the container version only, never fabricates fields on historical sessions. Do not rewrite an existing session with different content. Required session fields remain `id`, `created_at`, `topic`, `duration_minutes`, `level`, `hint_mode`, `targets`.

- `id`: unique nonempty string using letters, digits, dot, underscore or hyphen. Prefer timestamp + stable scene slug.
- `created_at`: ISO 8601 timestamp with offset, such as `2026-11-11T14:30:00+08:00`.
- `topic`: `{id, label, emoji?}`; use stable IDs, not translated labels as identity.
- `duration_minutes`: number 1–240; `level`: beginner / intermediate / advanced.
- `hint_mode`: immersion / guided / learning.
- `domain` (optional): business / everyday / other. Include on new records. Missing legacy values display 未分类, not everyday.
- `roles` (optional): `{learner, coach}` strings; `mission` (optional): visible communication goal.
- `mission_completed` (optional): boolean for older/simple tasks. It cannot express all business outcomes; use `business.outcome` for those. Do not set it false merely because a deal was declined.
- `targets`: array of `{expression, meaning_zh?, status, support?, evidence?}`. Status: mastered / developing / needs_review / not_observed. Support: independent / intent_hint / keyword_hint / model / none. Missing support defaults to none. Use only actual learner evidence. Do not copy the coach's model into learner evidence.
- `repairs` (optional): array of `{learner, natural, reason_zh}`. Preserve correct useful wording as a keep item by using the same natural text and explaining why it works. Label summaries explicitly when an exact utterance is unavailable.
- `scores` (optional): ordinary transparent 1–5 dimensions task_completion / clarity / range / interaction; not mandatory or standardized exam grades.
- `focus_next` (optional): nonempty strings, at most three when authoring.
- `next_drill` (optional): one short transfer task.
- `pronunciation` (optional): `{status: observed|not_observed, notes: [strings]}`. Text-only sessions must use not_observed and empty notes.

## Business extension (all fields optional)

Use `domain: business`. Preserve the ordinary fields and add `scenario` and `business` when evidence is available. Do not invent values just to fill the object.

```json
{
  "scenario": {
    "id": "biz-negotiation-01",
    "category_id": "negotiation",
    "category_label": "商务谈判与条件交换"
  },
  "business": {
    "industry": {"id": "software", "label": "软件、互联网与 AI 服务"},
    "context": "模拟：客户讨论年度订阅报价；双方需要确认预算与审批范围。",
    "constraints": ["折扣需要内部审批；不承诺未发布功能。"],
    "outcome": {
      "status": "deferred",
      "summary": "双方确认了需要审批的条件，尚未约定回复日期。"
    },
    "criteria": [
      {
        "criterion": "说明折扣授权边界",
        "status": "met",
        "evidence": "此处应引用本次学习者实际说出的句子；示例占位不可用于真实归档。"
      },
      {"criterion": "确认下一次回复日期", "status": "not_observed"}
    ],
    "feedback": [
      {
        "dimension": "boundaries",
        "observation": "解释了授权边界，没有直接答应降价。",
        "evidence": "此处只放实际发言或明确标注的摘要，不复制本示例。",
        "suggestion": "下次说明由谁审批，并约定回复日期。"
      }
    ],
    "next_action": "用两句话重新练习：说明审批路径并约定回复日期。"
  }
}
```

This fragment is a schema example, **not a real or directly archivable session**. A complete record also needs the required fields above. See `tests/fixtures/` for explicitly synthetic full fixtures used only by automated tests.

- `industry`: nonempty id + label. For general business practice omit it; do not require a fictitious industry choice.
- `context`, `constraints`, `next_action`: sanitized, learner-visible information only. Do not save counterpart-only facts or real client secrets.
- Outcome status: completed / partial / deferred / declined / not_observed. Declined means justified refusal or exit, not an automatic language failure.
- Criteria status: met / partial / unmet / not_observed. Every observed criterion requires nonempty evidence; unobserved evidence may be omitted. Label paraphrases as 摘要, never as exact quotes. `unmet` requires a fair opportunity and evidence of what happened.
- Feedback dimensions: clarity / register / interaction / boundaries / closure. At most one item per dimension and five items overall. Each requires observation, evidence and suggestion. Omit dimensions without evidence rather than filling them with generic praise.
- For custom scenes use `biz-custom-<slug>`, category_id custom, category_label 自定义商务场景. Bundled IDs come from `scripts/business.py`; use them consistently between attempts.

## Optional technical interview extension

Technical interviews keep `domain: business`, a unique stable scene ID and category `hiring` / 招聘面试与入职. Add `interview` only to new sessions with real conversational evidence; missing legacy fields remain missing. English expressions stay in `targets`, technical findings do not become business.feedback dimensions. The runtime scene library is separate from the archive: custom scene/concept IDs can be stored without installing a matching catalog entry.

`interview` requires:

- `track`: nonempty `{id, label}`; ID is a safe lowercase descriptive slug.
- `role`: candidate / interviewer; `depth`: foundation / implementation / system; `pressure`: low / moderate / high. These are independent from English level and hint mode.
- `question_ids`: unique nonempty question ID strings identifying questions actually practiced.
- `observations`: array of `{concept_id, label, question_id, status, language_support, technical_support, evidence?, observation?, suggestion?}`. Concept IDs are safe lowercase descriptive slugs; at most one observation per concept per session. The question_id must appear in question_ids.
- Observation status: met / partial / unmet / not_observed. Every observed item requires nonempty evidence, observation and suggestion. Label paraphrases 摘要; do not invent quotes or use a coach answer as learner evidence. Combine repeated attempts conservatively, including the help actually given.
- `language_support`: none / intent / keyword / model. `technical_support`: none / probe / hint / solution. A directed question that introduces a missing technical issue is probe, not independent performance; wording-only assistance does not automatically imply technical help. For not_observed both supports must be none; optional texts must be absent or empty.

The report states agreed assumptions and acceptable alternatives rather than rewarding one answer key. In interviewer role evidence is the learner's elicitation and diagnosis. No numeric technical mastery score or hiring verdict is inferred. For the complete authoring contract see [interview-contract.md](interview-contract.md).

Python `latest_technical` and browser `latestTechnical` aggregate by `(concept_id, depth, role)` across scenes, using newest observed evidence; a new not_observed item cannot erase earlier observations. A newer assisted answer stays visibly assisted rather than falling back to an older independent answer. Source session ID, date and scene remain attached. Markdown and webpage show technical review separately from English mastery denominators. `python <skill-directory>/scripts/interview.py review --concept <id>` reads the same archive and suggests matching scenes for a changed-condition drill. It never creates a missing data directory, edits records, claims mastery or schedules sessions automatically. Pass the same `--data-dir` used for archive/serve when overridden.

## Aggregation and review

Group records by `(domain or unclassified, scenario.id or topic.id)`, not display label. Renaming a topic must not split its history. Within each group, retain the most recent observed target status per exact trimmed expression. A new not_observed record does not erase older observed evidence. Do not merge the same phrase across unrelated scenarios or domains. Exclude never-observed targets from the mastery denominator and count them separately. Do not infer spaced repetition, cross-role transfer or enduring mastery merely from archive counts.

The webpage offers domain, category, industry and text filters over saved sessions. It does not initiate a conversation, edit source sessions or upload data. JSON preserves full history; cards show recent evidence and available history details. Markdown and webpage use the same identity and observation rules.

## Commands

```text
python <skill-directory>/scripts/workbench.py init
python <skill-directory>/scripts/workbench.py archive --input <temporary-session-json>
python <skill-directory>/scripts/workbench.py serve
```

Write the completed record to a temporary file, execute archive, and confirm success. Do not merely print JSON for the learner to maintain. The command validates fields, protects conflicting IDs, saves `sessions/<id>.json`, atomically replaces `workbench-data.json`, and regenerates `复习台.md`. Use unique session IDs and archive serially; atomic replacement does not provide cross-process write locking. Back up the whole data directory before manual changes. Avoid future-version state files; the script refuses to rewrite them.
