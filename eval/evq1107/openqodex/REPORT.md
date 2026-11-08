# OpenQodex evq1107

STAY I1. Scanners hit 2 of 3 planted changed lines and put 0 candidates on lines the diff did not touch. Default finalize still exits 0 when the findings are major. That does not beat the review skill. Potential is low, so I2 does not apply. The scanner install is also 524MB of binaries, which the I2 size gate does not allow.

`STAY I1 2 of 3 planted lines hit, 0 off-diff leaks, default finalize exits 0 on major findings`

## Catalog overlap

Same job: pre-push review of a diff. Scanners propose hits on changed lines, then something has to answer each hit. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch-1 verdicts under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | Why it covers this job | How OpenQodex compares |
| --- | --- | --- | --- |
| agentgg | I0 | Local SAST on a diff. Features include a semgrep prefilter. `eval/ev1107/agentgg/` caught planted `shell=True` and missed a planted Python secret written to a log. Needs a local model. | Same shell hit and the same log miss, plus a hardcoded GitHub token, with no model. Warm scan 4.461s. It does not beat that probe on the log line, and this lane did not re-run agentgg's historical diffs. |
| mattpocock/skills | I1 | Planning and review skills already on the path. Tag `#review`. Feature `review`. | The skill is the reviewer. OpenQodex does not write the review. It lists scanner candidates and rejects a finding whose source is not in the scan. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | A runtime guard. It does not scan a diff. |
| destructive_command_guard | I1 | Blocks destructive shell commands. The card says it overlaps write-guard. | A shell guard, not changed-line findings. |
| Bumblebee | I2 | Advisory read-only check for package lockfiles and MCP configs. | Different files. The 2026-10-06 ranking already points it at supply chain, not at code review. |
| SkillSpector | I3 | Static scan of a skill directory before copy. | Different input. It does not take a git diff. |
| Chiasmus | I1 | Call-graph impact for per-file review. The 2026-11-07 probe stayed I1 (impact agrees with test_select on 3/10 commits). | This probe passed `--no-graph`. No impact list was produced. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build starts. STAY I1. | It reads a ticket. These scanners read changed lines. |
| CodeGuard (entry 126) | I0, no card | Secure-coding rules and a SARIF reviewer agent. Not installed on nimo. | Rules text. This lane did not run it. |

Gap B in the 2026-11-07 ranking is the unproven `./pfy build` path (3h timeout, parked recheck). This probe does not touch that timeout. Batch-1 skill-up, SkillSpector, Strata, HiRoute, DSPy, and Bumblebee close other gaps.

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| npm | `openqodex@0.12.0` |
| dist.shasum | `f40517b83d612a59e566af8845cc84f85e973578` (sha1 of the tarball, rechecked with `npm pack`) |
| integrity | `sha512-rY6T5qdsl2wN3MUR1glOqRt2kuAsD8lFURI5J9mHI+UcDYDF6/xUhqnHER6ZwCUeXmlWiPYR/CPCXi/j1NLgAA==` |
| tarball | `https://registry.npmjs.org/openqodex/-/openqodex-0.12.0.tgz` (3.0 MB packed, 15.3 MB unpacked) |
| git tag | `v0.12.0` at `9c4d516a15954ba3ed648fe1177038c92fb8f884`. `packages/cli/package.json` on that tag is version 0.12.0. npm `gitHead` is null. The runnable pin is the tarball. |
| Node | v22.23.0 |
| license | Apache-2.0 |
| semgrep | 1.94.0 (uv lock in the package). `semgrep --version` printed 1.94.0. |
| gitleaks | 8.21.2. Archive sha256 `5bc41815076e6ed6ef8fbecc9d9b75bcae31f39029ceb55da08086315316e3ba` matches `toolchain.json`. Installed binary sha256 `50b742abd7daad8bbddb6301f3017efb680632d9a5b3b4d8f137b3aac250e359` matches the file inside that archive. |
| ruff | 0.8.4. Archive sha256 `c4e6591ae1bb4f15c09c9022b7bfc57e1c3a567acdc9cd76021cd1304b5868c3` matches `toolchain.json`. Installed binary sha256 `ce7b99797145b43d23b732d6050fbbd62e4f9059663cf24218810598753dfb90` matches the file inside that archive. |
| bandit | 1.9.4 (`bandit --version`). |
| install | prefix `du -sb` 15332053 bytes. Scanner home `du -sb` 523828358 bytes (about 524MB). ZFS `du -sh` on that home was 270M. |

