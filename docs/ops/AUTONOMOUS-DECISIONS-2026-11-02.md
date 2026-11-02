# Autonomous decisions 2026-11-02

- #306: rescued detached `cee9bdd` in `tmp/mvp-merge-plan-1031/tmp/stack-after` to `build/306-mvp-stack` and `bot/mvp-stack-1031` (issue's name); `bot/mvp-stack-1031` stays at `cee9bdd`, work continues on `build/306-mvp-stack`.
- #306: merged `origin/main` `2a744823` (matches the PM note); clean auto-merge, no hand resolution.
- #306: the four "stale fixtures" are the cloud catalog (C9), cloud2 catalog (C22 C31 C38 C39), review catalog (R3 R4 R11 R14), and the planted review diffs (b07); re-cut anchors, do not revert runners.
- #306: Hermes default model (`minimax-m3:cloud`) gave no response headless; Hermes `-z -m qwen3.6:35b` works and is used for the anchor re-cut.
- #306: planted set re-cut done directly in `build_cases.py` (small, spec'd edit) while Hermes ran the mutant catalogs; diffs and `cases.json` come only from the generator.
- #306: b08/g01/g04 keep their ids and labels so saved before/after rows still line up; their live grok review rounds were not re-run (cloud quota, and the replay test does not depend on diff bytes).
- #306: Hermes `-z -m qwen3.6:35b` on the mutant re-cut ran 45 min (timeout 2700, exit 124) with zero edits; fell back to Grok Build headless (`grok --prompt-file ... --always-approve`, same task file), which finished in about 9 min, exit 0.
- #306: Build's re-cut of C9 C22 C31 C38 C39 R3 R4 R11 R14 reviewed line by line and kept; R3/R4 anchor on the HTTP/transport outage branch (includes its `if`), R14 flips `_test_seam_on()` to `return True`.
- #306: full suite at `28daaa6` found a fifth stale check (`test_selfhost_1031_log` Built-by subjects, red since `cee9bdd`). Fixed directly (small): accept the current runner `commit_subject` rule and list the 10 reworded selfhost2 SHAs by exact id. Alternative was rewording history; rejected because it needs a force-push and touches other lanes.
