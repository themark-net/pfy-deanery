# Integration ticket: <slug>

Copy this file to `tmp/TICKET-<slug>.md`. Fill every section before `scripts/integrate_lane.sh --slug <slug>`. Branch: `bot/integrate-<slug>-<MMDD>`.

Do not raise `tier_ceiling`. Do not edit `integration_stage` by hand. I3 is a main-run receipt, not this ticket.

## Where the tool goes in the pipeline

Name the pipeline or the gate. Name the command, the file, and the caller. Say what runs before it and what runs after it.

## What it replaces or adds

Say whether this is new wiring or a replacement. Name the behavior that stays when this tool is not selected.

## How it fails safe

Default is today's behavior when the binary is missing, errors, or times out. State the timeout. A guard that denies destructive commands fails closed and prints the reason. Any other failure must leave the pipeline exit path unchanged.

## What stops two runs doing the same work

The driver marker is `tmp/integrate/<slug>.dispatched`. A second start exits 2. Name the extra lock this tool needs (one worktree, one state file, one port). Say what happens if two checkouts still call the tool.

## What real run on main produces the receipt

Name the command that runs on a commit that is already on `origin/main`. A worktree run, a doc, or a merged diff is not enough. The run writes `eval/integrate/<slug>/receipt.json` and that file is committed where `main_sha` is an ancestor of `origin/main`.

`run_kind` is `pipeline` or `gate`.

## What the receipt file contains

`eval/integrate/<slug>/receipt.json`:

- `slug`
- `run_kind` (`pipeline` or `gate`)
- `main_sha` (ancestor of `origin/main`)
- `run_id` or `log` or `log_path`
- `started` and `finished`
- `outcome`
- `tool_version`
- `did` (what the tool did in that run)

Card evidence line after the file is on main: `receipt:eval/integrate/<slug>/receipt.json`.

Stage apply is `scripts/catalog_apply_verdict.py`. A refusal leaves the card bytes unchanged. Record the reason and stop.
