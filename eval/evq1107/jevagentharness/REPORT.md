# JevAgentHarness evq1107

STAY I1. On a 4-step read of `data/stages/ollama.json`, the rules router picked the hand-labeled first tier on 4/4 steps. That arm still made 4 strong upstream calls, the same count as a strong-only run, plus 2 fast calls. Routed wall was 2.037s. Strong-only wall was 1.55s. Ratio 1.314. Nothing was wired into `./pfy`.

## Catalog overlap

Stage cards whose uses, features, or tags cover local inference or a local route:

| Card | Stage | Same job? | How JevAgentHarness compares |
| --- | --- | --- | --- |
| HiRoute | I2 | Yes. Difficulty router, cheap turns to the local model. | HiRoute's 2026-11-07 probe routed 20/20 and the client received the cheap tier (median decision 746 ms, `eval/ev1107/hiroute/VERDICT`). Here the client received the strong tier on both steps that started on fast. |
| Ollama | I2 | The engine this probe called. | JevAgentHarness does not serve a model. Gap L (a second local engine) stays open. |
| Strata | I2 | Second local engine, the gap-L candidate. | Strata's trial was 0.84x Ollama decode and stayed I2. A router in front of Ollama does not add that engine. |
| llama.cpp (server mode) | I1 | GGUF server on the local path. | An engine card. This proxy does not replace it. |
| colibri | I1 | Low-RAM MoE server. | An engine card. Not installed here. |
| LiteLLM | I2 | One OpenAI proxy for Grok and local models. | LiteLLM is already the stack proxy. This would be a second proxy. |
| magpie | I0 | One gateway config for every agent. | Gateway overlap only. magpie is still I0. |

neatroots (I2) checks saved traces for loops and errors after a run. harness2 (I1) edits a harness on the decision set. Neither routes the next model call. Entries 122 (llm-router) and 123 (HarnessRouter) have no stage card. The entry already separates them: llm-router scores a whole prompt, HarnessRouter fronts harnesses.

## Pins

JevAgentHarness 0.1.0 at `f2932199e1ef1d9f089b51d39430c87be0f560b5` (2026-10-16, subject `arXiv:2610.21412: badges, links and citation`). The entry recorded the prefix `f2932199e1ef`. `git rev-parse` matches that prefix. No file checksum was in the entry. `pyproject.toml` sha256 is `72b18f8e7741b213f5688b9b05b8cfaf41dc7f6bed6a85e910089a6ff6d43a83`. Source tree without `.git` is 32616355 bytes, under the 50 MB lightweight cap. The tree is not in the repo.

Install root: `~/.cache/pfy/tools/jevagentharness/`. Venv `jah` is `jah 0.1.0`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` for the install and for `jah serve` point under that cache. Real `~/.jah` was absent after the runs. No key and no hosted call.

Strong tier: `qwen2.5-coder:7b-instruct` (4683087561 bytes). Fast tier and the decision adapter: `qwen2.5-coder:1.5b` (986062089 bytes). Both were already on disk. This lane did not pull. AgentDecision weights were not downloaded. `qwen3.6:35b` was left unloaded.

## What ran

The probe is `eval/evq1107/jevagentharness/probe.py`. It reads the `integration_stage` line from `data/stages/ollama.json` (token `I2`) and drives four chat steps. The client appends three fixed tool results, so the route follows the fixture rather than whatever command the model invents:

1. Opening user turn. Hand label: strong (`first_steps`).
2. Tool result is the stage line. Hand label: fast (`no_signal`).
3. Tool result is a traceback with `AssertionError: 1 failed`. Hand label: strong (`error_signal`).
4. Tool result is `exit code 0` plus `ALLDONE`. Hand label: fast, then `verify_finish` if the reply is text with no tool call.

`verify_finish` is on. `tau` is 0.75. `on_error` is strong. `log_states` is false. Upstream `key_env` is empty.

Offline arm: rules backend, loopback stub, no Ollama. The stub returns a tool call until the result contains `ALLDONE`, then text.

Live arms, one `scripts/model_lock.sh` hold:

- `jah-auto` with `{type: rules}` and both tiers on `http://127.0.0.1:11434/v1`.
- `jah-strong`, pinned strong tier, same transcript.
- `jah-auto` with `{type: jev, provider: local}` pointed at a loopback `POST /v1/systemone` adapter. The adapter asks `qwen2.5-coder:1.5b` for one word, `routine` or `hard`, and returns probabilities 0.09 or 0.91. That adapter is probe code. It is not Laya and not AgentDecision-4B.

