# Hermes vs current local path (Entry 134)

## Re-run 2026-10-21 (meta tools off, matched thinking)

Not a Feature GO. Verdict: **NO-WIN**. The tie does not block the bot-interface flag. The operator already chose Hermes for the interface. The flag stays off unless `PFY_BOT_INTERFACE=hermes`.

Receipt: `pipelines/dogfood/hermes-bakeoff/results-rerun.json`. The 2026-10-19 file `results.json` is unchanged. Same 27 labels. Local Ollama `qwen3.6:35b` only. Pin `ddabd383`. opencode 1.18.32.

Both arms went through a local proxy that forced `think: false`, `temperature: 0`, `seed: 1`, and `reasoning_effort: none` on 153 `POST /v1/chat/completions` calls. The proxy log stores those fields and not the prompt. Hermes config set `tools.tool_search.enabled: off`. Each Hermes task was offered the six `mcp__bakeoff__*` tools and no `tool_search`, `tool_describe`, or `tool_call`. `meta_calls` is 0 on both arms. `meta.started` is `2026-10-21T07:40:26.585Z`.

Requested `num_ctx` 65536. After the tasks, `ollama ps` still reported `context_length` 262144 for `qwen3.6:35b` (resident size about 22.8 GB). The model was not loaded at the start. This run unloaded it (`model_unloaded: true`), and `ollama ps` was empty afterward.

| Metric | Hermes | opencode run | Prior run (2026-10-19) |
|---|---:|---:|---|
| Task success | 26/27 = 96.30% | 26/27 = 96.30% | 26/27 vs 25/27 |
| Wilson 95% | 81.7% to 99.3% | 81.7% to 99.3% | 81.7% to 99.3% vs 76.6% to 97.9% |
| Valid tool-call rate | 36/36 = 100% | 36/36 = 100% | 38/46 = 82.61% vs 45/46 = 97.83% |
| Narrate rate | 0 | 0 | 0 vs 0 |
| Latency p50 / p95 / mean | 7.011s / 8.806s / 7.854s | 7.191s / 8.585s / 7.292s | 8.75s / 13.65s / 9.63s vs 47.38s / 60.98s / 46.27s |
| Time to first tool call, p50 | 4.877s | 5.364s | 6.44s vs 42.00s (whole seconds) |
| Agent peak RSS | 239.8 MiB | 1.03 GiB | 221 MiB vs 1.04 GiB |
| Meta calls | 0 | 0 | 52 vs 0 |

TTFT uses the millisecond server stamps. Of the 24 tasks with a tool call on each arm, none of the `ttft_s` values are whole seconds. The first Hermes task, `ch-ph-01-green-idle`, took 30.42s of wall time (process cold start). Later tasks sit near 7s, so p50 stays 7.011s.

Failed condition: task success is +0.00 pp, and the bar is +10 pp. The Wilson intervals are the same interval, so they overlap. Valid rate, narrate, p50 (0.97x), and Hermes peak RSS pass.

The only miss on both arms is `ch-ph-08-missing-ci`. Each arm made one schema-valid `submit_choice` of `hold`. The label is `escalate`. That is one wrong choice, not a scattershot pair. On the 2026-10-19 pass Hermes chose `push` and opencode chose `push` then `hold`, and opencode also missed `ch-wz-06-cloud-grok`. Opencode passes `wz-06` on this re-run. Hermes no longer emits the empty `submit_answer` retries that made 8 of 46 attempts invalid, which is why the valid rate is now 36/36 on both arms.

Against the prior run: the valid-rate gap closed. The latency gap did not survive matched thinking (7.011s vs 7.191s, was 8.75s vs 47.38s). The RSS gap remains (239.8 MiB vs 1.03 GiB).

## 2026-10-19 scored pass

Not a Feature GO. No production wiring in that pass. Verdict: **NO-WIN**.

Hermes (`AIAgent.run_conversation` at pin `ddabd3837862022a6053331fe3ba97cf9716b9e3`) beat `opencode run` 1.18.32 by 3.70 percentage points on task success (26/27 vs 25/27) and was much faster (not like-for-like: thinking off on Hermes only, opencode CLI cold start, RSS excludes the model). That is short of the +10 point bar. Its bake-off valid tool-call rate was also 15.2 points worse. Wilson 95% intervals on task success overlap.

