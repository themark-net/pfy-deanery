# Run log: mvp-mutate-preflight-1031

Lane: mutation testing of `pfylib/build_preflight.py` (`classify_cloud_failure` and its ordered checks) and `eval/mvp-1031/check_receipt.py`.
Branch: `bot/mvp-mutate-preflight-1031`. Base: `origin/bot/mvp-integrate-1031` `0c3f133`. Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-mutate-preflight-1031`.
Launch: 2026-10-31T22:38:45Z. Stop new items: 2026-11-01T06:18:45Z. Wall cap: 2026-11-01T06:38:45Z (8h), which is earlier than 2026-11-02T02:00Z.
Method: `origin/bot/mvp-mutate-cloud-1031` `eval/mutation-1031/cloud/run_mutants.py` and `REPORT.md` (`9f707fd`).

Host at launch: MemAvailable about 57 GiB, 32 cores, load about 3.7. Under the pressure floor.

```text
LOOP EXIT CARD
Goal (success criteria):     at least 15 meaningful mutants scored on throwaway clones; before and after counts in eval/mutation-1031/preflight/; every survivor killed by a behavior test or recorded as equivalent; source files byte-identical
1 Goal met:                  run_mutants.py prints counts; results/before.json and results/after.json exist; REPORT.md matches those counts; tests.test_mut_preflight_harness is green
2 Turn cap:                  8 item iterations (exits, harness, baseline, survivor tests, after report, handoff, plus at most two repair passes)
3 Budget cap:                no local model, no --local, no paid API beyond this Grok session
4 Wall clock:                2026-11-01T06:38:45Z; no new item after 2026-11-01T06:18:45Z
5 No-progress:               the same failure twice with no new information, or 3 items skipped
6 Human interrupt:           user stop. Do not ask. Log a conservative decision and continue.
7 Error threshold:           3 consecutive same failures, then stop
8 External event:            if an anchor no longer matches because the base moved, mark that mutant unapplicable and fix the anchor once; do not edit another lane's source
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Push this branch only.
```

Drop-in exits (same run): wall cap, lane empty, no progress, host pressure (MemAvailable under 16 GiB, or load over 64 for 5 minutes, then pause 10 minutes and stop if it persists), red base (record and skip that area, do not stop the lane).

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-mutate-preflight-1031.md` are the binding.

Overview: Score meaningful mutants of the classifier and the receipt checker inside git clones under this worktree's `tmp/`. Do not write the source files. Where the current tests leave a survivor, add a behavior test under `tests/test_mut_preflight_survivors.py`, or record equivalence. Then score again and write the report.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-mutate-preflight-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-mutate-preflight-1031.md` | card and decisions exist before product or harness code | none | general
- harness | `eval/mutation-1031/preflight/run_mutants.py`, `tests/test_mut_preflight_harness.py` | `python3 -m unittest tests.test_mut_preflight_harness` is green; each anchor applies once; source bytes unchanged | exits | general
- baseline | `eval/mutation-1031/preflight/results/before.json` | at least 15 mutants scored with `--baseline-only`; counts printed | harness | general
- survivors | `tests/test_mut_preflight_survivors.py` | each non-equivalent survivor fails its new test on a clone and passes on the source | baseline | general
- after | `eval/mutation-1031/preflight/results/after.json`, `eval/mutation-1031/preflight/REPORT.md` | after counts recorded; no unexplained survivor | survivors | general
- handoff | `docs/ops/HANDOFF-mvp-mutate-preflight-1031.md` | state line in this log; pushed | after | general

Risks:
- Editing `pfylib/build_preflight.py` or `eval/mvp-1031/check_receipt.py` would cross a lane boundary. Mitigation: mutate copies only; killing tests are new files.
- A missed anchor scored as survived would hide a weak suite. Mitigation: anchor count other than 1 is `unapplicable` and the command exits 2.
- A red unmutated suite would mark every mutant killed for the wrong reason. Mitigation: score the unmutated suite first; on failure record red base and do not score mutants.
- Shared-host load. Mitigation: targeted niced unittest only; no discover, no local model, no pregate (the drop-in says the operator runs it).

Owned for this lane: the three `docs/ops/*mvp-mutate-preflight-1031.md` files, `eval/mutation-1031/preflight/**`, `tests/test_mut_preflight_*.py`. Product sources and their existing test modules stay with the round-1 owners.

Items:

```text
item | commit | tests | result
exits | b70c834 | none (docs only) | exit card and decisions written before the harness
harness | 800e238 | nice -n 19 python3 -m unittest tests.test_mut_preflight_harness | 5 tests OK in 3.010s; anchors apply; source bytes unchanged
baseline | b5c51f4 | nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --baseline-only --label before | scored at c798af8; 18 mutants; killed 6; survived 12; base suite 20 tests OK; sources unchanged
survivors | fe74696 | nice -n 19 python3 -m unittest tests.test_mut_preflight_survivors tests.test_mut_preflight_harness | 16 tests OK in 3.199s on the unmutated source
second-pass | 6e2f314 | nice -n 19 python3 -m unittest tests.test_mut_preflight_harness tests.test_mut_preflight_survivors | 24 tests OK in 3.371s; P10 and R13-R19 anchors apply
gate-shape | b5d57f8 | same modules, catalog test plus the two gate tests | R20 anchor applies; missing gate and a bare string are rejected
rescore | b5d57f8 | nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --baseline-only --label before; then --label after | 27 mutants; before 6 killed, 21 survived; after 26 killed, 1 survived (P9 equivalent); base suite green both rounds; sources unchanged
handoff | 718a925 | report plus the 25-test module run | lane empty
```

state: lane empty | 27 mutants; before 6 killed, 21 survived; after 26 killed, 1 equivalent (P9); tests: harness plus survivors 25 OK in 3.979s; pregate not run | files: harness, survivor tests, report, results | err: none
