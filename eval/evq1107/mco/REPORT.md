# mco evq1107

Verdict: STAY I1. mco 0.12.1 ran offline under a redirected HOME and a PATH that cannot see host CLIs. On one gap B fixture, two local shims ran in parallel, mco kept both raw answers, and the JSON envelope had 0 comparison decisions. `--synthesize` then failed with `context_file_unsupported`. Built-in provider review was SKIPPED. The 3 hour `./pfy build` timeout and the two pregate FAILs were not changed. Nothing was wired into a gate.

## Catalog comparison

Same job: run more than one coding agent on one task, keep the answers, and use that for a build lane or a review.

| Card | Stage | What it already does | How mco compares |
| --- | --- | --- | --- |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees | mco ran 2 shims in parallel and kept both lines. It does not create a worktree. The envelope still has 0 comparison decisions. |
| Emdash | I0 | Parallel agents GUI, one worktree each | Same fan-out shape, as a GUI. Not run here. |
| Foremerge | I1 | Pre-edit intent ledger for parallel agents on one machine | mco allows parallel writers and does not lock a path. |
| Kander | I1 | Branch overlap check and a two-role reviewer gate. The probe started no agent | mco did run 2 reviewers. Both answers stayed raw. Kander can mark both roles done with 0 runs. Neither one clears the parked pregate. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build starts | A review before the lane. These two answers named both gap B facts and did not pick one. |
| Chiasmus | I1 | Call-graph impact for per-file review | A map of the diff. mco did not build one. |
| Tree-sitter Analyzer | I1 | Local change-impact map for a per-file review | Same map job. Already trialed on pfy diffs. |
| OpenQodex | I1 | Scanner candidates, then a model-free check that a finding cites a real token | A finding has to point at a token. mco keeps opaque text. |
| mattpocock/skills | I1 | Planning and review skills already on the skill path | Those skills already review a change. |
| agentgg | I0 | Local SAST on a deploy, release, or secrets diff | A scan. mco is not a scanner. |
| CodeGuard | I0 | Secure-coding rule text a host agent can read | Rules for the host. mco does not apply them. |
| trailofbits-skills | I0 | Security review checklists an agent can read | Checklists. This probe did not grade a diff against one. |
| Cloudflare security-audit skill | I0 | Schema check for findings.json | mco emits no findings object. The decision-key count here is 0. |
| Hermes Teammates | I0 | Fixed tester/reviewer roster inside Hermes | A roster inside another product. |
| imcodes | I0 | Supervised review loop and final-answer memory. Reference only | Not installed in this lane. |
| Pi-Harness | I0 | Desktop control plane around Pi. Reference read only | Pi is one of the 4 adapters that accept prior-answer files. This lane did not start Pi. |
| Overtime | I0 | Wake and budget for one ACP agent. Gap B stayed 0 | mco also left gap B at 0. It does not budget a 3 hour build. |
| Festival | I1 | Filesystem plan and next-task. The probe did not close the timeout | mco is not a plan file. |
| Brigade | I0 | File ledger with an exclusive claim | mco has no claim. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards and loop types, already the orchestration toolset | The stop conditions a lane already uses. |
| Atomic Task Graph (ATG) | I2 | Compile, parallel tool waves, freeze, localized repair | A DAG. mco does not compile one. |
| Multica | I1 | Multi-agent board. Not our orchestrator | A board we would not adopt. |
| LangGraph (LangChain) | I1 | Graph orchestration. Our loops already cover the operator path | mco is a CLI fan-out, not that graph. |
| gstack | I1 | Role patterns already ported in docs | Do not clone a second process kit. |
| multi-agent-generator | I0 | Scaffolds CrewAI or LangGraph teams | A scaffold. Not a review of this repo. |

Open WebUI and the marketing council match a multi-model or multi-agent tag and do a different job. The 2026-10-06 ranking already places MCO under skip or hold as multi-provider review that assumes paid CLIs.

