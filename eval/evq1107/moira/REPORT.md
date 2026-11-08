# Moira evq1107

## Catalog tools on this job

The job is a build lane that stops on a real done-condition. Gap B is the 2026-11-06 `./pfy build` trial: it hit the 3 hour timeout, and the recheck stayed parked after two pregate FAILs. These cards already cover that job or the step graph next to it.

| Tool | Stage | What that card covers | How Moira compares |
|------|-------|----------------------|--------------------|
| Finn Loop / 8 exits | I1 | Exit card and loop types. Already the orchestration toolset. | The skill file names 8/8 exits and mentions `inputSchema` 0 times. A checker that only accepts the word "done" accepted 18/18 claims. Moira rejected 8/8 bad shapes and stopped 4/4 honest reports. The 4 lies finished in Moira too. |
| Rulora | I1 | Loop counters and output validators. Host still decides when a build lane stops. Native on 2 of 8 exits. The 3 hour stream stays active. | Moira also has no host clock. Elapsed 10 with pregate PASS finished. |
| Festival | I1 | Filesystem plan and checklist gates. The 2026-11-07 probe did not close the timeout. | Different surface. This probe also left the under-reported lane on `done`. |
| Open Steps | I0 | One stop nag. It does not see a 3 hour timeout or a parked pregate FAIL. | Moira does not see them either unless the agent writes them into the step. |
| Overtime | I0 | Wake and budget layer for an ACP agent whose folder outlives one process. The 2026-11-07 probe did not close the pfy build timeout. | Same hole. An under-reported elapsed of 10 seconds still finished here. |
| Kander | I1 | Branch overlap check and a two-role reviewer done gate. The probe started no agent. | A done gate on role files. Not a schema on a step payload. Not re-run. |
| LangGraph | I1 | Graph orchestration. Our loops already cover the operator path. | Not re-run. The extra piece here is the schema on the agent payload. It did not beat the exit card on this fixture. |
| Atomic Task Graph | I2 | Compile, parallel waves, freeze, repair. | A DAG compile. Not a step schema. Not re-run. |
| Sponsio | I2 | Pre-call order. One call can be blocked until an earlier call happened. | Neighbor. It does not parse this step schema. Not re-run. |
| neatroots | I2 | Offline rules on a saved trace (loops, repeated calls, error streaks). | After the trace exists. Moira decides at the step, then still accepts a schema-valid lie. |
| kanbots | I1 | Kanban that fans out to coding CLIs in worktrees. | Lane fan-out. Not a done-condition. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | Not run. Docker board, not this check. |

Moira does not beat the exit card, Rulora, or Festival on gap B. The part that measured ahead of the word "done" is shape: 8/8 malformed payloads rejected, against 0/8 for that prose check. The 4 lies that hide the fixture (pregate FAIL, elapsed 10800, fail_count 2) still finished.

## Verdict

STAY I1. Schema rejected 8/8 bad shapes. The condition stopped 4/4 honest reports (1 park, 3 timeout). 4/4 schema-valid lies routed to `done`. Two completion strings on the same FAIL payload both routed to `park` (0 of 2 strings changed the route). Nothing is wired into a gate.

## Pin

Git tag `v6.0.0` is commit `b66b537a0465194d8806fa638776237d8cf853c5` (2026-10-13, subject `feat(codespaces)!: run commands and files through one workspace owner`). `git describe --tags --exact-match` prints `v6.0.0`. Root `package.json` version is `0.3.5`. `@mcp-moira/workflow-engine` version is `0.3.0`. License in `package.json` and `LICENSE` is Apache-2.0. No account and no key. No model lock.

The image was not pulled. Upstream compose still defaults to `ghcr.io/moira-mcp/moira:latest`. This lane did not pin a digest because it did not start Compose.

MCP server path: SKIPPED. The README at this pin says every MCP tool call needs an access token. This lane did not create a local account, did not write a password, and did not pull images into the shared Docker daemon. Docker is installed (`29.6.0`) and this user is in the `docker` group. The step check does not need the server.