## Method

Both arms used Ollama `qwen3.6:35b` (`http://127.0.0.1:11434/v1`), one request at a time. Per-task timeout 180s. Max tool rounds 6. The only data tools were the stdlib MCP server in `examples/hermes-bakeoff/mcp_server.py`. The oracle reads that server's JSONL, not the model's prose.

| | Hermes | Baseline |
|---|---|---|
| Driver | `AIAgent.run_conversation` | `opencode run` |
| Binary / pin | checkout `ddabd383` | opencode 1.18.32 |
| How the model names tools | `mcp__bakeoff__*` | `bakeoff_*` |
| Temperature / seed | 0 / seed 1 | not exposed by `opencode run` |
| Thinking | `reasoning_effort: none`, `think: false` | not set |
| Config home | `./tmp/hermes-home` | `XDG_*` under `./tmp` |

`./pfy` attach for opencode execs the binary with `OPENAI_BASE_URL` set to the local engine. It is not a headless tool loop. A one-task probe showed `opencode run` can call this MCP server without writing `~/.config/opencode` (mtime stayed 2026-04-30). That is the scored baseline. `baseline_arm.py` is the direct `/v1/chat/completions` loop and was not scored.

Ollama is 0.30.8. Hermes refused 32768 (`ValueError`: context 32,768 is under the 64,000 minimum). Both arms then requested 65536. After the runs, `ollama ps` still reported `context_length` 262144. The OpenAI-compatible endpoint did not resize the already-loaded model. Both arms shared that window. No `qwen3.6-hermes-eval-*` tag was created.

`enabled_toolsets` was `["bakeoff"]` and approvals were `off`. Hermes still called its own `tool_search`, `tool_describe`, and `tool_call` envelope (52 meta calls). Those are not bake-off attempts. A first scoring pass counted them as invalid and produced a 42.2% valid rate. The published rate unwraps `tool_call` and drops the meta tools. The verdict is NO-WIN either way. No second model pass.

## Task set

`data/decision-gates/hermes-bakeoff.tasks.v0.json`, 27 tasks, labels fixed before any scored call.

- 14 Choice cases from `laya-trial.cases.v0.json`: ph-01, ph-03, ph-05, ph-08, wz-01, wz-04, wz-06, wz-10, hd-01, hd-06, hd-11, fm-01, fm-04, cp-02.
- 8 fetch tasks and 2 chains over `sources/entries/`, `data/tools.json`, and the committed local-bench / atg receipts.
- 3 negatives (arithmetic text, shell refusal, a word already in the prompt). They pass only with zero tool calls and the expected text.

## Metrics

| Metric | Hermes | opencode run | Margin |
|---|---:|---:|---|
| Task success | 26/27 = 96.30% | 25/27 = 92.59% | +3.70 pp, need ≥ +10 |
| Wilson 95% | 81.7% – 99.3% | 76.6% – 97.9% | intervals overlap |
| Valid tool-call rate | 38/46 = 82.61% | 45/46 = 97.83% | −15.2 pp, fail (> 2) |
| Narrate rate | 0/24 = 0 | 0/24 = 0 | pass |
| Latency p50 / p95 / mean | 8.75s / 13.65s / 9.63s | 47.38s / 60.98s / 46.27s | p50 is 0.18×, pass |
| Time to first tool call, p50 | 6.44s | 42.00s | |
| Agent peak RSS | 221 MiB | 1.04 GiB | ≤ 2 GiB, pass |
| Hermes meta calls | 52 | 0 | not in the valid rate |

Ollama RSS is not in either peak. The model resident size was about 23 GB.

## Verdict

**NO-WIN.** Failed conditions:

1. Task success is +3.70 pp, not +10 pp.
2. Valid tool-call rate is 15.2 pp worse, not within 2 pp.

Narrate, p50 latency, and Hermes peak RSS pass. The success intervals overlap, so the 1-task gap is not a stable edge.

## Failure autopsy