It does not beat what we have.

## Pins

| Item | Value |
| --- | --- |
| Tag | `v0.12.1`, tag object `9c37318e9cba7a76075bca0d3671bdf7bfbd725f`, tagger 2026-10-07 10:58:01 UTC |
| Commit | `3cfce130362dbcc2aedda6170d1a31e39cf67d3e`, `fix(ci): repair npm publishing and prepare v0.12.1` |
| Package | `mco` 0.12.1, MIT, Python >= 3.10, dependencies `[]`. `mco version` prints `0.12.1` |
| Local wheel | Built by pip from that commit. 120,911 bytes, sha256 `3dd720992dbaacbe239b05fbdffd5fd58b6caff7510f927c1801b04c4d5a05b2`. This is a local build receipt, not an upstream checksum. The entry gave none. |
| Tree | `~/.cache/pfy/tools/mco/src` is 9,809,804 bytes including `.git`. File bytes outside `.git` were 6,214,300 across 631 files, plus 3 dangling symlinks. The venv is 12,114,030 bytes. Under the 50 MB I2 copy limit. Not copied into the repo. |
| Upstream HEAD at fetch | `7ce642193a127f3fac9c68fb10c5d0198d4e837e`. This lane pinned the tag, not that moving HEAD. |
| Isolation | `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `MCO_CONFIG_DIR` point under `~/.cache/pfy/tools/mco/`. The mco subprocess PATH is `/usr/bin:/bin`. No `npm install -g`, no `npx`, no `mco skills sync`, no `mco doctor`, no `mco session`. |

## Commands

```bash
BASE=~/.cache/pfy/tools/mco
git clone --branch v0.12.1 --depth 1 https://github.com/mco-org/mco.git "$BASE/src"
# detached HEAD is commit 3cfce130362dbcc2aedda6170d1a31e39cf67d3e
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export PIP_CACHE_DIR="$BASE/cache/pip" PIP_DISABLE_PIP_VERSION_CHECK=1
python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install "$BASE/src"
python3 eval/evq1107/mco/probe.py
```

The probe writes two shim agents into the redirected `MCO_CONFIG_DIR` and reviews `eval/evq1107/mco/fixture/gap-b.txt` inside this repo. The fixture restates the gap B row: the 3 hour timeout and the two pregate FAILs. Each shim reads that file and prints one blocker line. The probe does not run `./pfy build`. Numbers are in `results.json`.

`mco doctor` and `mco review --providers claude,codex,pi` are SKIPPED. Doctor auth checks launch the provider CLI (`grok models`, a gemini prompt, `copilot` with `--allow-all-tools`). This lane does not start those processes.

## Numbers

| Check | Result |
| --- | --- |
| Built-in adapters | 11 |
| Adapter binary names that resolve | 8 of 11: agy, claude, codex, grok, hermes, opencode, pi, and `agent` (the cursor adapter) |
| Absent | copilot, gemini, qwen |
| `agent` path text | The resolved path does not contain the word cursor. Cursor's CLI is often named `agent`, so that miss does not identify the file. It was not executed |
| Provider CLIs executed | 0. Doctor and live review SKIPPED |
| Adapters with `context_files` | 4 of 11: claude, codex, hermes, pi |
| Dry run | exit 0, 57.2 ms, `would_execute` false, 2 invocations, stub log lines 0 |
| Parallel review | exit 0, status `complete`, 1057.4 ms |
| Overlap | true. Span 0.601 s. Roles `pregate` and `timeout` |
| Raw answers | 2 of 2 success: `blocker: timeout 3h` and `blocker: pregate fails 2` |
| Comparison decision keys | 0 on the parallel envelope and 0 on the synthesize envelope |
| Synthesize | exit 1, status `partial`, 1081.9 ms. Synthesis error `context_file_unsupported`. The log still has 2 roles, so the synthesis stage did not spawn a third stub |
| Repo writes | 0 (`reports/review`, `.mco`, `.mcorc.json`, `.mcorc.yaml` stayed absent) |
| Gap B closed | 0 |

mco kept the disagreement and did not choose a blocker.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. Two raw lines name the two facts already in the fixture. The envelope has 0 comparison decisions, so a parked build lane still has nothing new to act on.
2. Operator leverage: no. The stage that can see a prior answer exists on 4 adapters, and those adapters are hosted CLIs. The offline shim cannot enter that stage. This does not shorten a 3 hour build.
3. Evidence: yes. The pinned package ran. `results.json` records the exits, the two answers, and the synthesize error.
4. Blast radius: yes, while it stays in the cache. MIT. No model weights. About 22 MB for the source tree plus the venv. It did not become the product runtime. The default artifact directory is `reports/review` inside the repo; this run set `--artifact-base` under the cache and `--result-mode stdout`.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The README says answers stay opaque. The run was still required to see that a command shim fails synthesis with `context_file_unsupported`, and that only claude, codex, hermes, and pi accept prior-answer files.
2. Bounded surface: yes. `mco review`, `mco run`, and `mco doctor` are the entry points.
3. Isolatable: yes. The cache path, a redirected HOME, and a PATH of `/usr/bin:/bin` held the run. The repo gained no mco files.
4. Reversible: yes. Deleting the cache leaves the pin and this entry.

Modularity passes for a cache probe. That is not a promotion. The result is no longer ambiguous, and it does not help, so the card stays I1. I3 would also need a pipeline script and `self_pipeline` evidence. This lane wires nothing. `self_pipeline` is `not_applicable`.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Doctor starts a hosted CLI | `mco doctor` runs `grok models`, a gemini prompt, and copilot with `--allow-all-tools` when those binaries are on PATH | Do not run doctor on the host PATH. This lane did not. |
| Default artifacts land in the repo | `artifact_base` defaults to `reports/review` | Pass an absolute `--artifact-base` under the cache, and use `--result-mode stdout` when the JSON envelope is enough. This run left `reports/review` absent. |
| Synthesis looks like a merged review | `--synthesize` on a shim returns `context_file_unsupported` and the task status is `partial` | Treat `partial` as an unfinished provider call. The two raw lines are still the whole result. |
| `agent` on PATH | The cursor adapter launches `agent`. That is the usual Cursor CLI name, including when the path does not contain the word cursor | Do not execute it on an offline probe. This lane did not. Doctor stays skipped |
| Parallel writers | mco does not create worktrees and does not lock a file | One worktree per slug stays the lock. |
| Skill sync writes into agent homes | `mco skills sync` copies the bundled skill into calling-agent directories | This lane did not sync skills. Keep HOME redirected if a later ticket does. |
| Disagreement stays unresolved | 2 answers, 0 decisions. A lane can still hit the 3 hour timeout | Pregate and the 8 exits stay the stop. |

## Next gate

Stay I1. Do not wire mco into pregate, CI, or `./pfy`. Reopen only if a later ticket shows two local engines, with no paid CLI, producing a comparison decision on a real pfy diff that the review skills and pregate do not already state, and that ticket grills wiring first.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? An operator or a calling agent wants two or more agent CLIs on one prompt before acting.
2. What does it do, and which services does it read and write? It reads the repo and launches the selected provider CLIs. It writes raw answers to stdout and, in artifact mode, under the artifact base. The providers then use their own accounts. mco itself has no account in this probe.
3. What does it trigger next? A person or the calling agent reads the raw text. mco does not open pregate, does not start `./pfy build`, and does not emit a decision.
4. Where does a human re-enter? At the raw answers. Debate and synthesis are further provider calls, and a command shim cannot receive the prior answer files.
5. What stops two runs doing the same work? mco does not. It does not take a claim, and a repeated task id replaces that task's artifact directory. Our one worktree per slug stays the lock.
