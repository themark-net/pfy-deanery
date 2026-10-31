# Handoff: Entry 149 (MemPalace) smoke B2 fix and Reviewer follow-ups

Branch: `catalog/x-intake-149`. Date: 2026-10-29 PT. Author: Grok Bot (executor), working in `~/DEVELOP/pfy-mentat/tmp/x149` on nimo.

## Status

Code and tests done; branch pushed. Gate pending (pregate plus Reviewer at the pinned SHA). Not merged; bots fast-forward main to the pinned SHA after the gates.

## Problem

Reviewer B2: `smoke_149.py` fell back to running MemPalace with no sandbox (network reachable, writable root) when bwrap was missing or unusable, and could still exit 0 PASS. Entry 148's rule is that an unconfined run is never a PASS: exit 2 with a recorded reason.

## Change

- `examples/x-intake-local/smoke_149.py`
  - No bwrap or unusable bwrap: exit 2, reason `bwrap is not usable here; MemPalace must run with no network`. There is no unsandboxed path any more; `run()` always wraps in bwrap (`--ro-bind / /`, `--unshare-net`, tmpfs `/dev/shm`, `/proc`, only the smoke's temp dir writable).
  - Test-only `PFY_SMOKE_REAL_HOME_BIND=1` binds the real HOME writable so the real-HOME check can be exercised under bwrap (same knob as Entry 148). Superseded on 2026-10-30: production `smoke_149.py` no longer reads that variable. See the follow-up section.
  - Version pin is an exact match: the first `X.Y.Z...` token of `--version` must equal `MEMPALACE_VERSION` (was a substring test, so `3.12.0.1` or `13.12.0` passed).
  - Not-staged reason now names the full path `~/DEVELOP/pfy-mentat/tmp/mempalace/.venv`.
- `tests/test_x_intake_smoke_149.py` (10 to 18 tests)
  - `needs_bwrap` guard loads the smoke's own `bwrap_ok`, like Entry 148; tests that need a real scan skip without it.
  - New: no bwrap exits 2 and the stub never runs (empty PATH); child has no network (loopback listener sees no connect); child root is read-only (write outside the temp dir fails); child gets a temp HOME with the copied model cache; mine exit fails the run; timeout `0` and `-5` exit 2 with reason `bad PFY_XINTAKE_TIMEOUT`; inexact versions exit 2.
  - `test_real_home_write_fails` now runs under bwrap with the test-only bind (it used to depend on the unsandboxed fallback).
- `sources/entries/149-mempalace.md`: leading blank line removed; date carries PT (window also in PT and UTC); ChromaDB `/dev/shm` note marked as seen on the author's box only; smoke paths match the code (`~/DEVELOP/pfy-mentat/tmp/mempalace/...`); exact pin and bwrap exit 2 described; cosine/BM25 labelled as observed scores from one run.
- `docs/automation/x-intake-2026-10-29-handoff.md`: test count updated.
- Merged `fix/ci-ubuntu-image` (CI pins ubuntu-24.04 and installs ripgrep) so the tip's CI is green.

## Verify

```
python3 -m unittest tests.test_x_intake_smoke_149 tests.test_x_intake_smoke_148
# 39 OK in 4.312s on nimo (bwrap usable). 149 is 25 of those.
```

Also run with bwrap hidden, as GitHub's ubuntu-24.04 G0 job does: `PATH=/nonexistent /usr/bin/python3 -m unittest tests.test_x_intake_smoke_149` gives 25 OK, 16 skipped (2026-10-30, after the follow-up below). The historical B2 run was 18 OK, 11 skipped. The first tip CI run (41003563965 at 2c777bd) failed `test_version_pin_is_exact` there because the version probe runs inside bwrap; that test carries `needs_bwrap`. `test_version_pin_exit_2` now does too, because it asserts the pin reason rather than only the exit code.

## Follow-up 2026-10-30 (bot/pfy-followups-1030)

- `version_of` is exercised through a real stub on `PATH` (no `MEMPALACE_BIN`). A stub that prints `MemPalace 3.12.0` passes and the receipt `version` is `3.12.0`. A stub that exits 1 and prints `not-a-version` exits 2 with reason `version pin 3.12.0 != --version None` and does not run `init`.
- `test_version_pin_exit_2` requires reason `version pin 3.12.0 != --version 9.9.9`.
- Production does not read `PFY_SMOKE_REAL_HOME_BIND`. `test_real_home_write_fails` loads the smoke and passes `extra_binds` so the temp HOME is writable inside bwrap; the stub creates `.mempalace` and the smoke exits 1 with `real_home_unchanged`. `test_real_home_env_hook_does_not_bind` sets the old variable and expects exit 0 with `real_home_changed` empty. Entry 148 keeps its own hook. Its tests were not modified.
- `/proc` is mounted only when that directory is readable, and `/dev/shm` only when it is writable. If either required mount cannot be made, the smoke exits 2 with `required bind <path> is not usable; refusing to run unsandboxed` and does not run MemPalace. There is no unsandboxed fallback. When both are usable, every bwrap argv that runs the binary includes `--tmpfs /dev/shm` and `--proc /proc`.
- A `bwrap` on `PATH` that exits 1: exit 2, reason `bwrap is not usable here; MemPalace must run with no network`, stub does not run.
- The bare `2026-10-25` on the entry's checked-at line is now `2026-10-25T04:41:28Z` (upstream committer time from the public GitHub commit API). The Date line already said PT.

How the real-HOME change fails and recovers: if `main()` starts reading the env var, `test_real_home_env_hook_does_not_bind` goes red (the write lands). If the in-process seam stops passing `extra_binds`, or `home_sig` stops noticing the write, `test_real_home_write_fails` goes red (it expects the write to be visible and the run to exit 1). Recovery is the check plus the test-only argument. Do not put the bind back on an env var.

Mutation check recomputed on nimo on 2026-10-30. Each mutant was applied to `smoke_149.py`, `python3 -m unittest tests.test_x_intake_smoke_149` was run, and the file was restored. 13 applied, 13 killed, 0 survived.

| Mutant | Result |
|--------|--------|
| drop `--unshare-net` | killed (`test_child_has_no_network`) |
| `--bind / /` instead of `--ro-bind` | killed (`test_child_root_is_read_only`, `test_real_home_env_hook_does_not_bind`) |
| sandbox forced off in `run()` | killed (`test_child_has_no_network`, `test_child_root_is_read_only`, `test_proc_and_shm_are_mounted_when_usable`, `test_real_home_env_hook_does_not_bind`) |
| no-bwrap check removed | killed (`test_bwrap_exit_1_fails_closed`, `test_no_bwrap_exits_2_never_runs_unsandboxed`) |
| child HOME = real HOME | killed (`test_child_gets_temp_home_with_model_cache`) |
| mine_ok check removed | killed (`test_mine_failure_fails`) |
| `timeout <= 0` guard removed | killed (`test_zero_timeout_exit_2`, `test_negative_timeout_exit_2`) |
| version pin back to substring | killed (`test_version_pin_is_exact`) |
| `bwrap_ok` ignores the exit code | killed (`test_bwrap_exit_1_fails_closed`) |
| `PFY_SMOKE_REAL_HOME_BIND` restored | killed (`test_real_home_env_hook_does_not_bind`) |
| required-mount check removed | killed (`test_required_proc_bind_missing_exits_2`) |
| proc and shm mounts omitted | killed (`test_proc_and_shm_are_mounted_when_usable`) |
| `version_of` always returns the pin | killed (`test_version_of_rejects_broken_binary_on_path`, `test_version_pin_exit_2`, `test_version_pin_is_exact`) |

CI and pregate results at code SHA 996ea3d: eval-structural 41010561425 success (ubuntu-24.04 G0 and self-hosted nimo G0), operator-launch-filemode 41007276111 success; pregate `996ea3d-20261030T052903Z-459010` OVERALL=PASS pass=6 fail=0 skip=1 (SKIP suite by design). Reviewer verified B1 and B2 fixed at 996ea3d. The commit that fills this line is docs-only.

## How this fails / how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Host without bwrap (or userns disabled) | Smoke exits 2 with the bwrap reason; sandbox tests skip | Expected; run on nimo or a host with working bwrap |
| bwrap on PATH exits non-zero | Probe fails; smoke exits 2 with the bwrap reason; the tool does not run | Fix bwrap. Never run unsandboxed |
| `/proc` or `/dev/shm` not usable | Exit 2 with `required bind <path> is not usable`; the tool does not run | Fix the host mount. Never skip the mount and never run unsandboxed |
| Real-HOME env hook returns | A writable bind lets the stub write `.mempalace` and the env-hook test goes red | Remove the env read. The writable bind stays an in-process `extra_binds` argument |
| Real MemPalace not staged on nimo | Smoke exits 2 (not staged / model not cached) | Stage `tmp/mempalace/.venv` and warm `tmp/mempalace/home` once |

## Known gaps

- Real MemPalace is still not staged on nimo, so the end-to-end smoke has only run on the Grok Bot box.
- The ChromaDB `/dev/shm` finding is unreproduced on nimo.
- `sources/entries/149-mempalace.md` still says 18 stub tests. This run's only allowed edit in `sources/entries/` was the checked-at time zone. `docs/automation/x-intake-2026-10-29-handoff.md` still says 18 as well. The suite on 2026-10-30 is 25 tests in `tests.test_x_intake_smoke_149`.

## Next step

Reviewer delta gate at the pinned SHA, then bots fast-forward main. No PR (Mark's 2026-10-19 rule).
