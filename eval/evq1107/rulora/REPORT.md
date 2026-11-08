# Rulora evq1107

STAY I1. LoopControl stops 2 of 8 Build-lane exits. The 3 hour stream stays active. That does not beat the exit card we already require.

`STAY I1 LoopControl covers 2 of 8 Build-lane exits and the 3h stream stays active`

## Catalog overlap

Same job: bounded loops and validated outputs, with no model, as loop exits for Build lanes. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07) and the batch-1 verdicts under `eval/ev1107/` and `eval/catchup-1107/`.

| Tool | Stage | Why it covers this job | How Rulora compares |
| --- | --- | --- | --- |
| Finn Loop / 8-exits (`agent-loops`) | I1 | Exit cards and loop types. Features: 8 exits, agent-loops skill. Tags include `#loops`, `#exits`, `#stop-conditions`. | The skill already names all 8, including wall clock and a human interrupt separate from no-progress. Rulora enforces 2 of the 8, and only after the host calls `record`. It does not beat the card. |
| neatroots | I2 | Offline checks for loops, repeated tool calls, and error streaks on saved traces. `eval/ev1107/neatroots/` promoted I2 after a real 3-call error streak and a real identical grep. | Three failing turns whose hash still changes stay `active` here. Rulora does not read a trace. It does not beat that probe. |
| odai | I0 | Evidence-before-done governance skill. | A shape-valid payload with `tests_passed: false` is accepted. The boundary does not add that check. |
| LangGraph | I1 | Graph orchestration. The card already says our loops cover the operator path. | One counter package does not fill a hole that card left open. |
| Atomic Task Graph | I2 | Freeze plus localized repair. Live score was 2/10 valid DAGs. | `CollectiveControl` froze 2 ids and rejected an unknown id. It does not compile a task graph. |
| Hermes feedback loops | I1 | Feedback-loop pattern, already a skill. The runtime stays off the card. | Another small pattern. The skill is already the port. |
| kanbots | I1 | The 2026-10-06 ranking says it overlaps `/agent-loops` as fan-out into worktrees. | Fan-out is a different job. Rulora does not drive a worktree. |

Gap B review trials (Elephant-Goldfish STAY I1, Chiasmus STAY I1, agentgg STAY I0) score specs, impact, or diffs. This probe did not, because `CollectiveControl.select` only checks that an id is in a frozen list. Batch-1 skill-up, SkillSpector, Strata, HiRoute, DSPy, and Bumblebee close other gaps.

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| npm | `@rulora/core@0.1.0-alpha.4` |
| integrity | `sha512-kJraV2BZBAeqnPW5/SJZy75poZq8F1/9/AfPIW8otfU32704RaoWXWTjsT/RlGw58r9lkgdOS6c2zs5fTFpteg==` |
| shasum | `5a950513241ca428c160d9a1208024ac0ba8100e` |
| npm gitHead | `5d633cfc665f48ce43686afaf87d52f9c18eb24c` (2026-10-04) |
| entry commit | `7b09de37dddcfb608b727bda26fe9396828ddc82` (2026-10-07) |
| loop-control.js sha256 | `1acfaa4439ee71c05314bf53e06645a375a6beab3e96176641a8c0f19cf40689` |
| Node | v22.23.0 |
| license | Apache-2.0 |
| install size | 533K at `~/.cache/pfy/tools/rulora/prefix` |

The entry records both the npm version and commit `7b09de37dddc`. npm `gitHead` is the older merge `5d633cfc`. `src/loop-control.js`, `src/output-boundary.js`, `src/collective-control.js`, `src/orchestration-machine.js`, and `src/index.js` are byte-identical at the entry commit and in the installed package. `package.json` differs in the published `files` list, which still names a contact image the entry commit removed. No upstream tree and no image was committed. The runnable pin is the npm version plus that integrity string.

`docs/guarantees.md` at the entry commit matches the code we ran. `LoopControl` is counters and stop states. It has no scheduler, no cost field, and no cancel of an in-flight call. `OutputBoundary` rejects only when the host function returns something other than `true`.

## Commands

Install and probe both redirect `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` under `~/.cache/pfy/tools/rulora/`. No account and no key.

```bash
CACHE=~/.cache/pfy/tools/rulora
mkdir -p "$CACHE/home" "$CACHE/xdg-cache" "$CACHE/xdg-config" "$CACHE/tmp" "$CACHE/npm-cache" "$CACHE/prefix"
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg-config" \
  XDG_CACHE_HOME="$CACHE/xdg-cache" npm_config_cache="$CACHE/npm-cache" TMPDIR="$CACHE/tmp"
npm view @rulora/core@0.1.0-alpha.4 version dist.integrity dist.shasum gitHead repository --json
npm install --prefix "$CACHE/prefix" --ignore-scripts --no-audit --no-fund @rulora/core@0.1.0-alpha.4
node eval/evq1107/rulora/probe.cjs "$CACHE/prefix/node_modules/@rulora/core" \
  > eval/evq1107/rulora/results.json
```

`npm install` added 1 package in 513 ms. The probe's own timer is `wall_ms` 5. The process finished in 22 ms. No model lock. `ollama` was not called.

## Probe

Fixture is the eight exits in `.grok/skills/agent-loops/SKILL.md`, with that skill's defaults: turn cap 8, no-progress 3, error threshold 3. The 10800 second event is the 3 hour Build timeout in the 2026-11-07 ranking (gap B). `LoopControl.record` accepts only `{progressed}`. The probe sets `progressed` from `hash_changed` and leaves every other field on the event. An exit is native when the stop stream leaves `active` and the go stream stays `active`.

