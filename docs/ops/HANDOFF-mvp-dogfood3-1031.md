# Handoff: mvp-dogfood3-1031

Lane mvp-dogfood3-1031, wave 6. Branch `bot/mvp-dogfood3-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood3-1031`. Base `origin/bot/mvp-integrate-1031` at `1dee0b91bda11ba1fcda87819423437a3f10f289`. Drop-in `ab250dd521bda255319aa704b9f8d30710804979`. Exit card `e434df368174053a74c019e1bb2f1c88159173f4`.

Exit: lane empty. Six cloud `./pfy build` runs, five human-accept, one human-reject. Pass rate 5/6. Median wall of the six runs is 77s (63, 63, 72, 82, 103, 113). No merge, no PR, no tag. No `--local`. `scripts/pregate.sh` was not run.

## Six rows

| n | task | exit | attempts | review | wall s | commit | human |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | smoke128-timeout | 0 | 1 | accept | 63 | 2587cadd1a29 | accept |
| 02 | smoke131-timeout | 0 | 1 | accept | 63 | 55ad1b116ffd | accept |
| 03 | smoke137-timeout | 0 | 1 | accept | 113 | none | reject, class cross-lane |
| 04 | smoke098-timeout | 0 | 1 | accept | 103 | 4ef4c665081f | accept |
| 05 | smoke103-timeout | 0 | 1 | accept | 82 | 775e34bffab5 | accept |
| 06 | smoke106-timeout | 0 | 1 | accept | 72 | 98e5795fcc1a | accept |

Pass rate 5/6. The tree-hash skip is not a row. Cloud review accepted every run, including the one this lane rejected.

## Items done

Each accept is a product commit by `pfy-cloud-build <pfy-cloud-build@localhost>` plus a Built-by trailer. The red behavior test is the parent commit. Receipts live under `eval/mvp-1031/dogfood3/`.

- 01 smoke_128. Red test `f629abac774189f4d437c0519493a63e0598499c`. Product `2587cadd1a29b966a9a973c04d928740789a7cf5`. Cloud `d7c32ffbddd78d792094646d2cf0a394df241530`. `examples/x-intake-local/smoke_128_130.py` only. After land: `tests.test_smoke_128_bad_timeout` and `tests.test_x_intake_smoke_128_130`, 44 OK.
- 02 smoke_131. Red test `89c56d3bc77fe4539ca1bc297078abad84405f18`. Product `55ad1b116ffd1bab357f8905e1e9535578f97b31`. Cloud `fc03f165b86645705af6af727fd3c311c4d4d905`. Imports `timeout_problem` from smoke_128. It does not copy the function. After land: `tests.test_smoke_131_bad_timeout` and `tests.test_x_intake_smoke_131_133`, 40 OK.
- 04 smoke_098. Red test `ab7ed932b7c4b707ed52d0b5068217f7a391b76b`. Product `4ef4c665081f5f6ddea4aaa6da5734af78f24e8f`. Cloud `5694106559ad8593b57b4a6ffecec544208e22c6`. Local `timeout_problem` includes a dead `if raw is None` that matches the task text. After land: `tests.test_smoke_098_bad_timeout` and `tests.test_x_intake_smoke_098_100`, 13 OK.
- 05 smoke_103. Red test `37405a7b7f76d9064809827ef44045c4068a0f36`. Product `775e34bffab5d3250c389861ea41af085702b63b`. Cloud `94049ba4c728b3321e027d63979aeadb4db56b31`. One em dash in the receipt model tail was replaced with " - " before commit. Status, exit, and review verdict were unchanged. After land: `tests.test_smoke_103_bad_timeout` and `tests.test_x_intake_smoke_103_105`, 9 OK.
- 06 smoke_106. Red test `66ac698d11665f954f7aa2dcf945b012fbcea077`. Product `98e5795fcc1a85a6c2b02a42f78c47456e80ca10`. Cloud `8d09aef936e2cc6d122733431e9b62e861deb128`. `examples/x-intake-local/smoke_106_108.py` only (22 insertions, 2 deletions). Receipt has no em dash and no en dash. After land: `tests.test_smoke_106_bad_timeout` and `tests.test_x_intake_smoke_106_108`, 13 OK.

## Item 03 reject

FINDING-D3-01. Cloud run exited 0, review accept, wall 113s, attempts 1. Cloud commit `141b4c0c0ca3adc023d60b47c9b33412824bd6aa` stayed on the throwaway clone `tmp/target-03`. It was not cherry-picked.

The diff is the right timeout check: import `timeout_problem`, return 2 before the entry, docstring sentence, `tree_hash` untouched. 7 insertions, 2 deletions, `examples/x-intake-local/smoke_137_139.py` only. Human reject because `origin/bot/mvp-selfhost2-1031` commit `1faa9fd` already owns that file (tree_hash symlink readlink text, around line 135). The hunks do not overlap. The unpushed red test `tests/test_smoke_137_bad_timeout.py` was reset off this branch before push. Receipt and `diff.patch` are in `eval/mvp-1031/dogfood3/03-smoke137-timeout/`.

Failure class: cross-lane.

## How each change fails and recovers

Shared contract on the five landed mains. `xintake_timeout` or `tmo` still swallows a bad value into the default. The new check is an early return in `main`.

Fail: a set `PFY_XINTAKE_TIMEOUT` that is not a finite number of seconds > 0 (`abc`, `0`, `-1`, `nan`, `inf`) exits 2 before the entry. The receipt reason is `PFY_XINTAKE_TIMEOUT={raw[:40]!r} is not a number of seconds > 0`. Whitespace is stripped on 098, 103, and 106. `inf` fail-closes because it is not finite.

