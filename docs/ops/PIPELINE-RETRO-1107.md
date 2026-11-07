# Pipeline retro 2026-11-07

Run on nimo against the last 10 first-parent landings on `origin/main`. Command: `python3 scripts/pipeline_retro.py --offline`. GitHub answers came from `~/.cache/pfy/retro`. The network was not contacted. `github_ok` is true. Note: cached GitHub responses; network not contacted.

This is a snapshot. Other lanes were still writing pregate summaries while this was counted. The lint count below is the count at this run.

## Baseline

About 6 full-suite runs and about 127 runner-minutes per docs-only landing (39 min pregate + 44 min branch CI + 44 min main CI).

A landing is over baseline when full-suite runs are above 6 or rounded runner-minutes are above 127. Schedule minutes are listed beside that total and are not inside it. A cancelled job adds its seconds to the minutes and does not count as a suite run. A full-suite run is a pregate check that ran `python3 -m unittest discover -s tests` with status PASS or FAIL, or a CI job whose script does that and whose conclusion is not cancelled. Two such runs on one SHA are duplicated work.

The 39 min pregate in the baseline is the comparison line. These 10 landing SHAs did not retain a full pregate. Full discovers on disk for other SHAs (branch SHAs `b239a58`, `ac799d4`, `1375d6b`, about 39 min) are outside this window.

## Table

`pre` is pregate minutes. A blank `wall_s` means no retained pregate start. Full job names: `G0 (self-hosted nimo)`, `G0 (ubuntu-24.04)`.

```
sha        full  sel     pre  branch    main    self      gh   total   wall_s dup over  subject
341877173d    4    0     1.1    80.2    80.9    89.4    72.9   162.3     -834 yes  yes  strata: count an empty reply as invalid
e5c9d688ee    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  strata: fail the bench when any run is invalid
1cc1111ebe    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  strata: stay I2 after the nimo decode trial
b22dda5691    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  strata: record the Ollama bench and the fixed...
4f69919edf    4    0     0.0    77.9    77.0    88.7    66.2   154.9          yes  yes  catalog: 2026-11-07 catch-up re-rank of entri...
7ec63eed04    2    0     0.0     0.0    77.5    43.9    33.5    77.5          yes   no  catalog(x-intake): tests 166-167, receipt ign...
b87e954ceb    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  catalog(x-intake): smoke_165-167 commit-metad...
2d0e0e84b8    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  catalog(x-intake): entries 165-167 EGM, odai,...
b38db3765e    4    0     0.0    78.7    78.7    86.2    71.2   157.4          yes  yes  docs: x-intake README and gitignore for entri...
8a47858f82    0    0     0.0     0.0     0.0     0.0     0.0     0.0           no   no  test: stub unit tests for x-intake smoke 162-164
```

DUP `341877173d` full=4: `G0 (self-hosted nimo)` x2, `G0 (ubuntu-24.04)` x2. OVER runner-minutes 162.3 > 127.0.

DUP `4f69919edf` full=4: same pair x2. OVER 154.9 > 127.0. Schedule aside: 0.9 min (`nightly-models` matrix, 56s, success).

DUP `7ec63eed04` full=2: same pair x1. Under 127, so not over. Schedule aside: 108.2 min (`local-lab` job `lab (auto)`, failure, 6490s).

DUP `b38db3765e` full=4: same pair x2. OVER 157.4 > 127.0.

Six SHAs have zero Actions runs: `e5c9d688ee`, `1cc1111ebe`, `b22dda5691`, `b87e954ceb`, `2d0e0e84b8`, `8a47858f82`. They are intermediate commits in a push. Workflows ran on the tip only.

## What the minutes are

`341877173d` (tip). Push to main ran both G0 jobs to success (self-hosted 2623s, ubuntu 2174s). `workflow_dispatch` on `bot/catchup-strata-1107` ran both again (2642s, 2165s). A separate `workflow_dispatch` on main cancelled both G0 jobs at 19s and 25s. Those seconds are inside the 80.9 main minutes. They are not full-suite runs. Filemode and post-merge-brief add a few seconds. Pregate: 10 lint runs, 1.1 min, checks `lint x10`. Wall time is -834s because those lint runs started after main CI had already finished.

`4f69919edf`. Push to main ran both G0 jobs (1982s ubuntu, 2627s self-hosted). `workflow_dispatch` on `bot/catchup-1107` ran both again (1978s, 2689s). One progress-file PASS for pregate, no duration and no summary, so 0.0 pregate minutes and not a full suite.

`7ec63eed04`. Push to main ran both G0 jobs once (2628s self-hosted, 2007s ubuntu). No branch suite. The two jobs are still duplicated work. The 108.2 schedule minutes are the clock, not this push.

