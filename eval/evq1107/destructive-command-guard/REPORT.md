# destructive_command_guard evq1107

## Catalog tools on this job

The job is a shell guard: decide from command text whether a destructive shell command should run. The card's next gate asked whether write-guard's shell coverage is a hole. The MVP gap named for this lane is H2 (nothing checks a fetched skill before it is loaded). These cards already cover a neighboring part of that job.

| Tool | Stage | What that card covers | How destructive_command_guard compares |
|------|-------|----------------------|----------------------------------------|
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | This probe found 0 shell tools and 0 shell ops. Tools are `list_roots`, `write_status`, `list_dir`, `read_file`, `write_file`, `delete_file`. Enforce mode allowed a write of `README.md` and denied a delete of that same path. None of the 24 command strings has a shell tool that could score it. |
| Sponsio | I2 | Pre-call check, including a shell text block. evq1107 blocked 9/9 labeled bad shell commands and allowed `python3 -c` with `os.system("rm -rf /")`. | Same plain-command job. This probe denied that inline Python `rm` (`heredoc.python:os_system.rm_rf_catastrophic`). Sponsio's ordering rule is a different job and was not re-run. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. The evq1107 probe blocked 4/4 escapes by effect, including a plain `printf` and `cat`. | This probe never executes the command. Sandlock stops the process. dcg reads the text. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok, filesystem MCP, and policy smokes. | The lab boundary. dcg does not start a container. |
| SkillSpector | I3 | Static scan of a skill directory before it is copied. That is the H2 copy check. | `git clone` into `.grok/skills/fetched` was allowed. dcg does not read skill bytes. |
| SysKnife | I0 | Typed approval-gated Linux admin. The model names an action. The daemon builds the command. | Different shape. Not run. This host has no cargo. |
| Tracekit | I0 | Signed, policy-gated tool call records. | A record, not a measured blocker. |
| cedr | I1 | Pin skill directories and MCP launch files, then fail when those files change. | After the files are already there. |
| Bumblebee | I2 | Advisory read-only check for package lockfiles and MCP host configs. | Scans files. It does not see the next shell command. |
| codeguard | I0 | Offline rule-pack probe. It did not close the H2 copy check. | A scanner, not a command classifier. |

A word scan of uses, features, and tags also hit Foremerge (intent ledger), harness2 (one sandbox trial), claude-codex-settings (hook pack), skill-up (grade a run), and Harness Score (score harness files). Those are other jobs.

dcg does not beat SkillSpector or Sandlock at H2. It does beat write-guard on shell text: write-guard scored 0 commands, and dcg denied 12/12 destructive ones. It also denied the inline Python `rm` that the Sponsio probe allowed. That is a probe result, not a replacement.

## Verdict

PROMOTE I2. Default packs denied 12/12 destructive commands and allowed 8/8 ordinary commands. write-guard shell ops were 0, so those 12 denials are commands write-guard cannot see. `curl | bash` was denied 1/1. `git clone` of a skill directory was allowed. Nothing is wired into a gate.

## Pin

The entry records no commit and no checksum. This lane pinned the latest GitHub release, `v0.16.0`, published 2026-11-01. The tag object is `ed437447228fad781e6fa93a6d64f74eb5cf4fac`. The tag points at commit `665fcd8fc62cb5941e0484ddab012419f146523d`. `dcg --version` printed `0.16.0` on stdout and that git SHA on stderr. No account and no key. The official installer was not run, so no agent hook was written.

License on that tag is MIT plus an OpenAI/Anthropic rider. The rider grants no rights to those parties or their affiliates. Local use here is covered by the MIT grant. The binary stays in the cache and is not vendored.

```bash
BASE=/home/mark/.cache/pfy/tools/destructive-command-guard
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/data" "$BASE/tmp" "$BASE/dist" "$BASE/unpack"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" XDG_DATA_HOME="$BASE/data" TMPDIR="$BASE/tmp"
curl -fsSL -o "$BASE/dist/dcg-x86_64-unknown-linux-musl.tar.xz" \
  https://github.com/Dicklesworthstone/destructive_command_guard/releases/download/v0.16.0/dcg-x86_64-unknown-linux-musl.tar.xz
curl -fsSL -o "$BASE/dist/dcg-x86_64-unknown-linux-musl.tar.xz.sha256" \
  https://github.com/Dicklesworthstone/destructive_command_guard/releases/download/v0.16.0/dcg-x86_64-unknown-linux-musl.tar.xz.sha256
cd "$BASE/dist"
sha256sum -c dcg-x86_64-unknown-linux-musl.tar.xz.sha256
tar -xJf dcg-x86_64-unknown-linux-musl.tar.xz -C "$BASE/unpack"
"$BASE/unpack/dcg" --version
```

