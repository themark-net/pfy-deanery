# Autonomous decisions mvp-intfix-1031

One line each. Conservative default. No questions.

1. 2026-10-31T21:15:23Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Bound the loop to the drop-in exit list, the agent-loops exit card in `docs/ops/RUN-LOG-mvp-intfix-1031.md`, and `docs/ops/HANDOFF-mvp-intfix-1031.md`. Alternative was to stop and ask. The drop-in already states the exits and the handoff path.

2. 2026-10-31T21:15:23Z: Do not spawn implementation sub-agents and do not create another worktree. Both fixes share `bot/mvp-intfix-1031` and must be separate commits and pushes. The lead edits this worktree. Alternative was one sub-agent per item in `build/<phase>` worktrees. The drop-in forbids any other worktree under `tmp/` and forbids touching the main checkout. The project-map sub-agent may write gitignored `.project-map/` only.

3. 2026-10-31T21:16:00Z: `log_path_for_receipt` stays location-based. The only consumer is `rec["log"]` in `examples/local-bench/bench.py` `bench_one`. Entry 090: `relative_to` raising on a relative `--outdir` turned a good run into DROP. Recovery is a repo-relative path when the resolved log is inside the repo (a reader opens `root / log`) and an absolute resolved path when it is outside. A temp dir under `TMPDIR=$PWD/tmp` is inside the repo, so the old test's absolute assertion was the wrong contract for that placement. Fix the test for both placements, and return `str(resolved)` from the `ValueError` branch so an unresolved outside path is stored absolute. Alternative was to force every temp path to absolute even inside the repo. That would bake a machine prefix into in-repo receipts and contradict the helper docstring.
