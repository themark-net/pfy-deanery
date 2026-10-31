# RUN-LOG mvp-ci-cover-1031

Started: 2026-10-31T22:41:36Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-ci-cover-1031`
Branch: `bot/mvp-ci-cover-1031` (tracks `origin/bot/mvp-ci-cover-1031`)
Base: `origin/bot/mvp-integrate-1031` at `0c3f133` (pass 2). Head at start: `6c160d3` (lane drop-in only).
Needs a local model: no. Do not pass `--local`. Do not run `scripts/pregate.sh` (the operator runs it).

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     Every tests/test_*.py added since origin/main is collected by the ubuntu-24.04 G0 job and by the nimo G0 job, via unittest discover or an explicit list. Review modules tests.test_pfy_build_local_review and tests.test_pfy_build_local_review_ci are in that set and do not skip for a missing bwrap. A structural test fails when a new tests/test_*.py would sit outside either job. Workflow image pin stays ubuntu-24.04. No gate-semantic change.
1 Goal met:                  unittest of tests.test_ci_discover_cover (fixture miss, then discover recovers; real G0 YAML covers every tests/test_*.py, including the review modules). Evaluator is the test runner, not a model. Image pin helper stays green if a workflow file changes.
2 Turn cap:                  The listed CI scope, then further CI gaps that fit this lane. Stop when the lane is empty or another exit fires. Each item is one commit and one push.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover and no pregate unless the end-of-run host check allows pregate once.
4 Wall clock:                8 hours from 2026-10-31T22:41:36Z (stop new items by 2026-11-01T06:21:36Z, hard stop 2026-11-01T06:41:36Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge to main, PR, tags, main checkout, other worktrees, signaling processes this run did not start) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/main or another bot branch already closed an item, skip it and say so here. Do not check out other branches. This run does not merge.
Loop type:                   goal
Human gate:                  Mark merges after the gate named in the handoff. This run does not merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Launch 2026-10-31T22:41:36Z, so the 8 hour bound is 2026-11-01T06:41:36Z and it fires first. Stop new items by 2026-11-01T06:21:36Z.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 59803340 kB (about 57.0 GiB), load 3.70 3.21 3.36, nproc 32. Under the pressure line.

## Plan

Overview: Confirm the ubuntu-24.04 G0 job and the nimo G0 job collect every `tests/test_*.py` added since `origin/main`, including the review modules. Record modules that skip on ubuntu because a tool, an env var, or bwrap is missing. Fix a real gap with an install step, an env var, or a fake. Add a structural test that fails when a new `tests/test_*.py` would be outside either job's discovery. Do not change gate semantics. Keep the image pin lint green.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-ci-cover-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-ci-cover-1031.md` | exit card committed before the coverage test | none | lead
- cover-test | `tests/test_ci_discover_cover.py` | fixture: an explicit list misses `tests/test_new.py` on ubuntu; switching that job to `unittest discover -s tests` clears the miss. Real `.github/workflows/eval-structural.yml` covers every `tests/test_*.py` on both G0 jobs, including the two review modules. Targeted unittest green | exits | lead
- skip-audit | read-only on today's `tests/test_*.py` and the two G0 jobs | each added module is either collected, or the skip reason is recorded. A real gap in an owned file is fixed. A gap in another lane's file is a cross-lane request | cover-test | lead
- further-gaps | G0 workflow or this lane's test and docs only | next CI coverage gap that fits, or lane empty | skip-audit | lead
- handoff | `docs/ops/HANDOFF-mvp-ci-cover-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Owned for this lane: `.github/workflows/*.yml` only to close a real discover or install gap, `tests/test_ci_discover_cover.py`, this lane's three `docs/ops/*-mvp-ci-cover-1031.md` files.

Do not edit: `scripts/pregate.sh`, `scripts/check_workflow_image_pin.py`, product runners, `docs/TODO.md`, another lane's test module.

Risks:
- A string search for "discover" stays green if the start directory moves. Mitigation: parse the YAML and interpret `-s` and `-p` (and the long flags). A fixture with `-p 'test_old*.py'` must report `tests/test_new_gap.py` as outside.
- Editing the workflow to an explicit list of today's modules would miss tomorrow's file and could break the image pin. Mitigation: leave `runs-on: ubuntu-24.04` and the existing discover lines. The test locks them.
- Unskipping bwrap tests with a fake sandbox would pass confinement checks that did not run. Mitigation: record those skips. Do not add a fake bwrap for them.
- `run_structural.py` also discovers tests. A job with only that call would still run the suite, and this test would fail. Mitigation: the decision log says the job step itself must discover or list. Recovery is to keep the discover line on the job.

## Phases

### exits

Exit card and phase plan written before the coverage test. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-ci-cover-1031.md`.

Parallel implementation sub-agents are not used. The workflow and the new test are one file set. The lead implements them in order on this branch.

state: DONE | tests: none (docs only) | files: 2 | err: none

### cover-test

Host at 2026-10-31T22:49:02Z: MemAvailable about 55.9 GiB, load 4.71, nproc 32. Under the pressure line. Wall cap still 2026-11-01T06:41:36Z.

Both suite jobs in `.github/workflows/eval-structural.yml` already run `python3 -m unittest discover -s tests -t .`. The filemode job `G0 launcher 100755` does not, and it is not a suite job. No workflow edit. Image pin helper: `PASS workflow image pin: 5 file(s)`.

`tests/test_ci_discover_cover.py` parses the workflow YAML. An explicit `unittest` list that names only `tests.test_kept` reports `tests/test_new.py` as outside the ubuntu job. The same file is covered after that job uses discover. A pattern `test_old*.py` leaves `tests/test_new_gap.py` out of both jobs. Discover from `tests/fixtures` misses a top-level module. The real workflows cover every `tests/test_*.py` (74 or more), including the two review modules. Removing the ubuntu PyYAML install makes `ubuntu_yaml_gap` fail; putting the install back before discover clears it.

`TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_ci_discover_cover -v`: Ran 6 tests in 0.014s, OK.

Reviewer check, bwrap hidden: `tests.test_pfy_build_local_review_ci` OK in 31.944s. The review module ran 17 tests, skipped 0 (`tmp/review-ci-parity/result.txt`).

item | commit | tests | result
cover-test | this commit | tests.test_ci_discover_cover 6 OK; tests.test_pfy_build_local_review_ci ran=17 skipped=0 | pass

state: DONE | tests: tests.test_ci_discover_cover 6 OK | files: 1 | err: none

### skip-audit

Today's `tests/test_*.py` from `git diff --name-only origin/main...HEAD -- tests/` all import. Both G0 jobs collect them by discover. Skips that fire when a tool is missing:

- `tests.test_hermes_bakeoff`: one test skips unless `HERMES_BAKEOFF_LIVE=1`. Live opt-in. Not a CI install.
- `tests.test_mvp_1031_sixtask_report`: one test skips only when `eval/mvp-1031/sixtask/REPORT.md` is absent. The file is in the tree, so CI runs it.
- `tests.test_workflow_image_pin`: parse cases skip when PyYAML cannot be imported. The ubuntu job installs it before discover. The new test locks that order. Nimo is not given a pip install; this host imports PyYAML 6.0.3, and followups-fix2 left the lint step on the hosted job only.
- `tests.test_pfy_build_local`: bwrap confinement tests skip when bwrap is missing. That is the ubuntu-24.04 contract in `docs/ops/PREGATE.md`. Not faked.
- `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`: skips the whole test when `grok` is not on PATH. The ubuntu image has no grok, so this help check does not run there. The file is not owned here. Cross-lane request.
- `tests.test_pfy_build_local`: `test_real_opencode_accepts_the_flags_we_pass` skips when `opencode` is missing. It checks the real binary's flags. Not a fake and not a G0 install.
- `tests.test_x_intake_smoke_149`: sandbox cases skip when bwrap is unusable. The no-bwrap exit 2 case still runs. Same contract as entry 148.
- `tests.test_pfy_build_local_review` and `tests.test_pfy_build_local_review_ci`: no skip. Confirmed with bwrap hidden, 17 tests, skipped 0.

`tests/support_tmpclean_leaker.py` is not named `test_*.py`. Discover does not collect it, on purpose. `eval/mvp2/gates/test_mvp2_*.py` stay outside `tests/` because they are red on base by design.

No owned file needed a workflow, env, or fake change. Not counted as a skipped item. The audit is the record.

item | commit | tests | result
skip-audit | this commit (docs in the run log only) | import of the 24 diff modules OK; no suite | pass, no code gap

state: DONE | tests: import 24 modules OK | files: 0 product | err: none
