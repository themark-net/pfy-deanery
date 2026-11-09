# #243 Loop UX journey — catalog modules + live local/cloud hedge

**Cite:** GitHub **#243** only. Catalog **#70–#75** out. Do not reopen **#76**. No operator ops.
**Head:** `3cb788a6ed5f76c13da356b6cd9ece3b9945d15d` on `cursor/pr11-loop-local-cloud-ux-055e`
**Base tip for work:** `main` @ `e797151c47e10e2667cf72b6bcaca0d1ea1c521d`
**T:** T-0125

---

## Operator job (one sentence)

Open **Loop**, see where work can run, pick how hard it is, click which gathered catalog tools ride along, then **Launch session** — a grok or OpenCode window with those modules loaded is the proof.

---

## Happy path (numbered)

1. Open native window (`./pfy` / `./pfy board`) → **Loop**.
2. Read lede + numbered how-to (gathered tools — not a harness picker).
3. See **Local compute** (ON|OFF) and **Cloud orchestration** (STANDBY|SPENDING|OFF) with why-lines.
4. Read live route sentence: where *this* session will run, or next step if it cannot.
5. Pick work class: **Bulk** (stay local) · **Interactive** (local first) · **Hard** (may spend cloud).
6. Click **MODULES** to include; **not wired**/stub cannot enable (STUB/FAIL in-window).
7. **Launch session** → applies enabled modules → enterable grok/OpenCode (proof).
8. Optional: **Launch env** starts local model only (no coding session).

---

## Fail / next paths

| Condition | Paint | Next |
|-----------|-------|------|
| Local OFF + cloud OFF | Not ready · FAIL | Launch env or set `PFY_CLOUD_BUDGET` |
| Stub module enable | STUB | how from toolset cell |
| Unknown module | FAIL module | pick listed id |
| Bad task | FAIL task | bulk \| interactive \| hard |
| Launch session cannot prove | FAIL Launch session + next | Launch env / budget / wire module |

---

## Other tabs (one-line ledes only)

| Tab | Lede job |
|-----|----------|
| Engine | Local model — not the coding session; Loop → Launch session is |
| Attach | Open grok/OpenCode now without composing modules |
| Tools | Skills + catalog — does not start a session |
| Stage | Env check; SKIP = missing (no Stage redesign) |

---

## Proof

Enterable grok/OpenCode after **Launch session**, with enabled modules applied. Attach is not the composed-modules proof path.