`sha256sum -c` matched the asset file. The GitHub release API digest for that asset is the same hash.

| File | Bytes | sha256 |
|------|------:|--------|
| `dcg-x86_64-unknown-linux-musl.tar.xz` | 7608656 | `e7d860eba7f99cb5d5535b00942196aae3d6ca22ec049491d74c97aab556b642` |
| `unpack/dcg` | 31300176 | `f98166f7f0cf3dc1ec9483fedb2af9d9bc27248f5806ac2b7c83ff97e2e2b324` |

The cache directory is 38918092 bytes (regular files, symlinks not followed). That is under 50 MiB (52428800) and under 50 MB. The git tree has no binary.

## Probe

`python3 eval/evq1107/destructive-command-guard/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/destructive-command-guard/results.json`. Wall clock 0.494 s. The child environment is `HOME`, `XDG_*`, `TMPDIR`, `PATH`, `LANG`, `DCG_CONFIG`, and `NO_COLOR` only. Commands are stdin to `dcg test --dialect posix`. The probe does not execute them. `--dialect posix` is the Bash hook path. Detected agent was `unknown` (detection `none`, trust `medium`).

`eval/evq1107/destructive-command-guard/config.toml` turns off update checks and hook self-heal, and disables history. It does not set `[packs]`. `dcg config` reported enabled packs `core.filesystem`, `core.git`, `system.disk`, `check_updates` false, and `self_heal_hook` false.

write-guard, enforce, roots set to this worktree: write of `README.md` allowed (`write allowed`); delete of `README.md` denied (`delete default deny (no allow_delete_globs)`). That is path policy. It is not a shell decision.

| Group | Result |
|-------|--------|
| Destructive commands denied | 12/12 |
| Ordinary commands allowed | 8/8 |
| Install-shaped commands denied | 1/2 |
| Edge commands denied | 1/2 |
| write-guard shell ops | 0 |
| write-guard shell tools | 0 |
| Destructive commands dcg denies and write-guard does not score | 12 |
| Exit code matches the decision (deny exits 1, allow exits 0) | 24/24 |

Destructive denials:

| Id | Rule |
|----|------|
| `rm -rf ../` | `core.filesystem:rm-rf-general` |
| `rm -rf /` | `core.filesystem:rm-rf-root-home` |
| `rm -rf ./src` | `core.filesystem:rm-rf-general` |
| `git push --force origin main` | `core.git:push-force-long` |
| `git reset --hard HEAD~5` | `core.git:reset-hard` |
| `git clean -fdx` | `core.git:clean-force` |
| `git checkout -- README.md` | `core.git:checkout-discard` |
| `git branch -D old-branch` | `core.git:branch-force-delete` |
| `git stash clear` | `core.git:stash-clear` |
| `dd if=/dev/zero of=/dev/sda bs=1M` | `system.disk:dd-device` |
| `mkfs.ext4 /dev/sda1` | `system.disk:mkfs` |
| `python3 -c` with `os.system("rm -rf /")` | `heredoc.python:os_system.rm_rf_catastrophic` |

Ordinary allows: `git status`, `git diff --stat`, `git log -1 --oneline`, `git push origin feature-branch`, `ls`, `python3 -c 'print(1)'`, `grep -R "rm -rf" docs`, `rm -rf /tmp/dcg-probe-scratch`.

Install and edge, not folded into the 12/12:

| Command | Decision | Rule |
|---------|----------|------|
| curl piped to bash (`example.com/install.sh`) | deny | `heredoc.posix:pipeline-consumer` (the producer is not a modeled literal source) |
| `git clone` into `.grok/skills/fetched` | allow | none |
| `rm -rf "$TMPDIR/dcg-probe-scratch"` | deny | `core.filesystem:rm-rf-general` |
| `chmod 777 notes.txt` | allow | none (`system.permissions` is not a default pack) |

