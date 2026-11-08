### Entry 159: Skills Manager: one CLI to install skills and distribute them to many agents

- **URL**: https://github.com/shenysun/skills-manager (MIT, Copyright (c) 2026 Sun Yongshen, TypeScript). Checked at commit `fae0bb864a8b96c1d0ca6278a6b7062e62992a36` (committer 2026-10-27T03:20:24Z, `chore(release): v2026.10.27-1`). npm package `skills-manager-cli` version `2026.10.27-1`, bin `skills-manager`. GitHub API description: a CLI-first hub for agent skills, one npx install, manage in chat, distribute to many agents. The package description says 70+ agents; that count is their claim, not measured here.
- **Date**: 2026-11-02 (X intake)
- **Source / Poster**: https://x.com/DanKornas/status/2117314826049306660
- **Summary / Key Claims** (upstream package description; their claims except where marked verified): one CLI installs skills from git, a URL, an archive, a marketplace, or a well-known source, then distributes them (symlink or copy) to many agent homes. It can keep a tree SHA as an update anchor. A bootstrap with no subcommand mounts skills into agents it detects. `list` with no hub exits 1 and says there is no skill home.
- **Why it matters here**: pfy-mentat keeps portable skills in one tree, `bootstrap/grok-cli/skills/`, and points OpenCode at the same source. Skills Manager is a different distribution model: one npm CLI that installs a hub and copies or links skills into many agent directories. Comparison only. It does not replace that source tree, and this smoke does not point it at the repo's skills.
- **Fit on nimo**: AMD Strix Halo, Radeon 8060S, no NVIDIA. The CLI is Node. This machine has Node v22.23.0 at `/usr/bin/node` and an existing npm at `~/.npm-global/bin/npm`. No GPU. The install and the CLI ran inside a scratch directory under this worktree.
- **Verified on nimo** (2026-11-02, this worktree, no sudo): `python3 examples/x-intake-local/smoke_159.py` exited 0. Receipt verdict `PASS`. The pass path does not set a reason string. Checks: `list` is `listed`, `list_exit` is 0, and the npm cache and npm HOME were under `tmp/xintake-159/` in this worktree. `--version` contained `2026.10.27-1` and `--help` succeeded. `list --home` was a scratch hub, not a detected agent. The scratch directory was removed when the smoke exited. Bootstrap was not run. Real-HOME skill and npm paths that the smoke watches were unchanged.
- **Findings**:
  - `npx skills-manager-cli` with no args bootstraps into detected agents. The smoke never does that. It installs with `npm install --ignore-scripts --prefix` into the scratch prefix, then runs `--version`, `--help`, and `list --home`.
  - npm is given a dummy `package.json` in the scratch dir, plus `HOME`, cache, prefix, userconfig, and `TMPDIR` there, so it does not walk up and edit this repo's `package.json`.
  - A `list` that exits 1 with `No skill home` is also a pass (the CLI ran and refused). On this nimo run, `list --home` exited 0.
  - An npm failure, a timeout, a missing node, or a version mismatch exits 2. A help failure or any other list failure exits 1.
- **Extracted Repos / Tools**: https://github.com/shenysun/skills-manager · npm `skills-manager-cli@2026.10.27-1` · compare with `bootstrap/grok-cli/skills/`
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_159.py`. Uses `run_isolated`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads `$SKILLS_MANAGER_BIN` or installs the pinned package with `$SKILLS_MANAGER_NPM` or npm on PATH. `$SKILLS_MANAGER_NODE` overrides node. A set override that is not executable exits 2 and does not fall through. HOME and the npm cache stay under this worktree's `tmp/xintake-159/`. Pins `$SKILLS_MANAGER_VERSION` and `$SKILLS_MANAGER_COMMIT`. Does not bootstrap and does not distribute. Receipt: `pipelines/smoke/skills-manager/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_159` (8 stub tests: missing node, hang killed, no surviving grandchild, help plus a no-skill-home refusal, npm scratch stays in the worktree, real-HOME write, bad timeout, gitignored receipt).
- **Non-goals**: No bootstrap, no distribute into real agent homes, no write to the real HOME, no edit of this repo's `package.json`, no TOOLS.md row. Catalog HOLD 70-75 untouched.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Bootstrap writes into real agents | A no-arg CLI run links skills into `~/.claude`, `~/.grok`, and similar homes | The smoke never bootstraps. The finally compares one-level names of those homes and fails the run if they change |
| npm edits the repo | npm walks up and rewrites `package.json` | The install uses `--prefix` on a dummy private package under `tmp/` |
| Cache lands in the real home | npm uses `~/.npm` | `npm_config_cache`, `HOME`, and `TMPDIR` are the scratch dir. The receipt records those paths |
| Network or time box | The package and its tree exceed the limit | Exit 2 with the timeout or the npm error. Do not retry without a bound |

- **Status**: STAY I0 reference (read 2026-11-07). Pin `fae0bb864a8b96c1d0ca6278a6b7062e62992a36`, MIT, package `2026.10.27-1`. The 2026-11-02 smoke PASS (version, help, `list --home`) stands. This lane did not bootstrap or distribute. Not an H2 install gate. See `eval/evq1107/skills-manager/REPORT.md`. No Feature GO.
