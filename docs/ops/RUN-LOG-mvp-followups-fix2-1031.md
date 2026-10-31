# RUN-LOG mvp-followups-fix2-1031

Start: 2026-10-31T21:07:55Z (drop-in commit `ea62d21`).
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-followups-fix2-1031`
Branch: `bot/mvp-followups-fix2-1031`
Base: `origin/bot/pfy-followups-1030` at `c0d38af` (Reviewer B1 bwrap-probe fix and B2 root-length test fix). `origin/main` is `85c53dc`.
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-followups-fix2-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-followups-fix2-1031.md`
Context: `docs/ops/HANDOFF-pfy-followups-1030.md`
Needs a local model: no. Cloud Grok only.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): Tester should-fix items 2 to 5 (this log's items 1 to 4) are closed with behavior or fail/recover tests, each committed and pushed. Then further code or test follow-ups named in HANDOFF-pfy-followups-1030 that fit the owned files, until an exit fires.
1 Goal met:          each taken item's tests pass, or the item is skipped with a reason; the handoff is pushed. Evaluator: targeted unittest modules, not a vibe check.
2 Turn cap:          not a fixed iteration count. Stop when the wall cap or the no-progress exit fires.
3 Budget cap:        cloud Grok only. No local model. No spend beyond this session.
4 Wall clock:        8 hours from 2026-10-31T21:07:55Z, so stop new items at 2026-11-01T04:47:55Z (20 minute handoff buffer). Hard stop 2026-11-01T05:07:55Z. Also stop at 2026-11-02T02:00:00Z (Sunday 2026-11-01 18:00 PT, PST) if that is sooner. It is not.
5 No progress:       the same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:   user stop. No questions. Conservative decision, one line in the decisions file, keep going.
7 Error threshold:   same as exit 5 (same failure twice, or 3 skips in a row)
8 External event:    item already done on this base or on origin/main: skip that item. Red tests on the base before the change: record and skip that area. Do not stop the run for a red base.
Loop type:           goal, with a wall-clock cap
Human gate:          no merge, no PR, no tags. Tester plus Reviewer for runtime and CI changes. Pregate plus Reviewer for docs, eval, or test-only changes. Integration: merge after bot/pfy-followups-1030.
```

Operator exits (same card, checked before every item):

1. Wall cap: 8 hours from 2026-10-31T21:07:55Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00:00Z), whichever comes first. Leave 20 minutes to write the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the run.

## Plan

Overview: Wire the workflow image-pin lint into the hosted G0 job, make pregate and CI call one explicit interpreter and fail closed with that interpreter's path when PyYAML is missing, extend the lint to container and service images (tag pin, and digests when the repo already pins any), then kill attach.py mutants A3, A4, A5, A7, A8, and A10 (orphan window, lost exit code, missing install hint). After those four, take follow-ups from the 1030 handoff that fit the owned files.

Phases:
- item-1-ci-image-pin | `.github/workflows/eval-structural.yml` (lint step only), `tests/test_workflow_image_pin.py` | hosted job `structural-github` stays on `ubuntu-24.04` and a parsed step runs `scripts/check_workflow_image_pin.py` on `.github/workflows`. A PR that sets `ubuntu-latest` fails that step. Test parses the workflow YAML and executes the step (no file grep). | none | lead
- item-2-pyyaml-interpreter | `scripts/check_workflow_image_pin.py`, `scripts/pregate.sh` (lint call only), `.github/workflows/eval-structural.yml` (lint step only), `tests/test_workflow_image_pin.py` | both call sites use one explicit interpreter path. Missing PyYAML exits 1 and the message names that path. A PATH whose python3 lacks yaml fails closed with that message for both call sites. | item-1 | lead
- item-3-container-images | `scripts/check_workflow_image_pin.py`, `tests/test_workflow_image_pin.py`, `tests/fixtures/` workflow dirs | `jobs.*.container` (string and `image:`) and `services.*.image` need a non-latest tag. If any checked image uses `@sha256:`, every image needs a digest. Malformed forms fail closed. Fixture pass and fail cases. | item-2 | lead
- item-4-attach-mutants | `pfylib/attach.py`, `tests/test_attach.py`, this handoff's mutation table | tests kill A3, A4, A5, A7, A8, A10. Orphan child does not outlive a failed terminal. Child exit code reaches the caller and the receipt. Missing opencode prints an install hint and returns FAIL without spawning. Fix only where a test shows a real bug. | none (files disjoint from items 1-3; still after them because the request says in order) | lead
- handoff | `docs/ops/HANDOFF-mvp-followups-fix2-1031.md`, this log | SHAs, skips, evidence, fail/recover, cross-lane requests, gate, next step, final `state:` line | all prior | lead

Risks:
- Host is shared. Mitigation: targeted `nice -n 19 python3 -m unittest` only. No full discover, no local model, no docker. Pregate at most once at the end, and only if `pgrep -f 'Runner[.]Worker'` is empty, under the heavy lock.
- Items 1 to 3 share the lint files. Mitigation: the lead edits them in order on this branch. No implementation sub-agent.
- CI ubuntu-24.04 setup-python may lack PyYAML, so a wired lint can fail closed until item 2. Mitigation: item 2 lands in this same run before the handoff.
- Attach mutants are not written down in the 1030 handoff. Mitigation: recreate them from the three names in the drop-in, log the reconstruction, and re-run each mutant.

## Host at plan time (2026-10-31T21:07:55Z)

- MemAvailable: 64800176 kB (about 61.8 GiB). Floor is 16 GiB. Not pressured.
- Load: 3.32, 3.92, 3.85. Cores: 32. Threshold: 64. Not pressured.
- `origin/main` does not contain `scripts/check_workflow_image_pin.py`. The four items are not already done on the base or on main.

## Items

(one line per finished item: `item | commit | tests | result`)

item-1-ci-image-pin | a5805d9 | nice -n 19 python3 -m unittest tests.test_workflow_image_pin: 16 OK in 6.850s | hosted job structural-github stays on ubuntu-24.04; parsed step runs the helper (recording PATH python3); real workflows still pass; pregate --only lint still OVERALL=PASS
item-2-pyyaml-interpreter | 6d3f8de | nice -n 19 python3 -m unittest tests.test_workflow_image_pin: 17 OK in 12.846s | both call sites exec absolute PATH python3; a venv python3 without PyYAML fails pregate lint and the parsed hosted step, and the message names that interpreter path
item-3-container-images | e4f03f4 | nice -n 19 python3 -m unittest tests.test_workflow_image_pin: 21 OK in 13.428s | container string and image: forms, service images, registry ports, latest, missing tags, short digests, cross-file digest rule, and malformed forms; real workflows still pass
item-4-attach-mutants | 34ccff0 | nice -n 19 python3 -m unittest tests.test_attach tests.test_registry: 39 OK in 1.143s | orphan child reaped, process group reaped, exit code 7 on the caller and the receipt, missing opencode prints the setup hint and does not spawn. Mutants re-run then restored: A3 RED both reap tests, A4 RED group test and GREEN single-child test, A5 RED caller and GREEN receipt, A7 RED receipt and GREEN caller, A8 RED printed hint, A10 RED next_step hint

prior-state: lane empty at 2026-10-31T21:37:19Z. Items 1-4 done and pushed through 7164136. No further follow-up in HANDOFF-pfy-followups-1030 fits the owned files. Pregate not run: host busy (Runner.Worker pid 2242260). Handoff written. No merge.

## Round 2 (parent addendum)

The prior state line is superseded. Wall clock and the other exits from the card above still apply. Checked 2026-10-31T21:47:11Z, before this round's first item: under the 2026-11-01T04:47:55Z item stop. MemAvailable about 58 GiB. Load about 4.8 on 32 cores. Not pressured. `Runner.Worker` is alive. Pregate will not be run (addendum, and the runner is busy).

Overview: Make the Entry 149 bwrap probe pass the same `--bind <tmp> <tmp>` and `--die-with-parent` the real run uses, add the `--tmpfs-only` fake-bwrap twin of the existing `--proc` fake, prove a failing image-pin lint makes `scripts/pregate.sh` print OVERALL=FAIL and exit nonzero, and prove the root-length guard refuses a path over the limit and accepts one at the limit.

Phases:
- F1-bwrap-probe-flags | `examples/x-intake-local/smoke_149.py`, `tests/test_x_intake_smoke_149.py` | A fake bwrap that rejects `--bind` or `--die-with-parent` makes the smoke exit 2 with the bwrap reason and does not run MemPalace. | none | lead
- F2-tmpfs-only | `tests/test_x_intake_smoke_149.py` | A fake bwrap that exits 1 only when argv contains `--tmpfs` makes the smoke exit 2 with the bwrap reason. | F1 | lead
- P2-lint-fails-pregate | `scripts/pregate.sh` (lint call only), `tests/test_workflow_image_pin.py` | `PREGATE_IMAGE_PIN_ROOT` points at a fixture workflow with `ubuntu-latest`. `pregate --only lint` exits nonzero and prints OVERALL=FAIL. The lint log names that image. Unset, the helper still checks `.github/workflows`. | none | lead
- G1-root-length | `tests/test_workflow_image_pin.py` | `PREGATE_MAX_ROOT_LEN` one below the longer of the in-place run root and the scratch path exits 2 with `path too long` and no OVERALL. A limit equal to that length passes the guard and `--only lint` reaches OVERALL=PASS. | P2 | lead
- handoff | this log, `docs/ops/HANDOFF-mvp-followups-fix2-1031.md`, the decisions file | SHAs, fail/recover, gate, next step, new state line | all prior | lead

Risks:
- `smoke_149.py` was outside the round-1 owned list. Mitigation: the parent assigned F1 and F2. Those files are not on the must-not-touch list. The 1030 lane that last edited them is this branch's base. Do not edit catalog entries or `docs/ops/HANDOFF-x-intake-149-b2.md`.
- F1 does not share files with P2, but this worktree is the only checkout and each item is pushed before the next. Mitigation: the lead runs them in addendum order. No second worktree.
- G1's at-limit case runs `--only lint`, not the full pregate. Mitigation: same bounded call the existing lint test uses. The full pregate gate stays unrun.

## Round 2 items

F1-bwrap-probe-flags | b5754cb | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_x_intake_smoke_149: 27 OK in 2.889s | fake bwrap rejecting --bind or --die-with-parent exits 2 with the bwrap reason and does not init. Mutants that drop either flag from the probe go RED with a version-pin reason. Real probe with those flags returned 0 on this host.
F2-tmpfs-only | f6a74ea | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_x_intake_smoke_149: 28 OK in 2.940s | fake bwrap that exits 1 only for --tmpfs exits 2 with the bwrap reason. Mutant that drops --tmpfs from the probe goes RED with a version-pin reason. Host at 2026-10-31T21:53:24Z: MemAvailable about 57 GiB, load about 4.6 on 32 cores.
