# Handoff: AgentDescent eval-auto trial (Entry 119), 2026-10-15

Approved by the operator as an eval-auto trial on nimo. Branch `eval/agentdescent-trial` off origin/main `7b5107d`,
worktree `~/DEVELOP/pfy-mentat/tmp/agentdescent-trial`. Results: [REPORT.md](../../examples/agentdescent-trial/REPORT.md),
[results.json](../../examples/agentdescent-trial/results/results.json).

## Result

Held-out accuracy (20 cases): **baseline 0.70, AgentDescent 0.95, DSPy MIPROv2-light 1.00**.
AgentDescent: 201 s wall-clock (596.8 s summed across workers), 36 calls. DSPy: 686 s, 388 calls, ~338k tokens.

**Recommendation: provisional — AgentDescent as the candidate, not adopted.** n=20 held-out; DSPy scored higher;
exact McNemar baseline vs AgentDescent p=0.0625, baseline vs DSPy p=0.031, AgentDescent vs DSPy p=1.0; and the cases
were written by the trial author from handoff rows. AgentDescent's case is cost and reviewability (about 1/3 the wall
time, 1/10 the calls, a four-line diff to a SKILL.md), not accuracy. **Gate adoption on a rerun with raw post text and a
larger held-out set.** Never `apply` outside a PR with Tester and Reviewer. **Do not port the "default to CATALOG"
line** into the real triage text without a SKIP-heavy (borderline-rich) set first.

## Skill choice

pfy-mentat has no dedicated X intake triage SKILL.md. The written rules the daily intake applies are README.md
"Stage 0 gate" and docs/evaluation-framework.md "Phase 0". `examples/agentdescent-trial/skill/SKILL.md` is an **excerpt** of
them (it omits the CATEGORIZATION.md pointer and the Phase 0 AI-company routing bullet; its own header wrongly says
verbatim, kept byte-identical to what was scored; see `skill/README.md`) plus a one-word output line; that is the
"current skill". Pass/fail is exact match on CATALOG/SKIP.

## Case set

`build_cases.py` (deterministic): 28 CATALOG (Entries 086-088, 095-100, 103-121 from the intake handoffs) and 33 SKIP
(the SKIPPED lists of 2026-10-06..15 handoffs). LATER items excluded. Descriptions restate the facts in the handoffs
with the verdict removed. Stratified 2/3 split, seed 230 -> `train.jsonl` (41), `heldout.jsonl` (20).

## How to rerun

```
cd ~/DEVELOP/pfy-mentat/tmp/agentdescent-trial
uv venv tmp/.venv --python 3.12 && VIRTUAL_ENV=tmp/.venv uv pip install agentdescent==0.5.1 dspy optuna
python3 examples/agentdescent-trial/build_cases.py
python3 examples/agentdescent-trial/harness.py --stage all   # or baseline | evolve | dspy; writes tmp/agentdescent-trial-run/
python3 examples/agentdescent-trial/harness.py --promote     # only path into tracked results/ and skill/SKILL.evolved.md
python3 -m unittest tests.test_agentdescent_trial_harness
```

Runs write only under `tmp/agentdescent-trial-run/` (gitignored, `$TRIAL_OUT` overrides). Each stage writes
`stage_<name>.json`, replaced wholesale, and `results.json` is rebuilt from the current run dir's stage files (no merge
with older results). `--promote` refuses a run with errors. Exit codes: 0 ok, 1 a stage failed or timed out, 3 a
watched real-HOME dir changed.

