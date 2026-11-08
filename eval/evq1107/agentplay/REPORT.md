# agentplay evq1107

STAY I0 reference: Apache-2.0 replay map has no Grok Build reader and does not score H1

## What it is

agentplay (Entelligence-AI/agentplay) builds one redacted `agentplay/v1` JSON map per coding-agent session and plays it in a local viewer. A map records tool calls, file touches, MCP calls, skills, subagents, and model requests in order. The map stores no prompt text, tool input, tool output, or file contents. A shell command is a verb only. Paths outside a repo collapse to a bucket. The CLI is `agentplay.cli:main`. No arguments is rewritten to `view` (`cli.py`), which builds maps and opens a browser on `127.0.0.1:7317`. Other subcommands: build, list, export, import, agents, fix, repos, autotune. The agent tuple is claude-code, codex, cursor, copilot, copilot-vscode, opencode, kiro, gemini-cli, antigravity-cli. There is no `grok` name and no `AGENTPLAY_GROK_HOMES`.

License is Apache-2.0. Root `LICENSE`, `python/LICENSE`, and `NOTICE` say Apache 2.0, copyright 2026 Entelligence AI, Inc. `python/pyproject.toml` sets `"license": "Apache-2.0"` and version `0.2.6`. No runtime dependencies. Python >= 3.11.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `ff5f83e37063a38ec55ab7dd2b0fcdc435f4a72c` |
| Commit | 2026-10-27 01:30:59 +0530 (20:00:59Z). Subject: Merge pull request #45, bump-0.2.6. |
| Version | pyproject `0.2.6`. The shallow fetch did not download tag objects. |
| Fetch | same clock second (elapsed 0 s). `git init`, `git fetch --depth 1 origin ff5f83e37063a38ec55ab7dd2b0fcdc435f4a72c`, `git checkout --detach FETCH_HEAD`. No upstream script. |
| Bytes | worktree 3284896. `.git` 1412219. |
| Cache | `~/.cache/pfy/tools/agentplay/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/agentplay`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. This lane did not install the wheel and did not re-hash the entry's recorded wheel digest.

## Ideas, and the pfy file each would touch

1. A shareable map with that redaction contract. Touch `docs/ops/cage-session-resumption-design.md`.
2. Session totals (errors, retries, max context, compactions) so a list does not scan events. Touch `scripts/pfy_build_p.py` (`receipt.jsonl`).
3. File touch levels hit, read, and edit, with the first event index. Touch `bootstrap/grok-cli/skills-external/mattpocock/code-review/SKILL.md`.
4. Compaction marks with pre-token and post-token counts. Touch `docs/dogfood/D3-RESULTS.md`.

## Catalog comparison

Gap H1 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a repeatable with/without score, plus memory and context. That section holds entry 160 for comparison. This lane builds no pipeline step.

Same job, already covered: skill-up I3 (with/without grade, tag `#eval`), eval-harness (pfy) I1 (feature `eval`), Harness Score I0 (grades harness files, not a session), neatroots I2 (offline rules for loops, repeated calls, and error streaks on saved traces), Agent Beacon I0 (copies a committed Grok session to JSONL; scoring calls hosted Jev), Tracekit I0 (signed tool-call records before the call), Pi-Harness I0 (trace and replay for Pi, reference only), Hermes Agent (feedback loops) I1 (memory skill, not a map). Host session layout is `docs/ops/cage-session-resumption-design.md`. `./pfy build -p` already writes a receipt with a session id. The entry records smoke PASS on 2026-11-04 for version, help, import, and list of one synthetic map. That receipt file is not in this worktree. This lane did not re-run the smoke.

agentplay can read an OpenCode db and still cannot read `~/.grok/sessions`. It draws a picture. It does not add the H1 score skill-up owns. H1 memory cards that do not replay a session: ai-memory I1, OpenContext I1, cass-memory I0. codebase-memory-mcp I2 is the code graph.

## Gates

Value (3 of 4 for I3): gap fill no. Operator leverage no, because a Grok reader is new work this pin does not contain. Evidence yes: `examples/x-intake-local/smoke_160.py` is in the repo and the entry records PASS. This lane did not re-run it. That smoke never opens the viewer or parses a real transcript. Blast radius yes: Apache-2.0, no weights, worktree 3284896 bytes, under the 50 MB cap. Score 2 of 4.

Modularity (all 4 for a local copy): the format doc and the agent tuple were enough, so local code was not required. The unit is one PyPI package. The cache copy is isolatable, and deleting it leaves the pin. 3 of 4. Potential is low, so I2 does not open.

`uses` and `features` do not name a CI, test, or review role token. No `self_pipeline` field. No gate wiring. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Browser and email POST | A bare `agentplay` runs `view` | Do not run it. The smoke stays on version, help, import, and list, with `AGENTPLAY_NO_NETWORK=1`. |
| Repo and home writes | `fix` may write repo `CLAUDE.md`, `CLAUDE.local.md`, `.claude/settings.json`, or `.claude/settings.local.json`. `autotune on` writes a SessionStart hook into `~/.claude/settings.json`. `--at` only prints a crontab line | Do not run `fix`, `repos`, or `autotune`. This lane did not. |
| False reader | The synthetic import is treated as proof for `~/.grok` | Stay I0. The status line says there is no Grok reader. |
| Prompt text on disk | Titles keep the first 90 characters of a prompt in `index.json` | No `AGENTPLAY_HOME` on the real home. This lane created none. |
| Pin drift | Intake `main` was `b5fcffe889933cbcf28515d2ccc9d3567b22274b`, not this pin | Keep `ff5f83e` and version 0.2.6. |

## Next gate

Stay I0 reference. Re-open only if a later ticket names a Grok Build reader for `~/.grok/sessions` and still keeps scoring on skill-up. No install, no viewer, no code copy, no gate. Not a Feature GO.

## Pipeline questions

This lane does not put agentplay on a pipeline. The scheduler started it. It writes this directory, the card, and the entry Status line.

1. Trigger, if adopted later: a person asks to replay one session. Not this scheduler and not a gate.
2. It would read local transcripts for the nine agents above and write maps under `AGENTPLAY_HOME`. It would not read Grok Build sessions. This lane called no model and used no account.
3. Next: a person looks at the map. Nothing in pfy starts from it.
4. A human re-enters before any install, any viewer, any parser port, any `fix` apply, or any I1 catalog row.
5. One worktree per slug keeps this card private. Two builds must not share one `AGENTPLAY_HOME`.
