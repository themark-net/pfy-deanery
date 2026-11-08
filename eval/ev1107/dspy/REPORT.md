# DSPy ev1107

STAY I1. Held-out mean gain was 1 case. The pre-registered bar is the observed noise plus 2.

`STAY I1 held-out mean gain 1 is under noise 0 plus 2`

## Pins

| Piece | Version |
| --- | --- |
| uv | 0.9.26 at `/home/mark/.local/bin/uv` |
| Python | CPython 3.12.12 |
| dspy | 3.4.1 |
| litellm | 1.108.3 |
| openai | 3.46.0 |
| pydantic | 2.14.3 |
| cloudpickle | 3.1.2 |
| json-repair | 0.64.6 |
| gepa | 0.1.4 |
| aiohttp | 3.14.5 |
| httpx | 0.28.1 |
| optuna | not installed |
| model | `qwen3.6:35b` digest `a7eb95c53bcf`, Q4_K_M, 35.5B |

Install cache: `~/.cache/pfy/tools/dspy/venv`. No copy of upstream in the repo. optuna is absent because this probe uses BootstrapFewShot, which does not pull it.

```bash
UV=/home/mark/.local/bin/uv
CACHE=${PFY_DSPY_CACHE:-$HOME/.cache/pfy/tools/dspy}
(
  export HOME="$CACHE/home" XDG_CACHE_HOME="$CACHE/xdg-cache" \
    XDG_CONFIG_HOME="$CACHE/xdg-config" TMPDIR="$CACHE/tmp" \
    UV_CACHE_DIR="$CACHE/uv-cache" UV_PYTHON_DOWNLOADS=never
  "$UV" venv "$CACHE/venv" --python /home/mark/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12
  "$UV" pip install --python "$CACHE/venv/bin/python" 'dspy==3.4.1'
)
```

The subshell keeps the operator `HOME` intact. `run_live.sh` points `PFY_MODEL_LOCK` at the real `~/.cache/pfy/locks/local-model.lock` and passes the cache `HOME` only as the locked command, so the flock stays on the shared lock.

## Task

48 labeled Choice cases in `data/decision-gates/laya-trial.cases.v0.json`, `conf_gate` 0.85. Seed 230 matches harness2: sort the ids, then `random.Random(230).shuffle`. Train is the first 24, dev the next 8, held-out the last 16. That held-out list is the harness2 held-out. Dev is recorded and is not used to pick the program or the verdict.

Primary metric: parsed choice equals the label. A correct row also needs a criteria key and a confidence in [0, 1]. Official comparison is `n_correct` on the held-out 16, scored twice per arm.

Rule, fixed before the scores: `noise = max(|b0-b1|, |o0-o1|)`, `twice = (o0+o1)-(b0+b1)`, `need = noise+2`. Promote only when `twice >= 2*need` (mean gain at least noise plus 2). One score cannot promote.

## Live command

```bash
./eval/ev1107/dspy/run_live.sh
```

That script holds `scripts/model_lock.sh` for one step. Generation goes through a loopback proxy to native `POST /api/chat` with `think: false`, `temperature: 0`, `seed: 230`, `num_ctx: 4096`, `num_predict: 128`. The adapter is `dspy.JSONAdapter`. The optimizer is `BootstrapFewShot(max_bootstrapped_demos=4, max_labeled_demos=4, max_rounds=1, max_errors=8)`. DSPy wraps the uncompiled teacher with `LabeledFewShot(k=4)` during the search. The saved student kept 4 bootstrapped demos. `max_labeled_demos - 4` is 0, so no extra labeled demos were appended. Dummy bearer is the word `local`. `program.json` stores `lm: null`.

## Attempt 1 (no score)

Wall 326.3s, 16:49:39 to 16:55:05 local. About 4.5 minutes of that was waiting inside the lock because MemAvailable was about 44 GiB and the load bar is 47 GiB. Another lane had `qwen2.5-coder:7b-instruct` loaded. This lane did not unload it.

Native preload then succeeded: `eval_count` 2, `thinking_chars` 0, context 4096. The first DSPy calls still used `/v1/chat/completions`. That route ignored `think` and `options.num_ctx`. The completion was `reasoning_content` with `text` null, cut off at 128 tokens. Result: `AdapterParseError`, verdict `STAY I1 live probe failed AdapterParseError`. After exit, `/api/ps` showed `qwen3.6:35b` at `context_length` 262144. No held-out number from this attempt is in the verdict.

Attempt 2 translates each OpenAI chat body to native `/api/chat` and drops the thinking channel. A loopback stub test locks that.

## Attempt 2 (the verdict)

Model clock `2026-11-08T01:04:06Z` to `2026-11-08T01:06:03Z`. Wall 117.3s. MemAvailable 84.0 GiB at load. This lane loaded the model, `keep_alive` 2m. Context after preload 4096. Context after the first held-out pass 4096. `thinking_chars` on preload was 0. `lm_history` 84 calls: 40 baseline (held-out twice plus dev), 4 bootstrap attempts, 40 optimized.

