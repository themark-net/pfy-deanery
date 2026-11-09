# Grill step (before a CI, pipeline, or gate ticket)

A coordinator bot runs this before it writes `TICKET-<label>.md`, and sandcastle-grok runs it before a lane is cut, when the ticket touches CI, pipeline, or gate files. Tools stay off. The turn cap is 12 for the question call and the coordinator call together. The coordinator (not the operator) accepts or overrides each recommended answer. Answers that change behavior are written into the ticket as exit tests before Build, and the agent does not edit them.

The trigger list lives in one place: `TRIGGER_GLOBS` and `TEXT_NEEDLES` in `scripts/grill_ticket.py`. It covers `.github/workflows/**`, `ci/**`, `pipelines/**`, `scripts/pregate*`, `scripts/run_tests.py`, `scripts/test_select.py`, `scripts/test_cache.py`, `scripts/*gate*`, `scripts/model_lock.sh`, Makefile CI/test targets, `docs/ops/MODULAR-CI.md`, and `docs/ops/PREGATE.md`. Anything else prints `no grill needed` and exits 0.

## Command

From a pfy-mentat checkout:

```bash
python3 scripts/grill_ticket.py path/to/TICKET-<label>.md
```

Useful flags:

```bash
python3 scripts/grill_ticket.py path/to/TICKET-<label>.md \
  --paths scripts/pregate.sh \
  --diff origin/main \
  --max-turns 12 \
  --answers /tmp/grill-answers.json \
  --repo "$PWD"
```

`--max-turns` above 12 is rejected before any model call. With no `--answers` file the budget is split: the question call gets N-1 and the coordinator call gets 1. `--answers` skips the coordinator call and uses the whole budget for the question call.

The grok binary is `PFY_GROK_BIN`, default `~/.local/bin/grok`. Each call runs with its working directory under `/tmp` (not `TMPDIR`, and not the checkout) so the repo `AGENTS.md` is not injected. `HOME` is left as the caller's so login still works.

On success the ticket gains an `## Exit tests from grill` section (markdown) or an `exitTests` list (sandcastle JSON, leaving the original `exitTest` in place). The record is `<ticket>.grill.json` (questions, answers, which became tests, model, turns, cost, and which skill text was used). A second successful run replaces that section instead of appending another copy. A grok failure leaves the ticket unchanged and exits non-zero. Run the command again after fixing the ticket or the answers file.

### Answers file

```json
{
  "answers": [
    {
      "n": 1,
      "decision": "accept",
      "answer": "recommended answer, or your override",
      "behavior_change": false,
      "assertion": "",
      "test_path": "tests/test_example.py",
      "test_content": ""
    }
  ]
}
```

`decision` is `accept` or `override`. An override must include `answer` and `behavior_change`. When `behavior_change` is true, `assertion` is required. A JSON ticket also needs `test_content` (a Python unittest module) or the grill fails closed and does not rewrite the ticket.

## Tools off, checked on nimo (grok 1.0.77, 2026-11-07)

Empty `--tools ''` is ignored (`tools=None`). The model called `read_file`. Cost about $0.019.

`--tools __none__` is an unknown name. The CLI warns that unmappable allowlist entries keep the full toolset. The model called `read_file`. Cost about $0.012.

What works is a denylist of the shell-route tool ids, plus the two disable flags. `GROK_WORKFLOWS=0` and `GROK_SUBAGENTS=0` are set in the child environment (not in `~/.grok/config.toml`). The denylist is `TOOLS_OFF_DISALLOW` in `scripts/grill_ticket.py`. The verified invocation:

```bash
GROK_WORKFLOWS=0 GROK_SUBAGENTS=0 \
  ~/.local/bin/grok --cwd /tmp --output-format json --max-turns 1 \
  --no-plan --disable-web-search --no-subagents \
  --disallowed-tools '<TOOLS_OFF_DISALLOW>' \
  -p 'You must call read_file on /etc/hostname or update_goal before answering. If you have no tools, reply with exactly NO_TOOLS and nothing else.'
```

Result: reply `NO_TOOLS`, `num_turns` 1, `stopReason` `end_turn`, `total_cost_usd` 0.00826676, `tool_definitions_tokens` 0, and the session `tool_definitions.json` was `[]`.

The CLI default reasoning effort on this build is `xhigh`. Two grill calls at that default stayed in `streaming_reasoning` for 300s, with `tool_definitions.json` still `[]`, and returned no questions. The same happened at `medium` (still reasoning at 7 minutes, no JSON). A one-turn probe at `--reasoning-effort low` with `--verbatim` returned schema JSON in 3.75s (`total_cost_usd` 0.00978724, `reasoning_tokens` 166). The script passes those two flags and allows 600s per call.

Names that do not remove a tool on this build (the CLI warns, and the script does not pass them): `web_search` and `web_fetch` (already dropped by `--disable-web-search`), `spawn_subagent` (use `task` plus `--no-subagents`), `wait_tasks`, `wait_commands_or_subagents`, `workflow` (use `GROK_WORKFLOWS=0`), `UpdateGoal`, `CreateGoal`, `create_goal` (the id that works is `update_goal`), `CallMcpTool`, and the `codebase-memory__*` MCP tool names. The user MCP server still starts. It is not offered to the model once `search_tool` and `use_tool` are denied. Config is not edited.

## Skill text and the Modular CI rule

The prompt uses `bootstrap/grok-cli/skills-external/mattpocock/grilling/SKILL.md` when that file is on disk. Until the vendoring lane lands it, the script uses a short embedded summary and records `skill_source: embedded`. The Modular CI rule is the `Modular CI` section of `AGENTS.md` when present, else `docs/ops/MODULAR-CI.md`, else the embedded standing rule. The record names which one was used.

Seeds in every grill prompt: software-factory Q5 "What stops two runs doing the same work?", and that Modular CI rule.

## Sandcastle

`npx tsx src/lanes.mts --grill auto` (default) calls this script once per ticket before the exit-test commit. `--grill off` skips it. `PFY_MENTAT_DIR` selects the checkout (default `~/DEVELOP/pfy-mentat`). A failure blocks only that ticket. The lane receipt field `grill` has `count`, `turns`, and `costUsd`.

## Real run (nimo)

Samples are copies under `docs/ops/grill-samples/`. `tmp/TICKET-pk2.md` and `~/DEVELOP/pfy-mentat/tmp/fp1107/TICKET-s3.md` were not modified. Both runs used the embedded skill summary and the embedded Modular CI rule. Model `grok-4.7-build`. Each call was one turn and stopped with `end_turn`. The coordinator accepted every recommended answer.

| Sample | Questions | Behavior changes | Turns | Wall | Cost |
|---|---|---|---|---|---|
| TICKET-pk2.md | 18 | 16 | 2 (1+1) | 379.8 s | $0.08859176 |
| TICKET-s3.md | 13 | 11 | 2 (1+1) | 434.4 s | $0.09184556 |

pk2 call costs: grill $0.05037984, coordinator $0.03821192. s3 call costs: grill $0.06030988, coordinator $0.03153568. The two tickets ran at the same time, so the wall clock for the pair was 434.4 s.

pk2 left Q17 and Q18 as no behavior change (exit-test immutability stays the committed section; this lane does not edit AGENTS.md, the fastpipe scripts, or the catalog stage file). s3 left Q12 and Q13 as no behavior change (doc updates already named in that ticket, and a podman failure stays recorded). The other answers became the `## Exit tests from grill` sections in the copies.
