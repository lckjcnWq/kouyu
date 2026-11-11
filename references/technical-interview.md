# Go / Web3 technical interview protocol

This is an extension of Kouyu, not a second app or model API. Reuse preview → readiness → role-play → report → archive. Its scope is Go backend / trading systems and selected Web3 backend tasks, not all Web3 occupations.

## Route and load

Resolve scripts relative to the installed skill. For Go / Web3 interview requests use `python <skill-directory>/scripts/interview.py list --search <short keywords> --limit 6` or `tracks`; offer at most six concrete choices. Load one scene with `show <id> --role candidate --level intermediate --depth implementation --duration 20 --pressure moderate`. Roles are `candidate` and `interviewer`; technical depths are `foundation`, `implementation`, `system`; pressure is `low`, `moderate`, `high`. English level and hint mode retain the ordinary values. They are independent: a beginner English speaker may practice system-depth engineering.

`show` defaults to a learner-safe brief, without reference answers, follow-up branches or technical rubrics. Before coaching, load that same scene with explicit `--coach`; this is pedagogical separation, not security against inspecting local files. Do not expose `coach_only` in the preview. The runtime curriculum is self-contained; source paths document provenance but the original web3-go directory is not required after installation. Solana and prediction markets are optional future tracks, not implied coverage.

## Preparation and controls

State that this is a simulated technical interview. Agree the architecture assumptions before starting: custodial ledger vs noncustodial swap, chain semantics and the definition of success cannot be silently mixed. Retain the full duration-scaled recognition vocabulary bank, phrases and sentence groups from lesson-design.md; use the scene terms and target expressions as seeds, not a complete card. Provide reusable explanation structures, not the solution to the selected problem. In immersion mode no unrequested technical or language hints. Wait for readiness; honor end signals immediately.

For 5–10 minutes cover one anchor question and at most one useful follow-up; 20 minutes cover the anchor and two or three responsive follow-ups; 40 minutes can add deeper failure analysis and one transfer question. No mandatory eight-level interrogation. Ask one speakable question per turn and choose the next branch from the learner's actual answer, not a random list. English level controls wording, technical depth controls engineering demands, and pressure controls fair probing/time constraints. Pressure never authorizes abuse, changing facts or withholding essential assumptions.

For candidate practice the coach is the interviewer; never invent the learner's work history. Even in project-explanation scenes, default to hypothetical design unless the learner supplies a sanitized real experience; do not convert a fictional design into past-tense production achievements. For interviewer practice the learner asks and probes, while the coach plays a fictional candidate. Assess the learner's questions, technical diagnosis and evaluation reasoning, not the coach candidate's answer as if the learner produced it. Keep answer keys hidden until report or explicit teaching help. If a role or task gives no fair opportunity to demonstrate a concept, mark it not_observed.

## Separate language support from technical support

Language assistance supplies a frame or wording without introducing a missing technical idea. Technical assistance supplies a concept, failure window, design hint or solution. Chinese intent hints that suggest a missing technical step count as technical help, even if phrased as language assistance. Track these independently for every technical observation:

- `language_support`: `none`, `intent`, `keyword`, `model`.
- `technical_support`: `none`, `probe`, `hint`, `solution`.

A neutral follow-up asking the learner to justify their existing choice is not a technical hint; use `none`. Use `probe` when a directed question points to a missing issue. Use `hint` for a substantive idea, `solution` for a reference answer. Do not count repetition or assisted correctness as independent mastery. Ask the learner whether they want wording help or a technical explanation when unclear. Correct consequential technical misconceptions by clarification; save minor English issues for the report.

## Content and feedback contract

Each scene has an immutable descriptive ID, one anchor question, depth-tagged follow-ups, assumptions, both role tasks, English targets, technical concepts, and source mappings. Coach-only rubric items identify a concept, minimum depth and criterion, with acceptable alternatives and dangerous misconceptions. Reference answers are compact original English adaptations of user-provided local material, not audited production recipes. Discuss valid alternatives rather than enforce one design. Never imply that teaching parameters, finality thresholds, margin rules or performance examples universally apply.

Report language and technical findings separately. Preserve good original wording. For technical observations quote the actual learner response or explicitly label an evidence summary, state what was correct or missing under the agreed assumptions, and give a specific suggestion. Use `met`, `partial`, `unmet`, `not_observed`; no opportunity means not_observed, not failure. Record support honestly. Do not fabricate an overall technical score, hiring recommendation, pronunciation judgment from text, or professional certification. A concept observation is contextual evidence, not proof of general expertise.

## Archive and revisit

Use domain `business`, scenario category `hiring` / 招聘面试与入职, and each scene's unique ID. Ordinary targets continue to track English expressions only. Business feedback remains communication feedback. Add optional top-level `interview` as defined in workbench-data.md: track, role, depth, pressure, question IDs and technical observations. Do not put technical dimensions in business.feedback or technical concepts in targets. Archive only sanitized learner-visible facts and observed evidence; no coach-only answers or source dumps. Missing interview fields on old sessions remain missing.

Use `python <skill-directory>/scripts/interview.py review` to retrieve observed concept evidence from the same workbench data directory. `review --concept <id>` filters one concept; `review --scene <id>` narrows a scene. Output shows latest contextual evidence by concept + technical depth + role (including explicitly unobserved concepts), candidate scenes with applicable depth-filtered criteria, and one changed-condition transfer prompt. If no bundled criterion matches the depth, it explicitly requests a custom drill. It is not a mastery score or automatic spaced-repetition schedule. A later not_observed record does not erase earlier evidence. Prompted or solved answers remain visibly assisted. For the next drill change the failure condition, reconfirm assumptions and seek an independent explanation. Keep focus_next to three items total across language and technical findings.

## Privacy and provenance

Use fictional organizations, configurations and approximate amounts. Never request private keys, wallet seed phrases, production credentials, undisclosed customer data or confidential employer material. Distinguish hypothetical design from real experience. Do not modify the source web3-go material or learner archives to manufacture evidence. The local UI is review-only; model-client data handling is governed by the selected client. Defined content and structure tests are not real learner validation.