| Arm | Held-out A | Held-out B | Dev | Parse | Escalate | Wrong but confident |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline plain Predict | 12/16 | 12/16 | 7/8 | 1.0 | 0 | 4 |
| BootstrapFewShot | 13/16 | 13/16 | 7/8 | 1.0 | 0 | 3 |

Accuracy on held-out is 0.75 then 0.8125. Noise 0. Mean gain 1. Need 2. The two passes of each arm matched case for case.

The gained case is `fm-07-skip-unrelated` (baseline `fill:model`, label `skip`, optimized `skip`). Still wrong on both passes, confidence 0.95:

- `ph-07-waived-busy`: predicted `push`, label `hold`
- `ph-05-kronos-busy`: predicted `push`, label `hold`
- `ph-09-unknown-ci`: predicted `hold`, label `escalate`

Saved demos, all train, all augmented, confidence 0.95: structural-fail `fix_structural`, fill-model `fill:model`, truncate-bulky `truncate`, local-deepseek `deepseek-coder:6.7b`. The signature text is the original Choice instruction. BootstrapFewShot did not rewrite it.

## Gates

Value gate for I3 wants 3 of 4. This run has 2.

1. Gap fill: no. The score moved by one case, under the bar. harness2 already runs this held-out.
2. Operator leverage: no. One held-out case on a 117s probe is not a day-of-glue win for the operator path.
3. Evidence: yes. `./eval/ev1107/dspy/run_live.sh` is a runnable local probe. Receipt: `eval/ev1107/dspy/receipt.json`.
4. Blast radius: yes. The package lives in the cache venv. No weights in the repo. The probe is advisory and is not wired into pregate, CI, or any gate.

Modularity, all 4, for the cache install and the small probe. This does not by itself earn I2.

1. Local code needed: yes. The OpenAI route's ignore of `think` and `num_ctx` is not visible from the README.
2. Bounded surface: yes. One Python package and `BootstrapFewShot`.
3. Isolatable: yes. `~/.cache/pfy/tools/dspy`.
4. Reversible: yes. Delete the cache. The pin, the card, and this report remain.

Size: no in-repo upstream tree. The committed probe, receipt, and program are far under 50 MB. `tier_ceiling` stays I1. `potential` stays medium. `integration_stage` stays I1.

A later `catalog_stage_eval.py --apply` rewrites `uses`, `features`, `potential`, and `next_gate` from `data/catalog_stage_handoff.json`. This lane did not edit that handoff. `integration_stage` is left alone. Evidence that names a file on disk (`eval/ev1107/dspy/receipt.json`, `notes_doc:eval/ev1107/dspy/REPORT.md`) is kept.

## Risks

| How it fails | How we recover |
| --- | --- |
| OpenAI `/v1/chat/completions` ignores `think` and `num_ctx`, returns a reasoning trace, and reloads a 262k context. | The proxy calls native `/api/chat` with `think: false` and `num_ctx: 4096`, and it does not copy `thinking` into `content`. If context still exceeds 8192, the proxy returns 409 and the run STAYs. Stub test: `tests/test_dspy_decision_probe.py`. |
| The adapter cannot parse three calls. | The arm aborts. The run writes STAY and does not promote a partial. Attempt 2 parsed 16/16 on every pass. |
| A demo's task plus state is held-out only. | The run writes `STAY I1 optimized demos included a held-out case` and does not promote. |
| MemAvailable stays under 47 GiB for 30 minutes when this lane must load the model. | Wait inside the lock, then STAY `HOST-BUSY` and skip the live score. Do not unload someone else's model. |
| A single lucky pass looks like a gain. | Two held-out passes. Promote only when the mean gain clears the larger spread by 2 cases. |
| The model clock passes 60 minutes. | `TimeCap` is a `BaseException`, so BootstrapFewShot cannot swallow it. The run STAYs `time-cap`. This run used 117s. |

## Next gate

A fresh pair of held-out passes, same noise rule, on this bench or a harder one, where the mean gain is at least the noise plus 2. MIPROv2 was not run. Do not wire DSPy into a gate from this result.

## Pipeline questions

Advisory only. This lane builds no pipeline step.

1. Trigger: an operator asks for a with/without score on one labeled task. Not a commit hook and not pregate.
2. Read and write: read the case bank and local Ollama at `127.0.0.1:11434`. Write `program.json`, `receipt.json`, and `VERDICT` under `eval/ev1107/dspy/`. Hold the local model lock for that one step.
3. Next: nothing fires. A human reads the verdict.
4. Human re-entry: after the receipt. Choosing another task, promoting the card, or wiring a gate is a human decision.
5. Single flight: `scripts/model_lock.sh` allows one local-model holder. A second probe needs its own output directory. This run does not enqueue itself.

## Checks

```bash
python3 -m unittest tests.test_dspy_decision_probe
python3 scripts/catalog_check.py
python3 scripts/check_no_encoded_payloads.py
```
