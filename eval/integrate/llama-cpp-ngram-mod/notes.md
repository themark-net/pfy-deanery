# llama-cpp-ngram-mod notes

Opt-in decode for the model-bound lane. The flag is `PFY_LLAMA_NGRAM=1`. Any other value, including unset, keeps the current engine.

## Run

```bash
scripts/model_lock.sh python3 scripts/integrations/llama_ngram/run.py
eval/integrate/llama-cpp-ngram-mod/run-on-main.sh eval/integrate/llama-cpp-ngram-mod/receipt.json
```

`run-on-main.sh` exits nonzero unless HEAD is an ancestor of `origin/main`. It runs the step inside `scripts/model_lock.sh`.

## Env

| Name | Role |
| --- | --- |
| `PFY_LLAMA_NGRAM` | `1` opts in. Otherwise the baseline engine. |
| `PFY_LLAMA_NGRAM_MODEL` | Existing GGUF. Unset, missing, or over 25 GB uses the baseline engine. No download. |
| `PFY_LLAMA_NGRAM_MAX_BYTES` | Optional size cap in bytes. Default 25000000000. |
| `PFY_LLAMA_NGRAM_SERVER` | Optional llama-server binary. Default `/usr/local/lib/ollama/llama-server`, then `PATH`. |
| `PFY_LLAMA_NGRAM_FAKE_SERVER` | Test double. Stdout is the check text. |
| `PFY_LLAMA_NGRAM_BASELINE_TEXT` | Expected check text for the fake server. |
| `PFY_LLAMA_NGRAM_SHA` | Sha for the duplicate-receipt check. |
| `PFY_LLAMA_NGRAM_RECEIPT` | Existing receipt. Same sha exits nonzero and does not rewrite the file. |
| `PFY_LLAMA_NGRAM_LOCK_DIR` | Directory for this run's `server.pid`. |
| `PFY_MODEL_LOCK_HELD` | Must be `1` before a real server starts. `scripts/model_lock.sh` sets it. |

## Timeouts and failure

Health wait 180s. Completion wait 180s. The check is one fixed prompt, temperature 0, seed 7, `--spec-type none` then `--spec-type ngram-mod`. A mismatch, a dead server, low memory (model size plus 25 GiB), or a loaded model in `ollama ps` stops only this run's pid and prints `engine: baseline`. `ollama stop` is never called.

Leave the flag off for a suite. Each scored completion starts its own server, runs the check, then the task, and stops that server. `scripts/eval-auto.sh` runs one check only when the flag is 1 and Ollama is already up. A nonzero check does not abort the ladder. `make eval-auto` already holds `scripts/model_lock.sh`. Running the shell script by itself does not, so a real server stays off.

Cache and the child `HOME` stay under `~/.cache/pfy/tools/integrate-llama-cpp-ngram-mod/`. Nothing from that directory is committed.