`init` was not run. No account and no key.

## Commands

Install, checksums, and both probes used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `OPENQODEX_HOME` under `~/.cache/pfy/tools/openqodex/`. `PATH` for the tool was `/usr/bin:/bin`, so `claude` and `codex` on the real `PATH` were not visible. `OPENQODEX_AUTO_UPDATE=0`.

```bash
CACHE=~/.cache/pfy/tools/openqodex
mkdir -p "$CACHE/home" "$CACHE/xdg-cache" "$CACHE/xdg-config" "$CACHE/tmp" "$CACHE/npm-cache" "$CACHE/prefix" "$CACHE/oqhome"
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg-config" \
  XDG_CACHE_HOME="$CACHE/xdg-cache" npm_config_cache="$CACHE/npm-cache" \
  TMPDIR="$CACHE/tmp" OPENQODEX_HOME="$CACHE/oqhome" OPENQODEX_AUTO_UPDATE=0
export PATH=/usr/bin:/bin
node /home/mark/.npm-global/lib/node_modules/npm/bin/npm-cli.js view openqodex@0.12.0 version dist.integrity dist.shasum --json
node /home/mark/.npm-global/lib/node_modules/npm/bin/npm-cli.js install \
  --prefix "$CACHE/prefix" --ignore-scripts --no-audit --no-fund openqodex@0.12.0
python3 eval/evq1107/openqodex/probe.py "$PWD" > eval/evq1107/openqodex/results.json
```

The scored `results.json` is the second probe (tools already installed). `review --agent` took 4.461s and exited 0. The block-threshold rerun took 4.393s. `scan --block-on-severity major` took 4.251s. Finalize calls were 0.125s to 0.140s. No model lock. `ollama` was not called.

The first probe, same command, also installed the four scanners (`installing semgrep 1.94.0`, `gitleaks 8.21.2`, `ruff 0.8.4`, `bandit 1.9.4` on stderr) in 13.234s. Its planted token was `ghp_` plus 36 copies of one letter. Gitleaks reported no candidate. That plant is not what `probe.py` writes now. The scored plant is `ghp_` plus 36 hex characters from a fixed sha256, and it is redacted in `results.json`.

`--offline` was not passed. The package docs say that flag skips semgrep and skips scanner downloads. Semgrep's own `--version` printed an upgrade notice, so that process can reach the network. The review itself used the cached binaries.

## Probe

Throwaway git repo under the cache, not this worktree. Base commit, then one commit on top. `review --agent --base <base> --only semgrep,gitleaks,bandit,ruff --no-graph`. The real file is `scripts/sync_todo_status.py` from this repo with one comment word added. The other files are small plants.

| Plant | On the diff | Candidates on that line |
| --- | --- | --- |
| `subprocess.call(cmd, shell=True)` in `handlers/runner.py` | yes | semgrep `subprocess-shell-true` and bandit `B602`, both major |
| `print` of a `session_token` parameter in `handlers/session.py` | yes | none |
| hardcoded `ghp_` token in `handlers/tokenstore.py` | yes | gitleaks `github-pat`, major |
| `shell=True` in `handlers/legacy.py` | no, file not in the diff | none |
| comment-only edit of `scripts/sync_todo_status.py` | yes, one comment line | none |

3 candidates, 3 on a changed line, 0 off the diff. Planted hits 2 of 3. The log line is the miss.

Finalize writes a findings file and checks it with no model. The "good" file raises the shell candidate and drops the other two, including the real token hit, so the checker is what is measured there, not a judgment that the token is safe.

| Check | Exit | Receipt |
| --- | ---: | --- |
| every candidate answered, one major raised, no block threshold | 0 | Passed with warnings: 1 finding (1 major) |
| nothing answered, no block threshold | 0 | Passed with warnings: 3 findings (3 major) |
| source `made-up` | 2 | cites source "made-up", which is neither a scanner token in this scan nor a lens |
| same answers, config `review.block_on_severity: major` | 1 | Blocked: 1 finding at or above major (1 major) |
| nothing answered, same block config | 1 | Blocked: 3 findings at or above major (3 major) |
| `scan --block-on-severity major` (no reviewer) | 1 | Blocked: 3 findings at or above major (3 major) |

