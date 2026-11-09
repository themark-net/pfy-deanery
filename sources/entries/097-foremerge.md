### Entry 097: Foremerge — intent-level conflict detection for parallel coding agents, above Git

- **URL**: https://github.com/naw103/foremerge (Apache-2.0, Rust, about 530 stars at this read, release v0.5.1 on 2026-10-03, pre-1.0)
- **Date**: 2026-10-06 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2107436703765901427
- **Summary / Key Claims** (upstream README): Agents publish intent with semantic scopes (`symbol`, `api`, `schema`, `config`, `file`, `contract` and others, each with an operation such as replace or extend) before editing. A SQLite ledger inside `.git/foremerge/` is shared across worktrees on one machine. A deterministic detector (no model) flags clashes like "A replaces `PaymentService` while B extends it" before either worktree changes, with an explanation and a suggested split. Advisory during planning, never locks files; unresolved HIGH conflicts gate acceptance, and acceptance runs a registered check itself instead of trusting the agent. CLI with `--json`, an MCP server, and skills for Claude Code, Codex and Cursor. Grok Build is not in its client list, but the CLI and MCP server are client-agnostic. Upstream says there are no published benchmarks yet and cross-machine coordination is out of scope.
- **Fit on nimo**: Yes. The release tarball unpacks to a single binary (`foremerge`, plus an `fmg` alias). It can live in `~/DEVELOP/pfy-mentat/tmp/foremerge/`. Avoid `install.sh` (writes `~/.local/bin`) and `foremerge setup` (edits client MCP configs, Codex at user level) without the operator's approval.
- **Verified on the Grok Bot box** (release binary, sha256 checked, throwaway repo): `init`, `agent register`, `intent publish --scope symbol:PaymentService=replace`, then `conflicts check --scope symbol:PaymentService=extend` returned one HIGH `destructive_vs_additive` conflict (rule FM-C001) with `blocking: true`; an unrelated `file:README.md=modify` check returned none. The smoke below PASSed there.
- **Why it matters here**: The founder doctrine runs bots in parallel with open Grok Build sessions and pauses competing work on repos with an open Build session. Today that relies on agents noticing each other. Foremerge would let Build, Cursor agents and bots declare scope in the same repo and catch intent clashes before code, which is cheaper than a failed review cycle.
- **Extracted Repos / Tools**: https://github.com/naw103/foremerge · https://github.com/naw103/foremerge/releases/tag/v0.5.1
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke.py --entry foremerge`. Looks for `$FOREMERGE_BIN`, then `~/DEVELOP/pfy-mentat/tmp/foremerge/foremerge`, then PATH; missing exits 2. In a tempfile git repo it publishes the replace intent and expects the extend preflight to return a HIGH conflict and an unrelated scope to return none. Receipt: `pipelines/smoke/foremerge/latest.json`.
- **Non-goals**: No `setup` into client configs, no MCP registration, no use on the operator's main checkout.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Only works if everyone declares | One agent skips publishing and the ledger is blind to it | Trial only where every participant is scripted to call `conflicts check` first |
| Pre-1.0 schema churn | Ledger schema changes between versions | Ledger is per-repo under `.git/foremerge`; delete and re-init for a trial |
| Single machine | Cursor cloud agents and nimo don't share one `.git` | Scope a trial to agents running on nimo (Build plus local bots) |

- **Status**: STAY I1 after the 2026-11-07 nimo probe (ops:eval/evq1107/foremerge/REPORT.md). Release v0.5.1 is unpacked under ~/.cache/pfy/tools/foremerge/. Same-path modify is advisory, not a blocking gate. Not wired.
