# UX school — pfy operator window

**Product:** local-first LLM orchestrator. Native window titled `pfy`. Compose wizard + Launch session. Jev-style decision layer (typed Choice/Score; compaction + routing) beside Gab cloud lane (`https://gab.ai/v1` auto/pin) + local recommend sync. Cite **#230** only on this PR. Do not reopen #76.

**Not:** a leftover HTTP dump (`pfy board`, `:8765`, start via CLI, GitHub issue rail). Not Chrome. Not a localhost board URL. Not `NATIVE-SPEC.md` one-screen board as IA (see `DESKTOP-SPEC.md`). This file is curriculum for Design Bot PR scoring. Do not implement product code from it.

**Sources:** Nielsen 10 heuristics ([NN/g](https://www.nngroup.com/articles/ten-usability-heuristics/), 1994 / reviewed 2024). Norman: affordance, signifier, mapping, feedback (*Design of Everyday Things*). Operator-desktop class: [Warp blocks](https://docs.warp.dev/terminal/blocks/) (session canvas, command runs, exit state on the block), [Raycast Action Panel](https://manual.raycast.com/action-panel) (selected item + Enter runs the primary action), [Linear desktop](https://linear.app/docs/get-the-app) (native window, sidebar place, work lives in the canvas — not “open Chrome”).

---

## 0. One rule

A visible control must operate what it offers, or the window must show **FAIL**. Silent no-op is FAIL.

**#230 decision layer (school add):** Jev is a **decision API** (typed Choice/Score), not chat. Confidence is a certainty **margin**, not a correctness %. Paint decision active vs Gab/Grok cloud vs local with honesty chip `decision ≠ gab auto ≠ local`. Core value = coding-session context compaction + model/tool middleware — not browser-use demo. Prefer local **CUA-S1-FORMS** FreeToken-first smoke on nimo without the operator (mini-jev teaching fallback).


---

## 1. Affordance (Norman)

Affordance = what the control can actually do. Signifier = the visible cue that it can do that. Mapping = control ↔ outcome. Feedback = the operator sees the result in the same window, fast.

On this surface:

| Signifier in the window | Must do | Else |
|-------------------------|---------|------|
| Sidebar Loop / Engine / Stage / Attach | Look like controls. Selected state is obvious. Click switches the canvas. | FAIL — labels, not nav |
| Launch env | Inference + env-stage (same as bare `./pfy`). Loop shows PASS env / FAIL env. No harness exec. | Silent no-op / missing button = FAIL |
| Attach grok / Attach opencode | Spawn sidecar; Loop shows attached + pid / last verb. OpenCode is the operated bot; Grok optional monitor. | FAIL in-window (`pfy harness use grok`) — never mute `#attachmsg`, never fetch-throw-and-vanish |
| Refresh status | Re-poll; chips/tape change or FAIL | Silent no-op is FAIL |
| Copy stub one-liner | Clipboard gets the one-liner; in-window confirm | Silent no-op is FAIL |
| Harness chip hit | Start / inspect | GitHub `issue` `<a>` as the only click is FAIL |

False affordance is FAIL: a button that looks pressable and does nothing; nav that looks selected everywhere or nowhere; a chip that looks like an action but only opens GitHub.

If JS never bound, `/start` is missing, or the toolkit path has no handler: the control still exists in chrome — so the window must FAIL visibly. “It would have worked if the script loaded” is not a product.

---

## 2. Product copy vs design notes

The window is for the operator. Specs, ADRs, and this school are for bots. **Do not ship design notes as chrome.**

Engine view: engine name + READY (or PARTIAL / MISSING / SKIP / FAIL) chip. That is enough. Detector order, adapter lectures, and host theology stay in docs.

### Ban from the window (exact or paraphrase)

| Banned in-window | Why | Put it |
|------------------|-----|--------|
| “Ollama is an adapter, not the product” | Design note. Operator needs engine + chip. | ADR / spec |
| nimo-as-Actions-runner lectures (“nimo is an Actions runner with Ollama :11434, not a pfy profile”) | Host theology. Hostname can live in the title bar as `host`. | Spec § nimo |
| “honest state:” banners | Consultant voice. Honesty is the chip word, not a lecture. | Poller / chips |
| “pfy board” | Old product identity. Window title is `pfy`. | Legacy alias docs |
| `127.0.0.1:8765` as identity | Reads as “open Chrome.” URL is engine detail, not the app. | Hatch `--open` only |
| “Board does not spawn…” | Explaining architecture to the operator. Attach either runs or FAILs. | Spec process-ownership |

Also out: fake green, `unknown` chips, “attach sidecar” labels, login forms, git, GUI-toolchain one-liners, `board: http://…` on the primary path.

Honesty tokens stay as **chips**, not prose: `ready` / `partial` / `stub` / `detected-stub` / `missing` / `skip`. Unparsed = `missing`. Local pane tint only when engine live is ready.

---

## 3. Status dump vs app

A **status dump** is a poster: `pfy board` + `127.0.0.1:8765`, chip wall, GitHub issue rail, banners, “honest state,” **start via CLI**. The operator reads. Nothing runs. That is the #128 eval (leftover listener on `:8765`).

An **app** (Grok Bot / Warp / Raycast / Linear class — the class, not clones):

| Class pattern | In those products | In `pfy` |
|---------------|-------------------|----------|
| Native window | OS window, dock, not a tab you were told to open | Title `pfy`. Never load leftover `:8765`. Never print a board URL as the UI. |
| Selected place | Sidebar / list item is obviously current | Loop / Engine / Stage / Attach. One selected. Canvas switches. |
| Session canvas | Warp: command+output is a block. Linear: the issue. Raycast: the selected item. Grok Bot-class: the conversation. | Loop = env, last verb, next Launch env, then Attach opencode. Not split-pane plus five-button ribbon. |
| Actions that run | Raycast Enter = primary action. Warp Enter = the command. Linear shortcuts change work. | Verbs live with the selected view (Launch env on Loop, Run stage on Stage). Visible result or FAIL. |

Do not clone Grok Bot roster, billing, or computer-update rows. Do not clone Warp’s terminal grid. Steal the *shape*: window, place, canvas, verbs.

If the only native hit is a GitHub issue link, it is a dump with a hyperlink. FAIL.

---

## 4. Nielsen → this operator surface

Credit: Jakob Nielsen, [10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/). One line each, mapped.

1. **Visibility of system status** — Header + tape + chips always say engine / attach / last verb now; every click paints success, working, or FAIL in-window before the operator wonders.
2. **Match the real world** — Operator words: Launch env, Attach opencode, Attach grok, READY, FAIL. Not adapter, board, sidecar, honest-state, Actions-runner.
3. **User control and freedom** — Window owns the process; Attach is a sidecar the operator starts; continue/cage shows FAIL + `pfy harness use grok` with buttons disabled — no surprise spawn, no trapping them in a dump.
4. **Error prevention** — Do not offer a control that cannot run (or disable it with a reason); do not make issue URLs the only hit; do not print `127.0.0.1:8765` as the way in; do not load a leftover listener just because the port answered.
5. **Recognition rather than recall** — Selected nav, live chips, attached id, last verb, and the four primary actions stay on screen. No lecture to memorize from a banner.
6. **Help users recover** — FAIL copy is plain, in-window, next to the control, with the one-liner (`pfy harness use grok` / Copy stub). Never a silent miss, never an error code, never “open Chrome and see.”

Also binds (do not score as extra essays): consistency (same IA on Tauri / tk / HTML host), aesthetic/minimalist (engine + chip, not banners), shortcuts later — not a substitute for visible controls.

---

## 5. FAIL checklist (Design Bot scores a PR)

Score each row **PASS / FAIL / N/A**. One FAIL fails the PR. Window-opens stays Reviewer. Cite **#230** only. Do not implement. Decision layer: not chat; conf margin ≠ correctness; `decision ≠ gab auto ≠ local`; operator-free mini-jev smoke; no Env tab.

1. **Leftover listener.** If `:8765` / `PFY_BOARD_PORT` is already serving foreign or old HTML, do not load it. Bind current frontend or replace the occupant. Kill/lsof/open-Chrome copy to the operator = FAIL.
2. **Silent no-op / start via CLI.** Any visible control (sidebar, Launch env, Attach grok, Attach opencode, Run stage, Refresh status, Copy stub one-liner) either performs the offered action or shows FAIL in-window. Silent Launch env (no PASS/FAIL/SKIP paint) = FAIL. Missing **Launch env** on Loop = FAIL. **start via CLI** as a control or label = FAIL. Fetch throw / unbound JS / missing `/start` that leaves chrome unchanged = FAIL.
3. **False affordance.** Sidebar items look and act as controls; selected state is visible; click switches the canvas. Borderless text that cannot be told from a label = FAIL.
4. **Attach result.** Success = sidecar pid / attached id on Loop. Blocked (continue / agent-cage, missing harness) = FAIL copy `pfy harness use grok`, buttons disabled. No fallback spawn. Mute toast that needs `{ok, pid}` and vanishes = FAIL.
5. **Banned copy.** Window chrome contains none of: “Ollama is an adapter, not the product”; nimo-as-Actions-runner lectures; “honest state:” banners; “pfy board”; `127.0.0.1:8765` as identity; “Board does not spawn…”; **start via CLI**; `local = bulk · Grok = DoD`. Engine name + READY chip is enough.
6. **Dump vs app.** Loop is the session (env, last verb, next Launch env). Split LOCAL/CLOUD plus a five-button ribbon on every view = FAIL. Honesty-rail GitHub issue index = FAIL. Issue `<a>` as the only or primary hit = FAIL.
7. **Identity.** Title `pfy`. Quiet header host · profile. Primary path never prints a board URL or GUI-toolchain one-liner. Not Chrome. Not a leftover localhost board.
8. **Honesty without lecture + host parity.** Chips bind `./pfy status` live (`ready` / `partial` / `stub` / `detected-stub` / `missing` / `skip`). Unparsed = `missing`, never `unknown`. No fake green. No “honest state:” prose. Same IA on HTML/Tauri (when fresh) and tk. Org omitted when unused. No credentials. No git.

**PASS sketch (do not ship this as a screenshot caption):**

```
pfy
 Loop ●          env       READY
 Engine          last      Launch env
 Stage           [ Launch env ]
 Attach          [ Attach opencode ]  [ Attach grok ]
```

If Launch env cannot run: same chrome, FAIL env on the canvas — not a banner about boards, adapters, or nimo, not start via CLI.
