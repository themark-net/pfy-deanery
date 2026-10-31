# pfy local build MVP step 2: real-task trial, local vs cloud Build

Goal: measure honestly whether `./pfy build --local` (qwen3.6:35b via opencode, bwrap sandbox, tests as the gate) can replace cloud Grok Build for build-only runs. Base is main 997d892 (MVP step 1 merged). Work only on branch bot/mvp2-trial in this worktree. Rules: new commits only, never rebase or force-push, no PR, do not merge to main, never touch the main checkout of pfy-mentat or other worktrees, never use /tmp (use this worktree's tmp/), no em dashes, never print secrets. Never stop or pause Mark's processes. Run unattended, do not ask questions, record decisions in the report.

## Task selection
Read docs/TODO.md and open parked follow-ups in docs/ (for example the #300 and #303 deferred follow-ups, the 143-145 and 146-148 parked should-fixes) and pick 6 small, build-only, test-gated items: each has a clear acceptance test or can be given one in a few lines, touches at most 3 files, needs no network or keys, and is NOT catalog HOLD 70-75, GUI, trading, or anything on Mark's hands-off list. Write each as a task spec (title, base SHA, files likely touched, the exact test command that gates it) in eval/mvp2/tasks/. Pick a spread: 2 trivial, 2 medium, 2 slightly hard.

## Runs
For each task, in a fresh git worktree of the base SHA under tmp/mvp2-runs/<task>-<arm>/:
- Arm L: `./pfy build --local` with the task spec and the gate command (default model qwen3.6:35b, default sandbox, protect-by-default). Record the receipt.
- Arm C: cloud Grok Build headless (`grok -p <same prompt> --cwd <worktree> --always-approve`, timeout 40m per task), then run the same gate command yourself on the result in the same sandbox profile.
Run arms sequentially (nimo has one GPU and limited RAM; respect the memory guard; never run two model jobs at once). Cap cloud Build to these 6 tasks, no retries beyond one per task, because Build usage is limited (bots already used 27% of the weekly budget). Record Build usage delta if readable the way the weekday usage routine reads it (do not print tokens or auth contents; `test -s ~/.grok/auth.json` only checks existence).

## Measure
Per task and arm: PASS/FAIL by the gate, wall time, diff size, whether a human-quality review would accept the diff (read it, say why not), any gaming or scope creep, memory or timeouts, number of attempts. Then summarize: pass rate L vs C, time L vs C, quality gaps, which task shapes L handles, which it does not, and a go/no-go recommendation for making `pfy build --local` the default for build-only runs (and what is still missing, for example a retry policy, a bigger context, a stronger local model, or a review step).

## Deliverables
- eval/mvp2/tasks/*.md, eval/mvp2/results/<task>-<arm>.json (receipts and summaries; raw logs stay gitignored under tmp/), eval/mvp2/REPORT.md, docs/ops/HANDOFF-mvp2-trial.md, a RUN-LOG entry.
- Do not merge the produced task diffs into main; keep them as patch files under eval/mvp2/patches/. Landing default, as an owner override: prefer the cloud (C) patches; never land the local t4/t5 patches.
- Push branch bot/mvp2-trial and print the head SHA plus a 10-line verdict.