`b38db3765e`. `pull_request` on `catalog/x-intake-162-164` ran both G0 jobs (2578s self-hosted, 2121s ubuntu). Push to main ran both again (2584s, 2122s). One progress-file PASS, no duration. Pushes of this same SHA on `catalog/x-intake-162-164` and `catalog/x-intake-165-167` ran filemode only.

One G0 pair is about 33 to 36 min on GitHub-hosted plus about 43 to 45 min on self-hosted, about 77 to 80 min for the event. The baseline's 44 min branch plus 44 min main is about the size of one current pair, split across two labels. Two events land near 155 to 162 min, which is what crosses 127.

## Five questions

Words from the vendored software-factory skill: task, trigger, run, runner, git host, orchestrator.

### Pregate

1. An operator or a bot runs `scripts/pregate.sh`.
2. The run reads the worktree. It writes `tmp/pregate-runs` and a progress line. On these 10 SHAs the retained evidence is 10 lint runs on `341877173d` (1.1 min) and progress PASS lines with no summary for `4f69919edf` and `b38db3765e`. A full pregate runs `ubuntu-parity` and `eval-structural`, each `python3 -m unittest discover -s tests`, then skips `suite`.
3. Pregate does not start CI. A later push or dispatch starts CI on its own.
4. A human re-enters when a check FAILs.
5. Nothing stops two runs from doing the same work. Lint ran 10 times on `341877173d` after that SHA was already on main.

### Branch CI

1. `pull_request`, or `workflow_dispatch` on a branch other than main. Measured here: `pull_request` on `catalog/x-intake-162-164` for `b38db3765e`; `workflow_dispatch` on `bot/catchup-strata-1107` for `341877173d`; `workflow_dispatch` on `bot/catchup-1107` for `4f69919edf`.
2. GitHub Actions is the orchestrator. The git host is GitHub. Each event starts `eval-structural` on two runners. Both jobs run `python3 -m unittest discover -s tests`: `G0 (ubuntu-24.04)` on a GitHub-hosted runner, `G0 (self-hosted nimo)` on the self-hosted runner. The run writes the Actions job log.
3. A green branch run in this window was followed by a push to main. That push starts main CI on the same SHA. The branch run does not cancel the main run.
4. A human re-enters on a red job. The self-hosted job is `continue-on-error`. Main has no required status checks, so a red G0 does not block the push.
5. Nothing stops the branch pair and the later main pair from both running. That second event takes `341877173d`, `4f69919edf`, and `b38db3765e` from about 77 min to about 155 to 162 min.

### Main CI

1. Push to main. One push of several commits starts workflows on the tip SHA. The six intermediate SHAs have zero runs.
2. The same two G0 jobs, plus filemode and post-merge-brief (seconds). Schedule workflows are a clock: `local-lab` 108.2 min failed on `7ec63eed04`, `nightly-models` 0.9 min succeeded on `4f69919edf`. Those minutes are outside the landing total.
3. A main run does not start another suite. The next push starts the next main run.
4. A human re-enters on red. A red G0 does not stop the next push.
5. Nothing dedupes main CI against a branch run of the same SHA. `7ec63eed04` shows only the main pair: 2 full runs, 77.5 min, under 127, and still duplicated because the two G0 jobs discover the same tests.

## Lenses

Automated checks. The check that already exists and is duplicated is `python3 -m unittest discover -s tests`. It is wired as both G0 jobs in one `eval-structural` workflow, and the next event runs that pair again. Pregate's skipped `suite` check already records a third discover as redundant when a full pregate runs. `local-lab` is unwired from the landing: the landing did not trigger it, and its failure did not gate the landing.

Tool economy. The expensive repeated call is that discover. On the three over-baseline tips it ran 4 times (2 jobs, 2 events).

## Cut list

1. One full discover per pregate. Today `ubuntu-parity` and `eval-structural` each discover tests. These 10 landings did not retain a full pregate, so this cut is the known shape. It is not a measured 39 min here.
2. Do not run both G0 jobs as full discovers on the same SHA. They run the same command.
3. Do not run that pair again on push to main when the same SHA already passed it on the branch or on `workflow_dispatch`. The cached runs show no concurrency group and no skip when this SHA already has a green G0.
4. Stop repeating lint-only pregate on a SHA already on main. This snapshot has 10 of those on `341877173d`, about 1.1 min.
5. Keep schedule jobs out of the landing gate.
6. Do not add a workflow that replays the suite on each intermediate commit. The tip already pays for the batch.
7. Do not add a new CI job for this retro. No catalog tool joins local pregate logs with Actions minutes, so this report used the public Actions API cache plus local pregate and progress files, and it stops there.
