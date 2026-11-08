# repository-harness evq1107

STAY I0. On a scratch copy of this repo the new map named 0 of 6 authority paths. AGENTS.md already names 5 of 6. A same-version update kept 2 of 2 local marker lines and changed 0 seeded files. That does not beat project-process, and it does not move the `./pfy build` timeout.

`STAY I0 new map names 0 of 6 authority paths, 2 of 2 local markers kept on a same-version update`

## Catalog overlap

Same job: put an agent-facing protocol in a repo and update it without clobbering local edits. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | Why it covers this job | How repository-harness compares |
| --- | --- | --- | --- |
| project-process bootstrap | I3 | Scaffolds DESIGN, ADR, TODO, open questions, and AGENTS into another repo. `init.sh`. | 6 of 8 template files are already in this repo. On the seeded scratch, `init.sh --dry-run` skipped 5 existing files and would write 3. Harness adopted AGENTS.md and created 25 files whose map names 0 of the 6 paths above. |
| Jamon Holmgren agentic setup | I1 | One workflow post. Tags include `#agents-md` and `#harness`. The card says the process kit already covers AGENTS.md. | Same conclusion from this probe. |
| Grok CLI bootstrap | I3 | Operator env and skills install. | Installs skills into the operator home. This binary writes a protocol into the target repo. |
| adr-tools | I1 | Optional CLI beside the ADR skill. | This repo's decisions stay in `docs/adr/`. Harness would add `docs/decisions/README.md`. |
| Harness Score | I0 | Offline grade of harness files. `eval/evq1107/harness-score/` stayed L1. | A scorer, not an installer. |
| harness2 | I1 | Local edit trial on the 48-case set. | A measured trial, not a repo protocol. |
| gstack | I1 | Role patterns already ported. The card says do not clone the repo. | Docs-only overlap with the router. |
| Festival | I1 | Filesystem plan and next-task. The 2026-11-07 probe did not close the build timeout. | Different command. Same gap result. |
| kanbots | I1 | Kanban that fans out coding CLIs into worktrees. | Lane fan-out. This binary does not start a build. |
| HarnessRouter | I0 | One API in front of many harnesses. `eval/evq1107/harnessrouter/` added 0 local engines. | A router, not a repo protocol. |
| Open Steps | I0 | Stop hook on a git fingerprint. The card says it does not see the 3h build timeout. | A hook, not a map or an updater. |
| JevAgentHarness | I1 | Per-step proxy between a fast model and a strong one. | A model proxy. This probe used no model. |

Sponsio (I2), Runx (I0), llm-router (I0), and tree-sitter-analyzer (I1) also landed on main during this lane. They check a tool call, seal a skill receipt, route a prompt, or map change impact. None of them install a repository protocol.

Gap B in the 2026-11-07 ranking is the unproven `./pfy build` path (3h timeout, parked recheck). No entry in 137 to 167 closes it. This probe does not run `./pfy build`.

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Release | `harness-v0.1.10` |
| Commit | `e765792b635b4d5e3e5fc0578f82f9ca5dea2681` |
| Asset | `harness-linux-x64` |
| Bytes | 1914920 |
| sha256 | `68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397` (matches the release `.sha256` file and the release API digest) |
| Version line | `harness 0.1.10` |
| License | MIT |
| Install path | `~/.cache/pfy/tools/repository-harness/bin/harness` |

No account and no key. The curl installer was not used. `--with-engineering-wisdom` was not used.

## Commands

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under `~/.cache/pfy/tools/repository-harness/`. The probe's tool subprocess used `PATH=/usr/bin:/bin` and a private home inside its temp dir.

```bash
CACHE=~/.cache/pfy/tools/repository-harness
mkdir -p "$CACHE/home" "$CACHE/xdg-cache" "$CACHE/xdg-config" "$CACHE/tmp" "$CACHE/bin"
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg-config" \
  XDG_CACHE_HOME="$CACHE/xdg-cache" TMPDIR="$CACHE/tmp"
curl -fsSL -o "$CACHE/bin/harness-linux-x64" \
  https://github.com/hoangnb24/repository-harness/releases/download/harness-v0.1.10/harness-linux-x64
curl -fsSL -o "$CACHE/bin/harness-linux-x64.sha256" \
  https://github.com/hoangnb24/repository-harness/releases/download/harness-v0.1.10/harness-linux-x64.sha256
# sha256sum matched 68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397
chmod +x "$CACHE/bin/harness-linux-x64"
ln -sfn harness-linux-x64 "$CACHE/bin/harness"
python3 eval/evq1107/repository-harness/probe.py \
  --repo "$PWD" \
  --harness "$CACHE/bin/harness" \
  --out eval/evq1107/repository-harness/results.json
```

No model lock. `ollama` was not called.

## Probe

The scratch was a temp git repo, not this worktree. It was seeded with this repo's `AGENTS.md`, the six authority files, and the four files under `docs/plans/`. `harness install` on that scratch adopted 1 file and created 25. Wall times: dry-run 0.001s, install 0.015s, update 1.35s, doctor 0.003s, status 0.002s. `init.sh --dry-run` on the same seed was 0.031s.

