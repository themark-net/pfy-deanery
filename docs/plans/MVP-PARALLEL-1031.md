# MVP parallel plan 2026-10-31

Planning only. Branch `bot/mvp-plan-1031`, cut from `origin/main` `85c53dc`. No product code in this session.

Owner goal: by tonight, a functional pfy-mentat MVP. Mark runs `./pfy build` on a real small task and gets a gated, reviewed commit on a branch, with a receipt. Default is cloud Grok. `./pfy build --local` stays an opt-in fallback for when Build rate limits bite. Local stays NO-GO as the default (MVP-2 cloud 6/6 in 583.6 s, MVP-3 local loop 5/6 gate, 4/6 human accept, 3859.9 s).

This file is the lane menu. Round-1 sessions read it with `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. The operator launches one cloud Build per row of `docs/plans/MVP-PARALLEL-1031-lanes.tsv`.

## Functional MVP Definition of Done

Daily command (cloud, review on, no push):

```text
./pfy build "<task>"
```

Optional flags the DoD requires: `--repo DIR`, `--base REF` (default `origin/main`), `--test-cmd CMD` (default `python3 -m unittest discover -s tests -t .`), `--retries N` (default 2 extra attempts, 3 total), `--no-review` (one attempt, no review), `--receipt-dir DIR`, `--dry-run`, `--reap`, `--keep-worktree`.

PASS observable (all of these):

1. The process exit code is 0.
2. Stdout contains one summary line: `PASS ok branch=cloud/<slug>-<stamp> receipt=<path>`.
3. `<path>/receipt.json` exists. Schema `pfy-cloud-build/1`. Fields: `schema`, `status` (`PASS`), `reason` (`ok`), `exit_code` (0), `branch` (starts with `cloud/`), `commit` (40 hex chars), `base`, `review.verdict` (`accept`), `review.reasons` (list), `attempts` (list, length at least 1, last item `status` `PASS`), `gate.cmd`, `gate.before`, `gate.after`, `recovery` (empty string on PASS), `pushed` (false), `worktree_removed` (true unless `--keep-worktree`).
4. `git rev-parse <branch>` equals `commit`. That commit is not on the caller's previous HEAD. The caller's branch name and `git status --porcelain` are unchanged. The runner did not stash, reset, or commit in the caller checkout.
5. The commit tree contains only paths the review saw. A gitignored file that was not in that set is absent from the commit.
6. Nothing was pushed. No PR was opened. `pushed` is false.

Dry-run: `./pfy build "<task>" --dry-run` exits 0, starts no grok, writes no branch, and writes a receipt with `status` `DRY-RUN` and `commit` null.

Usage: `./pfy build` with no task exits 2 and prints the daily command, plus a pointer that `-p` is the jev dogfood wrap and `--local` is the opt-in fallback.

`./pfy build -p "<prompt>"` stays `scripts/pfy_build_p.py`. Its exit codes and `receipt.jsonl` contract do not change. `tests.test_pfy_build_p` stays green.

`./pfy build --local "<task>"` stays the local runner. After the review-fix lane lands, a gitignored extra file cannot be committed, and a no-change attempt runs the gate and records the gate tail in the retry feedback. Local is not the default. Review stays on by default there (`--no-review` keeps the one-attempt path).

### Failure cases

| Case | Command result | Receipt | Recovery |
|------|----------------|---------|----------|
| Cloud rate limit | Exit 4. No branch. | `status` `BLOCKED`, `reason` `rate-limit` | `recovery` is the exact `./pfy build --local "<task>"` command. This run does not start it. Mark runs that command later, under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`, only when he chooses the fallback. |
| Cloud auth failure or grok missing | Exit 1. No branch. | `status` `FAIL`, `reason` `unauthenticated` | `recovery` is `run grok once to log in, then rerun the same ./pfy build`. The runner does not open `auth.json` and does not suggest `--local` for this case. |
| Gate red, retries left | Exit stays open. No commit yet. | Attempt row `status` `FAIL`, `reason` the gate reason (`tests`, `tests-flaky`, or `tests-tampered`) | Feedback to the next grok call includes the gate tail. A later attempt may PASS. |
| Gate red, retries spent | Exit 1. No branch. | `status` `FAIL`, `reason` the gate reason, `attempts` length 3 by default | Fix the task or the test command and rerun. The failed tree is not committed. |
| Review reject, retries left | Exit stays open. No commit of that attempt. | Attempt `status` `PASS-REJECTED`, `reason` `review-rejected`, `review.verdict` `reject` | Next grok call receives the reject reasons and the previous diff. |
| Review reject, retries spent | Exit 1. No branch. | Final `status` `FAIL`, `reason` `review-rejected` | Rerun with a tighter task, or `--no-review` only when Mark accepts an unreviewed commit. Default stays reviewed. |
| No-change attempt | Counts as an attempt. Exit 1 if retries are spent. No branch. | Attempt `reason` `no-change` | The gate still runs. Feedback includes the gate tail, not only the word `no-change`. A green gate with an empty diff is still `no-change` (no empty PASS). |
| Scope vs commit mismatch | Exit 1. No branch. Index reset. | `reason` `scope-commit-mismatch` | The commit set is the reviewed path list. `git add -A -f` is not the cloud commit. A staged name outside that list aborts the commit. |
| Dirty caller checkout | Exit 0 is still allowed when `--repo` (or the worktree base) is clean. The dirty caller files stay dirty and are not in the new commit. | PASS receipt names the new branch only | The runner never stashes or resets the caller. If the base ref itself cannot be checked out into a new worktree, exit 1, `reason` `worktree-failed`, caller status unchanged. |
| Interrupted run (SIGINT or SIGTERM) | Exit 1. No branch. | `status` `FAIL`, `reason` `interrupted` | The grok process group is signaled. |
| SIGKILL (no chance to write) | Next `./pfy build --reap` exits 0. | `status` `ABORTED`, `reason` `no-receipt` for a cloud pid-file entry whose receipt is missing | Reap signals only pgids in `tmp/cloud-build.pids.json`. It does not signal pgids that are listed only in `tmp/local-build.pids.json`. |
| Timeout | Exit 3. No branch. | `status` `TIMEOUT`, `reason` `timeout` | Rerun with a longer `--timeout`. No commit. |

