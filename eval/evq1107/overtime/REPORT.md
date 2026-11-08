# overtime evq1107

Verdict: STAY I0. `@ukanwat/overtime@0.5.3` ran offline under a redirected home. A stub ACP backend resumed the same session id 1/1 after `daemon stop` (0.2505 s). A third `send` started 0 ACP processes and the agent paused with reason `budget` after the stub had reported $2.00 and 24 tokens (caps were $1 and 10). An idle edit of `dailyBudgetUsd` from 1 to 999 in `AGENT.md` was adopted. A planted watch ran 4 times in 4.1404 s with 0 ACP starts. Usable backends for this stack were 0. Gap B (the 3 hour `./pfy build` timeout and the two pregate FAILs) was not changed. Nothing was wired into a gate.

## Catalog comparison

The job is gap B from the 2026-11-07 ranking: `./pfy build` is not proven bot-usable. This tool is the wake, budget, and resume layer around an ACP coding agent, so a folder can outlive one process. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` do not measure this job. The closer probes are under `eval/evq1107/`.

| Card | Stage | What it already does | How overtime compares |
| --- | --- | --- | --- |
| Grok CLI bootstrap | I3 | Operator env and Grok sessions | The session ends when the process ends. Overtime has no grok backend. This probe did not launch Grok. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards and loop types, already the orchestration toolset | Those exits already say when a lane stops. Overtime would be a second loop runtime. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, open questions, AGENTS | The handoff files already outlive the session. |
| Festival | I1 | Plan, next task, and checklist files. Probe did not close the timeout. `fest next` matched a pending-filename sort 3/3. | Files survive there too. Festival does not need an ACP backend. |
| Rulora | I1 | Loop counters and output bounds. The host still decides when a Build lane stops. | A counter, not a daemon. |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees | Overtime did not fan out and did not open a worktree. |
| kanzo | I0 | Local kanban plus MCP | Same queue job, not a wake daemon. |
| AgenC | I0 | Watch a daemon coding agent. Do not run it as the operator. | Same shape we already refused. |
| Auto-Company | I1 | Company-daemon patterns. Not a runtime. | Overtime is a runtime. This lane did not extract a pattern. |
| Hermes Agent (feedback loops) | I1 | Feedback skill. Not the Hermes daemon. | The skill is the piece we kept. |
| HAR | I0 | Per-slot worktree plus a receipt. Probe was 0.837 s against a git worktree at 0.222 s. Gap B still open. | A folder plus a daemon, slower to adopt, and still not a build lane. |
| Brigade | I0 | Exclusive claim on a task ledger. 0 duplicate ids of 94. | No claim in this probe. |
| Pi-Harness | I0 | Desktop control plane: trace, replay, budget checkpoint. Not installed. AGPL. | Overtime's budget did pause the stub. Pi was not the comparison runtime. |
| imcodes | I0 | Supervised loop reference. No daemon in that trial. | imcodes mentions a Grok ACP smoke. This lane did not run it, and overtime 0.5.3 does not list grok. |
| agentplay | I0 | Session replay map. No Grok transcript reader. | Replay is a different job. |
| Emdash | I0 | Parallel agents GUI, one worktree each | Not run. Overtime is a CLI daemon. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker | Memory for a worker we already have. Not a wake daemon. OpenCode was not executed here. |
| Foremerge | I1 | Pre-edit intent ledger for parallel agents | Different job. |
| LangGraph | I1 | Graph orchestration. Our loops already cover the operator path. | Overtime is a daemon, not a graph. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | Same. |
| Atomic Task Graph (ATG) | I2 | Compile, parallel waves, freeze, localized repair | Does not keep an ACP session. |

It does not beat what we have. The stub resume is real. The operator path is not: usable backends for Grok or a local model were 0, and gap B stayed 0.

## Pins

| Item | Value |
| --- | --- |
| Package | `@ukanwat/overtime@0.5.3`, MIT, npm `gitHead` `fc215d4e90cd95fa6b64c39268bb49490cba7ca1` |
| npm dist.integrity | `sha512-7TRVkwud4AcYvW4Wwgem3gegB1z+t6Kl3ggI/4MRwZFmNs2dUACapjnrR7uZrNHqBj1VzLKcOqvGpy4P4C6owg==` |
| Tarball | `overtime-0.5.3.tgz`, 217972 bytes. sha512 matches that integrity (`tarball_integrity_ok` true). sha1 `af73b354d5b58ad924bf573b2ccaaa6ebe771cc3` matches npm `dist.shasum`. |
| GitHub tag | `v0.5.9` is commit `c4a5725c21c785b6bd014e164678fa70c04026f1` (published 2026-10-12). No release assets. Not the pin. |
| npm latest on 2026-11-07 | `0.7.1` (published 2026-10-17). Not installed. The entry smoke pin stays 0.5.3. |
| Node | `/usr/bin/node` v22.23.0 (engines field asks `>=22.19`) |
| Install | `~/.cache/pfy/tools/overtime/prefix`. Sum of file sizes 322459712 bytes. Over the 50 MB lightweight copy bar. Nothing from the install is in git. |
| License | MIT, from `package.json` |

`npm install` reported 119 packages in 9 s. `--ignore-scripts`. No global install. No `daemon install`.

## Commands

```bash
BASE=$HOME/.cache/pfy/tools/overtime
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/npm-cache" "$BASE/prefix" "$BASE/dl"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" \
  TMPDIR="$BASE/tmp" npm_config_cache="$BASE/npm-cache"
