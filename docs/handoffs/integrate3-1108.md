# Integrate3 handoff — 2026-11-08

Worktree `tmp/integrate3-1108/wt`, branch `bot/integrate3-1108`. No pull request. Pushes are fast-forwards of this worktree SHA to `origin/main`.

Wiring is the runner and the verdict file. A successful integration is a receipt whose `outcome` is `ok` from that runner on a commit that is an ancestor of `origin/main`, then `scripts/catalog_apply_verdict.py`. A refusal leaves the card bytes unchanged.

## Bumblebee

Wiring landed at `6f5591a50fb09f80876299af97d9d5f98d9ff9b5` (`eval/integrate/bumblebee/run-on-main.sh`).

Receipt: `eval/integrate/bumblebee/receipt.json`. Run id `bumblebee-6f5591a50fb0-20261108T212254Z`. `scripts/pfy_mcp_scan.py` scanned `tmp/bumblebee-fixture` and returned `CLEAN`, 0 findings. Tool version `bumblebee v0.1.2`. No model call.

Apply: `refused: above-ceiling: proposed I3 is above allowed I1 (evidence I1: notes, pin, report, VERDICT, script; tier_ceiling I1 agrees)`. Stage stays I2. Ceiling stays I1.

The integrate2 retry queue line `bumblebee` was archived and removed when this attempt started. The lane marker for the run was `tmp/integrate3-1108/bumblebee.dispatched`, not `tmp/integrate2/bumblebee.dispatched`. One attempt.

Factory questions for this receipt script:

1. What triggers it? An operator runs `eval/integrate/bumblebee/run-on-main.sh` after `HEAD` is an ancestor of `origin/main`. It is not a CI job.
2. What does it do, and which services does it read and write? It builds `tmp/bumblebee-fixture`, runs `scripts/pfy_mcp_scan.py` against that directory, and writes the receipt. It reads the local bumblebee binary under `~/.cache/pfy/tools/bumblebee/`. It does not scan the real home and it does not call a model.
3. What does it trigger next? `scripts/catalog_apply_verdict.py`. This run refused the proposed I3.
4. Where does a human re-enter? Before any ceiling move above I1, and before a pregate or CI gate. The card `next_gate` still says this lane is not a gate.
5. What stops two runs doing the same work? Noclobber on `BUMBLEBEE_LANE_MARKER`. A marker whose pid is not an ancestor of this process exits 2 and writes nothing.

## HiRoute

Pending in this handoff. The runner on main still exits 1 after the dispatched-marker check because classification is marked no-listen. The ev1107 probe scored 20/20 and stopped at I2. Ceiling stays I1.

## LiteLLM

Pending. No `pfy-litellm-local.service` yet. The receipt script probes an already listening proxy on `127.0.0.1:11435` or `127.0.0.1:4000`.

## Strata

Parked for this run. Do not start, stop, or download Strata. The earlier apply refusal stands: proposed I3 is above the evidence tier the checker allows, and the card stays I2.