`ollama ps` at the start of the locked run already listed both models, left resident by an earlier hold in this same lane. This run did not warm them, did not send `keep_alive`, and did not call `ollama stop`. The probe checks `MemAvailable` against model size plus 25 GiB before each model it would load. This run loaded none, so that list is empty. Sizes are in `results.json`.

## Commands

Install, with `HOME` and the XDG dirs under `~/.cache/pfy/tools/jevagentharness/`:

```bash
git clone --filter=blob:none https://github.com/JevAgentHarness/JevAgentHarness.git \
  ~/.cache/pfy/tools/jevagentharness/src/JevAgentHarness
git -C ~/.cache/pfy/tools/jevagentharness/src/JevAgentHarness checkout --detach \
  f2932199e1ef1d9f089b51d39430c87be0f560b5
python3 -m venv ~/.cache/pfy/tools/jevagentharness/venv
~/.cache/pfy/tools/jevagentharness/venv/bin/pip install \
  ~/.cache/pfy/tools/jevagentharness/src/JevAgentHarness
~/.cache/pfy/tools/jevagentharness/venv/bin/jah --version
```

Probe:

```bash
python3 eval/evq1107/jevagentharness/probe.py offline
scripts/model_lock.sh python3 -u eval/evq1107/jevagentharness/probe.py live
```

`live` exits unless `PFY_MODEL_LOCK_HELD` is `1`. Raw `jah` logs stay in `tmp/jevagentharness-probe/` and are not committed. `log_states` is false. A scan for the user-text marker found no log file.

## Numbers

Offline stub, rules. Wall 0.012s. Upstream models: strong, fast, strong, fast, strong. That is 3 strong calls and 2 fast calls. The routine step stayed on fast because the stub returned a tool call. The last step was `finish_check` (fast, then strong). No `Authorization` header on the stub. Reasons: `first_steps`, `routine`, `hard`, `finish_check`. Whys: none, `no_signal`, `error_signal`, `no_signal`.

Live rules vs pinned strong. Both arms' client-visible replies were the same: step 0 was a JSON blob with no stage token, steps 1 to 3 were `I2`. Token hits 3/4 on each arm. On the rules arm the `I2` text is the strong redo. `routine_reply_visible_from_fast` is false.

| Arm | Wall s | Strong calls | Fast calls | First tiers |
| --- | --- | --- | --- | --- |
| Rules, both tiers | 2.037 | 4 | 2 | strong, fast, strong, fast |
| Pinned strong | 1.55 | 4 | 0 | strong, strong, strong, strong |
| Local systemone | 2.239 | 4 | 2 | strong, fast, strong, fast |

Strong calls saved: 0. Wall ratio rules/strong: 1.314. Local systemone agreed with the rules first tier on 4/4. Decision errors: 0.

Rules step log:

| Step | Final reason | Final tier | Why | p(hard) | Calls (s) |
| --- | --- | --- | --- | --- | --- |
| 0 | first_steps | strong |  |  | strong 0.878 |
| 1 | finish_check | strong | no_signal | 0.10 | fast 0.244, strong 0.287 |
| 2 | hard | strong | error_signal | 0.90 | strong 0.246 |
| 3 | finish_check | strong | no_signal | 0.10 | fast 0.146, strong 0.229 |

Systemone calls, all `POST /v1/systemone`, model name `qwen2.5-coder:1.5b`, no `Authorization`:

| Call | Choice | Latency s |
| --- | --- | --- |
| After the stage line | routine | 0.134 |
| After the traceback | hard | 0.146 |
| After the clean exit line | routine | 0.155 |

