# RUN-LOG mvp-review-fix-1031

Started: 2026-10-31T19:50:34Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`
Branch: `bot/mvp-review-fix-1031` (tracks `origin/bot/mvp-review-fix-1031`)
Base: `origin/bot/mvp3-review-retry`
Head at start: `94450ac` (lane drop-in on top of the MVP-3 review-retry branch)
Needs a local model: no. Do not re-run the six MVP-3 tasks. Do not start Ollama.
Historical report `eval/mvp3/REPORT.md` stays as written.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     On ./pfy build --local with the stub agent: a gitignored path that git add -A -f would stage is absent from the commit, or the run resets the index, exits 1, reason scope-commit-mismatch, and creates no branch. A no-change attempt runs the gate once, records reason no-change, puts the gate tail in the retry feedback, and does not call the review model. Green gate plus empty diff is still no-change, not PASS. Spent retries exit 1 with no branch. Existing PASS, review reject, and --no-review tests still pass. --retries default stays 2. Review stays on unless --no-review. tests.test_pfy_build_local and tests.test_pfy_build_local_review pass. No Ollama process started.
1 Goal met:                  unittest of tests.test_pfy_build_local and tests.test_pfy_build_local_review (stub agent, temp git repo, no model). Evaluator is the test runner, not the model.
2 Turn cap:                  8 implementation items after the exit card. DoD items are scope-commit, no-change, retest. Further MVP gaps from the parallel plan count toward the cap.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session.
4 Wall clock:                8 hours from 2026-10-31T19:50:34Z (stop new items by 2026-11-01T03:30:34Z, hard stop 2026-11-01T03:50:34Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge, PR, tags, main checkout) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/main or another bot branch already closed a hole, skip that item and say so here. Do not check out other branches.
Loop type:                   goal
Human gate:                  Mark merges after Tester plus Reviewer. This run does not merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Check before every item. Leave 20 minutes to write the handoff. Launch 2026-10-31T19:50:34Z, so the 8 hour bound is 2026-11-01T03:50:34Z and it fires first.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 66692480 kB (about 63.6 GiB), load 3.23, nproc 32. Under the pressure line.

## Plan

Overview: Close two measured holes in the local review loop on `./pfy build --local`. The scope check and the commit must see the same paths, and a no-change attempt must run the gate once and feed the gate tail into the retry without calling the review model. This lane does not make `--local` the default, does not turn review off, and does not change exit codes. After the DoD, take the next MVP gap from `docs/plans/MVP-PARALLEL-1031.md` on `origin/bot/mvp-plan-1031` that fits the owned files, until an exit fires.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-review-fix-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix-1031.md` | exit card committed and pushed before any product code | none | lead
- confirm-holes | `scripts/pfy_build_local.py` (read only) | `files_changed` uses `git status` without ignored files, the commit path uses `git add -A -f`, and an empty change list continues before `run_tests`. If a hole is already closed, skip that item and say so here | exits | lead
- scope-commit | `scripts/pfy_build_local.py`, `tests/test_pfy_build_local_review.py` (or `tests/test_pfy_build_local.py`) | stage only the reviewed paths (keep excludes for tmp, bytecode, and pytest cache). After `git add`, `git diff --cached --name-only` matches the reviewed set. Mismatch resets the index, fails `scope-commit-mismatch`, creates no branch. Behavior test: a gitignored extra file is absent from `git show` of the commit, or the run fails closed with no branch | confirm-holes | lead
- no-change | same owned runner and tests | on no-change, run the gate once, record `no-change`, include a distinctive line from the gate tail in the next prompt. Do not call the review model. Green gate plus empty diff is still `no-change`. Spent retries exit 1 with no branch. Behavior test with the stub agent | scope-commit | lead
- retest | tests only | `tests.test_pfy_build_local` and `tests.test_pfy_build_local_review` pass. No Ollama process started | no-change | lead
- further-gaps | owned files only | next fitting row from the parallel plan, or lane-empty exit | retest | lead
- handoff | `docs/ops/HANDOFF-mvp-review-fix-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Owned files: `scripts/pfy_build_local.py`, `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, `tests/test_pfy_local_build_eval.py` only if a review-fix change forces a line there, plus the three docs/ops files named above.

