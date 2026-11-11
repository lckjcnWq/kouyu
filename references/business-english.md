# Business English training protocol

Load this reference only for business / professional requests. Reuse the ordinary preview → readiness → role-play → report → archive state machine; do not start a second skill or require a model API.

For Go / Web3 / trading-system technical interviews prioritize [technical-interview.md](technical-interview.md) and `scripts/interview.py`; the six generic hiring scenes and software industry overlay do not constitute a technical interview curriculum. Reuse this protocol's communication and privacy boundaries, not its sales-oriented outcome assumptions.

## Route without overwhelming the learner

1. Infer a concrete task from the request, not just the word “business.” Ask only for genuinely missing information; role, industry and immediate goal usually matter more than a long questionnaire.
2. Resolve `scripts/business.py` relative to this skill directory. Run `python <skill-directory>/scripts/business.py categories` for a broad request, or `list --search <keywords> --limit 6` / `list --category negotiation` for a specific task. Search is literal, not semantic: translate the request into short Chinese/English keywords, try synonyms or inspect the relevant category when no match appears. Do not silently substitute an unrelated scene.
3. Present at most 4–6 relevant concrete choices, not the full catalog. A sufficiently specific request needs no additional topic menu. Read `curriculum/business/catalog.md` only to browse the whole coverage; never read all 28 category files for one practice.
4. Load one scene with `show <id> --role a|b --level beginner|intermediate|advanced --duration 20`, optionally `--industry software`. Use `industries` to find available pack IDs. The output contains the selected scene and selected industry only.
5. Default to role A unless the request clearly describes role B; explain the selected role in the preview and allow switching. Do not ask for an industry when a general context is adequate. The catalog is a starting point, not an exhaustive promise.

Examples:

```text
python <skill-directory>/scripts/business.py list --search 报价 --limit 6
python <skill-directory>/scripts/business.py show biz-negotiation-01 --role b --industry software --level intermediate --duration 20
```

## Brief construction and information boundaries

- Treat every bundled company, number and event as fictional practice data. State “模拟商务场景” in the preview. Do not imply a real customer made these claims.
- Show the shared `context` and selected `learner_brief` objective, private information and constraints. Keep `coach_only` facts out of the learner preview and spoken output; reveal them only when the conversation reasonably elicits them. Tool output is locally inspectable, so this is pedagogical role separation, not a secret-storage guarantee.
- Never invent new facts to punish a learner or contradict established terms. State any extra simulated assumption in the preview. When an industry overlay conflicts with the base scene, explicitly adapt the background, both roles and constraints consistently before starting.
- Use industry terms, metrics and questions selectively; do not dump an entire pack or make claims about real products, laws, medical effects, financial returns or certifications.
- The three target suggestions are seeds, not the full preview or a fixed script. Adapt them to the selected learner role. Add the duration-scaled recognition word bank and phrase/sentence groups from `lesson-design.md`. Select a small active target subset; do not require every preview word to be used.
- Add 2–4 observable communication goals and the learner's authority boundaries. Do not reveal the counterpart's full objection sequence or provide a complete dialogue.
- For 5–10 minutes, practice one focused exchange, with no required complication. For 20 minutes, use at least two stages and one fair complication. For 40 minutes, use multiple stages, up to two complications and a transfer turn. For unusually short custom sessions, retain the preparation reference but narrow the active task.

## Separate three dimensions

| Dimension | What changes | What must not change |
|---|---|---|
| English level | Vocabulary, clause complexity, precision, question wording | Credibility of role, authority limits, respect |
| Hint mode | Timing and amount of help | Task scope, material volume, evidence rules |
| Counterpart pressure | Number and ambiguity of trade-offs | Truth of established facts or fairness |

Use low pressure as default for beginners and moderate pressure for intermediate/advanced practice unless the learner requests otherwise. State selected pressure in the brief. Strong pressure means a plausible time/budget constraint or a probing question, not abuse, arbitrary refusal or constantly moving the goalposts.

Do not override explicit hint mode with the level default. In particular, beginner + immersion still starts with natural English and waits for need before support.

## Counterpart behavior

- Follow business stages naturally; do not recite stage names or interrogate with several questions at once.
- Ask for a reason, a condition, a clarification or a next action when appropriate. Do not concede just because a grammatical sentence was produced.
- Accept a justified refusal, deferral, authorized escalation or no-deal outcome as potentially successful communication. Do not reward unauthorized discounts, invented guarantees or agreement at any cost.
- Preserve speakable turns. For a presentation, allow a longer learner turn without interrupting; resume with one follow-up at a time. Simulate additional stakeholders one at a time and label each speaker clearly when needed.
- Correct a meaning-changing number, unit, negation or commitment promptly; save minor grammar issues for the report. Ask what the learner intended instead of guessing.
- Treat “let's wrap up the meeting,” “close this deal,” and “we're done with onboarding” as possible in-scene language. End the training immediately only when the learner clearly addresses the practice or asks for feedback. If genuinely ambiguous, ask one out-of-character clarification; do not force another in-role reply.

## Business reporting

Use the ordinary evidence-based report, then add:

1. **Outcome:** `completed`, `partial`, `deferred`, `declined`, or `not_observed`, with a factual explanation. “Declined” describes justified refusal / exit, not automatic failure.
2. **Criteria:** label each selected communication goal `met`, `partial`, `unmet`, or `not_observed`. For observed labels, quote the learner's actual wording or label an evidence summary explicitly. Mark no fair opportunity as `not_observed`, not `unmet`.
3. **Feedback:** choose only observed, high-value dimensions: `clarity` (facts and meaning), `register` (role-appropriate directness), `interaction` (clarification and response), `boundaries` (conditions and authority), `closure` (owner, date, next step). Include observation, evidence and actionable suggestion. Do not force all five dimensions or a numeric business score.
4. **Next action:** one concrete follow-up or 2–5 minute drill. Keep `focus_next` to at most three items, including business and language issues together.

A business outcome and language mastery are separate judgments. Use the existing independent / intent-hint / keyword-hint / model evidence ladder. Never infer pronunciation from typed text. Do not put counterpart-only private facts or real client secrets into the archive.

## Custom scenes and multi-session transfer

For an unlisted task, construct the same structure: shared background; two role objectives; private facts and limits; staged task; plausible complications; role-appropriate targets; observable criteria. Assign a stable descriptive ID `biz-custom-<slug>` and category `custom` / 自定义商务场景. Do not pretend it is one of the 168 bundled definitions or silently add it to the installed library. Archive its visible, sanitized background with the session.

For follow-up practice, read the learner's existing `focus_next`, `next_drill`, visible conditions and unresolved items when available. Reconfirm time-sensitive fictional facts and permission before using real information. A sequence such as discovery → demo → negotiation → delivery can share a background, but do not claim there is an automatic CRM, persistent hidden counterpart state or spaced-repetition scheduler. The workbench stores reports, not full confidential negotiation dossiers.

## Privacy and professional boundaries

Ask for anonymized roles, approximate amounts and fictional organization names. Do not request login credentials, bank details, patient information or unpublished customer documents. All files remain local, but the model client's own data handling still follows that client's settings. Contract, employment, finance, customs, safety and medical questions require appropriately qualified confirmation; practice how to ask, qualify and escalate rather than issuing definitive advice.

## Coverage maturity

The library is original structured practice material. “Defined” means both role briefs, constraints, stages, complications, target suggestions and criteria exist. `business.py validate` establishes structural consistency only. Automatic tests and local UI checks do not prove teaching effectiveness, industry certification, or real learner outcomes. Do not call all scenes learner-validated until those observations actually exist.
