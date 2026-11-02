# Autonomous decisions 2026-11-02

- #306: rescued detached `cee9bdd` in `tmp/mvp-merge-plan-1031/tmp/stack-after` to `build/306-mvp-stack` and `bot/mvp-stack-1031` (issue's name); `bot/mvp-stack-1031` stays at `cee9bdd`, work continues on `build/306-mvp-stack`.
- #306: merged `origin/main` `2a744823` (matches the PM note); clean auto-merge, no hand resolution.
- #306: the four "stale fixtures" are the cloud catalog (C9), cloud2 catalog (C22 C31 C38 C39), review catalog (R3 R4 R11 R14), and the planted review diffs (b07); re-cut anchors, do not revert runners.
- #306: Hermes default model (`minimax-m3:cloud`) gave no response headless; Hermes `-z -m qwen3.6:35b` works and is used for the anchor re-cut.
- #306: planted set re-cut done directly in `build_cases.py` (small, spec'd edit) while Hermes ran the mutant catalogs; diffs and `cases.json` come only from the generator.
- #306: b08/g01/g04 keep their ids and labels so saved before/after rows still line up; their live grok review rounds were not re-run (cloud quota, and the replay test does not depend on diff bytes).