Receipt text is redacted (token, bearer, AKIA, private-key blocks). A receipt that contains those raw forms is a failed run.

## Gap list

Evidence is on `origin/main` `85c53dc` unless a tip is named. Assumed landed before integration: `origin/bot/mvp3-review-retry` `4428aa3`, `origin/bot/pfy-followups-1030` `654efa7`, `origin/bot/backlog-catalog-1030` `e04e926`.

| ID | Gap | Evidence | Lane |
|----|-----|----------|------|
| G1 | There is no cloud gated runner. Non-local `pfy build` always enters `scripts/pfy_build_p.py`. | `scripts/pfy` `cmd_build` (about lines 1803-1826). No `scripts/pfy_build_cloud.py` in `git ls-files`. | mvp-cloud-1031 |
| G2 | `./pfy build "<task>"` is not a command. A missing `-p` exits 2. | `scripts/pfy_build_p.py` `main`: `FAIL: need -p "<prompt>" or --prompt-file`. Help text (`scripts/pfy` about lines 157-166) documents only `-p` and `--local`. | mvp-cloud-1031 |
| G3 | The review-and-retry loop exists only on the local runner, on the MVP-3 branch, and local is NO-GO as the default. | `git diff origin/main origin/bot/mvp3-review-retry` adds the loop in `scripts/pfy_build_local.py` (`b25fc35`). `eval/mvp3/REPORT.md` Go / no-go: gate 5/6, human accept 4/6, wall 3859.9 s. Cloud arm is not in that trial. | mvp-cloud-1031 (cloud copy of the loop, with G4 and G5 already fixed), mvp-review-fix-1031 (local loop) |
| G4 | The local scope check and the commit do not see the same files. A gitignored receipt can land. | MVP-3 `files_changed` is `git status --porcelain -uall` (no `--ignored`). Commit is `git add -A -f`. t5 commit `4b017e4` added gitignored `pipelines/smoke/kander/latest.json`. Loop accept, human reject. `docs/ops/HANDOFF-mvp3-review-retry.md` Known gaps. | mvp-review-fix-1031, and the cloud runner must not copy this bug |
| G5 | A no-change attempt does not run the gate, so the retry feedback is the string `no-change` and the review model never runs. | MVP-3 loop: empty `changed` continues before `run_tests`. t4: 3 attempts, 2203.5 s, no diff, gate still red. `eval/mvp3/REPORT.md` "What is still missing". | mvp-review-fix-1031, same rule in the cloud runner |
| G6 | Rate limit and auth failure are one undifferentiated grok failure. The dogfood path also stats `auth.json`. | `scripts/pfy_build_p.py` writes `reason` `grok_p` on a non-zero grok exit (about lines 965-969). `grok_authenticated` stats `auth.json` (about line 620). No `rate-limit` recovery command. | mvp-preflight-1031 (classifier), mvp-cloud-1031 (receipt and exit codes). Cloud must not open `auth.json`. |
| G7 | Interrupt and reap exist for local only. | `scripts/pfy_build_local.py` docstring (about lines 16-20): pid file `tmp/local-build.pids.json`, `--reap`, `ABORTED` / `no-receipt`. Cloud has no pid file. | mvp-cloud-1031 |
| G8 | No operator card for the daily command. | `docs/ops/product-operator-surface.md` does not mention `pfy build`. `docs/modules/` has no pfy-build doc. `docs/modules/README.md` has no such row. | mvp-surface-1031. Integration adds the README row. |
| G9 | Nothing checks a cloud MVP receipt, and there is no small real fixture for the demo. | `eval/mvp2/` and `eval/mvp3/` measure a hand-rolled `grok -p` or `./pfy build --local`. No `eval/mvp-1031/`. | mvp-eval-1031. Integration runs it for real. |
| G10 | Overnight leftovers that are outside this MVP. Do not spend a round-1 lane on them. | Followups `654efa7` exit 3 after skipping T-0070 (no next scorer named), T-0081 (docker cage), T-0074 (`make eval-auto` needs a local model). Backlog `e04e926` lane empty. Still open and not this MVP: T-0005 stage promotion (human, OQ-0003), T-0091 voice (shelved), T-0062 Laguna lab, missing ADR-0017 file, `catalog_stage_eval.py --apply` overwrite. | None in round 1. |

