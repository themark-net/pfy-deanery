# pfy operator desktop app (spec)

**Status:** Design for implementer. Curriculum: `UX-SCHOOL.md` dump-vs-app.
**Ticket:** GitHub **#230** — cite that issue only on this PR. **#76 CLOSED** — do not reopen. Catalog **70–75 HOLD**. HOLD exception = this slice only. #228 Gab cloud lane + local sync stay. #225 wizard + Launch session stay. #207/#211 recommend/try stay the local surface. Ix **#198** parked.
**Bar:** Jev-style **decision layer** attach-usable (decision API, not chat); coding-session context compaction + model/tool choice middleware; wizard shows decision active vs Gab/Grok cloud; honesty chips never equate decision ≠ Gab `auto` ≠ local recommend. Product copy only. Title `pfy`. Operate-or-FAIL.
**Host:** Linux first (nimo: ~64 GiB 8060S VRAM pool; machineId `5c5c138b-c5f6-4ba5-a8d0-fe204735e5cc`). Mark is not the CLI operator and is not the installer. No Mark drip unless TypeSafe key is required for a smoke path (prefer local CUA-S1-FORMS smoke without Mark).
**Not this bot:** Design Bot does not implement. Prefer Grok Build on nimo after Design PASS. Copy-reviews when PM pastes a PR URL.

---

## 0. School (dump vs app)

A **status dump** paints “best model” or “AI deciding” without saying decision layer vs cloud router vs local pull. FAIL.

An **app** separates:
- **Decision layer** — Jev-style typed Choice/Score API (compaction + routing middleware); confidence thresholding honest
- **Gab cloud** — `https://gab.ai/v1`, `model=auto` (Intent Engine router) or pin-by-id
- **Local recommend/try** — FreeToken-first spine; Gab `/v1/models` open-weight families mapped to Ollama tags + host fit

**One rule still binds:** a visible control operates what it offers, or the window shows FAIL.

**IA:** Loop wizard from #225 stays primary. No Env nav tab. Attach secondary. Engine recommend/try from #207 stays the local ranking canvas. Decision layer is middleware beside lanes — not a chat pane, not a browser-use demo as core.

Lane labels (product copy):
- **local** — FreeToken-first local runtime (unchanged spine unless mini-jev is explicitly FreeToken-first)
- **cloud/subscription** — Gab (or Grok) subscription endpoint; do not claim local tools or local ranking
- **OpenCode free** — OpenCode free-model lane (do not claim Gab/Grok-sub tools)
- **decision** — Jev-style compaction/routing middleware (optional TypeSafe cloud key **or** local **CUA-S1-FORMS**; mini-jev teaching fallback)

Honesty chips (not banners):
- `decision` — typed Choice/Score active; not chat
- `gab auto` — cloud router only
- `local sync` — family signal → Ollama fit
- `decision ≠ gab auto ≠ local` — three distinct surfaces
- `conf low` / `conf ok` — threshold honesty (margin ≠ correctness claim)
- `fits` / `tight` / `won't-fit` — nimo VRAM/RAM
- `key missing` / `plus required` — Gab attach FAIL + next
- `typesafe key optional` — cloud TypeSafe path optional; local CUA-S1-FORMS preferred for Mark-free smoke

---

## 1. Why the operator still FAILs (#230)

| What they still see | Why it fails |
|---------------------|--------------|
| Decision layer painted as chat / agent conversation | Jev is **decision API** (typed Choice/Score), not chat |
| Confidence shown as “% correct” | Confidence is a **margin / certainty**; threshold per use — not a correctness guarantee |
| Core demo = browser-use / Jev Ultrafast show | Core value = **coding-session context compaction** + **model/tool choice middleware** |
| Wizard hides which layer is active | Must show decision vs Gab/Grok cloud vs local |
| Smoke needs Mark ops / TypeSafe key only | Prefer local CUA-S1-FORMS on nimo **without Mark** (mini-jev teaching fallback) |
| Decision equated with Gab `auto` or local recommend | Three different surfaces; honesty chip required |

---

## 2. Launch (window)

Bare `./pfy` → native window titled `pfy`. Window stay-open. Unchanged from #225.

---

## 3. IA — decision layer beside Gab + local (#230)

