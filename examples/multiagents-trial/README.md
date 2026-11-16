# Entry 194 local trial

Deanery check wrapper for a solo agent versus a coder/reviewer pair. It does not install upstream `multi-agents`, and it does not pull a model.

Default worker: `sdk@litellm/ollama/qwen3.6:35b`. Chat goes to local Ollama (`OLLAMA_HOST`, else `http://127.0.0.1:11434`) at `/api/chat`. That path is priced at $0.

```sh
python3 examples/multiagents-trial/trial.py --max-cost 0
```

The default task is `examples/eval-harness/tasks/001-is-palindrome`. The record is `tmp/multiagents-trial/latest.json` (pass/fail, tokens, cost, seconds). Scratch files stay under `tmp/multiagents-trial/`.

`--max-cost` refuses a paid provider and any worker this trial cannot price. A missing local tag exits 2 and does not pull. `--apply` writes `solution.py` only when `--repo` is under this worktree's `tmp/`. Without `--apply` the repo is not modified.

Exit 0 means both arms were graded. Pass/fail is in the record. Exit 2 is a refusal. Exit 1 means the run could not be graded cleanly, or `--apply` had no passing arm.

Tests: `python3 -m unittest tests.test_multiagents_trial`.