## Lanes (round 1)

Five lanes. None needs a local model. File sets do not overlap. Each lane is testable on its own branch (no cross-lane import required to go green).

### mvp-cloud-1031

- Branch: `bot/mvp-cloud-1031`
- Base: `origin/main`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-cloud-1031`
- Needs local model: no
- Handoff: `docs/ops/HANDOFF-mvp-cloud-1031.md`
- Drop-in: `docs/build-dropins/mvp-cloud-1031.md`

Scope: add the daily cloud runner and point bare `pfy build` at it. Self-contained review loop (do not import `pfylib/build_preflight.py`; duplicate the classifier with the same regexes so this branch tests alone). Do not edit the local runner or the `-p` dogfood script.

Owned files:

- `scripts/pfy_build_cloud.py` (new)
- `tests/test_pfy_build_cloud.py` (new)
- `scripts/pfy`, only the build help paragraph and `cmd_build`
- `.gitignore`, one added line: `pipelines/dogfood/build-cloud/`
- `docs/ops/HANDOFF-mvp-cloud-1031.md`, `docs/ops/RUN-LOG-mvp-cloud-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-cloud-1031.md`

Must not touch: `scripts/pfy_build_local.py`, `scripts/pfy_build_p.py`, `scripts/pfy_local_build_eval.py`, `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, `tests/test_pfy_build_p.py` (run it, do not edit), `tests/test_pfy_local_build_eval.py`, `pfylib/build_preflight.py`, `pfylib/attach.py`, `eval/mvp-1031/`, `eval/mvp3/`, `docs/modules/pfy-build.md`, `docs/ops/pfy-build-daily.md`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/README.md`, `data/tools.json`, `TOOLS.md`, `sources/`.

Dispatch rule:

- Any argv containing `--local` execs `scripts/pfy_build_local.py` (unchanged).
- First arg `-p` or `p` stays `scripts/pfy_build_p.py` (`p` shifted to `-p`, unchanged).
- First arg `--prompt` or `--prompt-file` stays `scripts/pfy_build_p.py` (do not steal the dogfood flags).
- Anything else, including `--help`, `-h`, a positional task, and `--dry-run` without `-p`, execs `scripts/pfy_build_cloud.py`.

Cloud commit rule: `git add` the reviewed relative paths only. Then `git diff --cached --name-only` must equal that set. On mismatch, `git reset` and fail `scope-commit-mismatch`. Never `git add -A -f`.

Review is a second cloud grok call. Tests inject a fake grok (`--grok-cmd` or `PFY_BUILD_GROK`). The fake prints `verdict: accept` or `verdict: reject` on the review call. No Ollama. No read of `auth.json`. Default protect globs include `auth.json`, `.env`, `*.pem`, and `pipelines/dogfood/**/grok-home/**`.

Pid file: `<repo>/tmp/cloud-build.pids.json`. Branch prefix: `cloud/`. Worktree: `<repo>/tmp/cloud-build/<stamp>/`, removed on PASS. Caller checkout is never the worktree.

Acceptance tests (behavior and fail/recover, temp git repos, fake grok, no network):

1. PASS: fake grok writes a source file, fake gate passes, fake review accepts, exit 0, branch and commit match the receipt, caller porcelain unchanged.
2. Gate red then retry then PASS: attempts length 2, commit exists only after the green attempt.
3. Review reject then retry then accept.
4. Final review reject: exit 1, `reason` `review-rejected`, no branch.
5. No-change: first attempt writes nothing, gate output appears in the second prompt, spent retries exit 1 with no branch.
6. Gitignored extra file: commit tree does not contain it. If the runner would stage it, the run fails `scope-commit-mismatch` and HEAD is unchanged.
7. Rate limit text and non-zero rc: exit 4, `reason` `rate-limit`, `recovery` contains `./pfy build --local`, no branch.
8. `not logged in` (or grok missing): exit 1, `reason` `unauthenticated`, recovery tells Mark to run `grok` once. Empty `HOME` must not raise from a missing `auth.json`.
9. Dirty caller checkout: the dirty file is still dirty and is not in the new commit.
10. SIGTERM during fake grok: exit 1, `reason` `interrupted`, no branch. `--reap` writes `ABORTED` for a cloud pid with no receipt, and does not signal a subprocess listed only in the local pid file.
11. `pfy build -p --help` still reaches the dogfood help. `pfy build --help` names `./pfy build "<task>"`. `tests.test_pfy_build_p` still passes.

### mvp-review-fix-1031

- Branch: `bot/mvp-review-fix-1031`
- Base: `origin/bot/mvp3-review-retry`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`
- Needs local model: no
- Handoff: `docs/ops/HANDOFF-mvp-review-fix-1031.md`
- Drop-in: `docs/build-dropins/mvp-review-fix-1031.md`

Scope: close G4 and G5 on the local runner only. Do not re-run the six-task local trial. Do not make `--local` the default. Do not turn review off.

Owned files:

- `scripts/pfy_build_local.py`
- `tests/test_pfy_build_local.py`
- `tests/test_pfy_build_local_review.py`
- `tests/test_pfy_local_build_eval.py` only if a review-fix change forces a line in that file
- the three `docs/ops/` files for this lane

Must not touch: `scripts/pfy`, `scripts/pfy_build_p.py`, `scripts/pfy_build_cloud.py`, `scripts/pfy_local_build_eval.py`, `pfylib/`, `eval/mvp-1031/`, `eval/mvp3/REPORT.md` (leave the historical report), `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, catalog files.

Work:

1. After the index is built for the commit, the staged name set must equal the reviewed name set. A gitignored file that `git add -A -f` would have added is either not staged, or the run resets and fails `scope-commit-mismatch` with no branch. Prefer staging the reviewed paths and then checking. Keep the existing exclude of `tmp`, bytecode, and pytest cache.
2. On a no-change attempt, run the gate once, record `no-change`, and put the gate tail into the retry feedback. Do not call the review model without a diff. A green gate plus an empty diff is still `no-change`, not PASS.
3. Behavior tests with a stub agent (no Ollama): gitignored extra file never appears in `git show <commit>`; no-change feedback contains a distinctive gate line the stub printed.

### mvp-preflight-1031

- Branch: `bot/mvp-preflight-1031`
- Base: `origin/main`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-preflight-1031`
- Needs local model: no
- Handoff: `docs/ops/HANDOFF-mvp-preflight-1031.md`
- Drop-in: `docs/build-dropins/mvp-preflight-1031.md`

Scope: a pure classifier the cloud runner can call after integration. This branch does not edit the runner.

Owned files:

- `pfylib/build_preflight.py` (new)
- `tests/test_build_preflight.py` (new)
- the three `docs/ops/` files for this lane

Must not touch: `scripts/`, `eval/`, `docs/modules/`, `docs/TODO.md`, `docs/ops/pfy-build-daily.md`, catalog files.

Contract:

```text
classify_cloud_failure(rc, stdout, stderr) -> "rate-limit" | "unauthenticated" | "other"
```

Rules, in order, case insensitive, over `stdout + "\n" + stderr` only when `rc` is not 0:

1. `rate-limit` if the text matches `rate limit`, `usage limit`, `quota exceeded`, `too many requests`, or `429`.
2. `unauthenticated` if the text matches `unauthenticated`, `not logged in`, `please log in`, or `auth.json`.
3. Otherwise `other`.

`rc` 0 is always `other`, even if the text contains those words. The function takes no path, opens no file, and returns only the enum (it does not echo the grok text).

Acceptance: one test per rule, plus rc 0 with "rate limit" in the text returns `other`, plus a PEM-looking string in the text does not appear in the return value.

### mvp-surface-1031

- Branch: `bot/mvp-surface-1031`
- Base: `origin/main`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-surface-1031`
- Needs local model: no
- Handoff: `docs/ops/HANDOFF-mvp-surface-1031.md`
- Drop-in: `docs/build-dropins/mvp-surface-1031.md`

Scope: the operator card Mark reads. Docs and one behavior test. Do not change `scripts/pfy` (the cloud lane owns the help text). Do not edit `docs/modules/README.md` (the backlog branch edits it; integration adds the row).

Owned files:

- `docs/modules/pfy-build.md` (new)
- `docs/ops/pfy-build-daily.md` (new)
- `tests/test_pfy_build_docs.py` (new)
- the three `docs/ops/` files for this lane

Must not touch: `scripts/`, `pfylib/`, `eval/`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/README.md`, `docs/modules/pfylib.md`, catalog files.

The card states the daily command, the exit codes (0, 1, 2, 3, 4, and `--reap` exiting 0 with receipt `ABORTED`), the receipt path and schema, the failure table from this plan (rate limit, auth, gate red, review reject then retry, no-change, scope mismatch, dirty caller, interrupt, SIGKILL plus reap), and that `--local` is opt-in and not the default. It states that `./pfy build -p` remains the jev dogfood wrap. Mention `scripts/pfy_build_cloud.py` as inline code, not as a markdown link (that file is not on this branch; the backlog hygiene test fails a dangling link). Link only files that exist on `origin/main`.

Acceptance: `tests.test_pfy_build_docs` fails if the card drops the daily command, an exit code, the schema name, `--local` as opt-in, the `-p` dogfood sentence, or any of the nine failure names. It also fails if either new doc has a relative markdown link that does not resolve.

### mvp-eval-1031

- Branch: `bot/mvp-eval-1031`
- Base: `origin/main`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-eval-1031`
- Needs local model: no
- Handoff: `docs/ops/HANDOFF-mvp-eval-1031.md`
- Drop-in: `docs/build-dropins/mvp-eval-1031.md`

Scope: the fixture and the receipt checker the integration demo uses. Do not call grok. Do not implement the runner.

Owned files:

- `eval/mvp-1031/fixture/` (a few real Python files: a function that returns the wrong value, and a test that expects the sum)
- `eval/mvp-1031/init_fixture.sh` (inits a temp git repo and copies the fixture in; the test is red before any fix)
- `eval/mvp-1031/check_receipt.py`
- `eval/mvp-1031/README.md` (how integration invokes the demo; inline paths, no link to the plan file)
- `tests/test_mvp_1031_receipt.py`
- the three `docs/ops/` files for this lane

Must not touch: `scripts/`, `pfylib/`, `docs/modules/`, `docs/TODO.md`, `eval/mvp2/`, `eval/mvp3/`, catalog files.

Checker (exit 0 accept, exit 1 reject):

- Accept a complete PASS receipt as specified in the DoD.
- Reject `status` PASS with a null `commit`, a branch that does not start with `cloud/`, `review.verdict` not `accept`, `pushed` true, or `attempts` empty.
- Reject a receipt whose serialized JSON contains `AKIA`, `BEGIN PRIVATE KEY`, or `sk_` followed by 8 or more characters.
- The fixture init script leaves a repo whose own test fails. The test module proves that, in a temp dir, without a model.

## File ownership matrix

Round-1 lanes. One owner per file. Integration is the only later writer, and only where the matrix says so.

| File | Owner | Anyone else |
|------|-------|-------------|
| `scripts/pfy_build_cloud.py` | mvp-cloud-1031 | Integration may replace the inline classifier with an import, under 40 lines, after the merges. Else mvp-dedupe-1031 (round 2). |
| `tests/test_pfy_build_cloud.py` | mvp-cloud-1031 | Round 2 dedupe may extend it. |
| `scripts/pfy` build help and `cmd_build` only | mvp-cloud-1031 | Nobody else in round 1. |
| `.gitignore` | mvp-cloud-1031 | One added line only: `pipelines/dogfood/build-cloud/`. Nobody else edits this file. |
| `scripts/pfy_build_local.py` | mvp-review-fix-1031 | Round 2 sandbox-gate, after integrate. |
| `tests/test_pfy_build_local.py` | mvp-review-fix-1031 | Round 2 sandbox-gate. |
| `tests/test_pfy_build_local_review.py` | mvp-review-fix-1031 | Nobody else. |
| `tests/test_pfy_local_build_eval.py` | mvp-review-fix-1031 | Only if forced. Prefer not to edit. |
| `pfylib/build_preflight.py` | mvp-preflight-1031 | Round 2 dedupe may edit. |
| `tests/test_build_preflight.py` | mvp-preflight-1031 | Nobody else. |
| `docs/modules/pfy-build.md` | mvp-surface-1031 | Nobody else. |
| `docs/ops/pfy-build-daily.md` | mvp-surface-1031 | Round 2 daily-card. |
| `tests/test_pfy_build_docs.py` | mvp-surface-1031 | Nobody else. |
| `eval/mvp-1031/**` except the demo outputs below | mvp-eval-1031 | Integration writes `demo-receipt.json` and `REPORT.md`. Round 2 local-t5 writes `local-rerun/` and `rerun_local.py`. |
| `scripts/pfy_build_p.py` | none | Do not edit. Dogfood path stays. |
| `docs/TODO.md` | none in round 1 | Integration adds one MVP note. Overnight branches already edit it; merge them first. |
| `docs/PENDING-HANDOFF.md` | none in round 1 | Integration adds one dated section. |
| `docs/modules/README.md` | none in round 1 | Backlog branch edits it. Integration adds one row after that merge. |
| `docs/modules/pfylib.md` | none | Followups and backlog both edit it. Integration resolves. No MVP lane. |
| `pfylib/attach.py` | none | Followups owns the landed change. No MVP lane. |

Lane handoff, run log, and decisions files are owned by the lane named in the filename. New files not listed here are forbidden. Record a cross-lane request instead.

## Integration lane

- Name: `mvp-integrate-1031`
- Branch: `bot/mvp-integrate-1031`
- Base: `origin/main`
- Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-integrate-1031`
- Needs local model: no
- Not a row in the TSV. Launch it after the five round-1 branches have pushed, or when the wall clock says round 1 should be collected.
- Handoff: `docs/ops/HANDOFF-mvp-integrate-1031.md`
- Drop-in: `docs/build-dropins/mvp-integrate-1031.md`

Merge order (merge commits, no rebase, no force push):

1. `origin/bot/backlog-catalog-1030` (`e04e926` or later on that branch)
2. `origin/bot/pfy-followups-1030` (`654efa7` or later)
3. `origin/bot/mvp3-review-retry` (`4428aa3` or later)
4. `origin/bot/mvp-review-fix-1031`
5. `origin/bot/mvp-preflight-1031`
6. `origin/bot/mvp-surface-1031`
7. `origin/bot/mvp-eval-1031`
8. `origin/bot/mvp-cloud-1031`

If a round-1 branch is missing, merge the ones that exist, record the skip, and do not invent the missing code. The demo runs only when `scripts/pfy_build_cloud.py` and `eval/mvp-1031/check_receipt.py` are both on the branch.

Conflict rule: the file owner in the matrix wins. For `docs/TODO.md` and `docs/modules/pfylib.md`, keep both sides' facts. Do not drop a done row. Do not close or open GitHub issues.

After the merges:

1. If both the inline classifier and `pfylib.build_preflight.classify_cloud_failure` exist, switch the cloud runner to the import when that edit is under 40 lines, and keep the cloud tests green. If it is not that small, leave the inline copy and name `mvp-dedupe-1031` as the next step.
2. Full suite, once, under the lock: `nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`. Record counts. A red test that also fails on the pre-merge base is recorded and skipped (exit rule 5). A red test introduced by the merge is fixed only when the fix is inside a conflict you just resolved or is a bad import from the optional classifier wire. Otherwise record it and do not rewrite a lane's feature.
3. Demo, one real cloud run, no local model. Build the fixture with `eval/mvp-1031/init_fixture.sh` into this worktree's `tmp/` (gitignored). From the integrate checkout run `./pfy build` with `--repo` pointed at that temp repo, `--test-cmd` pointed at the fixture test, and the task text: make `add` return the sum of its two arguments so the fixture test passes. Copy the receipt to `eval/mvp-1031/demo-receipt.json`. Run `eval/mvp-1031/check_receipt.py` on it. Write `eval/mvp-1031/REPORT.md` with the command, the exit code, the branch, the commit, the review verdict, and the receipt path.
4. A rate limit or auth failure on that one demo is an honest result: commit the failure receipt, say the demo did not PASS, do not retry into `--local`, do not fabricate a PASS.
5. Add one MVP note to `docs/TODO.md`, one dated section at the top of `docs/PENDING-HANDOFF.md`, and one row in `docs/modules/README.md` for `pfy-build.md`. No Feature GO. Catalog HOLD stays. No PR, no merge to main, no tag.

Demo PASS means the DoD list above, checked by `check_receipt.py` exiting 0, plus `git -C <fixture>` showing the `cloud/` branch and the commit.

## Round 2

Launch only after `origin/bot/mvp-integrate-1031` exists and has a pushed handoff. Base for every round-2 lane is that branch. If the branch is missing, the lane writes its handoff as blocked and stops. Not in the TSV. Still one local-model lane at most.

| Name | Branch | Needs local | Owns | Scope |
|------|--------|-------------|------|-------|
| mvp-dedupe-1031 | `bot/mvp-dedupe-1031` | no | `scripts/pfy_build_cloud.py`, `tests/test_pfy_build_cloud.py`, `pfylib/build_preflight.py` | Delete the inline classifier. Call `classify_cloud_failure`. Cloud behavior tests still pass, including rate-limit and auth. |
| mvp-sandbox-gate-1031 | `bot/mvp-sandbox-gate-1031` | no | `scripts/pfy_build_local.py`, `tests/test_pfy_build_local.py` | Close the known gap in `docs/ops/HANDOFF-pfy-local-build-mvp.md`: `--unsafe-no-sandbox` must not leave the test gate unsandboxed when bwrap works. A missing bwrap still blocks unless the flag is set, and the receipt records that the gate was unsandboxed only in that missing-bwrap case. Stub bwrap. No model. |
| mvp-local-t5-1031 | `bot/mvp-local-t5-1031` | yes | `eval/mvp-1031/rerun_local.py`, `eval/mvp-1031/local-rerun/` | One serialized rerun of MVP-3 t5 and, if time remains, t4, on the fixed local runner. Model `qwen3.6:35b` only, under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Unload when done. Do not edit product code. A product bug is a cross-lane request. Do not change the default to local. |
| mvp-daily-card-1031 | `bot/mvp-daily-card-1031` | no | `docs/ops/pfy-build-daily.md` | Append the integrate demo's real command, exit code, branch, and receipt path from `eval/mvp-1031/REPORT.md`. If the demo did not PASS, write that, and do not invent a green transcript. |

Round 2 file sets do not overlap, so they can run in parallel with each other. `mvp-local-t5-1031` is the only one that takes the heavy lock for a model.

## How to launch

Round 1 TSV columns: `name`, `branch`, `base`, `needs_local`, `dropin`. `name` equals the drop-in basename. `needs_local` is `no` or `yes`. Every round-1 value is `no`.

Integration and round 2 are drop-ins only. Do not add them to the TSV.

## Decisions

D1. The daily command is `./pfy build "<task>"`. `./pfy build -p` stays the jev dogfood wrap in `scripts/pfy_build_p.py`. Replacing `-p` would break the D1-D4 receipt contract and `tests.test_pfy_build_p`. Bare `pfy build --help` moves to the cloud help and points at both `-p` and `--local`.

D2. Cloud review is a second cloud grok call. The default path never starts Ollama. Local review stays inside `./pfy build --local`.

D3. A cloud rate limit does not auto-start `--local`. MVP-2 and MVP-3 both say local is NO-GO as the default. The receipt names the fallback command. Mark runs it if he wants.

D4. PASS does not push and does not open a PR. `pushed` is false. The branch ref remains after the worktree is removed.

D5. The cloud commit set is the reviewed path list. `git add -A -f` is forbidden on that path. Mismatch is `scope-commit-mismatch`.

D6. A no-change attempt runs the gate and is not a PASS, even if the gate is green. Empty commits do not satisfy the DoD.

D7. Round 1 has zero local-model lanes, so the five cloud sessions do not serialize on the heavy lock. The only local lane is round 2 `mvp-local-t5-1031`.

D8. The classifier is a separate module so the preflight lane does not edit the cloud runner. The cloud lane inlines the same regexes so its branch tests alone. Integration wires the import only when that edit is under 40 lines. Round 2 deletes the inline copy otherwise.

D9. The demo repo is a temp git repo from `eval/mvp-1031/fixture`, via `--repo`. The integrate checkout is not the task target. The receipt is copied to `eval/mvp-1031/demo-receipt.json`.

D10. Out of scope tonight: T-0081, the T-0074 model run, a new T-0070 scorer, T-0005 promotion, voice, Laguna, writing ADR-0017, catalog `--apply`, Feature GO, and any catalog HOLD change. A lane that believes it needs a new ADR writes an OQ draft in its handoff and skips the item.

D11. Round-1 lanes do not edit `docs/TODO.md` or `docs/PENDING-HANDOFF.md`. Those files already diverge on the overnight branches. Integration is the single writer after the merges.

D12. Lane host-pressure floor stays 16 GiB, as in the common rules. The followups log used 32 GiB. This plan does not rewrite the common rules.

D13. Local review defaults stay as MVP-3 left them (review on, `--retries` default 2). The review-fix lane does not disable the loop and does not change exit codes (0 PASS or reap or dry-run, 1 FAIL including review reject and interrupt, 2 usage, 3 TIMEOUT, 4 BLOCKED). Cloud uses the same exit codes. `--reap` exits 0 while the receipt says `ABORTED`.

D14. Cloud branch prefix is `cloud/`. Local prefix stays `local/`, which MVP-3 already uses.

D15. The cloud runner does not read or copy `auth.json`. Grok uses the operator's existing login outside the worktree. Tests use a fake grok. Detection of auth failure is from grok's own stderr and from a missing grok binary, not from statting the auth file.

D16. Default test command stays unittest discover, matching the local runner. The demo and the unit tests pass a targeted `--test-cmd` so they do not need the heavy lock. The one full discover is the integration suite, under the flock.

D17. No new ADR in this session. The default stays Grok (ADR-0002, ADR-0011). Local stays opt-in (ADR-0014 is the inference spine, not the build default). The measured MVP-2 result is the reason cloud is the daily path.

D18. G10 items are not silent skips inside a lane. They are excluded here so a lane that runs out of owned work stops on "lane empty" instead of inventing a scorer, a cage smoke, or a stage promotion.

D19. The cloud lane may add one `.gitignore` line, `pipelines/dogfood/build-cloud/`, so default receipts are not committed. No other lane edits `.gitignore`. The demo receipt that is meant to be kept is the copy at `eval/mvp-1031/demo-receipt.json`.
