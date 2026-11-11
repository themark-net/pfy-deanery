# skill-up eval

skill-up grades one case set with a skill and without it. That comparison is how this repo scores the devbot pfy trial (pfy-deanery against a plain Build run) and H1 (did a harness or skill change help). The 2026-11-07 nimo receipt is `ops:eval/catchup-1107/skill-up/REPORT.md`.

## How to run

The binary is not in git. Copy release v0.14.0 to `tmp/skill-up/skill-up` and check sha256 `5b1bdd0a30f57653c8f6a3a679e992b29982fe18709b2556d53a6f9ea1c85ab6`.

`make eval-skillup` runs the contract tests (no model, no network) and then `python3 eval/catchup-1107/skill-up/run_eval.py`. The live half needs Ollama, the tag `qwen3.6:35b`, and OpenCode on PATH. Before the model is loaded, MemAvailable must be at least 47 GiB. If that model is already loaded, the run continues and does not stop it. When this trial loaded the model, each request sends `keep_alive: 2m` so it unloads after the run. A model someone else loaded is left alone.

Live reports go to `tmp/skill-up-reports` (gitignored). `python3 eval/catchup-1107/skill-up/run_eval.py --score tmp/skill-up-reports` reprints the decision from `iteration-*/result.json` and does not call a model. Exit 0 means PROMOTE. Exit 2 means STAY. The reason is on stdout.

A test that needs the skill-up binary skips, with the reason in the skip message, when `tmp/skill-up/skill-up` is missing or the sha does not match.

## How to add a case

Work under `eval/catchup-1107/skill-up/cases/`.

1. Put the seeded bug in `evals/fixtures/repos/<id>/`. The seed must fail the judge.
2. Add `evals/fixtures/scripts/check_<id>.py`. Exit 0 only when the behavior matches the spec. Print a line that names the bad value. `chmod +x` the script.
3. Add `evals/cases/<id>.yaml` with `context.repo_fixture`, `expect.exit_code: 0`, and `judge.type: script`.
4. List that file under `cases.files` in `evals/eval.yaml`.

Run the new checker on the seed (must fail) and on a known fix (must pass) before a live run. `python3 tests/test_skillup_engine.py` does that for the five cases already here.

## How to compare

The baseline is `with_skill` against `without_skill`. Read `pass_rates` and `flake_rate` in `eval/catchup-1107/skill-up/summary.json`, and `run_summary.delta` in each `iteration-*/benchmark.json`.

To score pfy against a plain Build run, keep these case files and point `engine.custom` at the other command. The command must read the SessionInput path and print one JSON object with `exit_code` and `final_message`. To score a harness change, run the set on each side and compare those two summaries. A pass-rate delta of 0 is a result. A run full of ERROR, or a flake rate above 0.2, is not a comparison you can read. The promote rule used here is two iterations, both arms present, no ERROR, and flake at or under 0.2.

The skill under test is `karpathy-guidelines` because the cases are small edits that fail when the model rewrites the function. Swap `skills` in `eval.yaml` and `SKILLUP_SKILL_DIR` when you want a different skill. The adapter installs that directory only on the with-skill arm.
