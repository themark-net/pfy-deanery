### Entry 128: Harness Score — deterministic scanner that grades the harness around a coding agent (L0-L4)

- **URL**: https://github.com/paladini/harness-score (MIT, TypeScript, zero runtime dependencies; 585 stars at this read; npm `harness-score` 1.8.2, tag `v1.8.2` at `70a0ecc1aa90`, 2026-10-14)
- **Date**: 2026-10-17 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2111355034491392408
- **Summary / Key Claims** (upstream README at 1.8.2): `npx harness-score` scores a repo's agent harness on 36 filesystem checks in six dimensions (context files and rules, skills and commands, hooks and guardrails, sensors such as tests/lint/types, CI, hygiene and safety) and gives a maturity level L0-L4 plus the ranked fixes for the next level. Zero LLM calls, zero network, same output for the same tree. `--json`, `--md`, `--badge`, `--diff`, and `--min-level N` as a CI gate (exit 0 pass, 1 gate failure, 2 usage error or incomplete scan). Check IDs (`CTX-01` … `HYG-08`) are stable. Three leaked-credential checks can't be switched off in `.harness-score.json`.
- **Why it matters here**: Mark wants bots and Grok Build to stop making rookie mistakes (secret leaks, missing guards) before Tester sees them, and every active product repo must have `AGENTS.md`. This gives a deterministic, offline number for "is the harness there" across pfy-mentat, leasegrid-c, quietsoap and the bots' repos: AGENTS.md substance, gate hooks, tests in CI, `.env` hygiene, credential-free MCP config. **Possible eval-auto trial**: scan our product repos and compare its findings with what Tester/Reviewer flagged on recent PRs.
- **Fit on nimo**: Yes. Node >= 18 and the unpacked npm tarball under `~/DEVELOP/pfy-mentat/tmp/harness-score/` (117 KB). No `npm install -g`, no plugin install. Its Cursor plugin and GitHub Action are optional and not needed.
- **Verified on the Grok Bot box** (tarball sha256 `816c6362704e73111801cfce3861a189c2494868d0a95b4aa7883ca29a0b94c2`, matches the registry's sha512; Node 20.19.2 and 22.20.0; bubblewrap, no network, temp HOME): smoke PASS. The clean fixture found `AGENTS.md` and a protected `.env`; the leaky fixture failed `HYG-02` and `HYG-03`; a rerun was byte-identical; `--min-level 4` exited 1; fixtures, temp HOME and the watched real-HOME dirs (`~/.harness-score`, `~/.config/harness-score`) unchanged.
- **Finding**: a short but real `AGENTS.md` alone stays at **L0** (CTX-02 "substantive" needs more), so thresholds should be read per check, not only by level. The scan reads ignored and untracked files too (up to 512 KiB each), so run it on a clean worktree when a `.env` sits locally.
- **Extracted Repos / Tools**: https://github.com/paladini/harness-score · https://www.npmjs.com/package/harness-score · https://paladini.github.io/harness-score/
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_128_130.py --entry harnessscore`. Looks up `$NODE_BIN`, `tmp/node/bin/node`, then PATH, and `$HARNESS_SCORE_DIR` or `tmp/harness-score/package`; package version pinned to 1.8.2. Two temp fixtures only; never scans a real repo. Receipt: `pipelines/smoke/harnessscore/latest.json`.
- **Non-goals**: No CI gate wired in yet, no badge, no plugin or Action install, no changes to any repo's harness from its advice.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Score chasing | Repos gain files to please the scanner, not to catch mistakes | Gate only on named checks we care about (hygiene, hooks, CI tests), never on the total |
| Cursor/Claude bias | Grok Build conventions (`.grok/`, skills) not detected | `.harness-score.json` rules off with the reason; note gaps upstream |
| Local `.env` in the tree | HYG-03 fails on a dev checkout | Scan a clean worktree or CI checkout |
| Upstream churn (minor versions add checks) | Scores move between versions | Pin the version; `--diff` flags `maturityModelChanged` |

- **Status**: STAY I0 on nimo (2026-11-07). harness-score 1.8.2 scored this clean worktree L1 Documented, 48/105 (46%), 17/36 checks, in 0.0556s. The rerun was byte-identical (0.0528s). Removing AGENTS.md and 65 SKILL.md files dropped the score to 41/105 and left the level at L1. Skills stayed 0/17. Not a gate. Receipt: `eval/evq1107/harness-score/REPORT.md`.