Every child goes through `examples/x-intake-local/smoke.py` `run_isolated` (new session, killpg on timeout, stripped
env, temp HOME under the worktree `tmp/`). **No bwrap**, because `--unshare-net` would cut `localhost:11434`, so **children have network egress** (only env and
HOME are isolated). The children get only `OPENAI_BASE_URL`, a dummy `OPENAI_API_KEY`, and the model name. AgentDescent uses
`--store tmp/adstore`. Around every stage, in a `finally` that also runs on failure and timeout, the harness fingerprints real
`~/.agentdescent`, `~/.cache/agentdescent`, `~/.dspy_cache`, `~/.cache/dspy` and `~/.ollama` (sha256 for files up to
1 MiB, size+mtime_ns above that, so model blobs aren't hashed) and exits 3 on any change. The recorded run used the
earlier guard (`~/.agentdescent` names only, absent before and after); it was not rerun after the guard change, waits if Ollama has a different model loaded, and refuses to start a stage if host memory use is above 60 GiB.

## Issues hit (none blocking)

- AgentDescent spec refs take factory kwargs as top-level keys (`{"ref": ..., "model": ...}`), not under `config`.
  `openai_compatible` works against Ollama's `/v1` with `reasoning_effort: "none"` passed through as a body field.
- AgentDescent records tokens=0 from a JSON spec (usage needs a Python `Usage` object). Its `result.json`
  `fusion_trials[0].baseline_score` = 0.0 is a placeholder written for an unranked fusion trial (`fusion.py` `_record`,
  `ranked: false`), not a score. Its stop decision rests on `held_out_reward` 1.0 on its own internal split, which we
  did not verify; it may rest on unreliable internal scoring. Call count 36 is in `results/agentdescent_result.json`.
- AgentDescent stopped after round 1 because its internal held-out (30% of train) hit 1.0 >= target 0.98, so this
  trial does not exercise multi-round merging.
- MIPROv2 needs `optuna`, which plain `dspy` does not pull in; first DSPy attempt failed on that.
- Peak host memory 79 GiB (whole host, including the operator's processes) during the evolve invocation. No lock-up.

## Tester FAIL @ cce6e2c fixed

- B1: five-dir content guard in a `finally` (timeouts too), exit 3 on change, exit 1 on stage failure or timeout.
- B2: runs go to gitignored `tmp/`, explicit `--promote`, no results merging.
- Claims: 36 calls backed by `agentdescent_result.json`/`agentdescent_rounds.jsonl`; SKILL.md labelled an excerpt;
  recommendation now provisional with McNemar p-values; baseline_score explained; relative paths in committed logs; no
  bwrap / egress noted.
- `tests/test_agentdescent_trial_harness.py`: each fix was reverted in turn and the tests went red.

## Tester FAIL @ 07bca20 fixed

- B1': each stage record keeps its guard result; `--promote` refuses (exit 1) if any matching stage's guard failed or is missing.
- B2': `run.json` holds a run id plus SHA-256 of `skill/SKILL.md`, `cases.jsonl`, `train.jsonl`, `heldout.jsonl`; each stage record is stamped with both. `results.json` and `--promote` use only records matching the current run id and hashes (others listed under `refused_stale`); a single stage after an input change starts a new run id; `--stage all` clears the run dir first; promote copies only the files of matching, successful stages.
- Timing: AgentDescent 201 s wall-clock, 596.8 s summed across workers.

## Tester FAIL @ ac1c803 fixed

- Any new run id (no run.json, or input hashes changed) clears the whole run dir before the stage runs. Each stage deletes
  its own outputs and record when it starts. The AgentDescent run dir is the one this invocation created (set
  difference of the store before/after, exactly one), never the newest by name.
- `--promote` accepts only a COMPLETE run: baseline, evolve and dspy all present, matching run id and hashes, with a
  result, no error, and `guard.real_home_untouched is True`. Otherwise exit 1 and tracked files are untouched. On success it
  builds the new set in a temp dir next to `results/`, swaps it in by rename, and removes everything not produced by
  this run (including a stale `skill/SKILL.evolved.md`). run.json hashes also cover `harness.py` and `child.py`.
- `REPORT.md` moved from `results/` to `examples/agentdescent-trial/REPORT.md` so a promote can't delete it.
- The committed `results/` set predates run ids and stage records; a fresh `--stage all` plus `--promote` would replace it.

## Tester FAIL @ d915467 fixed

- B5: DSPy writes to `<run dir>/dspy-out`, which is removed when the stage starts (and with the run dir on a new run id).
  The stage fails if the child exits 0 without `dspy_result.json` and `dspy_program.json`.
- B6: promote is **journaled, not atomic** (two directory renames plus a file replace cannot be one atomic step). Order:
  stage the new results set in `.results.new-<tag>/` and the new skill in `skill/.SKILL.evolved.md.new`; write
  `.promote-journal.json` (state `swapping`); back up `skill/SKILL.evolved.md` to `skill/.SKILL.evolved.md.bak-<tag>`;
  rename `results/` -> `.results.old-<tag>/`; rename the new set -> `results/`; replace the skill; set state
  `committed`; delete the old set, backup and journal. Any exception before `committed` rolls back to the old
  `results/` and old `SKILL.evolved.md` and exits 1. Gitignored: `.results.new-*/`, `.results.old-*/`,
  `.promote-journal.json`, `skill/.SKILL.evolved.md.new`, `skill/.SKILL.evolved.md.bak-*`.
- **After a crash**: superseded by the B7 section below (the recovery described here at b826c43 did not handle a torn journal).
- Promote regenerates `results/agentdescent_vs_baseline.diff` (unified diff of `skill/SKILL.md` vs the promoted
  evolved skill), so the file REPORT.md cites survives a promote.
- Mutants: more than one new AgentDescent run dir is rejected; a guard flag that is truthy but not `True` is refused.
- Reviewer nits: the committed `results/` set has no `run.json` or stage records; it comes from the first harness, so
  any hashes it implies are historical until the rerun. `skill/SKILL.md`'s header no longer says verbatim, which also
  means its hash differs from the scored prompt (see `skill/README.md`).

## Tester FAIL @ b826c43 fixed (B7: crash recovery)

- The journal is written to `.promote-journal.json.tmp`, fsynced, renamed into place, and the directory is fsynced, so a
  reader sees the previous journal or the new one, never a torn one. It only records `swapping` or `committed`.
- Recovery runs at the **top** of `--promote`, before any run checks. So a promote from an incomplete or stale run
  still recovers first, then refuses.
- Recovery works from the files on disk. The journal only decides roll forward or roll back. A missing, empty, garbled
  or torn journal counts as mid-swap:
  - **`committed`** (parses and says so): keep the new `results/` and skill; delete the old set and backups.
  - **otherwise, with a `.results.old-*` present**: restore the skill from `skill/.SKILL.evolved.md.bak-*` (or remove it
    if `skill/.SKILL.evolved.md.absent-*` says there was none), also checking the copies moved into the old set during
    cleanup; then put the old set back as `results/`.
  - **otherwise, no old set**: `results/` never moved, so the skill wasn't replaced; drop the backups.
  - Then delete `.results.new-*`, `.results.trash-*`, the staged skill and the journal.
- Cleanup after `committed`: move the skill backup into the old set, rename the old set to `.results.trash-<tag>`
  (one rename), then delete it. So the old set, with its matching skill backup, is either fully there or gone.
- Bad state never shows a traceback. Promote exits 1 with a message and the manual fix:
  - more than one old set or skill backup: restore `results/` from the right `.results.old-*` or
    `git checkout -- examples/agentdescent-trial/results`, then delete the rest;
  - `results/` missing with nothing to restore from: `git checkout -- examples/agentdescent-trial/results`;
  - an OS error during recovery: restore by hand the same way, then delete `.results.*` and `.promote-journal.json`.
- Tests:
  - a simulated kill at each of the 7 phases, each with an ok, empty, garbled or missing journal, followed by a promote
    from an incomplete run;
  - a torn second (`committed`) write;
  - a kill after rename 1 and after rename 2;
  - no prior `SKILL.evolved.md`;
  - the journal write order (fsync, rename, then dir fsync);
  - ambiguous leftovers.
  Each fix was reverted in turn and the tests went red.
- REPORT wording: AgentDescent changed four lines (2 extended, 1 added, 1 replaced), not "added four lines".

## Tester FAIL @ c4904511 fixed (B8: stale old set)

Minimal change to `recover()`; no new machinery.

- **A `.results.old-*` replaces `results/` only when:**
  - `results/` is missing; or
  - a readable `swapping` journal names that old set's tag.

  An empty, garbled or torn journal still counts as mid-swap, but only under those two conditions.
- **Otherwise promote refuses (exit 1) and changes nothing.** It names the stale dir and gives the manual fix: inspect
  it, then `rm -rf examples/agentdescent-trial/.results.old-<tag>` if `results/` is right, or move `results/` aside and
  `mv` the old set into place. `results/` is never deleted in this case.
- **A `committed` journal deletes the old set only if its tag matches.** A mismatched tag is refused the same way.
- **Whenever recovery acts, it prints one `recovery: ...` line.**
- **Consequence:** a crash after the second rename combined with a lost or garbled journal now refuses and needs the
  manual fix, instead of guessing. With the fsynced journal, that needs outside corruption.
- **Tests:**
  - Tester's repro: a valid `results/` plus a stale old set with no journal, through both a complete and an incomplete
    promote, in plain, absence-marker and stale-skill-backup variants. Every file is unchanged.
  - A garbled journal and a swapping journal for another tag, each with a valid `results/`.
  - A forged committed journal with a mismatched tag.
  - The results-missing message and the OS-error message.
  - The crash-phase matrix updated to the new rule.

## Tester FAIL @ bccac7a fixed (B9: manual fix ignored the skill)

- **The refusal gives literal commands, run from `examples/agentdescent-trial/`, for each choice:**
  - **keep `results/`:** `mv skill/.SKILL.evolved.md.new skill/SKILL.evolved.md` (only if the staged skill is still
    there), then remove the skill backup or marker and `rm -rf .results.old-<tag>`.
  - **restore the old set:** either `mv` the skill backup (`skill/.SKILL.evolved.md.bak-<tag>`, or `.skill_backup`
    inside the old set after cleanup started) to `skill/SKILL.evolved.md`, or `rm -f skill/SKILL.evolved.md` if the
    no-skill marker is present. Then remove the staged skill and `rm -rf results && mv .results.old-<tag> results`.
  - **either way:** then `rm -f .promote-journal.json`.
- **With no old set:** a skill backup, marker or staged skill is deleted only if a `.results.new-<same tag>` dir proves
  the swap never started. Otherwise promote refuses, names the files, and prints no `recovery:` line.
- **Forged committed journal with `results/` missing:** the message says the old set is the only copy and offers only
  the restore commands.
- **Journal reading:** a missing, empty or garbled journal now reads the same, `(None, None)`; the separate garbled
  branch is gone.
- **Tests:** a kill after rename 2 and a kill after the skill replace, with the journal deleted. For each, the test
  follows the keep and the restore command from the message text literally, then checks that `results/` and the skill
  come from the same run, nothing was deleted at refusal, and a later promote succeeds. Also covered:
  - the no-skill-marker variants;
  - a backup already moved into the old set;
  - unproven and proven skill leftovers with no old set;
  - the forged-committed message with `results/` missing.

## Next

1. Tester and Reviewer gate on this PR (harness, case set, results only; no catalog or stage changes).
2. If accepted, a separate PR proposing the AgentDescent lines for the real triage text, and a TOOLS.md/stage
   move for Entry 119 backed by this receipt.
3. Rerun with raw post text and a larger held-out set before trusting the "default to CATALOG" line.
