# kanbots evq1107

Verdict: STAY I1. The pinned dispatcher created one worktree, stamped the commit author, and added the run trailers (1/1). The pre-push hook rejected an explicit ref before that stamp and accepted the same ref after it. A `HEAD` refspec was accepted before the stamp. 0 of 11 CLIs were dispatched. The 3 hour `./pfy build` timeout was unchanged (0 hours removed). Nothing was wired into a gate.

It does not beat git worktree plus `/agent-loops`.

## Catalog comparison

Same job: a board that sends coding CLIs into worktrees for the pfy build lane (gap B). Gap B is that `./pfy build` is not proven bot-usable. The 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate FAILs. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. kanbots is entry 078. The ranking row says it overlaps `/agent-loops`.

These cards already cover a piece of the job. Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` (agentgg, bumblebee, chiasmus, dspy, egm, hiroute, neatroots, osc, skill-up, skillspector, strata) do not. None of them is a multi-CLI kanban.

| Card | Stage | What it already covers | How kanbots compares |
| --- | --- | --- | --- |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards and loop types, already the orchestration toolset | This run enforced 0 of those 8. Feature-dev loops until abort. The qa kind throws. |
| git worktree | in this repo | `worktree add` and `remove` on the same one-file fixture | 5.1 ms. kanbots create plus stamp plus remove was 21.7 ms. |
| HAR | I0 | One slot plus a tree receipt. Its own probe stayed because the slot was slower. | Another worktree wrapper. The push guard did not hold in the supervisor's order. |
| Emdash | I0 | Parallel agents GUI, one worktree each. Comparison only. | Same shape. This probe did not open a GUI. |
| Kanzo | I0 | Local kanban plus MCP. AGPL. Comparison only. | Same board job. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | Same. A board we would not adopt. |
| Auto-Company | I1 | Persona patterns. Not a runtime. | kanbots personas still need a signed-in CLI. |
| Festival | I1 | Plan file and next step. Its probe stayed I1 and left gap B open. | kanbots also left the timeout unchanged. |
| Brigade | I0 | Exclusive claim. 0 duplicate ids out of 94 slugs. | The kanbots thread lock lives in the desktop store. This probe did not run it. |
| Foremerge | I1 | Pre-edit ledger for parallel agents. Its probe stayed I1. | Different lock. |
| Pi-Harness | I0 | Desktop runs, trace, and worktrees. Reference only. | Another desktop. Not installed here. |
| Rulora | I1 | Loop counters. The host still decides when a lane stops. | kanbots has no turn cap in feature-dev. |
| LangGraph | I1 | Graph orchestration. Our loops already cover the operator path. | kanbots is a board. |
| Atomic Task Graph (ATG) | I2 | Compile, parallel waves, freeze, repair. | Different job. |
| gstack | I1 | Role patterns already ported in docs. | Do not add a second process kit. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, open questions, AGENTS. | TODO is already the queue. |
| agent-cage (PNNL) | I3 | Container lab for Grok. | kanbots does not replace the cage. |
| grok-cli bootstrap | I3 | Operator sessions that already run the lanes. | `@kanbots/cli` registers 0 commands. |

## Pins

| Item | Value |
| --- | --- |
| Entry pin | "main or latest release". No checksum in the entry. |
| main | `7b256a024e65268d359ab3286e6c5d2c3d63a072` (the checkout that ran) |
| tag | `v1.2.0` at `80a978c590b5cb13fdb5c8aa0ec15479e8a422cc` |
| Delta | One commit. `packages/dispatcher`, `packages/cli`, `packages/api/src/autopilot`, and `supervisor.ts` are the same on both. The extra commit is cloud UI. |
| AppImage | `kanbots-1.2.0-linux-x64.AppImage`, 113,054,166 bytes. sha256 `e7466c7ca3bc02a2e04ea664c194121104ea8bdfc134a5e6078c48bddc917b6a` matches the GitHub release asset digest and `latest-linux.yml`. |
| npm | `npm view kanbots version` returned E404. The documented `npx kanbots` one-liner cannot install. |
| Source | `~/.cache/pfy/tools/kanbots/src/kanbots`, 5,052,032 bytes without `.git`. |
| Node | v22.23.0. Modules loaded with `node --experimental-strip-types`. No pnpm install. No Electron launch. |
| License | MIT, from the upstream package manifest. |

`HOME`, `GIT_CONFIG_GLOBAL`, and `TMPDIR` for the git and node subprocesses point under `~/.cache/pfy/tools/kanbots/`. The real login home had no `.kanbots` and no `.config/kanbots` before or after. The fixture repo was a throwaway one-file git repo under that cache. This worktree was not the repo under test.

## Commands

```bash
git clone --depth 1 https://github.com/leodavinci1/kanbots.git \
  ~/.cache/pfy/tools/kanbots/src/kanbots
