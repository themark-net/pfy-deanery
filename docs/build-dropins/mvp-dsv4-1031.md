# Lane mvp-dsv4-1031 (MVP 2026-10-31, low priority, local model)

Branch: `bot/mvp-dsv4-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dsv4-1031`
Base: `6664713` (bot/mvp3-review-retry: the MVP-3 local review loop). Never push to bot/mvp3-review-retry or main.
Run log: `docs/ops/RUN-LOG-mvp-dsv4-1031.md` (end with `state: <DONE|lane empty|blocked|wall cap> | ...`)
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-dsv4-1031.md`
Handoff (verdict): `docs/ops/HANDOFF-mvp-dsv4-1031.md`
Needs a local model: YES. Every model load, serve, or `--local` run must hold the heavy lock `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` (flock), one local job at a time. Download does not need the lock. Do not run scripts/pregate.sh; the operator runs it.

## Goal
Test the claim that the Unsloth Dynamic V3.1 GGUF of DeepSeek-V4.1-Flash-1017 performs at "Claude Sonnet 5.5 level" while running in 64GB+ RAM. Source: https://x.com/0x0SojalSec/status/2116263439681417554 (quotes an Unsloth post). Treat the claim as unverified marketing until measured.

## Steps (stop early and record if a step fails)
1. Find the Unsloth Hugging Face repo for that model (huggingface.co/unsloth/...). Record the exact repo, file names, sizes, and the Unsloth post. If it does not exist, record that, write the catalog entry as "not found", and stop.
2. Measure nimo: total RAM, free RAM, GPU and VRAM (nvidia-smi or rocm-smi if present), free disk on the target dir. Pick the largest quant whose file size plus about 8 GB of context overhead fits RAM+VRAM and leaves at least 50 GB free disk after download. If none fits, record that and stop.
3. Download with `huggingface-cli download` or curl (resumable) into `~/DEVELOP/pfy-mentat/_vendor/models/` (or the existing Ollama/llama.cpp models dir if one is already used by pfy). No sudo, no system changes. Never print tokens.
4. Serve it with an existing runtime on nimo (llama.cpp server, or Ollama via a Modelfile pointing at the GGUF). If llama.cpp must be built, build it under `_vendor/` as the user. Bind to 127.0.0.1 only. Stop the server when done and record its pid lifecycle. Never touch Mark's running Ollama models or processes; use a different port.
5. Smoke: one short prompt, record tokens/s and load time.
6. Run `./pfy build --local` (pointing at this model, per the docs for selecting a local model) on the MVP-3 six-task set (eval/mvp3/ on this branch). One pass, under the heavy lock. Record per task: gate, review verdict, human accept of the diff (your reading), attempts, wall seconds.
7. Compare with MVP-3 local results (eval/mvp3/REPORT.md: gate 5/6, loop accept 5/6, human accept 4/6, wall 3859.9 s) and MVP-2 cloud (6/6, 584 s).

## Deliverables
- A catalog entry for the model (follow the repo's catalog format: TOOLS.md / data/*.json, whichever the catalog lint uses), with honest status and measured numbers.
- `eval/mvp-1031/dsv4/REPORT.md` and receipts.
- Verdict handoff: does it reach the claimed level on this task set? GO/NO-GO as a local default.
Gate as catalog/docs (Reviewer plus pregate). Keep catalog lint green.

## Hard rules (pre-authorized, no questions)

- Follow the orchestrator skill (`~/.grok/skills/orchestrator/SKILL.md`) and the repo skills `prefer-behavior-and-fail-recover-tests`, `repo-handoff-doc-required` and `write-loop-exits-first`. Do not ask questions. Decide conservatively, log each decision as one line in this run's decisions file, and keep going.
- Work only in this worktree. Never touch Mark's main checkout `~/DEVELOP/pfy-mentat`, any other worktree under `tmp/`, or Mark's processes. Never stop or signal a process you did not start.
- Other lanes run in parallel on this host. Stay inside your owned files. If you must change a file another lane owns, do not; record it as a cross-lane request in your handoff.
- No sudo and no system changes. Do not use `/tmp`: scratch goes under this worktree's `tmp/` (gitignored), with `TMPDIR` pointed there.
- Never print, log or commit secret values. Do not read `~/.grok/auth.json`.
- Push only this run's own `bot/` branch, as new commits. No force push, no PR, no merge to main, no tags.
- No em dashes or en dashes in anything you write.
- Every item gets a behavior or fail/recover test when code changes (no tautological unit tests), a commit, and a push. Push after every item.
- Do not end your turn while any process you started is still running. Run long commands in the foreground with bounded waits, or detached with a pid file and a foreground poll loop.

## Shared host: heavy jobs and local models

- Cloud Grok is the default. Never call a local model unless this lane's drop-in explicitly says it needs one.
- Any local-model job (`ollama run`, requests to `127.0.0.1:11434`, `pfy build --local`, local evals) must run under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` and only one local-model job may run on the host at a time. Unload the model when done.
- Targeted tests are fine any time: `nice -n 19 python3 -m unittest tests.test_x`.
- Full `unittest discover`, `make eval-*`, docker builds: run with `nice -n 19` under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`.
- Pregate: at most once, at the end, only if the GitHub runner is idle (`pgrep -f 'Runner[.]Worker'` is empty), under the same flock. Otherwise record "pregate not run: host busy" in the handoff.

## Loop and exits (write these into the run log before any work)

This is a long orchestrator loop, not a single slice. After the listed items, keep taking the next MVP gap that fits this lane until an exit fires.

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Check before every item. Leave 20 minutes to write the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before your change. Record them and skip that area, but do not stop.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. Do not invent architecture: if an item needs an ADR, write it up as an OQ draft in the handoff and skip it.

## Per item

1. Read the item and its linked docs. Check it is not already done on the base or on `origin/main`.
2. Make the smallest change that closes it, plus behavior or fail/recover tests where code changes.
3. Run the affected test modules (targeted, niced).
4. Commit with a clear message naming the item. Push. Append one line to the run log: `item | commit | tests | result`.

## Finish (on any exit)

Write or update this run's handoff in `docs/ops/`: items done with SHAs, items skipped and why, test evidence, how each change fails and recovers, cross-lane requests, the gate needed (Tester plus Reviewer for runtime changes; pregate plus Reviewer for docs, eval or test-only changes), and the next step. Finish the run log with a final `state:` line. Commit and push. Do not merge.
