# Technical interview implementation contract

This document fixes the runtime content and archive interfaces. It is not a reference answer or a learner record. All paths are relative to the installed skill.

## Runtime curriculum

`curriculum/interview/tracks.json`: an array of exactly six `{id, label, description}` objects, IDs in order `architecture`, `trading`, `risk`, `liquidity`, `web3`, `go`.

`curriculum/interview/concepts.json`: an array of unique `{id, label, description}` objects. IDs match `[a-z][a-z0-9-]*`; reuse a concept across scenes where meaningful (e.g. state-authority, idempotency, timeout-semantics, finality, concurrency-ownership). Concepts represent contextual observations, not certifications.

`curriculum/interview/scenes/<id>.json`: 18 full scenes, three per track. First implement the sample `int-web3-broadcast-timeout`, then one per track, then all 18. Each object contains:

- `id`: `int-<track>-<descriptive-slug>`, stable and identical to filename stem.
- `track_id`, `label`, `context` (explicit fictional / simulated assumptions).
- `assumptions`: at least two strings distinguishing architecture, scope and success semantics.
- `roles`: `candidate` and `interviewer`, each `{label, label_en, objective, constraints: [strings]}`.
- `stages`: at least three strings; `complications`: at least two.
- `terms`: at least eight distinct `{en, zh}` technical terms; `targets`: at least three `{expression, meaning_zh, function}` English expression seeds, not complete answers.
- `concepts`: unique registered concept IDs, all covered by rubric items.
- `sources`: at least one `{path, sections: [strings]}`. Paths point to real user-provided `web3-go/*.md` material and never absolute paths or `..`. Section headings / locators document provenance, not mandatory installed runtime files. Teacher cards must be self-contained; no runtime source lookup or copying full source answers.
- `coach_only.anchor`: `{id, prompt}` one English anchor question.
- `coach_only.followups`: at least three `{id, depth, trigger, prompt}`; depth is foundation / implementation / system. IDs unique within the scene (anchor + followups). Triggers say when to use a follow-up based on the actual answer.
- `coach_only.reference_answer`: concise original English technical model with explicit conditions, not an invented personal experience.
- `coach_only.rubric`: array of `{concept_id, depth, criterion, interviewer_criterion, acceptable_alternatives: [strings], misconceptions: [strings]}`. At least one per concept. Depth is the minimum fair level for this criterion. The interviewer criterion assesses the learner interviewer's questions / diagnosis, not the coach's fictional answer.
- `coach_only.candidate_profile`: a clearly fictional candidate brief for role reversal, including a plausible incomplete answer; not presented as the learner's work history.
- `coach_only.transfer`: `{prompt, changes: [strings]}` one new condition for a short transfer drill.

`index.json` is generated, version 1, content_status defined, learner_validated false, with `tracks` entries (track identity + count), `scenes` lightweight entries `{id,label,track_id,track_label,concepts,tags,path}`. Tags generated from labels, term en/zh, role labels and concept labels. `catalog.md` is generated and learner-safe. Neither index nor catalog includes answers, branches or rubric. README explains self-contained runtime and original-source provenance / limits.

## Loader interface

`python scripts/interview.py tracks|concepts|list|show|validate|build-index|review`.

- list: --track, --concept, --search, --limit (1–100, default 6); literal casefold AND search, no model / network.
- show ID: --role candidate|interviewer, --level beginner|intermediate|advanced, --depth foundation|implementation|system, --duration 1–240 integer, --pressure low|moderate|high, optional --coach.
- Default show contains domain business, scenario `{id,label,category_id:hiring,category_label:招聘面试与入职}`, track identity, context, assumptions, learner_brief, stages, terms, target_suggestions, concepts, options and readiness controls. It excludes coach_only, reference answers, followups, rubric, transfer and complications. Explicit --coach adds coach_only with followups/rubric filtered to selected maximum depth, counterpart role and duration budget. No materialization of raw source paths required at runtime.
- validate checks data integrity, exact release counts, IDs, uniqueness, registered concepts, self-contained teacher content, index and catalog freshness. Source path existence is checked only when the source root web3-go exists (development); installed packages must validate without it. Reject path traversal even without original sources.
- build-index may overwrite only the generated index/catalog after full content validation; it does not edit source scenes.
- review: --data-dir (same home default as workbench), --concept, --scene. Read existing archive without creating a missing data directory. Use workbench validation and latest_technical function via importlib so invocation with python -I works. Return contextual observations (with latest session id/time, scene, role, depth, evidence and support) plus matching scene IDs for transfer drills. No scores or writes. Unknown concept / scene filters are errors; empty archive is an explicit empty result.

## Archive extension

Optional top-level `interview` requires domain business and a nonempty scenario (stable ID; no forced lookup against installed content so custom / future scenes remain archivable):

```
interview: {
  track: {id, label},
  role: candidate | interviewer,
  depth: foundation | implementation | system,
  pressure: low | moderate | high,
  question_ids: [unique nonempty strings],
  observations: [{
    concept_id, label, question_id,
    status: met | partial | unmet | not_observed,
    language_support: none | intent | keyword | model,
    technical_support: none | probe | hint | solution,
    evidence?: string,
    observation?: string,
    suggestion?: string
  }]
}
```

For observed statuses evidence, observation and suggestion are required nonempty strings. `question_id` must occur in question_ids. At most one observation per concept per session; combine repeated evidence conservatively and reflect assistance, not cherry-picked last success. For not_observed, all optional text must be absent or empty; supports must be none. IDs are safe descriptive slugs; display labels / evidence are arbitrary escaped text. Do not require bundled concept IDs at archive time; custom concepts remain possible. No numerical score and no mastery inference.

Python `latest_technical(sessions)` and JS `latestTechnical(sessions)` return latest entries per `(concept_id, depth, role)`, across scenes, newest first; a newer not_observed entry does not erase an older observed entry. Each result is `{...observation, depth, role, track: {id,label}, session_id, created_at, scenario_id}`. Equal timestamps retain input order. A later assisted observation stays assisted; do not silently fall back to an older independent answer. Language expression aggregation is unchanged.

Markdown and webpage show technical metadata, current-session evidence and a separate contextual technical review aggregated over the selected sessions; never add technical concepts to English expression denominators. Search remains local. UI remains review-only, with no archive editing or automatic scheduling. Tests and browser data must be explicitly synthetic and stored in temporary archives.
