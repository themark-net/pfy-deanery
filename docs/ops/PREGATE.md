# Pregate (local, free)

Run this before any Tester or Reviewer gate request and attach its summary. It catches the failure classes that cost past gate rounds: unsandboxed tests, red ubuntu CI, test-runner cheats, and orphan processes.

## Rule

1. Run pregate on the exact SHA you will gate (full run, no `--only`).
2. Attach `~/DEVELOP/pfy-mentat/tmp/pregate-runs/<run-id>/pregate-summary.md` to the gate request. The path is printed on the last lines of the run.
3. Do not spend Tester/Reviewer turns until overall is PASS, unless you have an explicit waiver for a documented known gap.

## How to run (nimo)

From any pfy-mentat worktree that has this script:

```bash
./scripts/pregate.sh                 # full run on HEAD in an isolated worktree
./scripts/pregate.sh 3278cfc         # full run on a SHA or ref
./scripts/pregate.sh --only lint,ci-parity,gate-hash REF   # fast loop (seconds), not for gate attachment
./scripts/pregate.sh --keep-worktree REF                   # keep the run worktree for debugging
./scripts/pregate.sh --in-place      # this checkout; HEAD must equal REF and the tree must be clean
./scripts/pregate.sh --force-suite REF                     # also run the standalone suite check
./scripts/pregate.sh --base origin/main REF                # base for the committed gate-file diff (default)
```

Environment knobs: `PREGATE_STEP_TIMEOUT` (seconds per check, default 2400), `PREGATE_MAX_ROOT_LEN` (default 60) and `PREGATE_KEEP_RUNS` (default 20).

Limits:

- One pregate per host at a time. Concurrent runs are not coordinated: they share `tmp/pregate-latest-summary.md`, compete for CPU (which can trip timing-sensitive tests), and two runs of the same SHA in the same second exit 2.
- A repo path containing whitespace is refused (exit 2).
- `--base` must resolve (default `origin/main`). An unknown base exits 2 instead of skipping the committed gate-file diff.

## Output

- Run folder (kept after the run): `~/DEVELOP/pfy-mentat/tmp/pregate-runs/<shortsha>-<UTC stamp>-<pid>/`
  - `pregate-summary.md`: the file to attach
  - `logs/<check>.log`: one log per check; every FAIL line names its log here
  - `receipts/structural.latest.md`, `receipts/golden.latest.md`: G0 receipts (tracked files are never rewritten)
- Convenience pointer: `~/DEVELOP/pfy-mentat/tmp/pregate-latest-summary.md` (overwritten by whichever run finishes last; attach the run-folder copy instead)
- Exit codes: 0 PASS; 1 FAIL, or no check passed; 2 usage or setup error (unknown check, missing `--only` value, bad ref, unknown `--base`, more than one REF, path too long, whitespace in path, dirty `--in-place`); 130/143 when interrupted by SIGINT/SIGTERM
- Retention: each run keeps the newest 20 run folders (`PREGATE_KEEP_RUNS`) and deletes older ones. Only folders in `tmp/pregate-runs/` whose name matches the run-id pattern are ever removed. Copy a summary elsewhere if it must outlive that.

The work happens in a detached worktree at `~/DEVELOP/pfy-mentat/tmp/pg/<shortsha>-<HHMMSS>` with scratch, `PFY_STATE_DIR` and `TMPDIR` under `~/DEVELOP/pfy-mentat/tmp/pgs/`. Both are removed on exit unless `--keep-worktree`. Paths stay short because harness2 sandbox sockets must fit sun_path (108 bytes). Pregate refuses to start (exit 2) if either path is over 60 characters. On SIGINT/SIGTERM it stops only its own child processes, writes a FAIL summary and cleans up. A run killed with SIGKILL leaves a stale worktree, and the next run prunes it once no live process uses it. The per-check watchdog only signals a process that is still a direct child of its pregate, so it never hits a reused PID or a child reparented after a SIGKILL.