```
LOOP / wizard
lane       local | cloud/subscription | OpenCode free
decision   off | local CUA-S1-FORMS | TypeSafe (optional key) | mini-jev (fallback)
cloud      Gab · https://gab.ai/v1 · auto | pin <id>   (or Grok cloud when that lane)
chip       decision ≠ gab auto ≠ local
[ Launch session ]

ENGINE / recommend (#207 surface)
source     Gab open-weight families · local sync
rows       tag · size · fits|tight|won't-fit · local|not-local
middleware decision: compact context · choose model/tool
[ Pull ]   only fits + not-local (opt-in); never auto 405B
```

---

## 4. Views (operator copy only)

### 4a. Loop / wizard — decision layer + Gab cloud

Wireframe (product paint) — decision off, Gab cloud:

```
pfy
 Loop ●
 lane      cloud/subscription
 endpoint  Gab  https://gab.ai/v1
 model     ● auto   ○ pin  [ qwen3-coder-… ▼ ]
 decision  ○ off
 chip      gab auto · cloud router
 [ Launch session ]
```

Decision local (preferred Mark-free smoke):

```
 lane      local
 decision  ● local CUA-S1-FORMS · FreeToken-first
 chip      decision · typed Choice
 chip      decision ≠ gab auto ≠ local
 conf      threshold set · conf ok | conf low → escalate
 [ Launch session ]
```

Decision TypeSafe optional (key when present; never required for smoke):

```
 lane      cloud/subscription | local
 decision  ● TypeSafe · compaction/routing
 key       set | optional missing (local CUA-S1-FORMS still usable)
 chip      decision · typed Choice · conf margin
 chip      typesafe key optional
 [ Launch session ]
```

Attach path (secondary): same decision toggle + Gab/Grok endpoint; Loop shows attached + pid / last verb or FAIL. Decision middleware may compact session context and route model/tool choice before Launch.

Docs labels (in-window next only): TypeSafe public docs if cloud path used; Gab Plus + API key for Gab lane. No private HTML scrape. No Mark drip for default smoke.

### 4b. Core value — compaction + routing middleware (not browser demo)

Primary operator value for #230:

1. **Coding-session context compaction** — fast-jev-compaction pattern: shrink session/tool context into typed decisions the runtime can act on
2. **Model/tool choice middleware** — Choice/Score over lane + engine + tool; confidence gate before auto-act; escalate on `conf low`

Not core: browser-use / Jev Ultrafast demo as the product story. Those may exist as refs; do not paint them as the wizard primary.

### 4c. Engine — local ranking sync (#228 surface, unchanged role)

