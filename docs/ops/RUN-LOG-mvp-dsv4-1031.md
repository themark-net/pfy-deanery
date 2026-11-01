# RUN-LOG mvp-dsv4-1031

Slug: mvp-dsv4-1031
Branch: bot/mvp-dsv4-1031
Worktree: ~/DEVELOP/pfy-mentat/tmp/mvp-dsv4-1031
Base: 6664713 (bot/mvp3-review-retry). Never push to that branch or main.
Started: 2026-11-01T00:04:13Z on nimo. Wall cap for this launch: 2026-11-01T08:04:13Z (8 hours), which is earlier than 2026-11-02T02:00Z.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): Measured verdict on whether Unsloth Dynamic V3.1 GGUF of DeepSeek-V4.1-Flash-1017 reaches the claimed Claude Sonnet 5.5 level on the MVP-3 six-task set, in 64GB-class RAM, with an honest catalog entry and GO or NO-GO as a local default.
1 Goal met:                  eval/mvp-1031/dsv4/REPORT.md plus catalog entry exist, with measured numbers or an honest stop (model not found, or no quant fits). Human reading of diffs is recorded. Comparison to MVP-3 local (gate 5/6, loop accept 5/6, human accept 4/6, wall 3859.9 s) and MVP-2 cloud (6/6, 584 s) is written.
2 Turn cap:                  8 items. Listed steps 1-7 count as the primary items. Extra MVP gaps only if the primary verdict is written and wall remains.
3 Budget cap:                Local only for the model under test. No paid cloud inference for the claim. No second full six-task pass.
4 Wall clock:                8 hours from the host clock line in this log, or 2026-11-02T02:00Z, whichever comes first. Leave 20 minutes to write the handoff.
5 No progress:               Same failure twice with no new information, or 3 items in a row skipped.
6 Human interrupt:           User stop. No questions. Irreversible actions stay inside the drop-in (own branch push only).
7 Error threshold:           3 consecutive same failures, then stop. Host pressure (MemAvailable under 16 GiB, or load over 2x cores for 5 minutes): pause 10 minutes, then stop if it persists.
8 External event:            If origin/bot/mvp-dsv4-1031 already contains this verdict, stop and record it. Do not redo a finished measurement.
Loop type:                   goal
Human gate:                  No merge, no PR, no tag. Push bot/mvp-dsv4-1031 only. Pregate is the operator's, unless the finish rule says the runner is idle.
```

Drop-in exits (same run, checked before every item):

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

## Overview

Treat the Unsloth "Claude Sonnet 5.5 level in 64GB+ RAM" claim for DeepSeek-V4.1-Flash-1017 Dynamic V3.1 GGUF as unverified marketing. Find the Hugging Face repo, fit the largest quant that leaves 50 GB disk and about 8 GB context headroom, serve it on 127.0.0.1 without touching Mark's Ollama, smoke it, then run one `./pfy build --local` pass on eval/mvp3. Write the catalog entry, the eval report, and a GO or NO-GO handoff.

## Phases

- exits | docs/ops/RUN-LOG-mvp-dsv4-1031.md docs/ops/AUTONOMOUS-DECISIONS-mvp-dsv4-1031.md | exit card and decisions file exist before model work | none | general
- find-model | docs/ops/RUN-LOG-mvp-dsv4-1031.md | exact unsloth HF repo, file names, sizes, and the Unsloth post URL, or "not found" | exits | general
- measure-host | docs/ops/RUN-LOG-mvp-dsv4-1031.md | RAM, GPU/VRAM, free disk, chosen quant or "none fits" | exits | general
- download | ~/DEVELOP/pfy-mentat/_vendor/models/ (weights only) | resumable download of the chosen GGUF, or stop recorded | find-model measure-host | general
- serve-smoke | this worktree tmp/ plus a 127.0.0.1 server this lane starts | one short prompt with tokens/s and load time; server stopped and pid lifecycle recorded | download | general
- mvp3-pass | eval/mvp-1031/dsv4/ | one ./pfy build --local pass on the six MVP-3 tasks under the heavy lock; per-task gate, review, human accept, attempts, wall seconds | serve-smoke | general
- compare-catalog | TOOLS.md data/ sources/ eval/mvp-1031/dsv4/REPORT.md docs/ops/HANDOFF-mvp-dsv4-1031.md | catalog lint green; verdict versus MVP-3 local and MVP-2 cloud; GO or NO-GO | mvp3-pass | general
- handoff | docs/ops/HANDOFF-mvp-dsv4-1031.md docs/ops/RUN-LOG-mvp-dsv4-1031.md | final state line, commit, push of this branch only | all prior | general

## Risks

- The named GGUF may not exist. Mitigation: record not-found, catalog status "not found", stop the measurement, still write handoff.
- Weights may not fit RAM or the 50 GB disk reserve. Mitigation: record the fit math and stop before download.
- A local job may already hold heavy-1030.lock. Mitigation: wait on flock; do not kill other jobs. Download does not take the lock.
- Serving could hit Mark's Ollama on 11434. Mitigation: different port, bind 127.0.0.1, never signal a process this lane did not start.
- Catalog format may reject a model row. Mitigation: follow catalog_check.py and the schema; if a model is not a tool, put the entry where the lint already accepts model or eval records and say so.
- Wall clock is long because of download plus six tasks. Mitigation: check the cap before each item; leave 20 minutes for the handoff.

## Owned paths

This lane writes: docs/ops/RUN-LOG-mvp-dsv4-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-dsv4-1031.md, docs/ops/HANDOFF-mvp-dsv4-1031.md, eval/mvp-1031/dsv4/, catalog files only when adding this model's entry, and this worktree tmp/. Model weights go to ~/DEVELOP/pfy-mentat/_vendor/models/ because the drop-in names that directory. No other files in the main checkout.

## Host at launch

nimo, 32 cores, load 3.54 3.83 4.99. MemTotal 115344580608 bytes, MemAvailable 76125134848 bytes, SwapFree 98304 bytes. AMD VRAM total 17179869184, used 3714129920. Disk available 479862718464 bytes. No nvidia-smi. Runner.Worker was not running.

## Progress

```text
state: PLAN | tests: none yet | files: run log + decisions | err: none
find-model | hf tree API | repo unsloth/DeepSeek-V4.1-Flash-1017-GGUF sha 8a6ec9cf118e | err: none
measure-host | meminfo + rocm-smi + df | smallest UD-IQ1_S 232979608420 + 8 GiB = 241569543012 > RAM+VRAM 132524449792 | err: none fits
download | skipped | fit gate | err: none
serve-smoke | skipped | no pid started | err: none
mvp3-pass | skipped | fit gate | err: none
compare-catalog | catalog_check PASS tools_md=53 stage_cards=53; unittest tests.test_catalog_stage_eval tests.test_catalog_entry_numbers Ran 4 OK | NO-GO | err: none
```

Item lines:

```text
exits | c0c7948 | none | exit card written before the HF fetch
find-and-fit | c0c7948 | no download | NO quant fits, stop
catalog-and-report | c0c7948 | catalog_check PASS; unittest Ran 4 OK | I0 row, NO-GO, claim unverified
```

```text
state: lane empty | fit gate: UD-IQ1_S 232979608420 bytes plus 8 GiB exceeds RAM+VRAM 132524449792 by 109045093220 bytes | tests: catalog_check PASS, unittest Ran 4 OK | err: none
```
