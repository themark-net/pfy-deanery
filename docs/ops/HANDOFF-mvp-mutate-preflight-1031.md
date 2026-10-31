# Handoff: mvp-mutate-preflight-1031

Exit: lane empty. 27 mutants of `pfylib/build_preflight.py` and `eval/mvp-1031/check_receipt.py` are scored. Before: 6 killed, 21 survived. After: 26 killed, 1 survived. The survivor is P9, recorded as equivalent. No product source was edited. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T22:38:45Z. Stop new items by 2026-11-01T06:18:45Z. Wall: 2026-11-01T06:38:45Z. This handoff is inside the cap.

Branch: `bot/mvp-mutate-preflight-1031`. Base: `origin/bot/mvp-integrate-1031` `0c3f133`. Scored tree: `b5d57f8`.

Report: `eval/mutation-1031/preflight/REPORT.md`.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Exit card and decisions | b70c834 | written before the harness |
| Mutation harness | 800e238 | `tests.test_mut_preflight_harness`, 5 OK |
| First baseline (18 mutants) | b5c51f4 | 6 killed, 12 survived, on `c798af8`; later replaced by the 27-row file |
| First killing tests | fe74696 | 11 gaps, green on the source |
| Second catalog (P10, R13-R19) | 6e2f314 | anchors apply, tests green |
| Non-string gate (R20) | b5d57f8 | empty-string coverage did not kill this mutant |
| Final before and after | 718a925 | 27 mutants; before 6/21; after 26/1; sources unchanged |

## Skipped

- No edit to `pfylib/build_preflight.py`, `tests/test_build_preflight.py`, `eval/mvp-1031/check_receipt.py`, or `tests/test_mvp_1031_receipt.py`. The survivors did not need a product change, and those files belong to other lanes.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md`. Integration owns them. This lane's note is this file.
- Pregate not run: the lane header says the operator runs `scripts/pregate.sh`.
- No local model. No `--local`. No ADR. No secret was read.
- Further mutants of the same two functions. The DoD (at least 15, every non-equivalent survivor killed, both counts published) is met. Decision 8.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mut_preflight_harness tests.test_mut_preflight_survivors`

25 tests, OK, about 4.0s. Harness: each anchor applies once and parses, a value flip is killed, a comment edit survives, a hang is killed, a missed anchor is not survived, a clone outside `<source>/tmp` is refused, and both target files stay byte-identical. Survivor tests pass on the unmutated source.

`nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --baseline-only --label before`

On `b5d57f8`. Base suite survived (20 tests). 27 mutants: 6 killed, 21 survived. About a minute.

`nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --label after`

Same commit. Base suite survived (40 tests). 26 killed, 1 survived (P9). Modules: `tests.test_build_preflight`, `tests.test_mvp_1031_receipt`, `tests.test_mut_preflight_survivors`.

Source sha256 matched across both rounds. `git diff` on the two targets was empty after the runs.

Not a red base. The unmutated suite was green before any mutant ran.

## How each change fails and recovers

Harness:

- A clone dest outside `<source>/tmp` returns status `error` and does not create the dest. Recovery: refuse before `git clone`.
- A missed anchor is `unapplicable`, not survived, and the command exits 2. Recovery: fix that anchor and re-run.
- A suite that exceeds 90s is killed, and processes whose cwd is still the clone are signaled. Recovery: the next mutant starts from a fresh clone.

Classifier tests (`tests/test_mut_preflight_survivors.py`):

- P7: a negative exit that names a quota or a login failure must still be classified. Recovery: only exact `rc == 0` is `other`. If `rc <= 0` skips the phrases, the test goes red.
- P8: `rate  limit` and `not  logged in` (two spaces) stay `other`. Recovery: match the exact substring. Collapsing spaces makes the test go red and would block a log that only looks similar.
- P10: `14290` and `x429y` are rate-limit. Recovery: `429` is a substring, so the operator still takes the quota path. A whole-token check makes the test go red.

Receipt tests, all exit 1 with one stderr reason and empty stdout:

- R1: status `FAIL` is not a PASS archive. Recovery: name status.
- R2: reason `gate-failed` is not ok. Recovery: name reason. A later retry can replace the receipt.
- R3: exit code `1` and JSON `false` are not integer 0. Recovery: name exit_code.
- R4: an empty `gate.cmd` ran no test. Recovery: name gate.cmd.
- R20: a missing gate, or a gate that is a bare string, is not a command. Recovery: `gate.cmd` must be a non-empty string. An empty-string-only check stays green on R4's test and fails this one.
- R5: a truncated `{` is not JSON and must not traceback. Recovery: name json.
- R13: a JSON array is not an object and must not traceback. Recovery: name the object check.
- R7: JSON `0` is not boolean false. Recovery: only `false` passes, so a PASS is not pushed.
- R8: attempts `"done"` is not a list. Recovery: attempts must be a non-empty list.
- R10: branches `cloud` and `cloudy` are not `cloud/`. Recovery: require the slash.
- R12: a missing path must not exit 0. Recovery: say the file is missing and do not create it.
- R14: 40 hex chars plus `zz` is not the git object. Recovery: the whole field must match.
- R15: an uppercase sha is not the lowercase object git records. Recovery: reject it.
- R16: review `"accept"` as a string is not `review.verdict`. Recovery: require an object.
- R17: no path, or an empty path, must not exit 0. Recovery: print usage and exit 1.
- R18: a non-utf8 byte must not be archived as PASS. Recovery: name utf-8.
- R19: schema `PFY-CLOUD-BUILD/1` is a different family if case is folded. Recovery: require the exact schema string.

P9 has no test. The extra `or rc == 0.0` cannot change a real exit code. Details are in the report.

## Cross-lane requests

None. Both targets stayed byte-identical. Killing tests are new files.

mvp-integrate-1031: this branch is eval and tests only. It does not change the daily command. Merge it only if the mutation report should ride with the integrate branch. No Feature GO.

## Gate

Docs, eval, and test-only. Gate is pregate plus Reviewer. Pregate did not run (the lane header says the operator runs it). Do not request Reviewer until a pregate on this tip is PASS.

```bash
nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock ./scripts/pregate.sh
```

Run that only when `pgrep -f 'Runner[.]Worker'` is empty and the lock is free.

## Next step

Lane empty for this scope. When either target changes, re-run:

```bash
nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --label after
```

If a row is `unapplicable`, update that anchor. If a row is `survived` and it is not equivalent, add a behavior test under `tests/test_mut_preflight_survivors.py`. Do not edit the two targets from this lane.