On Launch or scheduled refresh (unchanged from #228):

1. `GET https://gab.ai/v1/models` (auth optional)
2. Filter open-weight families Gab lists
3. Map → Ollama library tags + size estimate
4. Filter by host profile → `fits` / `tight` / `won't-fit`
5. Paint into existing recommend/try UI — do not replace FreeToken-first local spine

Decision middleware sits **above** recommend rows: may propose which tagged local model / tool to use; does not rewrite Gab auto as local ranking.

### 4d. Honesty copy (chips / one-liners only)

| Chip / line | Meaning |
|-------------|---------|
| `decision · typed Choice` | Decision API active; not a chat transcript |
| `conf margin` / `conf ok` / `conf low` | Confidence is certainty margin; low → escalate / human / fallback — not “% correct” |
| `gab auto · cloud router` | Best on Gab = Intent Engine `model=auto` |
| `local sync · family signal` | Gab open-weight families + hardware fit |
| `decision ≠ gab auto ≠ local` | Three surfaces; never collapse them |
| `typesafe key optional` | Cloud TypeSafe attach optional; local CUA-S1-FORMS smoke does not need Mark |

Ban: “Jev chat”, “AI is X% sure this is correct”, equating decision with Gab auto or local recommend, browser-use as core value, consultant chrome, Env tab.

### 4e. Attach paths (operate-or-FAIL)

| Path | When | Smoke |
|------|------|-------|
| **(a) TypeSafe optional** | `TYPESAFE_*` / documented key present → compaction/routing via TypeSafe Jev cloud | Optional; FAIL+next if toggled on without key |
| **(b) local CUA-S1-FORMS** | FreeToken-first on nimo; ~706K / ~2.8MB form-fill specialist (`trycua/cua`) | **Preferred** Mark-free smoke |
| **(c) mini-jev** | Teaching fallback only | Not primary local |

FreeToken-first local spine **unchanged** unless the mini-jev path is explicitly documented FreeToken-first (it should be).

### 4f. Not this PR

- Catalog 70–75 lift; reopen #76; #198; Env tab; invent Gab-hosted GGUF; change FreeToken-first order (except explicit mini-jev FreeToken-first); Mark drip for default smoke; browser-use as core; chat UI for Jev

---

## 5. Ban from the window

- Painting decision layer as chat
- Claiming confidence = correctness probability
- Equating decision with Gab `auto` or local recommend order
- Browser-use / Ultrafast as the primary product story
- Claiming Gab hosts downloadable weights
- Auto-pull / silent pull of 405B-class
- Scraping Gab / TypeSafe private HTML
- Consultant chrome (adapter / nimo theology / honest-state / `pfy board` / `:8765`)
- Env nav tab; fake green; requiring Mark for smoke
- Implying local toolsets on Gab cloud lane

---

## 6. FAIL checklist (every #230 PR)

Score **PASS / FAIL / N/A**. Cite **#230** only. Launch is Tester.

1. **Decision API.** Wizard/Attach paints Jev-style as typed decision (Choice/Score), not chat. HTML + tk.
2. **Confidence honesty.** Chip/one-liner: margin ≠ correctness; `conf low` escalates or FAILs visibly — no silent auto-act below threshold.
3. **Attach paths.** (a) TypeSafe key optional when present for compaction/routing; (b) local CUA-S1-FORMS FreeToken-first on nimo operates or FAIL (mini-jev fallback).
4. **Core value.** Compaction + model/tool middleware visible; browser-use not painted as core.
5. **Wizard clarity.** Chip or control shows decision active vs Gab/Grok cloud vs local.
6. **Smoke.** CUA-S1-FORMS Choice on nimo without Mark ops (mini-jev teaching fallback).
7. **Honesty.** `decision ≠ gab auto ≠ local`. FreeToken-first spine hold. #225 Launch intact. No Env tab.
8. **Not this slice.** Catalog 70–75; reopen #76; private scrape; Mark drip for default smoke.

**PASS sketch:**

```
lane       local
decision   ● local CUA-S1-FORMS · FreeToken-first
chip       decision · typed Choice · conf ok
chip       decision ≠ gab auto ≠ local

Engine recommend
 qwen3-coder:30b  fits  local
 chip      gab auto ≠ local ranking
```

---

## 7–9. Tech / will not build / consultant bind

- Extend #225 wizard state for decision toggle (off | local CUA-S1-FORMS | TypeSafe optional | mini-jev fallback).
- Optional TypeSafe cloud client when key present; CUA-S1-FORMS local path for offline nimo.
- Compaction middleware: session/tool context → typed decisions (fast-jev-compaction pattern as attach, not rewrite of product).
- Routing middleware: Choice over model/tool with confidence gate.
- Chips == live truth. Prefer Grok Build on nimo (`5c5c138b-c5f6-4ba5-a8d0-fe204735e5cc`).
- Will not: private HTML scrape; chat UI for Jev; browser-use as core; reopen #76; lift catalog 70–75; Mark drip for default smoke; equate decision with Gab auto.

Public framing only: https://typesafe.ai/ (decisions not chat; calibrated confidence); https://github.com/r-ms/mini-jev; https://github.com/tamaratran/fast-jev-compaction. Refs only — do not scrape private.

---

## 10. Implementer DoD (binds #230)

One PR from current main. Cite **#230 only**. Do not reopen **#76**. Catalog 70–75 HOLD (HOLD exception = this slice). Prefer Grok Build on nimo. No Mark drip for default smoke. See also a private ops note.

1. Decision layer: typed Choice/Score API surface in wizard/Attach — not chat; honest confidence thresholding.
2. Attach (a) optional TypeSafe key compaction/routing; (b) local CUA-S1-FORMS FreeToken-first on nimo.
3. Core: coding-session context compaction + model/tool choice middleware (not browser-use demo).
4. Wizard clarity: decision active vs Gab/Grok cloud; honesty chip `decision ≠ gab auto ≠ local`.
5. Smoke: CUA-S1-FORMS Choice on nimo without Mark ops (mini-jev teaching fallback).
6. FreeToken-first spine unchanged (unless mini-jev explicitly FreeToken-first). HTML + tk. Tester launch-pass. Reviewer + Design clear.

Design Bot copy-reviews when PM pastes a PR URL. Do not implement.