curl -fsSL -o "$BASE/dl/overtime-0.5.3.tgz" \
  https://registry.npmjs.org/@ukanwat/overtime/-/overtime-0.5.3.tgz
npm install --prefix "$BASE/prefix" --ignore-scripts --cache "$BASE/npm-cache" @ukanwat/overtime@0.5.3
python3 eval/evq1107/overtime/probe.py
```

The probe sets `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `OVERTIME_HOME` under that cache path for every overtime process. It does not pass the parent environment through. The stub is `eval/evq1107/overtime/stub_acp.mjs`. It speaks newline JSON-RPC, reports a fixed session id, and reads token and cost numbers from a profile file. No network from the stub. No model.

`/home/mark/overtime` was absent before and after. `overtime daemon install` was not run. Claude, Codex, Gemini, and OpenCode were not started. Codex is present at `~/.npm-global/bin/codex` and OpenCode at `~/.local/bin/opencode`. Gemini was not on PATH. Both present binaries stay unused: Codex wants an account, and OpenCode would be a local model, which this lane does not take.

## Numbers

Script exit 0. Wall 19.6075 s, including the idle budget poll and the 8 s wait on the third send. Numbers are `eval/evq1107/overtime/results.json`.

| Check | Result |
| --- | --- |
| `--version` | `0.5.3`, exit 0, 0.0944 s |
| `new gapb` | exit 0, 0.3118 s. Folder created. |
| `set backend=stub budget=1 tokens=10 protect=<cache dir>` | exit 0. Settings file matched all four. |
| Idle `AGENT.md` edit `dailyBudgetUsd` 1 to 999 | adopted. Settings became 999. Then `set budget=1` put it back. |
| Turn 1 methods | `initialize`, `session/new`, `session/prompt`. 1 process. 0.2507 s until `lastRunAt`. Session `stub-session-1`. `lastError` null. |
| Protect | Write outside the protected dir succeeded. Write inside returned `EROFS`. bubblewrap is `/usr/bin/bwrap`. |
| After `daemon stop` | Agent folder still present. `mainSessionId` still `stub-session-1`. Real home untouched. |
| Turn 2 methods | `initialize`, `session/load`, `session/prompt`. Loaded `stub-session-1`. No `session/new`. 0.2505 s. |
| Usage after two turns | 2 rows, $2.00, 24 tokens. Caps were $1 and 10. |
| Turn 3 | `send` exit 0. ACP starts 0. Status `paused`, `pauseReason` `budget`. |
| Watch | Monitor file planted in the shape `addMonitor` writes. Not created by the wake tool. 4 runs in 4.1404 s. ACP starts during that window: 0. |
| Gap B | 0. `./pfy build` was not run. |
| Grok as a builtin backend | 0. Builtins in this pin are claude, codex, gemini, opencode. |

The dollar cap and the token cap were both already over before the third send. The pause reason is `budget` for either cap, so this probe does not say which check fired. It does say the third spawn did not happen.

