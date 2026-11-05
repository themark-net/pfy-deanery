# pfy local build MVP step 3: review-and-retry loop, then re-run the MVP-2 tasks

Follow ~/.grok/skills/orchestrator/SKILL.md. This request is pre-authorized by Mark (MVP-3 approved 2026-10-30). Run unattended and ask no questions. Decide small things conservatively and log each one as a line in `docs/ops/AUTONOMOUS-DECISIONS-2026-10-30.md` (choice | alternatives | why).

## Where and hard rules

- Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp3`, branch `bot/mvp3-review-retry`. The base is `bot/mvp2-report` 85c53dc, which is origin/main 1e99251 plus the MVP-2 report. The MVP-2 assets (`eval/mvp2/tasks`, `eval/mvp2/gates`, `eval/mvp2/run_trial.py`, `eval/mvp2/results`) are on this branch.
- New commits only. Never rebase, never force-push, no PR, never merge to main. Push only `bot/mvp3-review-retry`, and push after every phase.
- Never touch Mark's main checkout `~/DEVELOP/pfy-mentat` or any other worktree under `tmp/`. Never stop, pause or renice Mark's processes, including any interactive `grok` session.
- No sudo, no package installs, no system or service changes. Never use `/tmp`; scratch goes under this worktree's `tmp/` (gitignored).
- Never print, log or commit secrets. Never read `~/.grok/auth.json` (`test -s` for existence only).
- No em dashes in anything you write.
- Model: `qwen3.6:35b` through Ollama only, the same as MVP-2. Never load a second model. Keep the existing 32 GiB `MemAvailable+SwapFree` floor; never lower it. Unload the trial model when you finish or exit.
- No cloud Build arm in this run. The MVP-2 cloud numbers are the baseline. Do not spend Build budget on re-running cloud.

## Exits (write these into the run log first, check them before every arm)

1. Done: all 6 tasks have a final local result (PASS-accepted, PASS-rejected, FAIL, BLOCKED or TIMEOUT) and the report is pushed.
2. Wall cap: 3 hours from start of the first model call. At the cap, finish the current attempt only if it ends within 10 minutes, otherwise kill its process group. Record what remains as `not-run (wall cap)`, write the report with partial numbers and push.
3. Memory or lockup: stop if `MemAvailable+SwapFree` drops below the floor, if any arm's process group outlives its timeout by more than 60 s, if `ollama ps` is unreadable twice in a row, if the Ollama API stops answering for 120 s, or if the host load average stays above 2x core count for 5 minutes. Kill only process groups this run started, unload the model, record `STOPPED <reason>` in the run log and the report, push, exit.
4. No progress: if two consecutive tasks end BLOCKED for the same infrastructure reason, stop and report it.
5. Red base: if `python3 -m unittest discover -s tests -t .` with bwrap hidden fails on the base before you change anything, record the failure and stop. Do not fix unrelated code.

## Part 1: the review-and-retry loop in `./pfy build --local`

Implement in `scripts/pfy_build_local.py` (and `pfylib/cli.py` only if a flag must be plumbed). Keep the default behavior of a run without the new flags identical except where stated.

After the agent's patch passes the gate (tests green, protected files untouched), run a review pass before reporting PASS:

1. Deterministic checks, no model needed:
   - Scope: every changed path must be allowed by the task spec. Allowed paths come from a `files:` list in the task text or `--allow-path` globs. A path outside them is a reject with the path named.
   - Size and breadth: reject when changed files exceed `--max-files` (default 3, plus the gate test file) or added plus removed lines exceed `--max-lines` (default 250). Report the numbers.
   - Required wiring: the task text may carry `require: ENV_VAR in <module>, <module>` lines (or `--require-wiring`). Each named env var or symbol must appear in the diff of every named module. Missing modules are a reject that names each one. This is the MVP-2 t5 failure: `PFY_SMOKE_RECEIPT_DIR` set in one test module and not the other.
2. Model review by the same local model. Pass it a short prompt with the task, the diff and the gate output, and ask for strict JSON `{"verdict": "accept"|"reject", "reasons": [..]}` that checks the change does exactly what the task says, at the place the task names, without widening behavior. MVP-2 t4 is the example to put in the prompt in general words: "a green test can still be wrong if the change applies to a broader block than the task names." Unparseable output counts as `reject` with reason `review-unparseable`, and that reason is fed back like any other reason.
3. On reject, start a new attempt from a clean worktree at the same base. Feed the agent the original task, the previous diff, and the reviewer's reasons. At most `--retries` (default 2) more attempts, so at most 3 in total. A gate FAIL on an attempt is also retried with the gate tail as the reason, within the same cap.
4. Receipts: one receipt per attempt (`attempt-1/receipt.json`, ...) with gate counts, diff stats, each deterministic check, model review verdict and reasons, wall seconds, and memory low-water mark. A top-level receipt names the final status (`PASS`, `PASS-REJECTED` when the last attempt was green but rejected, `FAIL`, `TIMEOUT`, `BLOCKED`), attempts used, and total wall time. Keep the existing receipt fields and their meanings.
5. Flags: `--review` / `--no-review` (default on for `--local`), `--retries N`, `--max-files`, `--max-lines`, `--allow-path`, `--require-wiring`. Record the effective values on the receipt.
6. The review model call obeys the same timeout, memory floor and sandbox as the agent. Never call a cloud model for review.

### Tests (follow prefer-behavior-and-fail-recover-tests)

Behavior and end-to-end tests in `tests/test_pfy_build_local.py` (or a new `tests/test_pfy_build_local_review.py`), using the stub agent and stub model patterns already in that file. No tautological units, no tests that only re-read a constant. Each test must be shown failing on the base or with the feature disabled; record that in the run log. Cover at least:

- A green patch that edits a file outside the allowed paths is rejected, retried with the path named in the feedback, and the second attempt that stays in scope ends PASS with `attempts: 2`.
- A green patch that sets a required env var in one of two named modules is rejected with the missing module named (the t5 shape), and the retry that wires both passes.
- A reviewer that keeps rejecting ends `PASS-REJECTED` after exactly 3 attempts, never loops further, and every attempt has its own receipt.
- Unparseable review output is a reject with `review-unparseable`, not an accept.
- A gate FAIL is retried and the gate tail reaches the next prompt.
- `--no-review` keeps the MVP-1 behavior: one attempt, PASS on a green gate.
- Recovery: killing the run mid-review leaves an ABORTED receipt via the existing stale-run cleanup, and the next run starts clean.

For each risk, state in the handoff how it fails and how we recover (for example: the reviewer is too strict, so everything ends PASS-REJECTED; recovery is `--no-review` and the receipts show which check fired).

Run the full suite with bwrap hidden (`scripts/pregate.sh --only ci-parity HEAD` is the quick form) and record baseline and final numbers. Commit and push.

## Part 2: re-run the same 6 MVP-2 tasks, local only, with the loop

- Use `eval/mvp2/tasks/*.md` and `eval/mvp2/gates/*` unchanged, at the same base `997d89264495861a178713ccf7d4447ea828afc4` (the MVP-2 base) so the numbers compare. Add each task's allowed `files:` and, only where the original spec names them, `require:` lines in a copy under `eval/mvp3/tasks/`. Do not add hints that were not in the MVP-2 spec beyond those two machine-readable lines, and record the diff of each copy against the original in the report.
- Add `eval/mvp3/run_trial.py` by copying the MVP-2 local arm, calling `./pfy build --local` with review on and `--retries 2`. No cloud arm. Prove the gates red again on the base first (`prove-red`).
- Run tasks one at a time. Unload the model between tasks when it is the only one resident, as MVP-2 did. Respect every exit above.
- Afterwards read every final diff yourself with the MVP-2 review standard and record your own accept or reject next to the loop's verdict, so loop verdicts and human-standard verdicts can both be compared with MVP-2.
- Results: `eval/mvp3/results/<task>-L.json`, patches `eval/mvp3/patches/<task>-L.patch` (evidence only; do not land task diffs), raw logs under `tmp/` (gitignored).

## Report: `eval/mvp3/REPORT.md`

A table per task and a summary row comparing MVP-3 local with MVP-2 local and MVP-2 cloud: gate pass, review accept (loop verdict and your human-standard verdict), attempts, wall time (total and per attempt), diff size, timeouts, memory blocks, gaming and scope creep. Baselines: MVP-2 local gate 5/6, review 4/6, 1694.0 s; MVP-2 cloud 6/6, 6/6, 583.6 s. State explicitly whether t4 and t5 were caught by the review and fixed by a retry, and whether the loop rejected anything MVP-2 accepted (false rejects). End with a go/no-go for making `./pfy build --local` with the loop the default for build-only runs, and what is still missing.

## Deliverables

- Code and tests on `bot/mvp3-review-retry`; `eval/mvp3/` (tasks, run_trial.py, results, patches, REPORT.md).
- `docs/ops/RUN-LOG-mvp3-review-retry.md` (exits first, then phases) and `docs/ops/AUTONOMOUS-DECISIONS-2026-10-30.md`.
- Handoff `docs/ops/HANDOFF-mvp3-review-retry.md`: status, what changed, how to run, test numbers, how each risk fails and how we recover, known gaps, next step. The gate is Tester plus Reviewer at the pinned SHA, because this changes runtime code.
- Push the branch after each phase. At the end, print the head SHA and a 10-line verdict.
