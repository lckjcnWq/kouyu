# English curriculum sources

This bundled source registry belongs to the `kouyu` English-speaking skill.

- Every entry in `sources.json` has `scope: english_kouyu`.
- `direct_adaptation` sources may ground an original, compact lesson target set.
- `reference_only` sources may inform difficulty, naturalness, or activity design, but must not supply copied dialogue, instructions, or a directly adapted target list.
- Do not reconstruct or quote full textbook dialogues.

The canonical external-source authoring registry lives outside the packaged skill. `sources.json` contains only the English subset needed at runtime so the skill can be installed independently.

## Go / Web3 interview curriculum

[interview/README.md](interview/README.md) describes six tracks and 18 self-contained technical interview scenes, adapted into original English coaching cards from user-provided local professional material. Keep this provenance separate from the externally verified English-source registry; do not invent an open license or certification for the source corpus. The source paths are development provenance, not runtime dependencies. The installed package excludes the original web3-go directory. Load only one scene using scripts/interview.py and separate learner-safe preview from explicit coach-only reference material. Technical observations and English expression mastery are independent.

## Original business curriculum

`business/` contains original fictional role-play definitions, not copied textbook dialogues or newly verified external sources. Keep its provenance separate from the external-source registry. Browse [business/catalog.md](business/catalog.md), follow [business/README.md](business/README.md), or use `scripts/business.py` to search and load one scene. The 12 industry overlays share the same English scope. Do not imply that structural validation proves learner outcomes or professional certification.