Node on `PATH` is v22.23.0. The repo `engines` field says `>=24`. The probe used the existing binary `/home/mark/.local/share/pfy-mentat/node/v25.9.0/bin/node` (v25.9.0). Nothing was written under `~/.local/bin`.

```bash
BASE=/home/mark/.cache/pfy/tools/moira
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/src" "$BASE/nm"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export npm_config_cache="$BASE/cache/npm"
git clone --depth 1 --branch v6.0.0 https://github.com/moira-mcp/moira.git "$BASE/src"
NODE=/home/mark/.local/share/pfy-mentat/node/v25.9.0/bin/node
cd "$BASE/nm"
"$NODE" "$(dirname "$NODE")/npm" init -y
"$NODE" "$(dirname "$NODE")/npm" install --ignore-scripts --no-fund --no-audit ajv@8.20.0 tsx@4.20.6
```

`ajv@8.20.0` is the version `package-lock.json` resolves at this pin. `tsx@4.20.6` only loads the TypeScript. It is not part of Moira.

The shared package barrel pulls Better Auth and SQLite. The probe does not load that barrel. A one-file package under the cache `node_modules` re-exports the real `ValidationError` (`packages/shared/src/errors/app-error.ts`) and the real `mapLegacyStatus` (`packages/shared/src/types/execution-error.ts`). `mapLegacyStatus` is not called. Symlinks:

```bash
mkdir -p "$BASE/src/node_modules/@mcp-moira"
ln -sfn "$BASE/nm/node_modules/ajv" "$BASE/src/node_modules/ajv"
ln -sfn "$BASE/nm/node_modules/@mcp-moira/shared" "$BASE/src/node_modules/@mcp-moira/shared"
```

`du -sb` of the checkout is 37527063 bytes (under 50 MiB). The probe's file walk, skipping `.git` and `node_modules`, is 28561760 bytes. `du -sb` of the ajv+tsx tree is 12444048 bytes. No wheel, no image, no checkout in git.

## Probe

`python3 eval/evq1107/moira/probe.py --out eval/evq1107/moira/results.json` from this worktree. Exit 0. Numbers are `eval/evq1107/moira/results.json`. Wall clock 0.15656 s. The 18 calls inside the engine took 14036.883 us. Child env is `PATH`, cache `HOME`, `XDG_*`, `TMPDIR`, `LANG`, `MOIRA_SRC`, and `NODE_NO_WARNINGS=1`.

The engine call is `SchemaValidator.enforceStrictSchema`, then `SchemaValidator.validate`, then `routeNode` when the schema accepts an object. That is the path `AgentDirectiveHandler` uses after a step payload arrives. The handler itself was not constructed. The completion string is placed on the node object passed to `routeNode`. The schema object we sent did not set `additionalProperties`. The engine set it to false.

Fixture, not read from the agent: pregate `FAIL`, elapsed `10800` seconds (3 hours), `fail_count` 2. The route checks elapsed `gte 10800` first, then pregate `eq FAIL`. `goal_met` and `fail_count` are required by the schema and are not routed.

| Group | Result |
|-------|--------|
| Malformed rejected (empty, bad enum, string elapsed, extra field, missing `goal_met`, negative elapsed, 10.5, prose string) | 8/8 |
| Schema-valid lies routed to `done` (PASS at 10s, PASS at 10799s, `goal_met` false, `fail_count` 2 with PASS at 10s) | 4/4 |
| Honest reports not `done` (FAIL at 1000s parks; FAIL at 10800s, PASS at 10801s, and FAIL at 10801s take timeout) | 4/4 |
| Completion string `pregate is PASS` vs `pregate is FAIL` on the same FAIL payload | both `park` (0/2 changed the route) |
| Prose check: the claim text is the word `done` | accepted 18/18 |
| `agent-loops` skill | 8/8 exit names present, 0 `inputSchema` mentions |

`mal-extra` error, first line from the engine: unknown field `lane_done` is not allowed. `mal-prose` error: root must be object, got string.