Forbidden: `scripts/pfy`, `scripts/pfy_build_p.py`, `scripts/pfy_build_cloud.py`, `scripts/pfy_local_build_eval.py`, `pfylib/`, `eval/mvp-1031/`, `eval/mvp3/REPORT.md`, `eval/mvp3/run_trial.py`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/`, `.gitignore`, catalog files (`data/tools.json`, `TOOLS.md`, `sources/`).

Risks:
- Staging only reviewed paths drops a file the review accepted under another name. Mitigation: compare cached names to the reviewed set after `git add`. On mismatch, `git reset`, reason `scope-commit-mismatch`, exit 1, no branch.
- A no-change path skips the gate or still calls the review model. Mitigation: run the gate first, record `no-change`, skip review when the diff is empty. A green gate with an empty diff stays `no-change`.
- Exit codes or the `--retries` default move. Mitigation: do not change them. Review stays on unless `--no-review`.
- A fix forces an edit in `tests/test_pfy_local_build_eval.py` or a forbidden file. Mitigation: prefer not to edit the eval test. If a forbidden file is required, record a cross-lane request and skip.
- Shared host. Mitigation: targeted `nice -n 19` unittest only. No Ollama. No `pfy build --local` outside the stub-agent tests. No full discover unless the pregate conditions hold at the end.

## Phases

### exits

Exit card and phase plan written before any product code. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix-1031.md`.

state: DONE | tests: none (docs only) | files: 2 | err: none

### confirm-holes

Checked on `122e207` before the product edit. Host: MemAvailable about 63.6 GiB, load 3.02, nproc 32. Under the pressure line. Wall cap still 2026-11-01T03:50:34Z.

Both holes are open:

- `files_changed` runs `git status --porcelain -uall` and does not pass `--ignored`.
- The commit path runs `git add -A -f -- .` with excludes for tmp, bytecode, and pytest cache.
- An empty `changed` list records `no-change` and continues or returns before `run_tests`.

A probe under `tmp/stage-probe` showed `git add -A -f -- .` stages `pipelines/smoke/kander/latest.json` when that path is gitignored, and `git add` of `:(literal)src/calc.py` plus the same excludes stages only `src/calc.py`.

state: DONE | tests: read-only plus a throwaway git probe | files: 0 | err: none

### scope-commit

Stage only the reviewed names. After `git add`, `git diff --cached --name-only` must match that set. Mismatch resets the index, reason `scope-commit-mismatch`, exit 1, no branch.

How it fails: a gitignored receipt is not in the reviewed set, so it is not staged. If the committed tree cannot pass the archive recheck (the ignored helper the tests import), the commit is rolled back and the reason is `commit-recheck-failed`. If the index gains a name the review did not see, the index is reset and the reason is `scope-commit-mismatch`.

How we recover: no `local/` branch, origin HEAD unchanged, the extra name is not on any ref.

item | commit | tests | result
scope-commit | 7bdede7 | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 70 tests in 91.800s OK

### no-change

An empty change list now runs the post-attempt gate once. The reason stays `no-change` when the gate is green. The gate tail is in the next prompt. The review model is not called. Spent retries exit 1 with no branch. `--retries` default is still 2. Review stays on unless `--no-review`.

How it fails: the agent writes nothing, so there is no diff to accept. A green gate does not become PASS.

How we recover: the next prompt contains the gate tail. When retries are spent, exit 1, reason `no-change`, no `local/` branch.

item | commit | tests | result
no-change | 88ebcae | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 72 tests in 95.741s OK

### retest

Same run as no-change. Both modules passed. No Ollama process was started by this lane. The stub HTTP server is the only model stand-in.

item | commit | tests | result
retest | same as no-change | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 72 tests in 95.741s OK
