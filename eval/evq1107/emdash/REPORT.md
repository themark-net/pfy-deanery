# Emdash evq1107

Verdict: STAY I0 reference: desktop comparison only, and it does not close gap B.

## What it is

Emdash (generalaction/emdash) is an Electron desktop app. The desktop coordinates. A workspace host on this machine, or over SSH, executes. Each task gets its own git worktree. The README names Claude Code, Codex, OpenCode, Amp, Cursor, Devin, Qwen Code, Droid, and GitHub Copilot. `agents/integrations/providers.md` at the pin lists 37 providers, including grok. Shipped hooks install into user-global provider config, and the Grok root is `~/.grok`. License is Apache-2.0 (`LICENSE.md`, and `@emdash/emdash-desktop` in its package.json).

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `ab766e8fbb436584dcf0f299740e79d559b8ed31` |
| Tag | `v1.2.10` matches the pin. `v1.2.10-canary.102` is `85dfa910ac92e69b09ed5df70ea60ee625a83f07` |
| Commit | 2026-10-30 12:22:18 +0100, Merge pull request #3389 from generalaction/v1.2.10 |
| Packages | `@emdash/emdash-desktop` 1.2.10. `@emdash/workspace-server` 0.1.13 |
| Node | engines `>=24.0.0`, `devEngines.runtime` 24.14.0 with `onFail: download`. This host is Node v22.23.0 |
| Fetch | In `~/.cache/pfy/tools/emdash/src`: `git init`, `git remote add origin https://github.com/generalaction/emdash.git`, `git fetch --depth 1 --filter=blob:none origin ab766e8fbb436584dcf0f299740e79d559b8ed31`, `git checkout --detach FETCH_HEAD`. Wall time 5s. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null` |
| Bytes | clone 51548638, worktree 38852258, `.git` 12696380 |
| AppImage | not downloaded. Entry pin size 233276140 |
| Ran | no upstream script, no installer, no package install |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| The host inventory is authoritative. A failed scan writes nothing. A deleted worktree is marked missing. A hand-made worktree is adopted. | `scripts/pfy_build_cloud.py` | A failed `git worktree add` is `worktree-failed`. The caller checkout stays put. `docs/plans/MVP-PARALLEL-1031.md` |
| One writer owns workspace rows. Worktree create and delete on one repo take one lock. | `scripts/pfy_build_cloud.py` | One evq worktree and one stage card per slug. `pfylib/stage_registry.py` writes catalog cards. |
| A conversation id outlives the provider process. Resume starts a new session of the same conversation. | `docs/ops/cage-session-resumption-design.md` | Cage resumption is per repo. Provider session ids stay outside the catalog. |
| Teardown is non-fatal and time-boxed, so a script cannot pin a workspace. Deletion intent can outlive a disconnect (upstream ADR 0006). | `scripts/pfy_build_cloud.py` | The runner removes its worktree in-process. `scripts/pregate.sh` adds a detached worktree for the run. |

Leave the Electron shell, the SSH keychain, and hook installs alone. ADR-0002 keeps Grok CLI as the operator surface.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path (3 h timeout). Entry 158 is on the hold-or-comparison list. No entry from 137 to 167 closes gap B.

Same job, already covered: kanbots I1 (tags `#worktree` `#multi-agent` `#ui`; the probe did not move the timeout), HAR I0 (per-slot worktree plus a tree receipt), kander I1 (branch overlap check; the probe started no agent), Foremerge I1 (pre-edit ledger for parallel agents on one machine), pi-harness I0 (desktop control plane with worktrees, also reference-only), gitai I1 (many agents on one branch), multica I1 (multi-agent board; our orchestrator stays pfy), squadra I1 (manual seats on one task), bugpatrol I1 (QA patrol, with a fixer worktree as one piece). Isolation stays agent-cage I3. continue-dev I1 is the other IDE client held as reference.

## Gates

Value (3 of 4 for I3): gap fill no. Operator leverage no (no install; hooks would write `~/.grok`; source Node is 24 and this host is 22). Evidence no (entry 158 smoke exits 2 because the GUI was not launched; this lane only read docs). Blast radius no: license is Apache-2.0 and the tree has no multi-GB weights, but hook installs write the operator home and the desktop plus workspace-server would be a second runtime. Score 0 of 4.

Modularity for I2, all 4 required: isolatable and reversible pass (cache copy; the pin stays if the copy is deleted). Docs were enough, and the unit is a monorepo (desktop, workspace-server, core, plugins, wire), so 2 of 4. The shallow clone is 51548638 bytes and the worktree is 38852258 (under 50 MB). Potential is low, so the I2 fork does not apply.

No `self_pipeline` field. No gate wiring. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Hook install | A trial writes `~/.grok` | Do not install. The cache checkout stays detached. |
| AppImage fetch | 233276140 bytes land on disk | This lane read git docs only. |
| Primary-surface swap | The Electron app replaces `./pfy` | ADR-0002 stays. Stay I0. |
| Pin drift | The canary tag is treated as v1.2.10 | Pin `ab766e8`. The release tag is that SHA. |
| Gap B false pass | A GUI is counted as a shorter build | The timeout stays a pfy bug. |

## Next gate

Stay I0 reference. Re-open only if a later ticket asks for a desktop trial outside this repo, on a machine where writing agent home configs is allowed. Not a Feature GO.

## Pipeline questions

This lane does not put Emdash on a pipeline. The scheduler started the lane. It writes the card, the entry Status line, and this directory.

1. Trigger, if adopted later: a person opens the desktop app. The evq scheduler does not start it.
2. It would read local or SSH repos and write worktrees plus a local SQLite mirror. Provider CLIs would send prompts to their own accounts. This lane called no model and used no account.
3. Next: nothing in pfy. Diff and merge stay in the app.
4. A human re-enters before any install, any hook write, or any I3 claim.
5. One worktree per slug already keeps this card private. Two desktops must not share one agent home.
