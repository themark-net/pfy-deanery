# HAR evq1107 (2026-11-07)

## Catalog tools on the same job

The job is an isolated worktree slot plus a deterministic verify receipt for the pfy build lane (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate failures. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. HAR is entry 107.

These cards already cover a piece of the job. Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` (agentgg, bumblebee, chiasmus, dspy, egm, hiroute, neatroots, osc, skill-up, skillspector, strata) do not. None of them is a worktree-slot verify tool.

| Tool | Stage | What it already covers | How HAR compares |
|------|-------|------------------------|------------------|
| git worktree plus `scripts/catalog_check.py` | in this repo | One worktree, the real check, remove. Measured below. | HAR ran the same check and added a tree receipt. The slot was slower. |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees. Ranking row: overlaps `/agent-loops`. | Covers fan-out. It does not write a tree-hash receipt. HAR is one repo CLI, not a board. |
| Emdash | I0 | Parallel agents GUI, one worktree each. Comparison only. | GUI slots, no headless verify receipt. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok. Docker sandbox. | Different isolation. HAR does not replace the cage. |
| eval-harness (pfy) | I1 | First-party structural ladder. `catalog_check` is part of it. | HAR called that check. The check time stayed about 43 ms. |
| harness2 | I1 | Local harness edit trial. Its own trial gain was 0. | Different job (gap H1). |
| gitai | I0 | CAS lands for many agents on one branch. | One shared branch. HAR's point is a separate slot. |
| TeaQL Agent Kit | I0 | Verification policy patterns. | Patterns, not a runner. |
| Elephant-Goldfish Model | I0 | Fresh-eyes spec read before a build lane. Ranking: indirect on gap B. | Does not launch a slot or time a check. |
| Chiasmus | I0 | Call-graph impact for a per-file read. Overlaps codebase-memory. | Review shape, not a worktree receipt. |

## Verdict

STAY I0. The tree receipt matched 2/2. Launch plus green verify plus teardown summed to 0.837s. A git worktree plus the same check finished in 0.222s. HAR does not beat what we have, and it does not move gap B.

## Pins

Install root: `~/.cache/pfy/tools/har/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `npm_config_cache`, and `TMPDIR` were directories under that root. No global install. The login home was not modified (stamps before and after matched). `~/.har` on the login home was absent before and after.

- Node v22.23.0, npm 11.12.1.
- npm `@osfactory/har@1.16.0`. Registry `gitHead` `874e9a1127e00d8d07524aca6b3c52cc62270111`, which starts with the entry commit `874e9a1127e0`.
- Tarball `https://registry.npmjs.org/@osfactory/har/-/har-1.16.0.tgz`, 829841 bytes. sha1 `830d1be850a7731d059c9f4838aedc424dfc6a06` matches `dist.shasum`. sha256 `634c992c0d510dc235cad9928104319633ad078c10dd6f06a026992e54c6203f`. Registry `dist.integrity` matches the sha512 of that file.
- Installed from that tarball with `--ignore-scripts`. `har --version` printed `1.16.0`. Prefix about 47 MB. npm cache about 35 MB. Nothing from the package was copied into the repo.
- License on the installed `package.json`: Apache-2.0.
- Every HAR command had `HAR_TELEMETRY=0` and `HAR_CONTROL_DISABLED=true`. `har telemetry off` wrote `enabled: false` under the cache home. Mission Control was not started. Docker was not used. `har hq`, `har mcp`, `har control`, `har env complete`, and the commit gate were not run.

## Commands

```bash
export HOME=$BASE/home
export XDG_CONFIG_HOME=$BASE/xdg/config
export XDG_CACHE_HOME=$BASE/xdg/cache
export XDG_DATA_HOME=$BASE/xdg/data
export npm_config_cache=$BASE/npm-cache
export TMPDIR=$BASE/tmp
export HAR_TELEMETRY=0
export HAR_CONTROL_DISABLED=true
npm view @osfactory/har@1.16.0 version dist.integrity dist.shasum dist.tarball gitHead --json
npm install --ignore-scripts --no-fund --no-audit --no-package-lock \
  --prefix "$BASE/prefix" "$BASE/meta/har.tgz"
```

`$BASE` is `~/.cache/pfy/tools/har`. The probe repo was a `git archive` of this worktree at `db42453` (tree `e7264dbe`), extracted into `$BASE/snap`, then committed there. A fresh `git add -A` skipped three force-added receipts that this repo gitignores (`pipelines/dogfood/local-bench-4/receipt-*.json`). The other 2491 blobs match `db42453`. `catalog_check` does not read those receipts.

```bash
har telemetry off
har env init --profile cli --no-cursor-rule --no-agents --commit-gate never
# then .har/stages.json verificationStages set to one command:
#   python3 scripts/catalog_check.py
# and commitGate.enabled set false
har env doctor
har env launch 1
har env verify 1 --full --json
# plant data/stages/zz-probe.json in the slot only, then verify again
har env teardown 1
```

The baseline, before init, was `git worktree add`, `python3 scripts/catalog_check.py`, `git worktree remove` on the same snapshot.

Init appended 24 lines to `AGENTS.md`, added two `.gitignore` lines (`.env.agent.*` and `ecosystem.agent.*.config.cjs`), and added 13 files under `.har/`. The scaffold commit is 15 files and 819 insertions, and it includes the stage edit. Doctor printed PASS. The slot work dir was under the cache `HOME` (`.../home/worktrees/main-1d76-har-agent-1-mscy`). Launch said no ecosystem manifest, so it did not install repo dependencies. The slot HEAD `1d7630a` is that throwaway scaffold commit. It is not product commit `db42453`. The pre-scaffold tree is the one whose 2491 blobs match.

## Numbers

| Step | Seconds | Result |
|------|--------:|--------|
| Baseline worktree add | 0.125 | |
| Baseline `catalog_check` | 0.045 | exit 0 |
| Baseline worktree remove | 0.05 | |
| Baseline total | 0.222 | one stopwatch around all three |
| `har telemetry off` | 0.11 | preference `enabled: false` |
| `har env init` | 0.302 | exit 0. One-time scaffold, not part of the slot sum |
| `har env launch 1` | 0.28 | exit 0. Slot HEAD equaled the throwaway scaffold HEAD |
| `har env verify 1 --full` green | 0.384 | exit 0. JSON `status: pass`, stage `catalog-check` 43 ms |
| `har env verify 1 --full` planted fail | 0.343 | exit 1. JSON `status: fail`, same stage 47 ms, only that stage |
| `har env teardown 1` | 0.173 | exit 0. Worktree gone. Branch `main-1d76-har-agent-1-mscy` kept |
| Launch + green verify + teardown | 0.837 | 0.28 + 0.384 + 0.173. 3.77 times the 0.222s baseline |

Agreement, checked against `git rev-parse HEAD^{tree}` and a separate temp-index `git write-tree` (read-tree HEAD, `git add -A`, write-tree). The in-probe helper had a path-format bug, so this confirmation ran after teardown by recreating the same dirty file on the kept branch. The hashes are the ones HAR wrote during the probe.

| Case | tree hash | head sha | match |
|------|-----------|----------|------:|
| Clean pass | `b794e2bc1e77f8bc2e5bec967512c01f472f80b9` | `1d7630a62680032acf279a811efa5f8fbdb78558` | 1/1. `changedFiles` empty. Equals `HEAD^{tree}`. |
| Planted fail | `b6534619bbca84825544b5c7ba4aa4f3bd56771a` | same head sha | 1/1. `changedFiles` is the planted `data/stages/zz-probe.json`. The clean pass record was kept under its own tree hash. |

The receipt has `headSha` and `treeHash`. It does not set `commitSha`. That field is filled later by the commit hook, which this run left off.

The snapshot checkout's tracked tree did not move. `git status --porcelain` was empty and HEAD stayed `1d7630a`. HAR still wrote two gitignored JSON files into the snapshot `.har/validations/` (a copy of the slot receipt). Login-home hook files were unchanged. The cache home did grow `.har/otel-hooks/otel_config.json` (265 bytes) with `exporter.enabled` false, `includeContent` false, and `allowRawContent` false. No `.cursor/hooks.json`, `.claude/settings.json`, or `.codex/hooks.json` appeared under the cache home.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. The measured hole was a worktree plus `catalog_check`. Git already does that in 0.222s. The 2/2 tree receipt is real, and it is not the 3 hour build timeout or the parked pregate failure.
2. Operator leverage: no. A slot still needs a redirected HOME, `HAR_TELEMETRY=0`, and a hand-edited `verificationStages` list. The scaffold defaults are typecheck, unit-tests, lint, and readiness, which this repo does not define. Gap B is unchanged.
3. Evidence: yes. The commands above ran on this host, offline after the tarball fetch.
4. Blast radius: yes, on the written gate. Apache-2.0, prefix about 47 MB, no model weights, no account, no primary runtime. The default with telemetry left on is a separate risk, recorded below. This run did not take that default.

Modularity, all four, for a cache probe only:

1. Local code was required. Docs say verify is tied to the exact tree. The run showed the key is the worktree tree hash, `commitSha` stays unset, and a disabled otel config file still appears with telemetry off.
2. The CLI entrypoint is one npm binary. Init does scaffold a `.har/` tree (13 files here). The unit of eval stayed the CLI.
3. It sat under `~/.cache/pfy/tools/har/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry. The product checkout was not initialized.

I2 asks for a probe that measurably helps. The receipt matched, and the slot was 3.77 times the git worktree baseline on the same check. That is not a help for gap B. I3 also needs a repeatable in-repo script and `self_pipeline` evidence. This lane adds neither, and it wires nothing into a gate.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Telemetry left at the default | A launch with the real HOME can write agent hook files. `readTelemetryPreference` treats a missing file as enabled. | `HAR_TELEMETRY=0` and `har telemetry off` before anything else, with HOME under the cache. This run did that. Login-home stamps matched. |
| Cache still gets an otel config | `.har/otel-hooks/otel_config.json` appeared even with telemetry off. The exporter is disabled. A smoke that treats that path as a hard failure would fail. | Read the file. Enabled false and raw content off is the disabled state. Do not treat the directory as a live hook. |
| `har env init` in a product checkout | This snapshot gained 24 lines in `AGENTS.md`, two gitignore lines, and a `.har/` tree. | Keep init on a throwaway snapshot. This lane did not init the worktree or Mark's checkout. |
| Scaffold stages do not match the repo | Verify fails on missing typecheck, lint, or readiness scripts. | Replace `verificationStages` with the real command before launch. Here that command was `python3 scripts/catalog_check.py`. Doctor passed after the edit. |
| Receipt is a tree, not a commit pin | `commitSha` was absent. A dirty slot keeps the same `headSha` and gets a new tree hash. | Accept a pass only when `changedFiles` is empty and `treeHash` equals `HEAD^{tree}`. This probe did that on the clean run. The planted file moved the tree and failed the check. |
| Ignored receipts land in the main `.har` | `recordValidation` copies the JSON into the harness root. Porcelain stays empty because the directory is gitignored. | Count the files. This run wrote 2. Tracked HEAD did not move. |
| Release churn | A later 1.x build renames the JSON or the flags. | Keep the 1.16.0 pin, the gitHead, and the tarball sha256. |

## Next gate

Stay I0. I2 needs a probe where the receipt beats a git worktree plus `catalog_check` on a real `./pfy build` run, or catches a miss that lane already drops. Wiring a gate is a separate ticket. This lane does not wire one.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A bot lane that wants a fresh worktree and a recorded verify before it keeps the branch. Nothing triggers HAR in this repo today. The scheduler already opens one worktree per slug and the driver already runs the quick checks.
2. What does it do, and which services does it read and write? It reads `.har/stages.json` and the slot worktree. It writes a worktree under `$HOME/worktrees` and validation JSON under `.har/validations` in the slot and in the main checkout. With telemetry left on it can also write agent hook files. This probe pointed HOME at the cache, set `HAR_TELEMETRY=0`, and set `HAR_CONTROL_DISABLED=true`. No hosted model and no account.
3. What does it trigger next? A person reads the receipt. It does not start pregate, CI, or a merge. `har env complete` would keep the branch after a matching full validation. This probe ran teardown instead, which also keeps the branch and drops the worktree.
4. Where does a human re-enter? Before any init of a product checkout, before any telemetry-on launch, before Mission Control or Docker, and before any gate uses the receipt. Mark's GO is required for those. This lane stops at the report.
5. What stops two runs doing the same work? One slot id owns one worktree. An occupied slot blocks a new launch until complete or teardown. This probe used slot 1 once. It does not take the local model lock. HAR does not call a model.

Numbers: `eval/evq1107/har/numbers.json`.
