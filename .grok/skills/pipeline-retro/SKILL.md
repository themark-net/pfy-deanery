---
name: pipeline-retro
description: >
  Retrospective on the pfy-deanery landing pipeline. Run it on every 10th
  landing on main, or when someone asks for a pipeline retro. Applies the
  retro skill's automated-checks and tool-economy lenses, plus the
  software-factory five questions, and writes a short report with a cut list.
---

# pipeline-retro

Use the vendored `retro` and `software-factory` skills as the lenses. The numbers come from `scripts/pipeline_retro.py`. The output is a short report plus a concrete cut list.

## When

Run this on every 10th first-parent landing on `origin/main`. Count with:

```bash
git rev-list --first-parent --count origin/main
```

When that count is divisible by 10, run the retro before the next landing starts. Also run it on demand when someone asks for a pipeline retro, or when a landing just ran the full suite more than once.

## Lenses

Read `bootstrap/grok-cli/skills-external/mattpocock/retro/SKILL.md` and apply only these two lenses to the pipeline, not to a single coding session:

- **Automated checks.** A check that already exists but is duplicated or unwired. Name the check that already ran. Do not propose a new suite. Pregate skips the standalone `suite` check because `ubuntu-parity` and `eval-structural` already run `python3 -m unittest discover -s tests`. That skip is not evidence the suite ran only once.
- **Tool economy.** Expensive repeated tool calls. Full-suite runs and runner-minutes are the evidence. The baseline in the script header is about 6 full-suite runs and about 127 runner-minutes per docs-only landing (39 min pregate + 44 min branch CI + 44 min main CI).

Read `bootstrap/grok-cli/skills-external/mattpocock/software-factory/SKILL.md` and answer its five questions for each pipeline task (pregate, branch CI, main CI):

1. What triggers it?
2. What does it do, and which services does it read and write?
3. What does it trigger next?
4. Where does a human re-enter?
5. What stops two runs doing the same work?

Use the words from that skill (task, trigger, run, runner, ticket tracker, git host, orchestrator). Answer from the script output. If the data does not show a brake, say so.

## How

From the repo root:

```bash
python3 scripts/pipeline_retro.py
python3 scripts/pipeline_retro.py --json
python3 scripts/pipeline_retro.py --since 2026-11-01
```

Default is the last 10 first-parent commits on `origin/main`. The script reads local pregate summaries, lane progress files, the public GitHub Actions API (cached under `~/.cache/pfy/retro`, unauthenticated, stops before the 60/hour floor), and optionally `~/actions-runner/_diag`. It does not push, merge, or edit a workflow. If GitHub is unreachable it still prints the local numbers and says the API was unavailable.

Write the report to `docs/ops/PIPELINE-RETRO-<MMDD>.md`:

- the baseline line and the table
- one answer set per task, tied to the counts
- a cut list: which duplicated or unwired checks to stop repeating, and which repeated calls to drop

No secrets in the report. No em dashes.

## Do not

- Add a CI or pregate step that re-runs a discover another step already ran.
- Edit `~/.grok/config.toml`, `install.sh`, or the operator's checkout at `~/DEVELOP/pfy-mentat`.
- Paste upstream skill text into this file. The vendored files stay verbatim.