## Checks

| check | what it covers |
|---|---|
| lint | The CI lint surface (this repo has no ruff job): launcher mode 100755, `py_compile` of board/gui, `bash -n scripts/pfy`, `./pfy help`, `check_no_encoded_payloads`, `smoke_contract_lint`, `catalog_check`, and a workflow image pin (`scripts/check_workflow_image_pin.py`): GitHub-hosted `runs-on` must be `ubuntu-24.04` as a string, a list, or a matrix expression that resolves to that pin. Self-hosted label lists pass. Malformed YAML fails the check. A missing PyYAML fails the check. `eval-structural.yml` must still install ripgrep |
| ci-parity | bwrap hidden. A static pin that the two runtime-dir tests pass `auto_unsafe=False` (code only; comments do not count), plus a run of those two tests. Catches the 2fadea1 ubuntu failure in seconds. FAILs if the test file is missing |
| gate-hash | `tests/` and gate files (`conftest.py`, `sitecustomize.py`, `pytest.ini`, ...) in the run tree match HEAD (catches modified, deleted, renamed, staged or untracked cheats with `--in-place`). Also FAILs on any committed add/modify/delete of a strict gate file vs the merge-base with `--base` (needs a reviewer waiver), and lists existing test files changed vs base as a NOTE for the reviewer |
| ubuntu-parity | The full `python3 -m unittest discover -s tests -t .` with bwrap hidden: the caller's PATH mirrored minus `bwrap`, with `PFY_STATE_DIR` set as in the ubuntu job. This mirrors the pinned `ubuntu-24.04` image, where bwrap is unusable and bwrap-gated tests skip. If the G0 image changes, revisit this check. Any test that passes only when bwrap is present fails here, as it would on ubuntu CI |
| eval-structural | The G0 ubuntu job's steps with the host PATH: structural (which runs the full discover, with sandbox tests where bwrap works, as on the nimo runner), golden, gab/jev/launch-wizard selftests, catalog_check, toolset matrix/plan, hedge decide, launcher exec, encoded payloads |
| suite | Standalone discover with the host PATH. Skipped by default because the two checks above already run it. Use `--force-suite` or `--only suite` |
| orphans | Runs last. Compares a process snapshot taken before the checks with one taken after. Any new live process of this user whose argv or cwd is under this run's root or scratch FAILs, as do `orphan*.pid` / heartbeat files. Fails closed if `ps` fails. Other worktrees' processes are never matched or signalled |

Every check has a watchdog (`PREGATE_STEP_TIMEOUT`). A hung step, such as an orphan holding the output pipe, is killed and reported as FAIL with its log.

Unittest skip counts depend on the host (bwrap, grok, Ollama, Python version), so compare them only between runs on the same host.

## Past failure types mapped to checks

- Unsandboxed tests and the `--unsafe-no-sandbox` auto-add: ci-parity, ubuntu-parity
- Red ubuntu CI because bwrap is missing: ubuntu-parity (full suite without bwrap) and ci-parity (fast pin). eval-structural alone does not cover this on a host with bwrap
- Test-runner cheats (new conftest/sitecustomize, edited or deleted protected tests): gate-hash
- Orphan processes and hangs: orphans, plus the per-check watchdog
- Structural G0 drift: eval-structural, lint

## What pregate does not replace

- Live model eval (`./pfy eval-local-build`)
- Tester/Reviewer judgment, including reading the gate-hash NOTEs about edited tests
- The ubuntu CI run itself: the Python version (3.12 on CI) and missing grok/Ollama are not emulated

## See also

- [HANDOFF-pregate.md](HANDOFF-pregate.md)
- [GATE-NOTES-fix2.md](GATE-NOTES-fix2.md)
- [HANDOFF-pfy-local-build-mvp.md](HANDOFF-pfy-local-build-mvp.md)
