# llm-router evq1107

Verdict: STAY I0. `llm-routing` 15.4.0 ran from a cache venv. On the same 20 prompts as the HiRoute I2 probe, `classify_signals` matched the economy-versus-primary labels on 14 of 20. The hook chain still named `ollama/qwen2.5-coder:7b-instruct` first on all 20. HiRoute routed 20 of 20 with a decision median of 746 ms. This does not beat that. Nothing was wired into `./pfy`.

## Catalog comparison

Same job: send cheap turns to the local model and keep hard turns off it. Gap L in the 2026-11-07 ranking is the local engine. Routing is the slice HiRoute and magpie were ranked for, and only after the engine choice.

| Card | Stage | What it already does | How llm-router compares |
| --- | --- | --- | --- |
| HiRoute | I2 | Difficulty router. 20/20 on this prompt set, decision median 746 ms, economy tier `qwen2.5-coder:7b-instruct` | Same set, same local model. The classifier is faster (median 0.144 ms) and wrong on 6 of 10 hard prompts. The draft chain does not leave Ollama. It does not beat HiRoute. |
| LiteLLM | I2 | One OpenAI-compatible proxy, with fallbacks. Already smoked | The wheel depends on litellm. This install resolved litellm 1.108.3. The new piece is the classifier, and that classifier under-routes this set. |
| Ollama | I2 | The local engine `./pfy` already talks to | llm-router is not an engine. It does not close gap L. |
| Strata | I2 | Second local engine. Median decode 51.86 tok/s, 0.84x Ollama on the same prompts | llm-router does not serve a model. |
| magpie | I0 | One gateway config for every agent. Ranked with HiRoute for routing | Not run here. llm-router's measured piece is the classifier, not a gateway file. |
| DSPy | I1 | Compile a prompt program on a labeled set | Not a per-request router. |
| antigravity-manager | I1 | Account-pool proxy | Needs accounts. This lane used none. |
| `./pfy hedge` | no card | Bulk stays local, hard goes cloud, and the text is ignored. Same stand-in the HiRoute probe used | On this set hedge is 10 local and 10 cloud by the task label. The complexity label agrees on 14 of 20. `org-spinny-decide` is not in this repo, so it was not called. |

It does not beat what we have.

## Pins

| Item | Value |
| --- | --- |
| Package | PyPI `llm-routing` 15.4.0. The entry records no git commit. This lane did not clone the repo. |
| Wheel | `llm_routing-15.4.0-py3-none-any.whl`, 3,016,977 bytes, sha256 `72938a98e11bb75311b741afc6a1337f38ef712b891dba319160be1712cf6a41` (matches the PyPI digest) |
| Import | `llm_router.__version__` is `15.4.0`. A package walk found 427 modules. That walk imported `storage/service.py` on the operator `HOME` and created an empty `audit.db`. This lane removed it. |
| Python | 3.14.4. The entry says 3.11+. |
| litellm | 1.108.3, whatever `pip` resolved for `litellm>=1.50.0`. Not hashed. |
| Install | `~/.cache/pfy/tools/llm-router/`, 458,427,046 bytes (437 MiB). `HOME`, `XDG_*`, `TMPDIR`, and `LLM_ROUTER_HOME` point under that directory. |
| Local model | `qwen2.5-coder:7b-instruct`, already on nimo (4.7 GB). Not pulled. `LLM_ROUTER_OLLAMA_MODEL` was set to that name so the chain builder did not call Ollama during classify. |
| Isolation | `LLM_ROUTER_DIRECT_EXECUTION=false`. `llm-router install` was not run. The offline rerun left `/home/mark/.llm-router` absent (`real_state_absent` true). No provider key was set in this process (`provider_keys_dropped` 0). |

## Commands

```bash
# wheel downloaded from PyPI, sha256 checked, then:
python3 -m venv ~/.cache/pfy/tools/llm-router/venv
# HOME, XDG_*, TMPDIR under that cache path
~/.cache/pfy/tools/llm-router/venv/bin/pip install \
  ~/.cache/pfy/tools/llm-router/wheels/llm_routing-15.4.0-py3-none-any.whl
python3 eval/evq1107/llm-router/probe.py
scripts/model_lock.sh python3 eval/evq1107/llm-router/probe.py live
```

