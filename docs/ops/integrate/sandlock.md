# Integration ticket: sandlock

Branch: `bot/integrate-sandlock-1108`. Card: `data/stages/sandlock.json` (I2, `tier_ceiling` I1). This lane does not edit those fields.

## Where the tool goes in the pipeline

Eval lanes that install or run a fetched tool call `scripts/integrations/sandlock/wrap.py`. The in-repo lane driver is `scripts/integrate_lane.sh`. The destructive-command-guard lane already taught that driver to run `eval/integrate/<slug>/run-on-main.sh` after a fast-forward land, then call `scripts/catalog_apply_verdict.py`. This lane does not edit the driver. A missing script keeps today's land. A receipt-script failure is logged and does not park. Apply refusal is logged and does not rewrite the card. The driver does not commit the receipt file.

For this slug the script is `eval/integrate/sandlock/run-on-main.sh`. It sandboxes one local fixture install (`cp` of `eval/integrate/sandlock/fixtures/hello.sh`) and one fixture run (`sh` of that copy). The script sets `PFY_SANDLOCK=all` so both steps are sandboxed.

What runs before it: land of the wiring SHA onto `origin/main`. What runs after it: the receipt script in the worktree, then `catalog_apply_verdict.py`. Apply is expected to refuse I3 while `tier_ceiling` is I1.

## What it replaces or adds

This is new wiring. No catalog card already sandboxed a fetched-tool install and a tool run in an eval lane. SkillSpector still scans a skill directory before copy. write-guard still mediates writes. agent-cage still runs the lab container. destructive-command-guard still classifies shell text. Those stay as they are.

When `PFY_SANDLOCK` is `off`, or the action is `run` under the default `auto`, wrap.py runs the command directly. That is today's behavior.

## How it fails safe

`PFY_SANDLOCK` defaults to `auto`.

- `auto` (or unset): sandbox `install` only.
- `all`: sandbox `install` and `run`.
- `off` (also `0`, `false`, `no`): never sandbox.

`SANDLOCK_BIN` is the only binary wrap.py calls. It must be an executable file. There is no PATH lookup. The receipt script points `SANDLOCK_BIN` at `scripts/integrations/sandlock/confine.py` and `SANDLOCK_REAL` at `~/.cache/pfy/tools/sandlock/unpack/sandlock` when `SANDLOCK_BIN` is unset and that unpack binary is executable. confine.py builds `sandlock run` with read grants on `/usr`, `/lib`, `/lib64`, `/bin`, and `/etc`, write on `SANDLOCK_STAGE` and the start-marker directory, `--clean-env`, and a forward of `PATH`, `LANG`, `LC_ALL`, `TMPDIR`, `SANDLOCK_STARTED`, and `SANDLOCK_STAGE`. It does not call `sandlock ps` or `kill`. It does not touch a process it did not start.

Self-test timeout is 30 seconds. The self-test argv is `binary true`. confine.py maps that to `sandlock check` plus `sandlock run -- /bin/true`. Command timeout is 120 seconds.

Missing binary, failed self-test, timeout before the command starts, or sandlock exiting before the starter marker: wrap.py logs `sandlock: unsandboxed` on stderr and runs the command once. A command that already started keeps its exit code, including timeout 124. There is no second unsandboxed attempt after a start. A profile denial after start is that exit code. This is not a deny-guard. A person can set `PFY_SANDLOCK=off`.

No sudo. No model lock.

## What stops two runs doing the same work

The driver marker is `tmp/integrate/sandlock.dispatched`. A second start exits 2.

wrap.py holds an advisory `fcntl` lock on `<cache>/lock` only for that cache. The success receipt is `<cache>/done/<sha256>.json`. The hash covers the action, the exact command, and `SANDLOCK_BIN`. A second successful call with the same binary, action, and command exits 0 and does not run the command. A missing binary is a different key, so a later direct call still runs. A nonzero exit is not stored as success. Two caches do not share the lock. There is no global lock and no edit to the shared test runner.

The lane cache is `PFY_SANDLOCK_CACHE`, or `~/.cache/pfy/tools/integrate-sandlock/lane`. Delete that directory to force the receipt script to run the fixture again.

## What real run on main produces the receipt

`eval/integrate/sandlock/run-on-main.sh RECEIPT.json`, from a checkout whose HEAD is an ancestor of `origin/main`. Otherwise the script exits 1 and writes nothing. The driver runs it after the wiring SHA is on `origin/main`. A worktree run, a doc, or this branch is not the receipt.

`run_kind` is `pipeline`.

## What the receipt file contains

`eval/integrate/sandlock/receipt.json` is written by `run-on-main.sh` into the worktree after land. The driver does not commit that file. It is not part of this branch. A commit of that file whose `main_sha` is already on `origin/main` is the I3 receipt. This lane stops when apply refuses.

- `slug`: sandlock
- `run_kind`: pipeline
- `main_sha`: the HEAD that was already an ancestor of `origin/main`
- `run_id`: `sandlock-<12 hex>-<started>`
- `log_path`: `eval/integrate/sandlock/notes.md`
- `started` and `finished`: UTC `YYYY-MM-DDTHH:MM:SSZ`
- `outcome`: ok
- `tool_version`: `sandlock --version` when `SANDLOCK_REAL` is set, else `sandlock-bin`
- `did`: sandboxed fixture install and one fixture tool run, or the unsandboxed fallback phrase when stderr contains `sandlock: unsandboxed`

`eval/integrate/sandlock/VERDICT.json` proposes I3 and names `receipt:eval/integrate/sandlock/receipt.json`. The card does not get that evidence line in this lane. `scripts/catalog_apply_verdict.py` refuses I3 under ceiling I1 and leaves the card bytes unchanged. Record the refusal and stop.