The host still has to notice the state and call `record`. A lane that never calls in does not stop.

| # | Exit | Stop status | Go status | Native |
| --- | --- | ---: | ---: | --- |
| 1 | goal_met | active | active | no |
| 2 | turn_cap | exhausted, then `LOOP_CLOSED` | active (7 turns) | yes |
| 3 | budget_cap | active | active | no |
| 4 | wall_clock (10800s) | active | active | no |
| 5 | no_progress | `human_handoff` on turn 3, then `LOOP_CLOSED` | active after a hash change resets the streak | yes |
| 6 | human_interrupt | active | active | no |
| 7 | error_threshold | active (3 errors, hash still changing) | active | no |
| 8 | external_event | active | active | no |

Native count: 2/8 (`turn_cap`, `no_progress`). `wall_clock_3h_status` is `active`. `kind: 'build_lane'` throws. Allowed kinds are `network_reconnect`, `constraint_revision`, and `business_broadcast`. The no-progress stop is named `human_handoff`, so exits 5 and 6 are not distinct. The stuck trace is `active`, `active`, `human_handoff`, not `exhausted`. No-progress is checked before the attempt cap, so a stuck stream does not reach the turn cap.

`OutputBoundary` with a summary-and-evidence check: valid payload accepted, empty summary rejected at stage `core`, unknown evidence id rejected at stage `audit`. The payload `{"summary":"done","evidenceIds":["E1"],"tests_passed":false}` is accepted (`lie_accepted` true).

`CollectiveControl`: frozen evidence stays `["E1"]` after the source array is mutated, select `b` returns `b`, select `invented` throws `UNKNOWN_CANDIDATE`. 3/3 on that contract. No diff was scored.

`OrchestrationMachine` is a form workflow, reported beside the 2/8 and not added to it. Token limit 100: 40 tokens stays open (`blocked` false), 40+70 sets `blocked` true, and the next turn throws `TOKEN_BUDGET_EXHAUSTED`. A session given 1 token and no elapsed argument stays `active` (`clock_status` active, `clock_blocked` false). There is no elapsed parameter. `recordNoProgress` returns `reask`, `correct`, `human_handoff`, then the next turn throws `HUMAN_HANDOFF_REQUIRED`. Same no-progress exit, hardcoded, still no clock. The host must already know the token count. The class does not cancel an in-flight call.

## Gates

Value gate for I3 wants 3 of 4. This run has 2.

1. Gap fill: no. 2/8, and the 3 hour case stays active. agent-loops already lists the 8. neatroots already checks streaks on traces from this repo.
2. Operator leverage: no. A 5 ms counter the host must call does not make `./pfy build` stop at a deadline.
3. Evidence: yes. The command above is the offline probe. Receipt: `eval/evq1107/rulora/results.json`.
4. Blast radius: yes. Apache-2.0, 533K in the cache, no weights, no account. Nothing was wired into pregate, CI, or a gate.

Modularity, all 4, for the cache install. That does not earn I2. The ticket promotes to I2 when the probe measurably helps. This one does not. Potential is low, so the ambiguous-potential path to I2 does not apply either.

1. Local code needed: yes. The README does not score these 8 exits, does not show that no-progress is checked before the attempt cap, and does not show that a 1-token session stays active when the fixture's elapsed time is 10800 seconds. npm `gitHead` is also not the entry commit. Those facts came from running the pin.
2. Bounded surface: yes. One package. The loop API is `record` / `snapshot`.
3. Isolatable: yes. `~/.cache/pfy/tools/rulora`.
4. Reversible: yes. Delete the cache. The pin, the card, and this report remain.

Size is far under 50 MB. No in-repo copy. `tier_ceiling` stays I1. `integration_stage` is I1 (staged eval after a passed offline pin). It was I0 on the entry because there was no card.

## Risks

| How it fails | How we recover |
| --- | --- |
| The host never calls `record`, so a 3 hour run keeps going. | Keep the exit card. Do not treat the library as a supervisor. This probe's 10800s row stays `active` on purpose. |
| `human_handoff` is read as a person stopping the lane. | Exits 5 and 6 stay separate lines on the agent-loops card. The status string is the no-progress stop. |
| A shape check is read as proof the tests passed. | `lie_accepted` is true. Business checks stay in the host. |
| Alpha rename of a status or error code. | Re-run `probe.cjs` on the pinned integrity. A hash change on `loop-control.js` needs a new probe before any stage move. |
| The published tarball and the entry commit drift. | Control sources match today. The pin is the integrity string, not the short commit alone. |
| Someone wires it into pregate from this card. | `next_gate` says stay I1. This lane added no gate, no Makefile target, and no workflow step. |

## Next gate

Stay I1. A later probe has to show the 3 hour Build-lane stream stopping inside the library, or native coverage above the 2 exits measured here (turn cap and no-progress), on a fresh pin. Do not wire a gate from this result.

## Pipeline questions

Advisory only. This lane builds no pipeline, CI, or gate step.

1. What triggers it? Nothing in the product. An operator re-runs the probe when the npm pin moves. A commit does not start it.
2. What does it do, and which services does it read and write? It reads the pinned package under `~/.cache/pfy/tools/rulora/` and the eight-exit fixture in `probe.cjs`. It writes `eval/evq1107/rulora/results.json`. No model, no account, no repo mutation beyond that receipt.
3. What does it trigger next? Nothing. The receipt sits until a person reads the verdict.
4. Where does a human re-enter? After the verdict. Moving the card, or any gate wiring, is a separate ticket.
5. What stops two runs doing the same work? One worktree per slug. The cache path is this slug's install. The probe only writes its own results file. It does not take the model lock, because it never calls a model.