The brief's threshold line with no config is `warn only, nothing blocks the push`. Unanswered candidates are counted as findings. They do not make finalize exit non-zero until the block threshold is set. `review --agent` also created `.openqodex/config.yaml` and `.openqodex/custom-instructions.md` in the throwaway repo.

Directory mtimes of `~/.claude`, `~/.codex`, `~/.cursor`, and `~/.openqodex` did not change. `~/.openqodex` is still absent. `~/.grok` changed during the run because this session writes there. The probe did not read it.

## Gates

Value (need 3 of 4 for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. The hits are stock semgrep, bandit, and gitleaks rules. agentgg already puts semgrep on a diff. The review skill is the review. The new piece is the source check, and it is a field compare. |
| Operator leverage | No for gap B. A 4.5s candidate list does not move the 3h build timeout. It can sit beside a hand review only as advisory text. |
| Evidence | Yes. The commands above ran. |
| Blast radius | Acceptable only as a cache probe. Apache-2.0. The package is 15.3MB. The scanner home is 524MB, with no model weights. `init` would write agent homes and was not run. A plain review writes `.openqodex/` into the repo it is pointed at. |

2 of 4. Not I3.

Modularity (all 4, required for I2 local code and for I3): the CLI flags are not knowable from the README alone (the warn-only exit is the example). The unit is one npm package. It sits in the cache and is removable without stranding the pin. The npm tree is 15.3MB, under the 50MB working-tree bar. I2 also needs ambiguous potential and no large binaries. Potential is low, and the scanner install is 524MB, so I2 is the wrong shelf.

`self_pipeline` is `not_applicable`. Nothing in this lane is on the pfy pipeline.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Warn-only default | A major finding still exits 0. This run printed "Passed with warnings" for one raised major and for three unanswered majors. | Set `review.block_on_severity`, or read the receipt. With `major` set, both of those finalizes exited 1. This lane did not wire that. |
| Unanswered candidates | Leaving `findings` and `dropped` empty still exits 0, and the candidates count as findings. | The same threshold. Do not treat exit 0 as "a reviewer answered". |
| Repo writes | `.openqodex/config.yaml` and `custom-instructions.md` appeared in the scanned repo. | Throwaway repo only. Do not commit them. `init` stays off. |
| Scanner download | First run needs network. Home is about 524MB. `--offline` skips semgrep. | Keep `OPENQODEX_HOME` in the cache. Record a skip if the download fails. |
| Low-entropy token | `ghp_` plus one repeated character was not a candidate. | The scored plant uses mixed hex. A gate still cannot assume every token shape is found. The log-line plant was missed either way. |
| Agent homes | `init` writes `~/.claude`, `~/.codex`, and `~/.cursor`. | Do not run `init`. This probe's `PATH` hid `claude` and `codex`. Those directories' mtimes did not change. |

## Next gate

Stay I1. I2 needs ambiguous potential and a lightweight copy with no large binaries. This probe's potential is low, and the scanner binaries are 524MB in the cache. I3 needs a repeatable script, `self_pipeline` evidence, and Tester and Reviewer, plus a probe that catches a defect on a real pfy diff which the review skill misses. Not this lane.

## Five questions, if this tool were on the pipeline

It is not on the pipeline. This is how it would run if someone picked it up later.

1. What triggers it? A person, or the Reviewer bot, runs `review --agent` on a throwaway worktree of one diff. No hook and no CI job.
2. What does it do, and which services does it read and write? It reads the git diff, runs the pinned local scanners, and writes a brief plus a receipt. Scanner binaries stay under `~/.cache/pfy/tools/openqodex/`. The scanned repo gets a `.openqodex/` directory. No hosted model and no account.
3. What does it trigger next? The reviewer writes `agent-findings.json` and runs `review --finalize`. Nothing in `./pfy` starts from that receipt today.
4. Where does a human re-enter? On the receipt. Exit 0 with "Passed with warnings" is not a stop. A block needs `review.block_on_severity` and a person reading the finding lines.
5. What stops two runs doing the same work? One throwaway worktree per diff. Two reviews in one checkout both write `.openqodex/`. There is no pfy lock because it is not wired in.