## Gates

Value gate, 2 of 4. The I3 bar is 3. Evidence and blast radius are met. Gap fill and operator leverage are not.

1. Gap fill. Not met. The 4 lies that hide the two pregate FAILs and the 3 hour clock all finished. Shape checks are ahead of the word "done" (8/8 vs 0/8) and do not close that hole. Rulora and Festival already recorded the same hole on the clock.
2. Operator leverage. Not met. A day of glue would still trust the agent for pregate and the clock. The host already has both. `goal_met` and `fail_count` are stored and never routed.
3. Evidence. Met. The probe exited 0 on this pin.
4. Blast radius. Met. Apache-2.0, no weights, checkout under 50 MiB, cache only, no account. The repo copy is text.

Modularity gate, all four hold for the unit that ran (the two functions). The Compose product was not the unit.

1. Local code needed. Met. The ignored completion string, the strict extra-field reject, and the `gte` edge are runtime behavior.
2. Bounded surface. Met for this unit. `SchemaValidator.validate` and `routeNode` in one package. The monorepo and the web UI were not the eval unit.
3. Isolatable. Met. Cache checkout. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I3 would need the two missing value items, a repeatable script, and `self_pipeline` evidence. The script is `eval/evq1107/moira/probe.py`, stubbed by `tests/test_moira_probe.py`. It has not been applied to this repo's pipeline, and this lane does not wire a gate. Potential stays low. The catalog ceiling stays I1 until a TOOLS.md row exists.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Completion string | Authors treat the string as a check. Both strings routed the same FAIL payload to `park`. | Read `output` from the condition cases. Keep the string out of the stop decision. |
| Valid lie | Agent sends pregate PASS and elapsed 10. The lane goes to `done` while the fixture is FAIL at 10800s. 4/4 such claims finished. | Do not use Moira as the build-lane stop. The host clock and pregate stay outside it. |
| Stored but not routed | `goal_met: false` and `fail_count: 2` were accepted and still finished when pregate was PASS and the clock was short. | A field stops the lane only when a case reads it. The probe keeps those two fields unrouted on purpose. |
| Cap boundary | `gte 10800` times out an honest report of exactly 10800. `10799` with PASS finishes. | Keep the operator next to the fixture number. Do not describe `gt` and `gte` as the same edge. |
| Account server | MCP calls need a token. A future run that starts Compose creates a local admin secret and uses the shared Docker daemon. | This lane skipped that path. Keep any `.env` under the cache, never in git, and never print it. |
| Unpinned image | `:latest` moves. | Do not `compose pull` until the image is `@sha256:`. |
| Shim drift | The cache shim exports two real modules so the barrel does not load. A later pin that imports another symbol from the barrel fails the import. | The probe exits 2 when the import throws. Re-point the shim at the new module or stay on this pin. |
| Early onboard | Treating 8/8 shape rejects as a product gate. | Stay I1. The lies are 4/4. |

## Next gate

Stay I1. A later ticket can re-open only if the completion string, or a host-supplied clock and pregate result, parks the lane when the agent says PASS with a short elapsed. No pregate, CI, or other gate wiring in this lane.

## Five questions (Moira in our pipeline)

1. What triggers it? A build lane would start a workflow when `./pfy build` starts. Nothing in this repo calls Moira today.
2. What does it do, and which services does it read and write? It checks the agent step JSON and, if the server were up, would write an execution row in its own SQLite. It does not read pregate output or the host clock unless an earlier step stored them. This probe kept those calls in memory.
3. What does it trigger next? A `park` or `timeout` edge would still need the host to stop the lane. This lane triggers nothing else.
4. Where does a human re-enter? A lock node can wait for an unlock. That path was not run. Mark re-enters on a later gate ticket, or by deleting the cache checkout.
5. What stops two runs doing the same work? Moira execution ids live in its database and do not know about bot worktrees. The host would have to pass a distinct id. This probe ran one in-memory call and wrote no database.
