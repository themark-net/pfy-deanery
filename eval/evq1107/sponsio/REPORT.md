# Sponsio evq1107

## Catalog tools on this job

The job is an install gate for a fetched skill: block the unsafe tool call, and do not load the skill until something has checked it. These cards already cover a neighboring part of that job.

| Tool | Stage | What that card covers | How sponsio compares |
|------|-------|----------------------|----------------------|
| SkillSpector | I3 | Static scan of a skill directory before it is copied. | Reads skill bytes. This probe allowed 2/2 absolute writes of a SKILL.md inside the repo. Sponsio did not read the body. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. | Stops the process. This probe never executes the command. `python3 -c` with `os.system("rm -rf /")` was allowed. |
| destructive_command_guard | I1 | Blocks destructive shell commands. Overlaps write-guard. | Same job as the shell pack. Not installed here. A one-call substring on the same 9 bad commands also blocked 9/9. Sponsio allowed the obfuscated `rm` that the substring blocked. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | Mediates writes inside the cage. Sponsio is a pre-call check in the agent loop. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok, filesystem MCP, and policy smokes. | The lab boundary. Sponsio does not start a container. |
| Bumblebee | I2 | Advisory read-only check for package lockfiles and MCP host configs. | Scans files. It does not see the next tool call. |
| cedr | I1 | Pin skill directories and MCP launch files, then fail when those files change. | After the files are already there. Sponsio runs before the call. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer, with a skill audit feature. | Installs and audits. This probe does not install a skill. |
| neatroots | I2 | Offline rule checks on saved traces (loops, repeated calls, error streaks). | After the trace exists. Sponsio decides before the call. |
| Rulora | I1 | Bounded loop counters and output validators, no model. | Counts turns. It does not read tool arguments. |
| Tracekit | I0 | Signed, policy-gated tool call records. | A record, not a measured blocker. |
| SysKnife | I0 | Typed approval-gated Linux admin. | Different shape. Not run (no cargo on this host). |

Sponsio does not beat SkillSpector, Sandlock, or a one-call shell substring. The part that measured ahead of the substring is cross-call order: 2/2 premature `copy_skill` calls blocked, and the substring blocked 0/2 because both copies have the same arguments.

## Verdict

PROMOTE I2. The ordering rule blocked 2/2 premature copies and allowed 2/2 copies that came after `scan_skill`. The shell pack blocked 9/9 labeled bad commands and allowed 5/5 ordinary commands. Absolute writes of a skill file inside this repo were blocked 0/2. Nothing is wired into a gate.

## Pin

PyPI `sponsio==0.2.0a17`, uploaded 2026-10-04. Git tag `v0.2.0a17` points at commit `957cb5264f156b98208e48c17700addf3aa7c64e` (the tag object is the commit). License-Expression on the installed METADATA is Apache-2.0. No account and no key. `SPONSIO_NO_AUTO_PUSH=1`. No model lock.

PyPI's non-pre release is still 0.1.1. Pre-releases after this pin run through `v0.2.0a21` (`99ebb16d65b9fc71f514fb66f3695feb169699fe`). This lane did not install them.

```bash
BASE=/home/mark/.cache/pfy/tools/sponsio
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/wheels"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export PIP_CACHE_DIR="$BASE/cache/pip" PIP_DISABLE_PIP_VERSION_CHECK=1 SPONSIO_NO_AUTO_PUSH=1
curl -fsSL -o "$BASE/wheels/sponsio-0.2.0a17-py3-none-any.whl" \
  https://files.pythonhosted.org/packages/06/56/7c277cb4c63483bd039baad48e3bc758e0fb00d5e6f3c6e5e7078e1e20ad/sponsio-0.2.0a17-py3-none-any.whl
echo "0e755cf9027da62051d3b05ec92a3557f34ec97aac142bc47704be16d86f0809  $BASE/wheels/sponsio-0.2.0a17-py3-none-any.whl" | sha256sum -c
python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install "$BASE/wheels/sponsio-0.2.0a17-py3-none-any.whl"
```

`sha256sum -c` printed OK. `sponsio.__version__` is `0.2.0a17`. The import path is the cache venv on Python 3.14.

The probe recorded 47678825 directory bytes (regular files, symlinks not followed, hard links once). `du -sb` of the same tree is 47678865. Both are under 50 MiB (52428800). The git tree has no wheel and no venv.

## Probe

`python3 eval/evq1107/sponsio/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/sponsio/results.json`. Wall clock 0.259 s. The child environment is `HOME`, `XDG_*`, `TMPDIR`, `PATH`, `LANG`, and `SPONSIO_NO_AUTO_PUSH=1` only. The probe calls `guard_before` and does not run the command, open the path, or talk to the hosted console.

Packs, enforce mode, `init_banner=False`:

| Pack | Contracts armed | What it is |
|------|----------------:|------------|
| shell | 9 | `sponsio:capability/shell` |
| order | 1 | `must_precede` of `scan_skill` before `copy_skill` |
| fs | 13 | `sponsio:capability/filesystem` plus `filesystem-strict` |

Warm check, one shell guard, 21 calls of `exec` `ls -la`, first sample dropped: median 283.9 us over 20. Upstream's hot-path claim is well under 1 ms. This median is in that range. It is one warm call, not the 0.259 s wall, which includes starting the venv interpreter.

