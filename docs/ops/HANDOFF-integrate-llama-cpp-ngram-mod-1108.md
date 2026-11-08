# Handoff: integrate llama-cpp-ngram-mod (1108)

Branch `bot/integrate-llama-cpp-ngram-mod-1108`. Opt-in ngram decode for the model-bound lane. Default stays the current engine. No push. The stage card is unchanged.

## What landed

- `scripts/integrations/llama_ngram/run.py` starts a llama-server this process owns when `PFY_LLAMA_NGRAM=1`. It uses a GGUF already on disk, a free `127.0.0.1` port, and `--spec-type ngram-mod`. It stops only that pid.
- `examples/eval-harness/run_scored_task.py` checks that one variable. When it is unset, `_chat_completion` calls the current engine with the same arguments. When the check falls back, it does the same.
- `scripts/eval-auto.sh` runs `run.py` only when the flag is `1`, after Ollama is up and before the existing ladder.
- `eval/integrate/llama-cpp-ngram-mod/run-on-main.sh` refuses a HEAD that is not an ancestor of `origin/main`, then runs one step inside `scripts/model_lock.sh`.
- `eval/integrate/llama-cpp-ngram-mod/VERDICT.json` proposes I3. Apply refused. See below.
- Ticket: `docs/ops/integrate/llama-cpp-ngram-mod.md`. Notes: `eval/integrate/llama-cpp-ngram-mod/notes.md`.

`pipelines/dogfood/local-bench-4/run_nommap_server.sh` is unchanged. No model download. No `ollama stop`.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, and the stage cards whose uses already name this job.

The 2026-10-06 ranking pairs row 7 (this flag) with row 1 (llama-server `--no-mmap`). The nommap launcher does not pass `--spec-type`. Strata is a second engine on gap L, not a decode flag. LiteLLM proxies. It does not decode.

Stage cards that already mention the engine path:

| Card | What it already covers |
| --- | --- |
| llama-cpp-ngram-mod | Zero-weight n-gram draft. I2. Ceiling I1. Non-goals include a default engine change and gate wiring. |
| harness2 | Own llama-server for the decision bench. No ngram flag. |
| hal0 | Reference only. Gap L stays with Ollama and llama-server. |
| reasonix | Engine path stays Ollama, llama-server, LiteLLM, and Strata. |
| open-webui | Chat client. Engines stay elsewhere. |
| deepseek-v4-1-flash-1017-gguf | Draft-model weights. They do not fit this host. ngram-mod has no second file. |

No card already runs `--spec-type ngram-mod` in the model-bound lane. This lane adds the opt-in and leaves the default path in place. The uses line is not a CI, testing, or review role, so the self-pipeline rule does not apply.

## Five questions

1. What triggers it? `PFY_LLAMA_NGRAM=1` on a model-bound decode (`run_scored_task.py`, `eval-auto.sh`, or `run-on-main.sh`). Unset does nothing new.
2. What does it do, and which services does it read and write? It reads a local GGUF and writes tokens to the caller from its own llama-server. It reads `ollama ps` and does not change Ollama. Cache writes stay under `~/.cache/pfy/tools/integrate-llama-cpp-ngram-mod/`.
3. What does it trigger next? The caller uses the completion, or the current engine when the check falls back. Stage apply is a separate command.
4. Where does a human re-enter? Mark raises `tier_ceiling`. The flag stays off until he wants it. A mismatch or a missing binary keeps the current engine.
5. What stops two runs doing the same work? `scripts/model_lock.sh` holds the local-model lock. A receipt whose sha matches `PFY_LLAMA_NGRAM_SHA` exits nonzero, does not start a server, and does not change the receipt bytes.

## Fail safe

Missing binary, missing or unset model, file over 25 GB, health timeout (180s), completion timeout (180s), empty output, or a check-prompt mismatch: log the reason, stop only this run's pid, print `engine: baseline`, exit 0. A real server also refuses to start unless `PFY_MODEL_LOCK_HELD=1`. Duplicate sha exits nonzero.

## Tests

Behavior tests, fake server, no network and no real model:

- `tests/test_llama_ngram_single_flight.py`
- `tests/test_llama_ngram_default_off.py`
- `tests/test_llama_ngram_model_guard.py`
- `tests/test_llama_ngram_mismatch_fallback.py`
- `tests/test_llama_ngram_fail_recover.py` (missing server, missing model, HEAD not on main)
- `tests/test_llama_ngram_hook.py` (the scored-task hook)

`python3 scripts/catalog_check.py` passed. `python3 scripts/check_no_encoded_payloads.py` passed.

## Apply refusal

```text
python3 scripts/catalog_apply_verdict.py --card data/stages/llama-cpp-ngram-mod.json --verdict eval/integrate/llama-cpp-ngram-mod/VERDICT.json
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I2: report, VERDICT, probe artifact, other; tier_ceiling I1 caps the evidence)
```

Exit 1. Card sha256 before and after: `9a9104acd083ea1cc1072be41e0839b95ac7580344e26a189d9586392816fb95`. `git diff -- data/stages/llama-cpp-ngram-mod.json` was empty. Stopped there. Ceiling stays I1. `integration_stage` stays I2.

## Receipt run

`ollama ps` was empty and MemAvailable was about 61 GiB. The lock was free. The run used HEAD `14b79a0a81d71e63c02007137010d8f0a17021a4` while that SHA was `origin/main`. It is still an ancestor of `origin/main`. Do not run the command again. A second run for this sha exits nonzero and must not rewrite the receipt.

```bash
eval/integrate/llama-cpp-ngram-mod/run-on-main.sh eval/integrate/llama-cpp-ngram-mod/receipt.json
```

Exit 0. Stdout: `engine: ngram`. The receipt is `eval/integrate/llama-cpp-ngram-mod/receipt.json`.

- `tok_s` 77.18
- `baseline_tok_s` 34.83
- `identical_outputs` yes
- ratio about 2.22 on this one short check prompt
- `tool_version` `version: 1 (6f3a9f3de)`
- servers listened on `127.0.0.1:52555` and `127.0.0.1:42595`, then logged cleanup
- ngram-mod log: 53 accepted of 53 drafted tokens

The evq probe median was 4.71x on five longer prompts. This receipt is a different, shorter check. Both texts matched. No llama-server process was left running. This run does not apply I3. The ceiling refusal above still stands.

## Out of scope

No push, no PR, no card edit, no `tier_ceiling` change, no Makefile or `.github/` edit, no gate wiring.