| Check | Number |
| --- | --- |
| Payload paths from `install --dry-run` | 26 |
| Payload paths that are already files here | 1 (`AGENTS.md`) |
| Seeded files whose bytes changed | 0 of 11 |
| Existing `docs/plans/` files whose bytes changed | 0 of 4 |
| Authority paths named by `docs/README.md` plus `docs/WORKFLOW.md` | 0 of 6 |
| Authority paths named by the adopted `AGENTS.md` | 5 of 6 |
| project-process template files already in this repo | 6 of 8 |
| Scratch `init.sh --dry-run` skip / write | 5 / 3 |
| Local marker lines kept by `update` | 2 of 2 |
| Update conflicts | 0 |
| Update versions | 0.1.10 to 0.1.10 |
| Doctor `healthy` | true |
| Status files flagged modified after the markers | 2 |

The five paths in `AGENTS.md` are `docs/DESIGN.md`, `docs/adr/README.md`, `docs/TODO.md`, `docs/OPEN_QUESTIONS.md`, and `docs/PENDING-HANDOFF.md`. The sixth, `docs/QUICKSTART-pfy-build.md`, is in neither the adopted router nor the new map.

The empty-install map links one file, `patterns/encoding-invariants.md`. It does not name the six paths. The dry-run left only `.git` in its empty directory.

Three new payload files land in a directory that already holds other files: `docs/README.md`, `docs/WORKFLOW.md`, and `docs/plans/README.md`. The plans file would sit beside the four real plan files. Those four were unchanged on the scratch. `docs/decisions/README.md` would be a new directory beside `docs/adr/`.

`update` applied and kept both marker lines (`AGENTS.md` and `docs/WORKFLOW.md`). `from_version` and `to_version` were both 0.1.10, so this run did not stage an overlapping edit. Conflict staging stays unmeasured.

The two missing process-kit template files are `docs/adr/0001-process-docs-bootstrap.md` and `docs/open-questions/README.md`. This repo already has its own ADR tree and open-questions pages.

## Gates

Value (need 3 of 4 for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. The router and the process kit already name the authority files. The new map named 0 of 6. |
| Operator leverage | No. A 0.015s install does not change the 3h `./pfy build` timeout. |
| Evidence | Yes. The commands above ran. `results.json` holds the counts. |
| Blast radius | Acceptable for the cache binary. MIT. 1914920 bytes. No daemon and no weights. An install into this repo would still add a second decisions directory and a README inside `docs/plans/`. |

2 of 4. Not I3.

Modularity (all 4, required for I2 local code and for I3): the binary had to be run to see that install adopts an existing file and that a same-version update keeps a local line. The surface is one binary with `install`, `update`, `status`, and `doctor`. It sits in the cache. Deleting that copy leaves the pin and this entry. 4 of 4.

I2 also needs ambiguous potential, a copy under 50 MB, and a measured gain on the gap. The binary is under 50 MB. Potential is low. The measured gain on gap B is 0 of 6 authority paths. I2 is the wrong shelf.

`self_pipeline` is unset. The card is below I3, and the uses text is not a CI, testing, or review role. No TOOLS.md row. No `data/tools.json` row. `python3 scripts/catalog_check.py` passed with this card as stage-only.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Layout collision | `docs/plans/README.md` lands beside real plan files, and `docs/decisions/` sits beside `docs/adr/`. | Do not install into this repo. The scratch left 4 of 4 plan files unchanged. |
| Same-version update | 2 of 2 markers survived because upstream was still 0.1.10. An overlapping change was not staged. | Treat conflict staging as unmeasured. Re-probe only on a pin that changes a line this repo already edited. |
| Silent rewrite | A binary could report adopt and still change `AGENTS.md`. | The probe compares sha256. `tests/test_repository_harness_probe.py` fails when a stub rewrites the file or drops the marker, and passes when the stub keeps both. |
| Generic `harness` on PATH | Another binary answers. | Call the cache path. The probe takes `--harness`. |
| curl pipe bash | The upstream installer can pull a different build. | This lane used the pinned asset and the published sha256. |

## Next gate

Stay I0. Re-open only if a newer pin changes a line this repo already edited and the merge keeps that line. Do not install into this repo. No gate wiring. Not a Feature GO.

## Five questions, if this tool were on the pipeline

It is not on the pipeline.

1. What triggers it? A person runs `harness install` in a throwaway copy of a product repo, then `harness update` when a new pin is chosen. Not this scheduler, and not `./pfy build`.
2. What does it do, and which services does it read and write? It reads the target worktree and writes the payload paths (`AGENTS.md` is adopted when it already exists). The binary stays under `~/.cache/pfy/tools/repository-harness/`. No hosted model and no account.
3. What does it trigger next? Nothing in `./pfy`. A human reads `doctor` and `status` before any copy is kept.
4. Where does a human re-enter? Before install into a real product repo, and on any update whose `conflicts` list is non-empty. This probe's conflict list was empty because the version did not change.
5. What stops two runs doing the same work? One scratch directory per trial. Two installs in one checkout both write `.harness-core/`. There is no pfy lock because it is not wired in.