# HEAD 7b256a024e65268d359ab3286e6c5d2c3d63a072
# AppImage downloaded to the same cache and hashed. It was not executed.
python3 eval/evq1107/kanbots/probe.py --net
```

The probe writes `eval/evq1107/kanbots/results.json`. Live CLI dispatch is SKIPPED: each provider reuses its own sign-in, and this lane does not call `claude`, `codex`, or `opencode`. The Electron GUI is SKIPPED: the binary can start a cloud device login.

## Numbers

| Check | Result |
| --- | --- |
| git worktree add plus remove | 5.1 ms |
| kanbots create | 10.2 ms |
| stamp identity | 8.6 ms |
| remove | 2.9 ms |
| create plus stamp plus remove | 21.7 ms (4.3 times the baseline) |
| Pre-push file | installed in the common `.git/hooks`, 643 bytes |
| Push `refs/heads/kanbots/issue-78-1` before stamp | exit 1, rejected by pre-push |
| Push `HEAD:refs/heads/kanbots/issue-78-1` before stamp | exit 0, new branch |
| Same explicit ref after `stampWorktreeIdentity` | exit 0, new branch. `core.hooksPath` is set. |
| Commit author | `kanbots agent (run #1) <agent+1@kanbots.local>` |
| Trailers | `Kanbots-Run-Id: 1` and `Kanbots-Issue: 78` both present |
| Outside tool paths blocked | 3/4. `Read` of an absolute outside path returned ok. |
| URL command `curl https://example.com/gap` | marked escape (false positive) |
| `runCheck` of `true` | pass, 1 ms |
| `runCheck` of `sleep 5` with `timeoutMs` 400 | fail, 404 ms, summary `timed out` |
| Check default in source | 5 minutes, and only when a caller uses `runCheck` |
| CLIs on PATH | 3/11 (`claude`, `codex`, `opencode`). 0 dispatched. |
| `@kanbots/cli --help` | Usage and options only. 0 subcommands. |
| qa autopilot | source throws `is not implemented yet` |
| feature-dev turn cap | no `turnCap`, `maxIterations`, or `MAX_TURNS` |
| Gap B | 0 hours removed. `./pfy build` was not started. |

The supervisor calls `createWorktree` and then `stampWorktreeIdentity`. That is the order this probe measured. The stamp points `core.hooksPath` at a private directory that has the commit-msg trailer hook and not the pre-push hook, so the explicit-ref reject stops applying.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. git worktree already isolates a lane. `/agent-loops` already has the 8 exits. This run enforced 0 of them. The push guard does not survive the supervisor's own stamp.
2. Operator leverage: no. The CLI has 0 commands. The npm name is missing. The desktop app was not a headless lane. The timeout stayed 3 hours.
3. Evidence: yes. The pinned source ran. `results.json` records the exits. The AppImage hash matched.
4. Blast radius: yes, while it stays in the cache. MIT. Source is 5,052,032 bytes without `.git`. The 113,054,166 byte AppImage was not launched and is not in the repo. No model weights. It did not become the product runtime.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The docs say the pre-push hook blocks agent pushes and that qa autopilot re-runs checks. The run showed the product order lets the explicit ref through, a `HEAD` refspec bypasses the guard, and qa throws.
2. Bounded surface: no. The product entry is an Electron monorepo. `@kanbots/cli` registers 0 commands.
3. Isolatable: yes. The cache path held the checkout, the AppImage, and the fixture.
4. Reversible: yes. Deleting the cache leaves the pin and this entry.

Modularity fails the bounded surface. The result is no longer ambiguous, and it does not help, so the card stays I1. I3 would also need a repeatable pipeline script and `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| HEAD refspec | `git push <remote> HEAD:refs/heads/kanbots/issue-78-1` exits 0 while the hook is installed. The hook matches `refs/heads/kanbots/issue-*` and the local ref is `HEAD`. | Do not use the hook as a push gate. One worktree per slug and the driver's fast-forward push stay the rule. |
| Stamp hides pre-push | After `stampWorktreeIdentity`, `core.hooksPath` is set and the explicit ref push exits 0. | The supervisor uses this order. Leave the tool unwired. |
| Containment holes | `Read` of a path outside the worktree returns ok. A URL command is marked escape. Default mode in the docs is `warn`, not a hard stop. | The cage stays the isolation boundary. |
| qa docs disagree with code | Starting kind `qa` throws `is not implemented yet`. | Do not start that mode. Pregate stays the check. |
| No turn cap | feature-dev is `while (!signal.aborted)`. A null USD budget does not stop it. A child can overshoot the budget before the next check. | Do not start autopilot. `/agent-loops` stays the exit card. |
| npm name missing | `npx kanbots` cannot resolve. | Pin the git commit and the AppImage sha256. |
| Cloud login | Launching the AppImage can start the hosted device flow added on main. | This lane did not launch it. |
| Real home writes | A run without a redirected `HOME` can create `~/.kanbots`. | Subprocesses used the cache home. The real paths stayed absent. |
| Second queue | A board and TODO plus the 8 exits can disagree about the next lane. | Leave the card at I1. |

## Next gate

Stay I1. Do not wire kanbots into pregate, CI, or `./pfy`. Reopen only if a later ticket shows a headless command that still rejects the agent ref after the identity stamp and stops a lane on a wall clock without an account, and that ticket grills wiring first.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? An operator opens the Electron board. `npx kanbots` would be the other trigger, and that package name returned 404 on 2026-11-07. Nothing in `./pfy`, pregate, or the lane scheduler calls kanbots.
2. What does it do, and which services does it read and write? It reads a local git repo and writes `.kanbots/` (SQLite, config, worktrees). A dispatch spawns whichever agent CLI is on `PATH`. Those CLIs use their own sign-in. GitHub mode and the cloud device flow are hosted. This lane used neither, and it did not point the tool at the product checkout.
3. What does it trigger next? A person promotes a worktree or stops a run. The qa kind throws, so it does not start a check. It does not start `catalog_check`, pregate, or CI.
4. Where does a human re-enter? Decision prompts and the promote button. Our re-entry stays the `tmp/evq` markers, `tmp/STOP`, and Mark.
5. What stops two runs doing the same work? The supervisor rejects a second run on a thread that is already active. It does not see the scheduler's `.pid`, `.dispatched`, `.done`, or `.parked` markers. One worktree per slug stays the lock.
