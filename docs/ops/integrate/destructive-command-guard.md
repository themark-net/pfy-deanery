# Integration ticket: destructive-command-guard

Branch: `bot/integrate-destructive-command-guard-1108`.

Do not raise `tier_ceiling`. Do not edit `integration_stage` by hand. I3 is a main-run receipt, not this ticket.

Card: `data/stages/destructive-command-guard.json` (I2, `tier_ceiling` I1). Probe: `eval/evq1107/destructive-command-guard/probe.py`. Binary: `~/.cache/pfy/tools/destructive-command-guard/unpack/dcg` (override `PFY_DCG_BIN`). The probe denied 12 of 12 destructive commands and allowed 8 of 8 ordinary ones.

## Where the tool goes in the pipeline

The pipeline is the I2-to-I3 lane in [INTEGRATE.md](../INTEGRATE.md). The driver is `scripts/integrate_lane.sh`. It runs git and grok for the agent. Each of those commands goes through `run_checked`, which calls `scripts/integrations/dcg/guard.sh` and runs the command only when the guard exits 0.

No in-repo eval lane driver executes an agent shell command. `examples/eval-harness/` and `data/eval-lanes.json` run fixed make and python commands. `scripts/pfy_build_cloud.py` `run_command` starts the test gate and the grok process. It does not classify one shell argv. There is no in-repo Build hook config for Grok. This lane does not write `~/.grok`.

Before the guard: the driver has already created `tmp/integrate/<slug>.dispatched`. After an allow: the same git or grok command runs as it does today. After a deny: the driver parks on that command and does not run it. After a fast-forward land, the driver runs `eval/integrate/destructive-command-guard/run-on-main.sh` when that file is in the worktree, then `scripts/catalog_apply_verdict.py`.

## What it replaces or adds

This is new wiring. write-guard stays the write mediator. It does not see the shell command. Sandlock and Sponsio stay on their own jobs.

When this tool is not selected, `PFY_DCG_DISABLE=1` is the only opt-out. The command then runs and the guard prints `dcg-disabled`. A missing `guard.sh` prints `dcg-fallback` and keeps today's behavior for the driver command.

## How it fails safe

The dcg timeout is 2 seconds. The child environment is `PATH`, `LANG`, `NO_COLOR`, `DCG_CONFIG`, and a cache `HOME`. History, update checks, and hook self-heal are off in `scripts/integrations/dcg/config.toml`.

If the binary is missing, dcg errors, the JSON decision is unusable, or the 2 second timeout fires, the guard prints `dcg-fallback` and does not execute the command. Ordinary commands exit 0 so the driver keeps today's behavior. These argv patterns still exit 126:

- `rm -rf /`, `rm -rf ../`
- `git push --force`, `git push -f`, `git push --force-with-lease`
- `git reset --hard`
- `git clean` with both `f` and `d` in a short option (`-fd`, `-fdx`)
- `dd` with `of=/dev/...`
- `mkfs` and `mkfs.*`

`git push origin main` is not in that list. The pinned binary allows the driver's `git fetch`, `git rebase`, and non-force `git push`.

## What stops two runs doing the same work

The driver marker is `tmp/integrate/<slug>.dispatched`. A second start exits 2. The guard adds no lock and no state file. Two lane runs both classify and neither divides a command with the other. A receipt is written only to the path the caller passes. `run-on-main.sh` exits nonzero and writes nothing when `HEAD` is not an ancestor of `origin/main`. `scripts/catalog_apply_verdict.py` is the only writer of `integration_stage`.

## What real run on main produces the receipt

`eval/integrate/destructive-command-guard/run-on-main.sh RECEIPT.json` from a checkout whose `HEAD` is an ancestor of `origin/main`. The lane driver runs that script after the fast-forward land, then calls `scripts/catalog_apply_verdict.py`. A worktree run, a doc, or a merged diff is not the receipt. `run_kind` is `gate`.

## What the receipt file contains

`eval/integrate/<slug>/receipt.json`:

- `slug` (`destructive-command-guard`)
- `run_kind` (`gate`)
- `main_sha` (ancestor of `origin/main`)
- `run_id`
- `started` and `finished`
- `outcome`
- `tool_version`
- `did` (what the guard classified in that run)

Card evidence line after the file is on main: `receipt:eval/integrate/destructive-command-guard/receipt.json`.

Stage apply is `scripts/catalog_apply_verdict.py`. The card `tier_ceiling` is I1, so apply refuses I3. A refusal leaves the card bytes unchanged. Record the reason and stop.