The offline command re-execs the cache venv. It classifies `prompts.jsonl` (the HiRoute set), builds the hook chain, asks `pfylib.hedge.decide` with local status ready, and runs `llm-router demo`. It does not call Ollama. The live command holds `~/.cache/pfy/locks/local-model.lock` with the real `HOME`, then the probe points the tool home at the cache. Live drafts are the 10 trivial prompts only.

Route rule, fixed before the run: complexity `simple` counts as economy. Anything else counts as primary. The chain is recorded beside that label and does not change it.

## Numbers

Classify median is the timed pass after one warmup call. Warmup was 46.444 ms. The 20 calls sum to 2.7 ms, max 0.199 ms, median 0.144 ms. HiRoute's decision median on the same set was 746 ms. Eleven of the 20 calls were not confident (score under 2), so the task type fell through to the policy default `query`.

`HOOK_POLICY` and `HOOK_LIVE_POLICY` returned the same complexity on 20 of 20. `llm-router demo` exited 0 in 50.0 ms and printed a Complexity and Model table. Those dollars are the tool's example prices, not a measurement.

| id | task | complexity | confident | route | label ok | hedge | chain first |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t01 | query | simple | no | economy | yes | local | ollama |
| t02 | query | simple | yes | economy | yes | local | ollama |
| t03 | query | simple | no | economy | yes | local | ollama |
| t04 | query | simple | no | economy | yes | local | ollama |
| t05 | query | simple | yes | economy | yes | local | ollama |
| t06 | query | simple | no | economy | yes | local | ollama |
| t07 | query | simple | no | economy | yes | local | ollama |
| t08 | query | simple | no | economy | yes | local | ollama |
| t09 | query | simple | yes | economy | yes | local | ollama |
| t10 | query | simple | no | economy | yes | local | ollama |
| h01 | code | moderate | yes | primary | yes | cloud | ollama, then claude-sonnet-4-6 |
| h02 | generate | moderate | yes | primary | yes | cloud | ollama, then claude-sonnet-4-6 |
| h03 | query | simple | yes | economy | no | cloud | ollama |
| h04 | query | simple | no | economy | no | cloud | ollama |
| h05 | query | simple | yes | economy | no | cloud | ollama |
| h06 | code | moderate | yes | primary | yes | cloud | ollama, then claude-sonnet-4-6 |
| h07 | query | simple | no | economy | no | cloud | ollama |
| h08 | query | simple | no | economy | no | cloud | ollama |
| h09 | code | moderate | yes | primary | yes | cloud | ollama, then claude-sonnet-4-6 |
| h10 | query | simple | no | economy | no | cloud | ollama |

Label agreement is 14/20. All 10 trivial prompts are simple. Six hard prompts are simple too (h03 and h05 confident, the other four low-signal and short, so the query length curve stays simple). If the route is the first chain model, agreement with HiRoute is 10/20: every draft starts on Ollama, including the 10 hard prompts HiRoute sent to primary.

The secret regex in `PiiSignal` matched 3 of 3 synthetic shapes and did not match the clean prompt (`pattern_rows_ok` 4, `pii_production_caller` false). No production module constructs `PiiSignal` or `DecisionEngine`. `probe_rule_action` in `results.json` is a one-rule engine this probe built. `secret_scrubber` redacts stored text. That is not a route. The fail-closed "secrets stay on Ollama" claim was not observed.

Live drafts used Ollama `/api/chat` on `127.0.0.1:11434`, temperature 0, `num_predict` 16, model `qwen2.5-coder:7b-instruct`. `ollama ps` was empty, so this lane loaded the model and sent `keep_alive` `2m`. It did not call `ollama stop`. `MemAvailable` was 77,558,497,280 bytes. The floor was 31,843,545,600 bytes (listed size rounded up, plus 25 GiB). No HOST-BUSY wait.