`p(hard)` on those steps was 0.09, 0.91, 0.09. Tau 0.75, so the choices match the first tiers.

Per-step rows and reply heads are in `results.json`.

## Gates

Value gate (needed for I3, recorded here, not claimed). 2 of 4.

1. Gap fill: no. Gap L is a second local engine. This proxy calls Ollama. HiRoute already sends a cheap turn to the local model, and the client in that probe received the cheap tier. This trace saved 0 strong calls.
2. Operator leverage: no. A call needs the proxy, two model names, and, for the local decision lane, a systemone server. `verify_finish` redid both fast text answers, so the routed arm was slower (2.037s vs 1.55s).
3. Evidence: yes. This probe, with the pin and the commands above.
4. Blast radius: yes. MIT. Loopback only. Empty `key_env`. Cache install. Source without `.git` is 31.1 MB. No AgentDecision weights.

Modularity gate (all 4 would be required to keep a local copy at I2). The copy stays in the cache. The card stays I1 because the value number is not a help.

1. Local code needed: yes. The finish redo and the systemone body showed up by running `jah serve`.
2. Bounded surface: yes. One CLI, `jah serve -c`.
3. Isolatable: yes. The process uses the cache home. It is not the product runtime.
4. Reversible: yes. Delete `~/.cache/pfy/tools/jevagentharness`. The pin and the entry remain.

`uses` and `features` do not cover CI, testing, or review, so `self_pipeline` is unset. No `TOOLS.md` row and no `data/tools.json` row. I3 would also need a repeatable script plus self-pipeline evidence. This lane adds neither.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Finish check on a short trace | Both fast text answers were redone. Strong calls stayed 4. Wall was 1.314x strong-only. | Keep `verify_finish` on. Reopen only for a trace whose routine steps are tool calls, and require fewer strong calls than the strong-only arm. |
| Silent fallback | A dead decision server logs `decision_error` and sends the step strong. Savings become zero. | This run had 0 decision errors. A later run reads `steps.jsonl` and stops if that share is high. |
| Fast reply quality | The client never saw the 1.5b text, so this probe has no fast-tier accuracy number. | Do not treat the 3/4 `I2` hits as a fast-model score. They are the strong redo. |
| Chat model as systemone | The 4/4 agreement is `qwen2.5-coder:1.5b` behind a probe adapter, on a fixture the rules already label. | Point a later trial at a real systemone server. Until then the lane is rules plus this wire check. |
| Non-commercial weights | AgentDecision models are CC BY-NC. | They were not downloaded. Do not pull them for anything sold. |
| Prompt text in logs | A later config sets `log_states` true. | This run kept it false. The marker scan was empty. The smoke fails if task text shows up in the logs. |
| Host memory | Loading a model without 25 GiB free on top of its size can crowd other lanes. | The lock holds the whole live command. The probe waits up to 30 min, then records HOST-BUSY and skips the live calls. This run did not load. |
| Real home | `jah` defaults `log_dir` to `~/.jah`. | Serve used an explicit log dir and a cache `HOME`. Real `~/.jah` was absent. |

## Next gate

Stay I1. Do not wire JevAgentHarness into `./pfy`, pregate, or CI. Do not add a `TOOLS.md` row from this lane. A later ticket has to show strong-call savings on a tool-call trace and compare that number with HiRoute before anyone talks about I2 again.

## Pipeline questions

How JevAgentHarness would run if a later ticket put it in the pipeline. This lane did not add that path.

1. What triggers it? An agent client posts a chat completion to the loopback proxy. Not a CI job.
2. What does it do, and which services does it read and write? It reads the step, applies rules or `POST /v1/systemone`, and forwards the step to Ollama on `127.0.0.1:11434`. It writes a step log under the trial directory. It does not write the repo and it does not call a hosted model.
3. What does it trigger next? The chosen model reply goes back to the client. It does not start a land step or a gate.
4. Where does a human re-enter? Before any gate wiring, any hosted Jev key, or any AgentDecision download.
5. What stops two runs doing the same work? One worktree per lane, and `scripts/model_lock.sh` for any live Ollama use. This lane held that lock once for all three live arms.
