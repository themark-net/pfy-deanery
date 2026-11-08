# Auto-Company evq1107

STAY I1 reference: persona and consensus patterns already live in docs/ops/auto-company-patterns.md

## What it is

Auto-Company (package `autonomous-company` 3.0.0) is a company loop with 14 role files under `.claude/agents/`. A daemon repeats a CLI call. The call reads `PROMPT.md` and `memories/consensus.md`, the team skill picks 2 to 5 roles, and the call updates the consensus file. A person steers by stopping the run and editing Next Action or Human Overrides. The product center is `http://127.0.0.1:8810/center`. Claude Code is the default engine. Codex is `ENGINE=codex`. The Cursor adapter is refused. OpenAI-compatible is opt-in. Upstream `docs/project-isolation.md` refuses native macOS and Windows and requires bubblewrap 0.9 or newer on Linux and WSL2. The README still prints a macOS `make start`. This lane ran no start command. The README banner still says dashboard v2.2.0. Both GitHub URLs, Auto-Company and Autonomous-Company, resolve to this commit. License is MIT. Root `LICENSE`. Copyright 2026 jinmingyang and 2025-2026 Zheyuan (Max) Kong and contributors.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `211baad12b08d25c75b10ade86ed301098be69b2` |
| Commit | 2026-10-21 16:38:21 +0800. Merge pull request #60, fix/return-motion-20261018. |
| Fetch | 3 s. `git clone --depth 1 https://github.com/MaxMiksa/Auto-Company.git`. No upstream script. |
| Tree | 14 agent files, 36 `SKILL.md` files plus `frontend-design.md`, 1001 checkout paths, worktree 17504513 bytes. |
| Cache | `~/.cache/pfy/tools/auto-company/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/auto-company`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. This lane did not run make, the daemon, the dashboard, or any script.

## Ideas, and the pfy file each would touch

1. Named roles, squad of 2 to 5. Already `AGENTS.md` and `docs/ops/gstack-role-recipes.md`.
2. One markdown baton with a human Next Action. Already `docs/TODO.md` and `docs/ops/auto-company-patterns.md`.
3. Pre-mortem before a major decision. Already `/adr`, `/open-questions`, and `docs/ops/loop-engineering.md`.
4. Forbidden-action list, and Human Overrides kept byte-for-byte. Already the write-guard posture and the same pattern note.
5. One usage row per cycle (`cost_usd`, tokens) beside the prose baton. A later ticket could touch `scripts/pfy_build_p.py`. Gap B is the 3 hour `./pfy build` timeout, and this row leaves that timeout where it is.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path. That section says no entry from 137 to 167 closes it. Entry 066 is the persona source. This lane builds no pipeline step. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How Auto-Company compares |
| --- | --- | --- |
| gstack | I1 | Role patterns already ported. The clone stays out. |
| marketing-council | I1 | First-party named advisors and a dissenter. |
| Multica | I1 | Teammate board. Stays off the orchestrator. |
| Squadra | I1 | Manual seats and a non-author close. |
| Festival | I1 | Checklist gates. The probe left the timeout in place. |
| Finn loop | I1 | Exit cards already own loop stops. |
| mattpocock/skills | I1 | Plan and review skills already on the path. |
| Elephant-Goldfish | I1 | Fresh-eyes spec pass before Build. |
| MCO | I1 | Parallel raw answers. The probe left the timeout in place. |
| Kander | I1 | Two-role done gate. The probe started no agent. |
| kanbots | I1 | Worktree fan-out. The probe left the timeout in place. |
| Hermes Teammates | I0 | Fixed roster, blocked until Hermes is the bot interface. |
| multi-agent-generator | I0 | CrewAI or LangGraph scaffold. |
| Brigade | I0 | Exclusive task claim. Different file from consensus.md. |

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no, evidence no (`make start` needs Claude or Codex; this lane did not run it; host-local model servers need a broker this pin does not have), blast radius no (CLAUDE.md says do not wait for a person; ADR-0002 keeps Grok CLI; the daemon would be a second runtime). Score 0 of 4.

Modularity, all 4: the README and CLAUDE.md were enough, so a local copy was not required to decide. The tree is scripts, a dashboard, 14 agents, and the skill set. The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. 17504513 bytes is under the 50 MB I2 bar. Potential is low, so I2 stays closed. No `self_pipeline`. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Charter skips the person | CLAUDE.md says do not wait for approval | Stay on Grok CLI. Do not start the daemon. |
| Host writes | The charter allows new repos, deploys, commits, and global installs | This lane ran nothing. |
| Local model looks supported | `ENGINE=openai-compatible` accepts loopback HTTP | Upstream `docs/project-isolation.md` says host-local model servers are unavailable. Leave Ollama on the pfy path. |
| Prompt rules treated as a sandbox | The README says those rules do not block arbitrary commands | Linux cycles require bubblewrap. This lane did not install it and did not start a cycle. |
| Three-cycle table treated as a state machine | The README says the table is guidance. Upstream `docs/product-cycles.md` says one cycle is one coordinator attempt | Keep the pattern note. Leave that table as prompt text. |

## Next gate

Stay I1 reference. Re-open only if a later ticket shows this pin contradicts `docs/ops/auto-company-patterns.md`, and that ticket still leaves the daemon out. No Feature GO.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory.

1. Trigger, if a later ticket adopted it: a person starts one documented cycle. The evq scheduler is not that trigger.
2. It would read `PROMPT.md` and `memories/consensus.md` and call Claude Code or Codex. It would write the consensus file, `logs/usage.jsonl`, and project files. This lane called no model and used no account.
3. Next would be another cycle until a budget, an error breaker, or a human pause. pfy does not start from that file.
4. A human re-enters by stopping the run and editing Next Action or Human Overrides.
5. One worktree per slug keeps this card private. Two loops on one checkout would both write `memories/consensus.md`.
