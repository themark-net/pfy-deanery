# Slice 1: per-file review with a change-impact map (replaces the 12k raw-diff cap)

Context: scripts/pfy_build_cloud.py has DIFF_CAP = 12000 and review_refusal() refuses any diff over it
(reason review-diff-too-large). The 2026-11-05 slice-2 trial made a ~24 KB, 5-file diff and was refused
after 7081 s with no commit (receipt: tmp/headless-1105/tmp/trial-receipt/receipt.json in the parent tmp dir).

## Behavior
1. Review per file: split the diff by file, review each file's hunk with the task, gate tail, and a
   change-impact map, then combine verdicts (any reject = reject; all accept = accept). Keep #308
   guarantees: the reviewer must see every line it accepts; binary-change refusal stays.
2. Change-impact map from the cataloged tools: prefer codebase-memory-mcp (examples/codebase-memory-mcp,
   binary $HOME/.local/bin/codebase-memory-mcp) for callers/callees of changed symbols; fall back to
   Tree-sitter Analyzer (catalog entry 121, --change-impact) if available; if neither is available, a plain
   `git grep` of changed symbol names, and record which source was used in the receipt (impact.source).
   Never fail the build only because the impact tool is missing.
3. Per-file size guard, configurable: PFY_REVIEW_FILE_CAP (chars, default 12000) and a --review-file-cap
   flag. A file over the cap is refused with reason review-file-too-large naming the file.
4. Check the guard EARLY: right after the agent finishes and before the full gate runs, so an oversize
   change fails in seconds, not after the 35-minute gate. Receipt records phase=precheck.

## Exit tests first (behavior, not tautology)
- A 24 KB diff across 4+ files, each under the cap, reviews successfully (stub reviewer) and commits.
- One file over the cap fails with review-file-too-large before the gate runs (assert gate never started).
- Env var and flag change the cap.
- Impact map present in each per-file review prompt; impact.source recorded; missing tools fall back.
- A reject on any one file rejects the build.
How could this fail + how do we recover: document in the test docstrings.
