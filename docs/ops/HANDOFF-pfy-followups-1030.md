# Handoff: pfy-followups-1030 (Run A)

Status: stopped. Branch `bot/pfy-followups-1030`, worktree `~/DEVELOP/pfy-mentat/tmp/pfy-followups-1030`. Exit 3: three items in a row skipped (T-0070, T-0081, T-0074) after T-0124. Do not merge. No PR.

Checked 2026-10-31T04:13:02Z: MVP-3 pid 1695827 is alive. `ollama ps` listed no model at that instant. The host stays busy while that pid is alive. Pregate not run: host busy.

## Done

| Item | Commit | Tests | Gate |
|------|--------|-------|------|
| MVP-2 reviewer follow-ups (docs) | `6b63b4d` | none (docs only) | Pregate plus Reviewer. Pregate not run: host busy |
| MemPalace smoke 149 follow-ups | `a1e7a47` (run log `ece7072`) | `tests.test_x_intake_smoke_149` and `tests.test_x_intake_smoke_148`: 39 OK in 4.312s. Hidden bwrap: 25 OK, skipped 16 | Tester plus Reviewer |
| Workflow image-pin YAML lint | `53933b3` (run log `0f3356a`) | `tests.test_workflow_image_pin`: 15 OK in 8.380s, including `pregate --only lint` OVERALL=PASS | Tester plus Reviewer |
| T-0124 OpenCode enterable behind `pfylib/attach.py` | `6c8d00a` (run log `1c0aa9d`) | `tests.test_attach` and `tests.test_registry`: 33 OK in 0.061s | Tester plus Reviewer |

Stamp commits only record the item SHA. They do not change behavior.

## How each change fails and recovers

MVP-2 docs. There is no runtime path. The landing default is an owner override: prefer the cloud (C) patches, and never land the local t4/t5 patches. Prove-red still has no standalone receipt. The truncated-prompt and weekly-percent sentences are operator observations with no receipt field.

Smoke 149. A missing or non-zero `bwrap`, or a required `/proc` or `/dev/shm` that is not usable, exits 2 with a reason and does not run unsandboxed. A version that is not the pin exits 2 with `version pin 3.12.0 != --version <value>`. `PFY_SMOKE_REAL_HOME_BIND` is not read. Recovery: install a usable bwrap, make `/proc` readable and `/dev/shm` writable, and install MemPalace at the pin. The real-HOME write test uses the `extra_binds` argument that `main()` never passes.

Image pin. `scripts/check_workflow_image_pin.py` exits 1 when a GitHub-hosted job is not exactly `ubuntu-24.04`, when YAML is malformed, when `runs-on` is missing, or when PyYAML cannot be imported. A self-hosted label list passes. Recovery: pin the job to `ubuntu-24.04`, fix the YAML, or install PyYAML for the interpreter that runs the helper. A missing parser is a failure, not a pass. Fixture parse tests skip when this interpreter has no PyYAML. The missing-import test always runs.

T-0124. `open_opencode_session` returns FAIL and does not spawn when `opencode` is missing. A terminal that does not stay up returns FAIL and clears the session file. A failed models-and-smoke prove does not paint READY. A tools-env pin does not replace the probed base. Recovery: install `opencode` or `opencode-cli`, or point the live detect base at an endpoint that passes prove, then call again. The four harnesses stay on `open_session`.

## Skipped

| Item | Why |
|------|-----|
| `pfy build --local` loose ends | `origin/bot/mvp3-review-retry` rewrites `build_local` and `parse_args`. The named gaps are already `--reap`, need a model run, or were left as known gaps on purpose. |
| T-0070 | `examples/eval-harness/tasks/013-stage-card/` already has a scorer plus pass and fail fixtures, and `run_structural.py` already runs them. No next scorer is named. A new one would be invented. |
| T-0081 | OpenCode-in-cage smoke needs a cage. That is docker. MVP-3 is busy, so this run does not start docker. |
| T-0074 | The no-model part is already `scripts/eval_auto_candidates.py` and `tests/test_eval_auto_candidates.py` (empty fit-select falls back to `deepseek-coder:6.7b-instruct`, then `deepseek-coder:6.7b`). The rest is `make eval-auto`, which runs a local model. |

Run B (`bot/backlog-catalog-1030`) still owns catalog, X-intake entries, `TOOLS.md`, and `data/tools.json`. This run edited `sources/entries/149-mempalace.md` once, for the time zone only.

## Next step

A later run can take code or test follow-ups named in recent `docs/ops/HANDOFF-*.md` Known gaps or Next step sections, still staying off Run B's files and off the MVP-3 review-and-retry hunks in `scripts/pfy_build_local.py`. T-0081 waits until docker is allowed. T-0074's model run waits until the host is quiet. T-0070 waits until a next scorer is named.

When MVP-3 pid 1695827 is gone and `ollama ps` is empty, and `pgrep -f 'Runner[.]Worker'` is empty, and no other pregate is running, run pregate once under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Until then, pregate not run: host busy.

Reviewer for the docs. Tester plus Reviewer for the smoke, the image-pin helper, and T-0124. Do not merge.
