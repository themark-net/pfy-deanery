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

The old runner exited 2 when `tmp/integrate2/hiroute.dispatched` existed, then exited 1 with `classification needs a listener` without running the binary. The binary is installed under `~/.cache/pfy/tools/hiroute/`, and `routing list` is `local_control_only` with `model_call: never`.

`eval/integrate/hiroute/run-on-main.sh` now queries that socket. It does not bind a port, does not use 11434, and does not call a model. A receipt from this runner is a plan list, not `routing_agreement_of_20`. That metric needs the decision model. `ollama ps` was empty, so a new completion would load a model. That load is not approved. The runner does not do it.

Factory questions:

1. What triggers it? An operator runs the script after `HEAD` is an ancestor of `origin/main`. Not a CI job.
2. What does it do, and which services does it read and write? It runs `hiroute routing list` against the existing trial-home control socket and writes the receipt. It reads the cache install. It does not write the daemon's store (the command effect is `none`).
3. What does it trigger next? `scripts/catalog_apply_verdict.py`. The verdict proposes I3 for `routing_agreement_of_20`. This list does not measure that metric. Apply is expected to refuse while the card evidence has no main-run receipt line. The card is not hand-edited.
4. Where does a human re-enter? Before a GPU model load for the 20-prompt agreement, before any ceiling or stage edit, and before wiring HiRoute into `./pfy`.
5. What stops two runs doing the same work? A foreign `PFY_HIROUTE_LANE_MARKER` (default `tmp/integrate2/hiroute.dispatched`) exits 2. An ancestor pid is the admitted lane.

Receipt on `d6088a477cf79b27c681c358ff0812d91e93c87f`: outcome ok. One plan, alias `hiroute-eval-difficulty-route`. `model_call never`. Apply refused: `above-ceiling: proposed I3 is above allowed I1 (evidence I1: entry, report; tier_ceiling I3 does not raise it)`. Card bytes unchanged. This is a local-control receipt, not an I3 integration. The 20-prompt agreement was not re-run. The stale `tmp/integrate2/hiroute.dispatched` (dead pid 3485105) was moved into `tmp/integrate2/archive/` before the run. One attempt.

## LiteLLM

Wiring was already on main (`eval/integrate/litellm/run-on-main.sh`, commit `8a35fd5e` and later). This run installed a real proxy. It is not a stand-in.

- Package: `litellm[proxy]` 1.108.3 in `/home/mark/.cache/pfy/tools/litellm/venv`
- Service: `pfy-litellm-local.service` (systemd user, enabled)
- Listen: `127.0.0.1:11435`
- Config: `/home/mark/.cache/pfy/tools/litellm/config.yaml`
- Model name: `local-coder`, upstream `ollama/qwen2.5-coder:1.5b` at `http://127.0.0.1:11434`
- No cloud provider and no API key. `general_settings.dangerously_permit_weak_or_unset_master_key` is true so the loopback proxy can answer the receipt's unauthenticated `GET /v1/models`. LiteLLM 1.108.3 refuses to boot otherwise.
- `GET /v1/models` returned HTTP 200 and 1 id, `local-coder`. `ollama ps` was empty before and after that GET. The models list did not load a model.
- Completion was not run. A completion would load `qwen2.5-coder:1.5b`. That load is not approved. The completion check is parked pending GPU approval. The receipt says `No completion.`

Receipt on `ed8a6aa6a8af8e1cb6644cf73dc8ed22406728f7`: outcome ok, `tool_version` 1.108.3. `PFY_LITELLM_LANE_MARKER` pointed at a missing integrate3 path so the stale integrate2 marker did not block the run. The integrate2 marker was left in place.

`scripts/catalog_apply_verdict.py` printed `PROMOTE I3 readonly_proxy_models_status threshold=200 value_gate=pass modularity_gate=pass` and changed only `integration_stage` from I2 to I3. `tier_ceiling` stayed I3. The rubric metric is the models status. This promotion is that measurement on the real proxy, not a compile check.

`tests/test_litellm_fail_closed.py` now compares the committed receipt bytes before and after a refused run and a stubbed probe. A receipt that is already on main stays. A run that rewrites it still fails.

Factory questions for the already-landed probe:

1. What triggers it? An operator runs the script while the proxy is already listening on 11435 or 4000, and `HEAD` is an ancestor of `origin/main`.
2. What does it do, and which services does it read and write? It reads `GET /v1/models` from the loopback proxy and writes the receipt. It does not call Ollama for that probe. The proxy, when asked for a completion, would read Ollama. This run did not ask.
3. What does it trigger next? `scripts/catalog_apply_verdict.py`, which promoted the stage to I3.
4. Where does a human re-enter? Before a completion or any other call that loads a model, and before any cloud key is added to the proxy config.
5. What stops two runs doing the same work? `PFY_LITELLM_LANE_MARKER`. A marker whose pid is not an ancestor of this process exits 2.

## Strata

Parked for this run. Do not start, stop, or download Strata. The earlier apply refusal stands: proposed I3 is above the evidence tier the checker allows, and the card stays I2. The card text names a GPU run. No receipt was attempted.
