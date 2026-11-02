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
- #306 Tester FAIL at 89cc0d2: BX3 came in by cherry-picking 3a550e5, 0d3c0fc, 0e683b9, ff8b881 (not a merge of 4be797e), because the stack already holds the earlier retry fixes as cherry-picks and a merge would re-add their originals. The ff8b881 conflict on HANDOFF-mvp3-fix2-1031.md (absent on the stack) took the branch's version, which equals the file at 4be797e.
- #306: the B2/S3/S4 test fixes went to Grok Build, not Hermes, because Hermes timed out at 45 min with no edits on today's comparable multi-file task.
- #306 B2a: skip the real-tree dogfood2 audit only in a shallow clone with the commit absent, instead of raising CI fetch-depth, so CI stays fast and a full clone still fails on a missing commit.
- #306 S1: recorded patch-ids rather than pushing the 10 receipt commits to origin, since the patch-ids prove the diffs match without adding refs.
- #306 S6: filed #307 for the bare ./pfy ollama serve start; not fixed in this lane.
- #306 Reviewer FAIL: reworded only the 14 listed "Mark merges/cherry-picks" lines to name DevBot (and relabeled those "Human gate:" lines "Merge gate:"); other historical docs untouched.
- #306 Reviewer B4: removed the one em dash in code (scripts/pregate_orphans.py:89); the other 10 added em dashes are inside recorded receipts and planted diffs, left byte-for-byte as evidence.
- #306: filed #308 for the cloud runner's 12000-char review cut (fail closed instead), alongside #307.