Token check is the same case-sensitive word match as the HiRoute probe. 8 of 10 trivial drafts passed. t03 answered `Yes`, t10 answered `Ok`. The first call was 4459 ms and includes the load. The other nine were 173 ms to 189 ms, median 180.0 ms. HiRoute's economy tier missed t03, t04, and t10 on case. This direct call passed t04 (`blue`). That is the model, not a better router.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. Gap L is the engine. HiRoute already routes this set 20/20. This heuristic misses 6 hard prompts, and the chain does not move them off Ollama.
2. Operator leverage: no. A 437 MiB install, no Grok host, and a classifier that under-routes the labeled set. Not a day of glue in front of `./pfy hedge`.
3. Evidence: yes. This probe, with the pin and the commands above.
4. Blast radius: yes, while it stays in the cache. MIT. No model weights in the wheel. It is not the product runtime. The direct-execution default is a separate risk below.

Value score: 2 of 4.

Modularity (all 4 required for an I2 local copy):

1. Local code needed: yes. The chain still leading with Ollama on a moderate prompt, and `PiiSignal` having no caller, showed up only by running the package.
2. Bounded surface: no. One wheel exposes 427 modules and a CLI that installs host hooks, a dashboard, and team reports. The classifier function is small. The package is not.
3. Isolatable: yes, when `HOME` is redirected before import. The cache held the install. Importing the package tree without that redirect created an empty operator `audit.db`, which was removed.
4. Reversible: yes. Deleting the cache leaves the pin and this entry. `./pfy` does not call llm-router.

Modularity is 3 of 4. The install is also 437 MiB, over the 50 MB copy gate, so this would not be an in-repo copy even if the route had matched. The result is no longer ambiguous. It does not help, so the card stays I0. I3 would also need a pipeline script and `self_pipeline` evidence. This lane wires nothing. `uses` and `features` are routing, not CI, testing, or review, so `self_pipeline` is not set. No `TOOLS.md` row and no `data/tools.json` row.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Under-route | 6 of 10 hard prompts are classified simple, 2 of them confident | Do not wire. HiRoute remains the measured router for this set. |
| Label is not the draft | A moderate prompt is labeled primary and the chain still starts at Ollama. The hook skips Claude in direct execution | Do not read a primary label as "this left the machine". |
| Direct execution defaults on | The local model can write files and run commands | This probe set `LLM_ROUTER_DIRECT_EXECUTION=false`. Do not run a trial without that. |
| `install` writes host config | Hooks land in the real home | Not run. Keep `HOME` on the cache. |
| Import builds `audit.db` | `storage/service.py` constructs `StorageService` at import and creates `audit.db` on the resolved home. A package walk with the operator `HOME` created `/home/mark/.llm-router/audit.db` (0 rows) | Removed in this lane. The probe redirects `HOME` first and refuses that path in-process. Do not walk the package on the operator home. |
| Secret route is unwired | A prompt with a key shape is not forced onto Ollama by any caller this probe found | Keep the standing no-secrets rule. Do not treat `PiiSignal` as a gate. |
| Size | 437 MiB with litellm and friends, over the 50 MB copy gate | Leave it in the cache. Do not vendor it. |
| Cold load | The first draft was 4459 ms while the 7B loaded | The route number does not depend on that call. A later lane that finds the model already loaded must not send `keep_alive` and must not unload it. |
| Dep drift | A later `pip install` can move litellm while the wheel hash stays | Re-check the wheel hash before any pin bump. Do not treat 1.108.3 as a hashed pin. |

## Next gate

Stay I0. Do not wire llm-router into pregate, CI, or `./pfy`. Reopen only if a later ticket shows the heuristic matching a labeled local-versus-escalate set at HiRoute's 20/20 bar without a model call, and that ticket grills wiring first.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? A prompt arriving at a host hook or at `llm-router serve`. Not a CI job. This lane did not install a hook.
2. What does it do, and which services does it read and write? It classifies the prompt, then the hook chain tries Ollama on `127.0.0.1:11434` and can walk on to a paid model when a key is configured. It writes state under `LLM_ROUTER_HOME` when that variable is set (here, the cache). Importing `storage/service.py` without it creates `audit.db` under the process home. It does not write this repo. This lane set no provider key.
3. What does it trigger next? The first model in the chain drafts a reply. On this set that model was Ollama for every prompt. It does not start a land step.
4. Where does a human re-enter? Before any `install` into a real home, before direct execution is left on, and before any gate wiring.
5. What stops two runs doing the same work? llm-router does not. This lane held `scripts/model_lock.sh` once for the ten drafts. One worktree per slug stays the other lock.
