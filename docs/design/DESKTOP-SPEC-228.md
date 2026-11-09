# pfy operator desktop app (spec)

**Status:** Design for implementer. Curriculum: `UX-SCHOOL.md` dump-vs-app.
**Ticket:** GitHub **#228** — cite that issue only on this PR. **#76 CLOSED** — do not reopen. Catalog **70–75 HOLD**. Ix **#198** parked. #225 wizard + Launch session stay. #207/#211 recommend/try stay the local surface.
**Bar:** Gab cloud lane attach-usable; local recommend syncs Gab open-weight family signals → Ollama tags sized for nimo; honesty chips never equate Gab `auto` with local ranking. Product copy only. Title `pfy`. Operate-or-FAIL.
**Host:** Linux first (nimo: ~64 GiB 8060S VRAM pool). Mark is not the CLI operator and is not the installer.
**Not this bot:** Design Bot does not implement. Prefer Grok Build on nimo. Copy-reviews when PM pastes a PR URL.

---

## 0. School (dump vs app)

A **status dump** paints “best model” without saying cloud router vs local pull. FAIL.

An **app** separates:
- **Gab cloud** — `https://gab.ai/v1`, `model=auto` (Intent Engine router) or pin-by-id
- **Local recommend/try** — FreeToken-first spine; Gab `/v1/models` open-weight families mapped to Ollama tags + host fit

**One rule still binds:** a visible control operates what it offers, or the window shows FAIL.

**IA:** Loop wizard from #225 stays primary. No Env nav tab. Attach secondary. Engine recommend/try from #207 stays the local ranking canvas.

Lane labels (product copy):
- **local** — FreeToken-first local runtime (unchanged spine)
- **cloud/subscription** — Gab (or Grok) subscription endpoint; do not claim local tools or local ranking
- **OpenCode free** — OpenCode free-model lane (do not claim Gab/Grok-sub tools)

Honesty chips (not banners):
- `gab auto` — cloud router only
- `local sync` — family signal → Ollama fit
- `fits` / `tight` / `won't-fit` — nimo VRAM/RAM
- `key missing` / `plus required` — Gab attach FAIL + next

---

## 1. Why the operator still FAILs (#228)

| What they still see | Why it fails |
|---------------------|--------------|
| “Best” implied as local GGUF leaderboard from Gab | Gab does **not** publish local-download ranking; best = cloud `model=auto` |
| No Gab attach / wizard endpoint | Cloud lane unusable |
| Recommend ignores Gab open-weight families | Reinvents hardware bake-off; drifts from Gab coding/agents signal |
| Pull offered for 405B-class without opt-in | Dangerous / dishonest |
| Copy claims Gab hosts downloadable weights | Lie |

---

## 2. Launch (window)

Bare `./pfy` → native window titled `pfy`. Window stay-open. Unchanged from #225.

---

## 3. IA — Gab cloud + local sync (this PR)

```
LOOP / wizard
lane       local | cloud/subscription | OpenCode free
cloud      Gab · https://gab.ai/v1 · auto | pin <id>
key        set | missing → FAIL + docs next
[ Launch session ]

ENGINE / recommend (#207 surface)
source     Gab open-weight families · local sync
rows       tag · size · fits|tight|won't-fit · local|not-local
[ Pull ]   only fits + not-local (opt-in); never auto 405B
chip       gab auto ≠ local ranking
```

---

## 4. Views (operator copy only)

### 4a. Loop / wizard — Gab cloud lane

Wireframe (product paint):

```
pfy
 Loop ●
 lane     cloud/subscription
 endpoint Gab  https://gab.ai/v1
 model    ○ auto   ○ pin  [ qwen3-coder-… ▼ ]
 key      missing
          FAIL  set GAB_API_KEY · Plus/max plan
          next  gab.ai/docs/api-auth
 [ Launch session ]  disabled until key or honest SKIP
```

When key present:

```
 lane     cloud/subscription
 endpoint Gab  https://gab.ai/v1
 model    ● auto
 chip     gab auto · cloud router
 [ Launch session ]
```

Pin-by-id: dropdown/field uses exact ids from `GET /v1/models` (auth optional for list). Launch wires OpenAI-compatible base URL + Bearer key. Do not invent cloud toolsets.

Attach path (secondary): same endpoint + auto/pin; Loop shows attached + pid / last verb or FAIL.

Docs labels (in-window next only, not lecture): Plus required for API; max/Plus plan + API key — link `https://gab.ai/docs/api` / `https://gab.ai/docs/api-auth`. No private HTML scrape.

### 4b. Engine — local ranking sync into recommend/try (#207)

On Launch or scheduled refresh:

1. `GET https://gab.ai/v1/models` (auth optional)
2. Filter open-weight families Gab lists (gemma / qwen / deepseek / glm / kimi / …)
3. Map → Ollama library tags + size estimate
4. Filter by host profile (nimo ~64 GiB VRAM / ~61 GiB RAM) → `fits` / `tight` / `won't-fit`
5. Paint into existing recommend/try UI — do not replace FreeToken-first local spine

Wireframe:

```
 Engine ●
 recommend  local sync · Gab families
 chip       gab auto ≠ local ranking

 qwen3-coder:30b     ~20G   fits      local
 gemma4:26b          ~17G   fits      local
 glm-4.7-flash       ~12G   fits      not-local   [ Pull ]
 qwen2.5:72b         ~40G   tight     not-local   [ Pull ]  (opt-in confirm)
 llama-405b          ~220G  won't-fit —           disabled
                            FAIL won't-fit · next smaller Q4 ≤32B

 [ Refresh sync ]
```

Comfortable tiers (nimo): prefer ≤~32B Q4 for snappy agent loops; allow 70B–120B when free VRAM ≥40 GiB **and** operator opts in. Prefer overlap already on nimo (`gemma4:26b`, `qwen3-coder:30b`, `qwen3-coder-next`, `qwen2.5-coder:32b`, `gpt-oss:120b`, `glm-4.7-flash`, …).

### 4c. Pull path

- One-click Engine **Pull** or `./pfy` action → `ollama pull <tag>` for recommended-not-yet-local that **fits**
- `tight` → confirm gate
- `won't-fit` → control disabled + FAIL + next (smaller tag)
- Never auto-pull 405B-class without explicit opt-in
- After pull: re-probe recommend; do not paint live until endpoint lists it (same #207 handoff)

### 4d. Honesty copy (chips / one-liners only)

| Chip / line | Meaning |
|-------------|---------|
| `gab auto · cloud router` | Best on Gab = Intent Engine `model=auto` on `https://gab.ai/v1` |
| `local sync · family signal` | We mirror Gab open-weight / `recommended_for` families + hardware fit |
| `gab auto ≠ local ranking` | Never imply Gab publishes a local-download leaderboard |

Ban: “Gab best local model”, “download from Gab”, scrape private pages, consultant chrome.

### 4e. Not this PR

- Catalog 70–75 lift; reopen #76; #198; Env tab; invent Gab-hosted GGUF; HF API as ranking source; change FreeToken-first order

---

## 5. Ban from the window

- Equating Gab `auto` with local recommend order
- Claiming Gab hosts downloadable weights
- Auto-pull / silent pull of 405B-class
- Scraping Gab private HTML
- Consultant chrome (adapter / nimo theology / honest-state / `pfy board` / `:8765`)
- Env nav tab; fake green; credential fields beyond Gab key path already used for cloud attach
- Implying local toolsets on Gab cloud lane

---

## 6. FAIL checklist (every #228 PR)

Score **PASS / FAIL / N/A**. Cite **#228** only. Launch is Tester.

1. **Gab cloud lane.** Wizard/Attach usable: base `https://gab.ai/v1`, `auto` + pin-by-id. HTML + tk.
2. **Key FAIL+next.** Missing key / Plus-required → FAIL in-window + docs next; no silent Launch.
3. **Local sync.** Recommend/try fetches `/v1/models`, filters open-weight families, maps Ollama tags, paints fits/tight/won't-fit for host.
4. **Pull.** Fits + not-local → Pull operates (`ollama pull`) or FAIL; won't-fit disabled + next; no auto 405B.
5. **Honesty.** Chip or one-liner: Gab auto ≠ local ranking. No Gab-hosts-weights claim.
6. **Spine hold.** FreeToken-first local unchanged. #225 Launch session intact. No Env tab.
7. **Not this slice.** Catalog 70–75; reopen #76; private scrape.

**PASS sketch:**

```
lane       cloud/subscription · Gab · auto
chip       gab auto · cloud router

Engine recommend
 qwen3-coder:30b  fits  local
 glm-4.7-flash    fits  not-local  [ Pull ]
 chip      gab auto ≠ local ranking
```

---

## 7–9. Tech / will not build / consultant bind

- Extend #225 wizard state + Attach handoff for Gab endpoint/env (`GAB_API_KEY` / `GAB_AI_API_KEY`, base URL).
- Extend #207 recommend path: Gab models fixture for CI (offline); live fetch on Launch/refresh.
- Chips == live truth. Prefer Grok Build on nimo.
- Will not: private HTML scrape; claim downloadable Gab weights; auto-pull huge tags; reopen #76; lift catalog 70–75.

Public endpoint labels only (https://gab.ai/docs/api): OpenAI-compatible `https://gab.ai/v1`; `GET /v1/models`; `model=auto` cloud Intent Engine; Plus required for API.

---

## 10. Implementer DoD (binds #228)

One PR from current main. Cite **#228 only**. Do not reopen **#76**. Catalog 70–75 HOLD. Prefer Grok Build on nimo. No Mark. See also a private ops note.

1. Cloud lane: Gab OpenAI-compatible attach/wizard — auto + pin-by-id; max/Plus + API key docs as FAIL next.
2. Local ranking sync into existing recommend/try (#207): `/v1/models` → open-weight families → Ollama tags + size → fits/tight/won't-fit (nimo).
3. Pull path for recommended-not-yet-local that fit (opt-in for tight/large).
4. Honesty: Gab auto ≠ local ranking; never imply Gab hosts weights.
5. Tests: offline fixture of Gab `/models` JSON; no network required in CI.
6. FreeToken-first spine unchanged. HTML + tk. Tester launch-pass. Reviewer + Design clear.

Design Bot copy-reviews when PM pastes a PR URL. Do not implement.
