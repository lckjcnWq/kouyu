# Reporting and mastery

Produce a compact report that makes the next practice decision obvious.

## Report sections

1. Session: topic, duration, level, hint mode, roles, and mission outcome.
2. Wins: specific successful turns or expressions.
3. Target coverage: independent, intent-prompted, keyword-prompted, imitated, or unused.
4. Expression review: pair the learner's actual wording with the correct or more natural expression and a short reason. Include successful wording as “keep” when it is useful evidence; label changed wording as “repair.”
5. Focus next: at most three high-value items.
6. Next drill: a 2–5 minute transfer task in a slightly different situation.

Quote only wording actually produced in the current session. If an exact learner sentence is unavailable, paraphrase and label it as a summary. Never invent a learner sentence to complete the comparison. Prioritize differences that affect correctness, naturalness, meaning, or register instead of rewriting every utterance.

## Mastery rules

- `mastered`: independently correct use in context, preferably more than once or transferred to a new turn.
- `developing`: correct after a Chinese intent hint or a light self-repair.
- `needs_review`: required English keywords, a full model, repeated repair, or remained unused.
- `not_observed`: the session never created a fair opportunity.

An assistant example never counts as learner mastery. Do not penalize the learner for a target that was not fairly elicited.

## Scoring

If a numeric summary helps, use four transparent 1–5 dimensions: task completion, clarity, range, and interaction. Avoid false precision and do not collapse them into a test-like overall grade unless requested.

Pronunciation feedback is permitted only from audible evidence. Text-only sessions must set pronunciation to `not_observed`.

## Business evidence extension

For business sessions, follow `business-english.md` and the optional fields in `workbench-data.md`. Report an outcome (`completed`, `partial`, `deferred`, `declined`, `not_observed`) separately from expression mastery. A justified refusal, no-deal or authorized escalation can be successful communication. Record observable criteria with actual evidence; `unmet` requires a fair opportunity, while `not_observed` does not imply failure. Give feedback only in observed dimensions: clarity, register, interaction, boundaries and closure. Each feedback item needs observation, evidence and a specific suggestion; do not force five comments or invent quotations. Evidence summaries must explicitly say “摘要”. Save at most three next-focus items overall.

Use a stable scene identity so the same phrase practiced in unrelated contexts does not imply cross-scene mastery. A later unobserved attempt does not erase earlier observed evidence; the workbench retains the latest observed status without claiming automatic long-term retention.

## Technical interview evidence

For Go / Web3 interviews also follow [technical-interview.md](technical-interview.md). Add the optional `interview` record from workbench-data.md, separate from English targets and business communication feedback. For each fairly elicited concept record met / partial / unmet with actual evidence, an observation under the agreed assumptions, and a specific suggestion; otherwise not_observed. Record language_support and technical_support independently. A model answer repeated correctly is assisted evidence, not independent technical mastery. For interviewer-role sessions use the learner's questions and diagnosis, never the coach candidate's answer. Do not produce a combined technical-English score or hiring verdict. Select up to three next-focus items total and one changed-condition drill. Cross-scene concept observations remain separated by role and depth; counts do not establish general competence.

## Tone

Lead with concrete evidence, not generic praise. Limit correction volume so the report remains usable. Explain natural phrasing in plain Chinese when that is the learner's support language.
