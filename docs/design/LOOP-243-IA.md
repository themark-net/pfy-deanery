# #243 Loop UX - information architecture

**Cite:** #243 · T-0125 · head `3cb788a6ed5f76c13da356b6cd9ece3b9945d15d`

---

## Hierarchy

```
pfy (native window)
├── Loop     ← product front door (default)
├── Engine   ← local model detail
├── Stage    ← env-stage honesty
├── Attach   ← bare TUI open (no module compose)
├── Tools    ← skills + catalog (no session start)
└── Org      ← collapsed unless used
```

---

## Loop canvas (ordered)

1. **Lede** - gathered catalog tools → Launch session proof
2. **How-to** - 4 numbered steps
3. **Where work runs**
   - Local compute: ON/OFF · engine · status (`missing` not `unknown`) · endpoint · meaning
   - Cloud orchestration: STANDBY/SPENDING/OFF · budget/spent/left · profile · gab key · meaning
4. **Live sentence** - `route` (+ `next_step` when not ok) · this-session chip
5. **How hard** - Bulk / Interactive / Hard
6. **MODULES** - wired / partial / not wired; stub cannot enable
7. **Open** - Launch session (proof) · Launch env (model only) · copy helpers

Compose wizard (#225) runs **under** Launch - not Loop front door. No harness picker on Loop.

---

## State words

| Surface | Allowed tokens |
|---------|----------------|
| Local live | ready / partial / missing / skip / FAIL - never unknown |
| Local lane | ON / OFF |
| Cloud lane | STANDBY / SPENDING / OFF |
| Module (operator) | wired · partial · not wired |
| Actions | READY / FAIL / STUB / SKIP in-window |

---

## Code → paint map

| Concern | Source | Surfaces |
|---------|--------|----------|
| story / meanings / route | `pfylib/loop_paint.py` `story()` + `fields()` | HTML + tk |
| Module toggle | `POST /module` → `loop_paint.toggle` | HTML + tk chips |
| Task class | `POST /loop/task` → `loop_paint.set_task` | Bulk/Interactive/Hard |
| Launch applies modules | board launch → `loop_paint.apply_enabled` | Launch session |
| Hedge decide | `pfylib/hedge.py` | panes + route |