| Group | Result |
|-------|--------|
| Shell bad commands blocked | 9/9 |
| Ordinary commands allowed (`ls`, `git status`, `git diff --stat`, relative `rm -rf tmp/...`, `curl` to a file) | 5/5 |
| `git push origin main` | allowed (1/1). The shell pack has no push rule. |
| Install commands with no banned pipe (`cp` into a skills dir, `git clone` into `.grok/skills`, python open of a SKILL.md) | allowed 3/3 |
| `python3 -c` with `os.system("rm -rf /")` | allowed. A one-call substring that looks for `rm -rf /` blocks it. |
| `sh-py-curl`, a python open of a SKILL.md whose source contains the text `curl \| bash` | blocked. The same open without that text (`sh-py-write`) was allowed. This is one of the 9/9. The block is the shell regex, not a skill-write rule. |
| Premature `copy_skill` (no earlier `scan_skill` on that guard) | blocked 2/2 |
| `copy_skill` after `scan_skill` | allowed 2/2 |
| Same premature copies under the one-call substring | blocked 0/2 |
| Absolute write of `SKILL.md` under this repo (`.grok/skills` and `bootstrap/grok-cli/skills`) | blocked 0/2 |
| Absolute write of `SKILL.md` under `/home/mark/.grok/skills` | blocked 1/1 (outside the workspace) |
| Relative in-repo path (`write` of a skill, `read` of the entry) | blocked 2/2 |
| Absolute read of `sources/entries/098-sponsio.md` | allowed |

Every ordinary shell command was allowed and also marked escalated (5/5). The call is not held. `sudo apt-get update` was blocked. The actions on that call were `blocked` and `escalated`. The shell pack's confirm rule fails closed when `confirm_reconfirmed` has not been called.

The one-call substring blocked the same 9/9 shell-bad commands. It is not `destructive_command_guard`. That tool was not installed. The substring is there so the order result has a baseline that cannot see earlier steps.

Real skill directories were not written. The paths were arguments only.

## Gates

Value gate, 2 of 4. The I3 bar is 3. Evidence and blast radius are met. Gap fill and operator leverage are not.

1. Gap fill. Not met for the install gate. In-repo skill writes were blocked 0/2, and `cp`, `git clone`, and a python open of a skill were allowed. The order rule did beat a one-call check (2/2 vs 0/2), but only on the names `scan_skill` and `copy_skill`. No cataloged tool in the table measured that pattern. It is a measured difference, not a closed hole versus SkillSpector or Sandlock.
2. Operator leverage. Not met. The blocked copy uses a made-up tool name, `copy_skill`. Enforce mode also escalates 5/5 ordinary shell calls. A day of glue would not make the install gate safer than the substring plus SkillSpector.
3. Evidence. Met. The probe exited 0 on this pin.
4. Blast radius. Met. Apache-2.0, no weights, no account, cache directory under 50 MiB, alpha. The repo copy is text.

Modularity gate, all four hold.

1. Local package needed. Met. Escalate-but-allow, the relative-path block, and the order state are runtime behavior.
2. Bounded surface. Met. `guard_before` on one Python package.
3. Isolatable. Met. Cache venv. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I3 would need the two missing value items, this probe, and `self_pipeline` evidence. The probe is repeatable (`eval/evq1107/sponsio/probe.py`, stubbed by `tests/test_sponsio_probe.py`). It has not been applied to this repo's pipeline, and this lane does not wire a gate. Potential stays medium. The catalog ceiling stays I1 until a TOOLS.md row exists. The stage is I2 because the order question is answered and the content question is answered in the negative.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Alpha pin | A later 0.2.0a release changes `guard_before` or bundle names. a18 through a21 already exist and were not run. | The probe exits 1 when a labeled call flips. Stay on 0.2.0a17 until someone re-runs the probe on a new pin. |
| Wrong tool name | The order rule watches `copy_skill`. A write of `SKILL.md`, `cp`, or `git clone` never hits it. Those were allowed. | Keep the known-bad `copy_skill` in the probe. Do not treat the rule as a scan of skill bytes. SkillSpector stays the content check. |
| Escalate noise | 5/5 ordinary shell calls were allowed and escalated. | Read `allowed`, not the mere presence of a violation. Start a real loop in observe mode before any enforce flip. |
| Over-block | Unconfirmed `sudo` is blocked. filesystem-strict blocks 2/2 relative paths, including a read of a repo file. | Do not include filesystem-strict for this repo's relative paths. Confirm is a separate marker the loop must emit. |
| Obfuscated command | `os.system("rm -rf /")` was allowed. A substring caught it. | One layer next to Sandlock. A regex miss is not confinement. |
| Hollow scan | The agent can call `scan_skill` and then `copy_skill` without scanning anything. The second call was allowed. | The rule only orders names. It does not inspect the skill. |
| Early onboard | Treating 9/9 shell blocks as a product gate. | Stay I2. The shell pack tied a substring. The content hole is 0/2. |
| Hosted console | `sponsio push` or a cloud config ref needs an account. | This run set `SPONSIO_NO_AUTO_PUSH=1` and used a local yaml path. Do not call `sponsio push`. |

## Next gate

Stay I2. A later ticket can grill one observe-mode wrapper on a real tool loop, still beside SkillSpector for bytes and Sandlock for the process. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? A later tool loop calls `guard_before` before it runs a shell or write. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the local yaml and the call arguments. It does not run the command. With `SPONSIO_NO_AUTO_PUSH=1` it does not upload the yaml. No hosted model, no account, no key.
3. What does it trigger next? Nothing in this lane. A blocked call would return to the agent. That loop is not built.
4. Where does a human re-enter? On the escalate notice, and before anyone flips a contract to enforce. The 5/5 ordinary shell escalations are the place to look. This lane does not make that a gate.
5. What stops two runs doing the same work? Each case builds a fresh guard. The run does not edit the installed wheel. This lane is one worktree and does not take the model lock.