Fewer than five tasks failed on each arm. The rest of the list is the invalid-call pattern that pulled the valid rate down. Excerpts are the captured assistant text. No keys.

1. **Hermes `ch-ph-08-missing-ci` (fail).** CI state is missing. The label is `escalate`. Hermes called `submit_choice` with `choice: push` and wrote "Local CI green (not known-red) and Kronos idle". Schema-valid, wrong label. Wall 8.0s.
2. **Hermes empty `submit_answer` (tasks still passed).** On fetch and chain tasks Hermes first called `submit_answer` with `value: ""` (and sometimes `compute_sum` with `a: 0`) inside `tool_call`. Those calls never reached the server. The retry with the real value did. Eight tasks account for the 8 invalid attempts (46 attempts, 38 valid).
3. **Hermes meta tools.** Before some calls it ran `tool_search` / `tool_describe` for `mcp__bakeoff__*` names. 52 such envelopes. They are excluded from the rate above and would have made the first-pass rate 42%.
4. **Baseline `ch-ph-08-missing-ci` (fail).** Same case. First call `push` ("known_red is false"), then `hold` ("CI is unknown"). Never `escalate`. Captured text: "submit_choice called once with choice push". Wall 62.3s.
5. **Baseline `ch-wz-06-cloud-grok` (fail).** Hermes passed this case (`choice: grok`, 8.4s). opencode exited 0 in 49.8s with no MCP call and empty captured text. The raw event stream was not retained, so this row is "no structured call reached the server."

Negatives passed on both arms (zero tool calls, expected text).

## What was not measured

- A second model pass, other models, or the direct `/v1/chat/completions` loop as a scored arm.
- Whether forcing Ollama `num_ctx` 65536 (native `/api/chat`, or a `qwen3.6-hermes-eval-*` tag) changes accuracy. The shared window was 262144.
- opencode temperature and seed. The CLI does not set them. Hermes sent temperature 0 and seed 1.
- Gateway, cron, skills creation, terminal, or web tools. Those stayed off except Hermes's own tool-search envelope.
- Multi-turn sessions, channels, or a human approval prompt. Approvals were `off` so the headless run could not hang.
- Cost. Local only.

## What would have to change for a re-run

The meta-tools-off re-run with matched thinking is the 2026-10-21 section at the top of this file. Prerequisites and the founder choice are in the handoff.

Item C (adapter plan) is skipped. A re-run is worth it only if the question changes. On this 27-task set both arms are already above 92%, and +10 points means about three more baseline misses. The intervals overlap.

1. Turn off Hermes `tool_search`, `tool_describe`, and the `tool_call` batch tool so the model emits MCP calls directly. Recompute the valid rate. The success gap can stay inside the margin even if the rate recovers.
2. Keep the same labels. Do not retune oracles after seeing these transcripts.
3. If the question is latency or operator RSS, Hermes already wins those rows. That is not the WIN rule.
4. Pass one `num_ctx` both clients actually apply, and record `ollama ps` `context_length` after the first request of each arm. If it is not 65536, say so again.
5. Save the raw `opencode run --format json` stream. The empty `wz-06` row cannot be autopsied further from what was kept.

## Reproduce

Scratch lives under `./tmp` (git-ignored). The pin, venv, and `HERMES_HOME` are not in git.

```bash
# offline
python3 examples/hermes-bakeoff/run.py --check --base-url http://127.0.0.1:9
python3 -m unittest tests.test_hermes_bakeoff

# live, sequential, one model
python3 examples/hermes-bakeoff/run.py --live --skip-ctx-probe --num-ctx 65536 \
  --work ./tmp/bakeoff/full1 \
  --out pipelines/dogfood/hermes-bakeoff/results.json
```

The scored run in this eval used that command after a 32768 probe had already refused and a one-task opencode probe had succeeded. `qwen3.6:35b` was already resident, so the pre-load 47 GiB gate was not reapplied. MemAvailable was 45.9 GiB before the scored tasks and 45.1 GiB after.

Raw per-task JSON and JSONL stayed in `./tmp/bakeoff/full1/` and are not committed. The aggregate is `pipelines/dogfood/hermes-bakeoff/results.json`.
