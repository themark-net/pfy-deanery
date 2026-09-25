# Operator launch wizard (compose then Launch session)

Cite **#225** only. Catalog 70–75 HOLD. #198 parked. LIVE_HARD_OFF. Do not reopen #76. Do not add an Env nav tab.

Loop is the primary path. The painted job is **catalog modules** plus a live **local compute | cloud orchestration** split. Hedge picks the lane (`bulk`/`interactive` stay local when a runtime is up; `hard` spends cloud credits when `PFY_CLOUD_BUDGET` remains). **Launch session** applies enabled modules into an enterable TUI — that grok/opencode session is the proof. Attach X stays on the Attach tab. The operator window stays open.

The compose wizard (#225) still runs under Launch (runtime health, child env, review). It is not the Loop front door.

## Steps (operate-or-FAIL)

| Step | Pick | Fail / skip |
|------|------|-------------|
| 1 runtime/health | FreeToken-first live engine | FAIL + `Launch env or ./pfy up` |
| 2 model lane | `local` \| `cloud/subscription` \| `OpenCode free` | FAIL + pick lane. OpenCode free needs OpenCode. cloud/subscription needs Grok\|Claude\|Codex. LIVE_HARD_OFF: pfy does not call cloud APIs. |
| 3 toolsets/skills/modes | `bare` · `orchestration` · `code-graph` · `catalog` | orchestration missing skill → FAIL + `./pfy setup`. code-graph missing Axon and codebase-memory → FAIL + `pip install axoniq`. catalog without prompt / HOLD 70–75 → honest SKIP (not auto-lifted). |
| 4 harness/TUI | OpenCode \| Grok \| Hermes \| Codex \| Claude | FAIL + pick harness. Reuses attach-usable paths (#193/#196/#202/#220/#221). |
| 5 review paint | `runtime · lane · toolsets · harness` | Incomplete → FAIL + complete wizard. Loop Launch fills an empty toolset from enabled modules (`orchestration` or `code-graph`, else `bare`) and an empty harness from the agent selected on Loop (default grok; OpenCode when the lane is OpenCode free). |
| decision (optional, #230) | `off` \| `CUA-S1-FORMS` \| `TypeSafe` \| `mini-jev` | Off does not block Launch. TypeSafe without key → FAIL+next. `conf low` → no silent auto-act. |

Primary CTA **Launch session** → enterable TUI with composed env **or** FAIL+next. Child inherits `LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL` via attach-usable. Mode handoff via #208. Catalog prompt via #209 when toolset is catalog. Session compose **#224** paints honest lane labels (`local FreeToken-first` · `cloud/subscription (Grok-sub)` · `OpenCode free`) and enabled toolsets (SKIP/FAIL if not wired), and writes the in-session AGENTS/prompt brief on Launch.

## How to run

```bash
python3 scripts/pfy_launch_wizard_225.py --selftest
python3 scripts/pfy_launch_wizard_225.py --runtime
python3 scripts/pfy_launch_wizard_225.py --lane local
python3 scripts/pfy_launch_wizard_225.py --toolset bare
python3 scripts/pfy_launch_wizard_225.py --harness grok
python3 scripts/pfy_launch_wizard_225.py --decision cua-s1-forms
python3 scripts/pfy_launch_wizard_225.py --review
python3 scripts/pfy_jev_230.py --selftest
python3 scripts/pfy_launch_wizard_225.py --launch
python3 scripts/pfy_session_compose_224.py --selftest
./pfy launch
./pfy launch compose
python3 scripts/pfy-board.py --wizard runtime
python3 scripts/pfy-board.py --launch
python3 scripts/pfy-gui.py --selftest
bash -n scripts/pfy
```

On Loop (HTML+tk): numbered how-to on the page. **LOCAL COMPUTE** and **CLOUD ORCHESTRATION** panes each say why they exist (ON / STANDBY / SPENDING / OFF). Work-class chips and **MODULES** say what a click does. **Launch session** is the proof; Launch env only starts the local engine. Attach grok/opencode/hermes/codex/claude live on the Attach tab.

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_STATE_DIR` | `launch-wizard.json`, `launch-wizard-review.md` | composed wizard + review paint |
| `PFY_ATTACH_MODE` | child env (#208) | `bare` \| `orchestration` \| `code-graph` (catalog maps to bare + catalog prompt) |
| `PFY_CATALOG_ASK_PROMPT` | child env (#209) | next-launch catalog prompt when toolset is catalog |
| `LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL` | attach-usable child | FreeToken-first live base |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Do not

- Reopen #76 · unpark #198 · catalog 70–75 HOLD
- Add an Env nav tab
- Treat Attach X as the Loop front door
- Paint Launch session ok without composed review
- `LIVE_HARD_OFF`: no cloud embeddings / live catalog writes from this path
- Close the operator window after Launch session
