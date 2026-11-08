# reasonix evq1107

STAY I0 reference. MIT. DeepSeek-native coding agent. Docs only. Gap L stays open.

## What it is

Reasonix (esengine/DeepSeek-Reasonix) is a coding agent. The program runs on the machine. The model is a provider you configure. Surfaces at this pin: terminal, Studio desktop, `reasonix web`, and `reasonix acp`. The npm wrapper calls itself a cache-first DeepSeek coding agent. The README Versions table marks `studio` (2.x) active and `main-v2` (1.x) maintenance. This checkout is Go (`go 1.26.0` in `go.mod`). `README.md` has no TypeScript line. The pin README does not describe a SEARCH/REPLACE hold until `/apply`. Edit tools write. `docs/CHECKPOINTS.md` says rewind uses file snapshots and does not track `bash`.

## Pin and license

| Item | Value |
| --- | --- |
| Pin | `737a181c49367a7a153c71889c168638fcfc0ba3` |
| Commit | 2026-11-01 16:37:22 -0800. Subject: Merge pull request #14923 from esengine/release/studio-2.57.0. The entry records tag `studio-v2.57.0` at this SHA. |
| License | MIT. Root `LICENSE`. `npm/reasonix/package.json` is MIT, version `0.0.0`. |
| Fetch | `git clone --filter=blob:none --no-checkout`, then `git fetch --depth 1 origin <pin>`, detach. No upstream script ran. Wall clock not recorded. |
| Bytes | `du -sb`: src 155511288, `.git` 75408200, `--exclude=.git` 80103088. Over the 50 MB I2 copy bar. The entry's CLI tarball was not downloaded. |
| Cache | `~/.cache/pfy/tools/reasonix/src`. Not committed. |

The uncommented DeepSeek block in `reasonix.example.toml` is `kind = "openai"`, `base_url = "https://api.deepseek.com"`, `api_key_env = "DEEPSEEK_API_KEY"`. A Claude block is also uncommented. `docs/REASONING_PROVIDERS.md` says new official DeepSeek entries use `https://api.deepseek.com/anthropic` and DeepSeek's automatic prefix cache. `docs/DSH.md` says the key lives in the Reasonix home.

## Ideas, and the pfy file each would touch

| Idea | pfy file | Already covered by |
| --- | --- | --- |
| Keep the system prefix byte-stable. Put dynamic state on the turn tail. A planner on another provider gets its own session. | `docs/ops/local-cloud-split.md` | Workers use an OpenAI base URL. There is no DeepSeek prefix cache on that path. |
| Rewind edit-tool files from snapshots. Leave shell side effects alone. | `harness/write-guard-mcp/src/write_guard/server.py` | Write mediation. Shell denial is destructive-command-guard. |
| Headless Ask fails closed. Deny rules still hold in Auto and Yolo. | `docs/ops/loop-engineering.md` | Exits are written before the run. The cage is the boundary. |
| A session can start from a committed base in its own worktree. | `bootstrap/grok-cli/skills/best-effort-and-bot-budget-build-max/SKILL.md` | Named branches stay off the founder checkout. Reasonix also omits uncommitted files. That part is not copied here. |
| Opt-in `host_verification = "on"` holds a changed turn for a check, a review, and a sign-off. Release note 2.49.0 says that hold is no longer the default. | `docs/build-dropins/mvp-review-quality-1031.md` | Review before done is already the pfy rule. The flag stays theirs. |

## Catalog comparison

Same job: a terminal coding agent, and gap L (local inference), which is why this slug was queued. Searched `data/stages/*.json` uses, features, and tags. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) puts entry 164 on the hold-or-comparison list. The gap L pick there is Strata. This lane builds no pipeline, CI, or gate.

| Tool | Stage | What it covers | How Reasonix compares |
| --- | --- | --- | --- |
| Aider | I1 | Local terminal editor. Its card records 1 of 1 commits in 7.6536 s. | Default path is hosted DeepSeek. Snapshots, where Aider commits. |
| Grok CLI bootstrap | I3 | The operator harness. | A second coding CLI. |
| Ollama, llama.cpp server, LiteLLM, Strata | I2, I1, I2, I2 | The local engine path. | Reasonix calls a provider. An example comment names Ollama Cloud, a hosted preset. |
| dsh-superagent | I0 | DeepSeek harness design docs. | Reasonix can be a dsh ACP child. We do not run dsh. |
| write-guard, agent-cage, destructive-command-guard | I3, I3, I2 | Write, lab, and shell limits. | Ask, Auto, and Yolo sit inside Reasonix. |
| Pi-Harness, Continue.dev, OpenClaude | I0, I1, I1 | Other coding clients. | Same class of overlap. |
| deepseek-v4-1-flash GGUF | I0 | Its card says the GGUF does not fit nimo. | This pin wants the API. |

Beats what we have: no.

## Gates

Value (3 of 4 for I3): gap fill no (gap L is the engine). Operator leverage no (a provider key, and a second coding CLI). Evidence no (docs only; this lane did not run the smoke; the entry designs that smoke to exit 2 without unpacking the CLI). Blast radius no (terminal, desktop, web, and editor are one runtime; license is MIT; no multi-GB weights). Score 0 of 4.

Modularity (all 4 for I2): local code was not required. The surface is the Go kernel plus desktop, Android, and the npm wrapper. Isolatable and reversible pass. 2 of 4. Worktree 80103088 bytes. Potential is low, not ambiguous, so the I2 shelf does not apply. No `self_pipeline`. Uses and features name no CI, test, or review role. No TOOLS.md row. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Setup writes a provider key | `reasonix setup` stores a key under its home | Do not run setup. The cache is source only. |
| The agent edits a real tree | A trial points at Mark's checkout | Stay I0. A later trial uses an isolated worktree. |
| Hosted DeepSeek spend | The example `base_url` is `https://api.deepseek.com` | No key and no request on this lane. |
| Pin drift | `studio` moves past this SHA | Keep `737a181c49367a7a153c71889c168638fcfc0ba3`. |

## Next gate

Stay I0 reference. Re-open only if a later ticket copies one rule (stable prefix, or edit snapshots that skip the shell) into an existing pfy doc, and that ticket grills the copy first. Not a Feature GO.

## Pipeline questions

This lane does not put Reasonix on a pipeline. The scheduler started the read. It writes this directory, the card, and the entry Status line. No model and no account.

1. Trigger, if adopted later: a person runs setup with a provider key. Not this scheduler.
2. It would read a project folder and call the configured provider. This lane only read the checkout.
3. Next: nothing in `./pfy`.
4. A human re-enters before any install, any key, or any I1 row in TOOLS.md.
5. One worktree per slug keeps this card private. A second read must not edit the same card.