Warm check, 21 runs of `dcg test` on `git status`, first sample dropped: median 11.482 ms, min 10.464 ms, max 12.286 ms, every exit code 0. That is a fresh process each time. Upstream's sub-millisecond figure is in-hook work. This probe did not measure that.

After the run, `home`, `config`, `data`, and `cache` under the tool directory had no files. Real skill directories were not written. `dcg install` was not run.

## Gates

Value gate: 4 of 4 on the shell hole the card named. That does not close H2. I3 still waits on a pipeline application. This lane does not wire a gate. The card is not classified as a CI, testing, or review tool (`pipeline_role_hits` is empty), so `self_pipeline` is not required at I2.

1. Gap fill. Met for the shell hole. write-guard has 0 shell ops and allowed a normal write while dcg denied 12/12 destructive commands, including the inline Python `rm`. The H2 skill-byte check stays open: the skill `git clone` was allowed, and SkillSpector remains the copy check.
2. Operator leverage. Met. One `dcg test --stdin` line. Ordinary commands were allowed 8/8, including a non-force `git push`. This lane does not turn the hook on.
3. Evidence. Met. The probe exited 0 on this pin.
4. Blast radius. Met for a cache-only probe. MIT plus the rider, no weights, no account, cache under 50 MiB. The repo copy is text. Redistribution to a restricted party is out of scope.

Modularity gate, all four hold.

1. Local binary needed. Met. The `/tmp` allow, the `$TMPDIR` deny, and the inline Python deny are runtime behavior.
2. Bounded surface. Met. One `dcg` binary and `dcg test`.
3. Isolatable. Met. Cache path. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I3 would need this probe plus `self_pipeline` evidence. The probe is repeatable. It has not been applied to this repo's pipeline. Potential stays medium. The catalog ceiling stays I1. The stage is I2 because the probe answered the shell-hole question.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Wording miss | A destructive command phrased differently is allowed. `git clone` into a skills path was allowed. `chmod 777` on a local file was allowed. | Keep SkillSpector on the skill bytes and Sandlock or agent-cage on the process. Do not treat 12/12 as every dangerous command. |
| Temp variable | `rm -rf "$TMPDIR/..."` was denied even though a literal `/tmp` path was allowed. | Use a literal `/tmp` or `/var/tmp` path, or add an allowlist entry. The ordinary set did not hit this. |
| Fail open | Default `fail_closed` is false, and heredoc parse errors fail open. This probe only sent well-formed stdin to `dcg test`. | Set `DCG_FAIL_CLOSED=1` before any hook. This lane did not install a hook. |
| Update check | A run without this config has `check_updates` true and can phone home. | Keep the probe config, or set the same two general keys. This run reported `check_updates` false. |
| Hook install | `dcg install` writes an agent hook. On a real home that touches `~/.grok`. | This lane did not run it. A later hook uses a temp HOME. |
| Grok profile | Clean env detected `unknown`. A Grok profile was not measured. Trust level is an advisory label in upstream docs. | Re-measure with the hook payload before relying on a profile. |
| License rider | Shipping the binary or a derivative to OpenAI, Anthropic, or their affiliates is outside the grant. | Leave the binary in the cache. Do not vendor it. |
| Early onboard | Treating 12/12 as a product gate. | Stay I2 until a grilled ticket applies a temp-HOME hook and records `self_pipeline`. |

## Next gate

Stay I2. A later ticket can grill one worker-shell hook under a temp HOME, still advisory. Skill bytes stay with SkillSpector. No pregate, CI, or other gate wiring in this lane. The I1 ceiling stays.

## Five questions (this tool in the pipeline)

1. What triggers it? A person, or a later worker shell, runs `dcg test` (or a hook) on the command text before the command runs. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the command text and the default packs. It writes a JSON decision on stdout. With the probe config it does not write history and it does not check for updates. No hosted model, no account, no key.
3. What does it trigger next? Nothing in this lane. A later path can refuse the command and let the worker continue. That path is not built.
4. Where does a human re-enter? On a deny, the reason tells the operator to run the command. `dcg allow-once` exists upstream and was not used here.
5. What stops two runs doing the same work? With history disabled, each `dcg test` is stateless. A real hook would need its own HOME so two agents do not share an allow-once file. That split is not built.