Recover: unset or empty returns None, so the entry still runs. A real prereq miss is still the operator string:

- smoke_128: `node not found ($NODE_BIN, tmp/node/bin/node, PATH)`
- smoke_131: `jah not found ($JAH_BIN, tmp/jevagentharness/.venv/bin/jah, PATH); see the handoff`
- smoke_098: `no Python with sponsio` plus the venv install line in the module
- smoke_103: `no bugpatrol` plus the npm install line in the module
- smoke_106: `no @rulora/core` plus the npm install line in the module. The package check happens before the Node check, so this is the unset recover path.

Each planted test was red first: `FAILED (failures=5)`, and the reason was the prereq string, not `PFY_XINTAKE_TIMEOUT`. Unset and empty cases passed on the red tree. The cloud edit turned the same module green (2 tests OK inside the clone). The paired module was rerun after land.

Item 03 did not land, so a bad timeout on smoke_137 still reaches the neatroots prereq miss. Recover on this branch: none.

## Skipped

Survey skips, logged before item 01, do not count toward the 3-skip exit. Detail is `docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood3-1031.md`.

- realfail3 unwritable tmp and hung gate. Tests already on this tip.
- review-quality prompt. Owned by `origin/bot/mvp-review-quality-1031`.
- cloud-perf phase seconds and gate overlap. Live on `scripts/pfy_build_cloud.py`.
- timeoutfix row07, review truncation, keep-rejected diff, kolibri recheck. Live on the cloud runner. This lane does not edit `scripts/pfy_build_cloud.py` or `scripts/pfy_build_local.py`.
- dogfood2's nine tasks, including smoke_149 `home_sig` `3e4c7ba` and smoke_109 `state_snapshot` `110f24a`.
- selfhost2 snap_dir, kolibri, and typed-decisions. Also smoke_140 `tree_hash`, which that lane was building.
- help-test grok skip. crosslane `7d12860` already fakes grok on PATH.
- t1 smolvm, pregate sun_path, gate allowlist, tamper usage note. Open questions. No new ADR.
- TODO T-0091, T-0094, T-0081, T-0064, T-0043, T-0062, T-0046, T-0016, T-0005, and closed T-0110. `docs/TODO.md` was not edited.
- `pfylib/adapters/base.py` `tree_hash`. Skill-install equality hash.
- smoke_149 content-size cap. Would fork dogfood2 `home_sig`.
- harness2 mode-751 prune. dogfood2 already recorded it as a human allowlist skip.
- Item 04 smoke_137 tree_hash. Not a build. selfhost2 `1faa9fd` already hashes symlink readlink text. Empty-dir recording stays out.

After 098, 103, and 106, the smoke mains that still swallow a bad timeout are owned: smoke_109_111, smoke_112_114, smoke_115_116, smoke_117_118, smoke_119_121, smoke_122_124, smoke_137_139, smoke_148, smoke_149. That is the lane-empty exit. Turn cap was 8 cloud builds. Six were used.

## Test evidence

Targeted, niced, no full discover, no heavy lock:

- `tests.test_smoke_128_bad_timeout` `tests.test_x_intake_smoke_128_130`: 44 OK
- `tests.test_smoke_131_bad_timeout` `tests.test_x_intake_smoke_131_133`: 40 OK
- `tests.test_smoke_098_bad_timeout` `tests.test_x_intake_smoke_098_100`: 13 OK
- `tests.test_smoke_103_bad_timeout` `tests.test_x_intake_smoke_103_105`: 9 OK
- `tests.test_smoke_106_bad_timeout` `tests.test_x_intake_smoke_106_108`: 13 OK

Receipts were scanned before commit for AKIA, BEGIN PRIVATE, ghp_, xai-, sk-, and Bearer. No match. Product `*.py` diff from the integrate tip to `98e5795` has no em dash and no en dash.

## Cross-lane requests

Integrator, after selfhost2 `1faa9fd` is on the integration tip: apply `eval/mvp-1031/dogfood3/03-smoke137-timeout/diff.patch` onto `examples/x-intake-local/smoke_137_139.py`. Do not cherry-pick cloud `141b4c0c0ca3adc023d60b47c9b33412824bd6aa`. Replant the red test (it is not on this branch) and confirm a bad `PFY_XINTAKE_TIMEOUT` exits 2 before the neatroots lookup, while unset still reports the neatroots prereq string. The tree_hash hunk in `1faa9fd` does not overlap this timeout hunk.

No other file this lane needed is owned by a sibling.

## Gate

Tester plus Reviewer. The five accepts change runtime smoke mains. Docs, receipts, and the planted tests ride along. Pregate was not run.

pregate not run: host busy.

At 2026-11-01T01:14:13Z, `pgrep -f 'Runner[.]Worker'` was empty and MemAvailable was about 67 GiB, load about 3.8 on 32 cores. `flock -n ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` failed. This lane did not wait on the lock.

## OQ draft

ADR-0017 is still missing. This lane does not invent it and did not edit `docs/OPEN_QUESTIONS.md`. Links that name that ADR stay drafts until a lane that owns the decision index writes it.

## Project map

`.project-map/index.html` was not drawn. selfhost2, cloud-perf, timeoutfix, mvp3-fix2, and merge-plan still had live `grok --prompt-file` processes at handoff, and selfhost2 was inside a cloud review. Same rate-limit choice as the exit card.

## Next step

Merge this branch only through the integrator, with Tester plus Reviewer on the five smoke mains. Apply FINDING-D3-01 after `1faa9fd`. Run pregate when the heavy lock is free and `Runner.Worker` is idle. Do not start another bad-timeout build on an owned smoke file.