The watch result is the daemon runner only. A session that calls the wake tool was not part of this stub. The agent stayed `status: new` because the stub never rewrote `AGENT.md`, so it never counted as having a job. The default one-hour wake (source: `DEFAULT_WAKE_MS` in this pin) was not waited out.

Protect was measured with bubblewrap present. The "turn refuses when bwrap is missing" line in the risks table is from `dist/runtime/sandbox.js` in this pin, not from a second run.

## Gates

Value gate, 1 of 4. Short of I3.

1. Gap fill. Not met. Gap B stayed 0. The folder and the handoff files we already keep also outlive a process. Festival, the loop exits, and the project-process docs already cover that. AgenC is already the daemon we do not run.
2. Operator leverage. Not met. There is no grok backend, and this lane did not start OpenCode or any local model. A stub that answers `STUB_OK` does not keep a Build lane going.
3. Evidence. Met. The probe exited 0 on the pinned package.
4. Blast radius. Not met for onboard. MIT, no weights, and the stub path used no account. The default backend is still Claude at $100 a day. An idle edit of the budget in `AGENT.md` was adopted. In this pin the daemon treats that as the person's edit. An edit made by the agent during a session was not tested. The installed prefix is 322459712 bytes, and the process is a detached daemon.

Modularity gate, all four hold for a cache probe. That does not promote the card.

1. Local package needed. Met. Resume, the adopted budget edit, the `EROFS` protect miss, and the pause are host behavior.
2. Bounded surface. Met. One `overtime` bin. This probe used `new`, `set`, `send`, `ls`, and `daemon stop`.
3. Isolatable. Met. Cache path plus `OVERTIME_HOME`. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I2 needs a probe that measurably helps while potential is still open, and a copy under 50 MB. Potential is low: the machinery works, and it does not help gap B on this stack. The prefix is also over 50 MB, so this is not an in-repo copy.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Default backend is Claude at $100 a day | A `send` before `set backend=` tries Claude | This probe set `backend=stub` and `budget=1` before the first `send`. Do not send on the default. |
| Idle `AGENT.md` budget edit is adopted | This pin treats an edit while no session is running as the person's edit. A session edit by the agent was not tested. | Set the budget with `overtime set`. Do not treat the README "puts it back" sentence as a tested control. |
| No usable ACP backend | Grok is not a builtin. OpenCode and Codex were not started. | Stay I0. A later ticket has to bring a backend that needs no account and no model lock. |
| Detached daemon | `new` starts `overtimed`. `daemon install` would add a login autostart. | This probe never ran `daemon install`. It ran `daemon stop` and checked the lock. `OVERTIME_HOME` stayed under the cache path. |
| Protect depends on bubblewrap | `dist/runtime/sandbox.js` in this pin refuses the turn when `protect` is set and bwrap is missing. This probe did not uninstall bwrap. | bwrap was present and the protected write got `EROFS`. If bwrap is missing, drop `protect` or do not send. |
| npm moved on | latest is 0.7.1. GitHub v0.5.9 is a different commit from the 0.5.3 gitHead. | Stay on 0.5.3 until a deliberate bump. |

## Next gate

Stay I0. Do not wire a gate. Do not install the login autostart. Re-open only if a later ticket has a Grok or local OpenCode ACP backend that needs no account and no model lock, and that ticket shows a build lane still going after the parent process exits. That ticket grills wiring first. Not a Feature GO.

## Five questions (if this tool were in the pipeline)

Not wired. The answers below are the shape it would have, and the reason it stays out.

1. What triggers it? A person runs `overtime send` or `overtime wake`, or the daemon's own schedule or watch fires. Nothing in pfy calls it.
2. What does it do, and which services does it read and write? It reads the agent folder under `OVERTIME_HOME` and spawns an ACP backend on stdio. It writes that folder (settings, state, messages, usage) and the daemon socket and log. This probe's backend was a local stub. No hosted model and no account.
3. What does it trigger next? The backend session, then the next wake the daemon stored. It does not start pregate, CI, or `./pfy build`.
4. Where does a human re-enter? `overtime answer` when the agent asks a numbered question, or when the daemon pauses the agent for budget. Any later wiring needs Mark's GO. This lane does not ask for it.
5. What stops two runs doing the same work? One daemon per `OVERTIME_HOME`, and one folder per agent name. This lane did not add a pfy lock. Two pfy runs are unchanged because overtime is not on their path.
