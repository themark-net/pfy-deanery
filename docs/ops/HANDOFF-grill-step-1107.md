# Handoff: grill step before a CI, pipeline, or gate ticket (bot/grill-step-1107)

## What changed

pfy-mentat (this worktree, branch `bot/grill-step-1107`):

- `scripts/grill_ticket.py` grills a markdown ticket or a sandcastle JSON ticket or batch when a touched path or the ticket text hits the CI, pipeline, or gate list in `TRIGGER_GLOBS` and `TEXT_NEEDLES`. Otherwise it prints `no grill needed` and exits 0.
- Behavior-changing answers are appended as `## Exit tests from grill` on a markdown ticket, or as `exitTests` cases with `fromGrill` on a JSON ticket. The original `exitTest` stays. A second successful run replaces that section.
- The record is `<ticket>.grill.json`.
- `tests/test_grill_ticket.py` drives a fake grok. No network.
- `docs/ops/GRILL-STEP.md` is the operator command. `docs/ops/loop-engineering.md` iron law 4 points at it. `docs/ops/BUILD-GATE-TRIALS-1103.md` has a one-line pointer.
- Real-run copies and records are in `docs/ops/grill-samples/`.

sandcastle-grok worktree `tmp/sc` (branch `bot/grill-step-1107`, not `~/DEVELOP/sandcastle-grok`):

- `src/grill-step.mts` calls the python script. `src/lanes.mts` runs it before the exit-test commit when `--grill auto` (the default). `--grill off` skips. `--grill-only` and `--then-cut` support the smoke.
- A grill failure sets that lane to `blocked` with the reason. Other tickets continue.
- The receipt field `grill` has `mode`, `count`, `turns`, and `costUsd`.
- `smoke/grill-hook.mts` proves a CI ticket is grilled and committed, a plain ticket is skipped, and a failing grill blocks only that ticket.
- `README-INTEGRATION.md` documents the hook.

## Commands

```bash
python3 scripts/grill_ticket.py path/to/TICKET.md
python3 -m unittest tests.test_grill_ticket -q
```

From `tmp/sc` (node_modules is the existing symlink; do not install another):

```bash
./node_modules/.bin/tsx smoke/grill-hook.mts
```

Sandcastle sets `PFY_MENTAT_DIR` to the pfy checkout. The default is `~/DEVELOP/pfy-mentat`. Until this branch is on that checkout, point `PFY_MENTAT_DIR` at a tree that contains `scripts/grill_ticket.py`.

The grok child uses `PFY_GROK_BIN` (default `~/.local/bin/grok`), cwd under `/tmp`, `HOME` unchanged, `GROK_WORKFLOWS=0`, `GROK_SUBAGENTS=0`, and the tools-off denylist in `TOOLS_OFF_DISALLOW`. Cap is 12 turns total. With no `--answers` file the question call gets 11 and the coordinator gets 1.

## Real run (nimo, 2026-11-07)

| Sample | Questions | Behavior changes | Turns | Wall | Cost |
|---|---|---|---|---|---|
| TICKET-pk2.md | 18 | 16 | 2 | 379.8 s | $0.08859176 |
| TICKET-s3.md | 13 | 11 | 2 | 434.4 s | $0.09184556 |

Model `grok-4.7-build`. Skill source `embedded`. Modular CI source `embedded`. Coordinator accepted every recommended answer. Details and the two answers that did not change behavior are in `docs/ops/GRILL-STEP.md`.

## Catalog

Checked `docs/eval/TOOLSET-RANKING.md` (2026-11-07 catch-up) and `data/tool_integration_stages.json`. `mattpocock/skills` is stage I1 with evidence `path:bootstrap/grok-cli/skills-external/mattpocock` and features to-spec, tdd, and review. The grilling skill file is not on this branch, so the script uses the embedded summary until that file exists. Nothing in the ranking is a tools-off pre-ticket grill. Headroom was trialed in `docs/ops/BUILD-GATE-TRIALS-1103.md` and was not adopted. This step uses the grilling prompt plus the grok CLI from that trial. Catalog files were not edited.

## Risks

- The CLI default effort is `xhigh`. On nimo, `xhigh` and `medium` stayed in `streaming_reasoning` and returned no questions (300 s and about 7 min). The script pins `--reasoning-effort low` and `--verbatim`. A one-turn low probe cost $0.00978724 and finished in 3.75 s. The two successful ticket runs above are the numbers to use.
- The coordinator accepted recommendations that disagree with this ticket's rules: treat any Makefile touch as a trigger, exit 3, store a missing cost as null, and pass `--max-turns 6` on a normal run. Those sentences are in the sample tickets. The script keeps the ticket rules: Makefile triggers only for a CI or test target, failure exits 1, a missing cost is recorded as 0, and a cap of 12 splits 11 and 1.
- The user MCP server still starts from `~/.grok/config.toml`. That file was not edited. With `search_tool` and `use_tool` denied, the offered tool list was empty.
- User skills still load. The low probe sent 13464 input tokens.
- `AGENTS.md` has no Modular CI section in this worktree, and `docs/ops/MODULAR-CI.md` is not here yet. The script uses the embedded rule and will prefer those files when they exist. This lane did not edit `AGENTS.md`, `scripts/run_tests.py`, `scripts/test_select.py`, `scripts/test_cache.py`, pregate, or the catalog stage file.
- `PFY_MENTAT_DIR` default `~/DEVELOP/pfy-mentat` does not contain this script until the branch lands. A missing script blocks the sandcastle ticket. It does not skip the grill.
- The sandcastle commit is in `tmp/sc` only.

Not pushed.
