# Handoff: mvp-dogfood-fix-1031

Exit: lane empty. Daily-use friction from the dogfood lanes is fixed on `bot/mvp-dogfood-fix-1031`, or recorded below as already done or skipped. No merge, no PR, no tag. Not a Feature GO.

Branch `bot/mvp-dogfood-fix-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-fix-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`. Launch 2026-10-31T22:38:38Z. Wall cap 2026-11-01T06:38:38Z. This handoff is inside the cap.

Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood-fix-1031.md` (9). Run log: `docs/ops/RUN-LOG-mvp-dogfood-fix-1031.md`.

Compare: https://github.com/themark-net/pfy-mentat/compare/bot/mvp-integrate-1031...bot/mvp-dogfood-fix-1031

## Items done

| Item | SHA | What |
|------|-----|------|
| Exit card | `1a2d714` | Loop exits and the friction queue, before any runner edit. |
| F-subject | `13a63ea` | Cloud commit subjects stop on a word (72 characters). The body keeps the rest of the task. `commit_subject`, called from `commit_paths`. |
| F-redact | `599d2d2` | Short fixture assignments stay in the receipt. Uppercase env names, password and secret names, and credential-shaped values stay redacted. `redact` only. |
| F-env | `50ac9ba` | The product gate drops secret-named parent env vars. The grok call still sees them. Scrub is inside `gate` only. |
| F-base | `2348080` | If `origin/main` exists and is not HEAD, the run exits 2 until `--base` is set. `--base origin/main` still excludes caller-only commits. `resolve_base` only, plus the `--base` help, the `scripts/pfy` help line, and the two card rows. |
| F-gate | `36cda3c` | A missing gate binary, or the default unittest command failing on import, exits 2 before grok. A custom red gate still reaches grok. `before_gate_block`, called from `execute`. |
| F-stdout | `74fea83` | A non-empty `recovery` is printed on stderr. Printing it does not start `--local`. `finish` only. |

Doc commits that record those SHAs: `466fe2b`, `58f9774`, `f88e50f`, `3d7dfbf`, `8abbe98`, and the commit that adds this handoff.

## Items skipped

| Item | Why |
|------|-----|
| F1, new test file is `tests-tampered` | Already done on this base. `tests_tampered` only hashes the base snapshot. `--writable-test` covers an edit of a base test. Integrate pass 2 took the cloudfix file. Not re-applied. |
| Gom item 1, same as F1 | Same reason. Handed to mvp-cloudfix-1031 and already on this base. |
| Review diff cap 12000 | Dogfood2's closest patch was 10454 characters. No truncation was observed. |
| Dogfood2 run 02 wall 1490s | Model time. Shrinking it needs an ADR this lane will not invent. |
| Em dash in a produced comment | Model output on a throwaway commit, not the CLI. |
| Missing ADR-0017 links | Open question. `docs/modules/README.md` is not this lane's file. Draft below. The dogfood handoff already has the same draft. |
| Daily-card demo section | It copies a real PASS. No friction to fix. |
| `tests/test_pfy_build_local.py` help clash | Red base from the integrate handoff. That file is not this lane's. Not re-run, not edited. |
| `tests.test_local_bench` outdir path | Red base when `TMPDIR` is inside the repo. Not this lane's file. |
| Pregate | Not run. The drop-in says the operator runs `scripts/pregate.sh`. |

## Test evidence

Targeted, niced, `TMPDIR` under this worktree's `tmp/`. No local model. No `--local`. No full `unittest discover`.

Latest full cloud module, after F-stdout, at the tree that became `74fea83`:

`nice -n 19 python3 -m unittest tests.test_pfy_build_cloud`

55 tests, OK, 12.492s. MemAvailable then about 18.3 GiB (above the 16 GiB line). Load about 5.4 on 32 cores.

Then `tests.test_pfy_build_docs` plus `test_missing_gate_binary_exits_2_before_grok` and `test_rate_limit_exits_4_and_does_not_start_local`: 7 tests, OK, 0.202s.

Earlier locks, still in that module: word-boundary subject, short subject, fixture ids versus `API_TOKEN` and `password`, gate env scrub with grok still seeing `GROK_API_KEY`, HEAD mismatch exits 2 before grok, `--base origin/main` excludes `later.txt`, matching HEAD stays `origin/main`, default import error exits 2, custom `No module named` still reaches grok.

## How each change fails and recovers

- Subject: a task longer than 72 characters used to end mid-word (`task[:72]`). The subject now stops on the previous word and ends with `...`. The body is the full task. A short task is the subject with an empty body. Recover by restoring `commit_subject`. The two tests go red if the slice returns.
- Redact: `user_key=list-user`, `token=land-user`, and `token=RAWTOKEN-only-in-source` stay. `API_TOKEN` with a mixed letter-digit value, and `password=hunter2`, become `[redacted]`. AKIA, bearer, `sk_`, private-key blocks, and `xai-` still redact before that check. Recover by putting the fixture lines back in `redact`. The fixture test goes red if every KEY or TOKEN assignment is hidden again.
- Gate env: `GROK_API_KEY` and `MY_PASSWORD` are unset in the gate, `PATH` stays set, and the grok process still sees `GROK_API_KEY`. Recover by scrubbing only inside `gate`. Do not scrub `child_env`, or an operator login that lives in the environment stops reaching grok. The test goes red if the gate prints the key, and it goes red if grok misses it.
- Base: HEAD that is not `origin/main` exits 2, names both short shas, and does not start grok. Pass `--base origin/main` to build that older commit, or `--base HEAD` to build the caller commit. When the shas match, the default name is still `origin/main`. When `origin/main` is absent, the default is still HEAD. Recover by passing `--base`. The mismatch test goes red if the run returns 0 and builds the older tree in silence.
- Gate usage: a missing binary is `gate-missing`, exit 2, no grok. The default `python3 -m unittest discover` failing with `ModuleNotFoundError`, `No module named`, or `Start directory is not importable` is `gate-unusable`, exit 2, no grok. A custom `--test-cmd` that prints `No module named` still calls grok and records `tests`. Recover by passing `--test-cmd` with an interpreter that can import the repo. The custom-gate test goes red if every import error becomes usage.
- Stderr recovery: `finish` prints the recovery line after `FAIL: <reason>`. The rate-limit line is `./pfy build --local <task>`, and the sentinel that would mean `--local` started stays absent. Recover by printing `self.recovery` and not execing it. The rate-limit test goes red if the line is missing or if the sentinel file appears.

## Cross-lane requests

mvp-cloudfix-1031 also edits `scripts/pfy_build_cloud.py`. This lane kept each change to one function, plus two new helpers (`commit_subject`, `before_gate_block`). Functions touched:

- `commit_paths` (subject and body only)
- `redact` (the assignment replacer only)
- `gate` (secret-name scrub only)
- `resolve_base`
- `execute` (the `before_gate_block` call only)
- `finish` (print recovery only)

If cloudfix has commits that are not on this base, merge this branch after that one and expect those functions to conflict. Do not drop the behavior tests in `tests/test_pfy_build_cloud.py`.

`docs/ops/pfy-build-daily.md` and `docs/modules/pfy-build.md` gained the `--base` sentence, the `gate-missing` and `gate-unusable` rows, the fixture-redact sentence, and the stderr recovery sentence. `scripts/pfy` gained one help line: pass `--base` when HEAD is not `origin/main`.

## OQ draft

Not filed in `docs/OPEN_QUESTIONS.md` (that index is not this lane's file).

`docs/modules/pfylib.md` and `docs/modules/README.md` link to `docs/adr/0017-product-catalog-evaluation-handoff-harness.md`. That file is absent on this branch and on `origin/main` as of the dogfood handoff. Question: write the ADR, or retarget the two links at an existing doc? This lane did not choose.

## Gate

Tester plus Reviewer. This lane changed runtime code (`scripts/pfy_build_cloud.py`, `scripts/pfy`) and tests.

Pregate not run. The drop-in says the operator runs `scripts/pregate.sh`.

## Next step

Reviewer reads the six functions above and the new tests. Integrate `bot/mvp-dogfood-fix-1031` after any still-open cloudfix commits on `scripts/pfy_build_cloud.py`. Do not merge to main from this lane.
