# #243 Loop UX - wireframes (ASCII)

**Cite:** #243 · operator chrome only

---

## Loop - local ON, interactive

```
┌─ pfy ─────────────────────────────────────────────────────────┐
│ Loop*  Engine  Stage  Attach  Tools                           │
│ Loop is the product. Other tabs are details.                  │
├───────────────────────────────────────────────────────────────┤
│ LOOP                                                          │
│ This screen runs the catalog tools we gathered. …             │
│ That window is the proof they work together.                  │
│                                                               │
│ HOW TO                                                        │
│  1 See where work can run                                     │
│  2 Pick work class so cheap jobs stay local                   │
│  3 Click modules to include (stub = not wired)                │
│  4 Launch session  ·  Launch env = local model only           │
│                                                               │
│ 1. Where can this work run?                                   │
│ ┌ Local compute ──────────┐  ┌ Cloud orchestration ─────────┐ │
│ │ why: model on this box  │  │ why: leftover credits        │ │
│ │ ON                      │  │ STANDBY                      │ │
│ │ engine  freetoken       │  │ budget 3 · spent 0 · left 3  │ │
│ │ status  ready           │  │ profile (unset) · gab missing│ │
│ │ endpoint http://…/v1    │  │ Credits remain. Cloud idle…  │ │
│ │ A model is answering…   │  │                              │ │
│ └─────────────────────────┘  └──────────────────────────────┘ │
│                                                               │
│ This session will run on your machine (freetoken).            │
│ this session  READY                                           │
│                                                               │
│ 2. How hard?                                                  │
│ [ Bulk - stay on this machine ]                               │
│ [ Interactive - local first ]●                                │
│ [ Hard - allow cloud ]                                        │
│                                                               │
│ 3. MODULES                                                    │
│ [ jev     wired      click to include ]                       │
│ [ orch    wired      in next session ]●                       │
│ [ gab     partial    click to include ]                       │
│ [ ghost   not wired  cannot enable ] (disabled)               │
│ enabled  orch                                                 │
│                                                               │
│ 4. Open                                                       │
│ [ Launch session ]  [ Launch env ]  [ Copy endpoint ]         │
│ READY Launch session - grok · modules applied                 │
└───────────────────────────────────────────────────────────────┘
```

---

## Loop - not ready

```
│ Local compute: OFF · status missing                           │
│ Cloud orchestration: OFF · left 0                             │
│ Not ready to run a session.                                   │
│ Next: Launch env or set PFY_CLOUD_BUDGET.                     │
│ this session  FAIL                                            │
```

---

## Loop - Hard / SPENDING

```
│ Hard - allow cloud ●                                          │
│ Cloud orchestration: SPENDING                                 │
│ This session will spend one cloud credit.                     │
```

---

## Other tabs - lede only

```
ENGINE  - local model tab; Loop → Launch session is the coding session
ATTACH  - open grok/OpenCode now without composing modules
TOOLS   - skills + catalog; does not start a session
```

---

## FAIL+next (in-window)

```
STUB module ghost - not implementable yet
Next: <how from toolsets.json>

FAIL Launch session - local missing
Next: Launch env or ./pfy up
```
