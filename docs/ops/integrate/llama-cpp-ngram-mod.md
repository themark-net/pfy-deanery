# Integration ticket: llama-cpp-ngram-mod

Branch: `bot/integrate-llama-cpp-ngram-mod-1108`. Card: `data/stages/llama-cpp-ngram-mod.json` (I2, tier_ceiling I1).

Do not raise `tier_ceiling`. Do not edit `integration_stage` by hand. I3 is a main-run receipt, not this ticket. Apply is expected to refuse I3 while the ceiling stays I1.

## Where the tool goes in the pipeline

The model-bound lane is the serialized local-model step. Host callers are `scripts/eval-auto.sh` (`make eval-auto` already holds `scripts/model_lock.sh`; the shell script alone does not) and `examples/eval-harness/run_scored_task.py` `_chat_completion` (nightly suite via `examples/eval-harness/run_suite.py`).

What runs before it: structural checks in eval-auto, or the task prompt load in the suite. What runs after it: the existing Ollama ladder when the flag is unset or the ngram check falls back. Pregate does not call this tool.

The receipt command is `eval/integrate/llama-cpp-ngram-mod/run-on-main.sh`. It checks that HEAD is an ancestor of `origin/main`, then runs one step inside `scripts/model_lock.sh`.

## What it replaces or adds

This is opt-in wiring. `PFY_LLAMA_NGRAM=1` starts a llama-server this process owns, on `127.0.0.1` and a free port, with `--spec-type ngram-mod`, using a GGUF already on disk. The entrypoint is `scripts/integrations/llama_ngram/run.py`.

Unset, empty, or any value other than `1` keeps the current engine. `_chat_completion` calls that engine with the same arguments it uses today. `pipelines/dogfood/local-bench-4/run_nommap_server.sh` is unchanged.

## How it fails safe

Default is today's behavior when the binary is missing, the model path is missing or unset, the file is over 25 GB (`PFY_LLAMA_NGRAM_MAX_BYTES` overrides that cap), the server does not become healthy, or the fixed check prompt differs from the baseline text.

Health wait is 180 seconds. One completion wait is 180 seconds. Stop waits 2 seconds, then SIGKILL on the pid this run started. A real server also requires `PFY_MODEL_LOCK_HELD=1`. Low MemAvailable (under model size plus 25 GiB) or a non-empty `ollama ps` logs the reason and uses the baseline engine.

This is not a destructive-command guard. Failure leaves the pipeline on the current engine and exits 0. A duplicate receipt for the same sha exits nonzero and does not start a server. The script does not call `ollama stop` and does not signal any other pid.

## What stops two runs doing the same work

The integrate driver marker is `tmp/integrate/llama-cpp-ngram-mod.dispatched`. A second driver start exits 2.

`scripts/model_lock.sh` is the serializer for the model step. A second opt-in run waits on that lock instead of starting another llama-server. Each run stops only the pid it started (`PFY_LLAMA_NGRAM_LOCK_DIR/server.pid` records it).

`run-on-main.sh` sets `PFY_LLAMA_NGRAM_SHA` and `PFY_LLAMA_NGRAM_RECEIPT`. When that receipt already has the same sha, `run.py` exits nonzero, does not launch llama-server, and leaves the receipt bytes unchanged.

## What real run on main produces the receipt

```bash
eval/integrate/llama-cpp-ngram-mod/run-on-main.sh eval/integrate/llama-cpp-ngram-mod/receipt.json
```

HEAD must be an ancestor of `origin/main`. The command exports `PFY_LLAMA_NGRAM=1`, points at the on-disk qwen2.5-coder blob when `PFY_LLAMA_NGRAM_MODEL` is unset and that file exists, and execs `scripts/model_lock.sh`. A worktree run can verify the script. Stage apply still needs the receipt on main and a ceiling of I3 or higher. This lane does not change the ceiling.

`run_kind` is `pipeline`.

## What the receipt file contains

`eval/integrate/llama-cpp-ngram-mod/receipt.json` follows `docs/ops/INTEGRATE.md` and adds the speed fields:

- `slug` (`llama-cpp-ngram-mod`)
- `run_kind` (`pipeline`)
- `main_sha` (ancestor of `origin/main`) and `sha` (same value, so a second run can see it)
- `log_path`
- `started` and `finished`
- `outcome`
- `tool_version`
- `did`
- `tok_s`, `baseline_tok_s`
- `identical_outputs` (`yes` or `no`)

Card evidence line after the file is on main: `receipt:eval/integrate/llama-cpp-ngram-mod/receipt.json`.

Stage apply is `scripts/catalog_apply_verdict.py`. A refusal leaves the card bytes unchanged. Record the reason and stop.
