# Jev decision layer × org bots × pfy-deanery dogfood

**Status:** Plan (docs-only)  
**Date:** 2026-10-04 (PT)  
**Owner ask:** Integrate TypeSafe Jev with Grok Bot org + Grok Build on nimo, and with pfy-deanery; dogfood whether `./pfy` + catalog tooling can replace or augment bare `grok -p` for bots and a human dev.  
**Related:** [#230](https://github.com/themark-net/pfy-deanery/issues/230) · [ADR-0016](../adr/0016-jev-decision-layer.md) · [ops/jev-230.md](../ops/jev-230.md) · [ops/integration-stages.md](../ops/integration-stages.md) · org skill `org-spinny-decide` · `themark-net/org-spinny-decide`

---

## 0. Inventory (2026-10-04)

### Already in pfy-deanery (wired, local-first)

| Asset | Path / surface | Calls cloud TypeSafe? |
|-------|----------------|------------------------|
| ADR | `docs/adr/0016-jev-decision-layer.md` | No — pins optional cloud |
| Ops / module | `docs/ops/jev-230.md`, `docs/modules/jev-230.md` | Documents optional key |
| Design locks | `docs/design/JEV-230-*.md` | — |
| Implementation | `scripts/pfy_jev_230.py` (~1.1k LOC) | **Only if** `TYPESAFE_API_KEY` set; raw `POST https://api.typesafe.ai/v1/systemone` via `urllib` (**no** `typesafe-sdk` import) |
| CLI | `./pfy decision` (`smoke` / `route` / `compact` / `queue` / path toggles) | Smoke = CUA-S1-FORMS, operator-free |
| Toolset | `data/toolsets.json` id `jev` (`catalog_tool: null` by design) | Lane local = CUA / mini-jev; cloud = TypeSafe |
| Skills (SoT) | `bootstrap/grok-cli/skills/jev-decision/SKILL.md` | Points at optional cloud + official TypeSafe skill |
| Applied skill | `./pfy toolset apply jev --harness grok` → `GROK_HOME/skills/pfy-jev-decision` | Local |
| Env registry | `bootstrap/env/REGISTRY.md` + `env.example` (`# TYPESAFE_API_KEY=`) | Optional; never required for smoke |
| Selftest | `python3 scripts/pfy_jev_230.py --selftest` | Offline PASS on nimo (2026-10-04) |
| Smoke | `./pfy decision smoke` | READY · CUA-S1-FORMS (2026-10-04) |

**Verified on nimo:** `typesafe-sdk` **not** installed; shell `TYPESAFE_API_KEY` **unset**; `.env` / `.env.bak` have **no** key line; only commented placeholder in `bootstrap/env/env.example`. **No live TypeSafe API calls** were made for this plan.

### Org / bot surfaces (local System-One style, not cloud Jev)

| Asset | Where | Notes |
|-------|-------|-------|
| `org-spinny-decide` package | `~/DEVELOP/org-spinny-decide` → `themark-net/org-spinny-decide` | Ollama Choice gates (`push_hold`, `nimo_yield`, `pm_route`); README: **Not cloud TypeSafe** |
| Org agent skill | `$HOME/agent-data/workflows/org-spinny-decide/SKILL.md` | Same: **No cloud TypeSafe** |
| Bot coordination | `bots-coordinate-build-and-cursor-execute` | Explicitly: use org-spinny-decide for cheap gates; heavy implement → Grok Build / Cursor |
| Grok Build | `use-grok-build-on-nimo` | Headless: `~/.local/bin/grok -p … --cwd <worktree> --always-approve` |
| nimo Grok skills | `~/.grok/skills/jev-decision`, `pfy-jev-decision` | Present; Pfy apply path |

### Official TypeSafe (verified 2026-10-04, not the viral article)

| Fact | Source |
|------|--------|
| PyPI package | `typesafe-sdk` **0.7.2** (TypeSafe AI / Daniel Gafni); import `typesafe_sdk` |
| Avoid | Third-party `typesafe-ai` shim; unrelated `typesafe` package |
| Env | `TYPESAFE_API_KEY` (console.typesafe.ai/keys); client also reads `TYPESAFE_DEFAULT_MODEL`, `TYPESAFE_BASE_URL` |
| Default model (SDK) | `jev-latest` (pfy pins `PFY_JEV_MODEL` default **`jev-1.13.0`** — keep pin in-repo) |
| API | `POST /v1/systemone` at `https://api.typesafe.ai` |
| Question types | `Choice`, `Score` (ordered criteria list since 0.6), `Noul` |
| Official skill | `npx skills add typesafe-ai/skills --skill typesafe-ai` / https://github.com/typesafe-ai/skills |
| Early access | Blog still describes waitlist / early access — treat key absence as expected |

**pfy already matches the “thin adapter, no SDK lock-in” goal:** questions/thresholds in `scripts/pfy_jev_230.py` + env; offline/local path is default; cloud is optional HTTP.

### GitHub org code search

`org:themark-net` code search via MCP/`gh` returned empty / unauthenticated for private index. Inventory above is from **nimo checkouts + clone remotes**, not search hits. Confirmed remotes: `themark-net/pfy-deanery`, `themark-net/org-spinny-decide`.

---

## 1. Decision map (org pipeline → keep-in-code vs Jev vs LLM)

Pipeline reminder: bots coordinate (PM / DevBot / Tester / Reviewer / CEO) → heavy implement = Grok Build headless on nimo → gates = Tester PASS + Reviewer PASS + green CI → pinned squash merge (no operator ask). **Feature GO stays human.**

**Hard rule:** Jev / spinny / `./pfy decision` **must never replace** Tester or Reviewer PASS outright. Shadow-log first; automate only the safest branch.

| Decision | Frequency | Keep-in-code | Local spinny / pfy decision (Jev-style) | Frontier LLM | Notes |
|----------|-----------|--------------|------------------------------------------|---------------|-------|
| Merge gate ship / return / escalate (after Tester+Reviewer+CI facts) | High | Thresholds + required checks in code | **Shadow** Choice later (`ship`/`return`/`escalate`) + blast_radius Score + needs_human Noul | Draft rationale only | Automate **return** when known-red; never auto-ship without existing merge card rules |
| Waive self-hosted CI wait | Med | Explicit allowlist of flake labels / known-green jobs | Noul `ci_wait_waive` in **shadow** only | No | Default = wait |
| Route work: Build vs Cursor vs bot-only | High | Size/heuristics (diff LOC, eval length) | Choice over live options (org-spinny `pm_route` / pfy `route`) | Escalate ambiguous | Bot coordination skill already points here |
| Which Tester / Reviewer to ping | Med | Round-robin / specialty labels in code | Choice when >1 eligible | No | |
| PR touches GUI → needs launch proof? | Med | Path globs (`gui/`, `scripts/pfy-gui.py`, Loop) in code | Noul `needs_launch_proof` **shadow** | No | LOOP-243: Launch opens grok/OpenCode only — not a harness picker |
| Tool-call danger class | High (inside agent) | Deny-list in code / write-guard | Choice/Score danger class **beside** existing guards | No silent bypass | Align with ADR-0007 |
| Compaction / model-tool route inside a Build session | High | — | **`./pfy decision compact` / `route`** (CUA primary) | Session chat only if escalate | Already implemented #230 |
| org-spinny `push_hold` / `nimo_yield` | High | Exit codes + threshold env | **Keep local Ollama/CUA**; optional later shadow vs TypeSafe | Escalate on exit 3 | Do not cloud-require |
| Feature GO / money / legal / new cloud account | Rare | — | — | — | **Human / CEO only** |
| Writing DoDs, ADRs, thesis | Low | Templates | Never | LLM ok | Spinny non-goal |

### Rollout

1. **Shadow:** log `{gate, state_hash, choice, confidence, engine, would_auto}` beside current behavior; current path still acts.  
2. **Safest auto:** only branches that today already auto-act on deterministic code (e.g. hold on `known_red`) and where shadow agreement ≥ threshold for N days.  
3. **TypeSafe cloud:** off until a key exists; then one smoke + shadow parallel to CUA/Ollama — never block operator-free path.

---

## 2. pfy-deanery proposal

### How pfy wraps Grok Build today

- Operator path: `./pfy` / `./pfy launch` / `./pfy start grok` = inference detect → env-stage → native Loop window or named harness.  
- Decision path is a **module beside** Gab lane and local recommend (`decision ≠ gab auto ≠ local`).  
- Bot path today for implement: bare `grok -p … --always-approve` in an isolated worktree (org skill).  
- Goal of dogfood: show bots **and** a human can use `./pfy` tooling (toolset apply, decision, launch, catalog-backed modules that are actually green) **instead of or around** bare `grok -p`, without pretending incomplete catalog rows are ready.

### Catalog stages (reminder)

| Stage | Meaning |
|------:|---------|
| I0 | Awareness |
| I1 | Staged evaluation (default) |
| I2 | Ad-hoc lightweight probe |
| I3 | Onboard (skill/smoke/env) |
| I4 | Embedded (rare) |

**Working / usable for dogfood (slim `data/tools.json` + toolsets, 2026-10-04):**

- **I3:** Grok CLI bootstrap  
- **I2:** codebase-memory-mcp ↔ toolset `code-graph`  
- **I1 + toolset implemented:** Finn Loop / orchestration (`agent-loops`)  
- **Toolset `jev`:** implemented for grok/opencode/… with `catalog_tool: null` (ADR-0016 — not a TOOLS.md Stage-0 local-first row for TypeSafe SaaS)

**Do not dogfood on:** Kolibri-1 I0 (`FAIL_NO_BACKEND`), catalog 70–75 HOLD, PR #256 Loop agent-picker split, eval-auto `NameError: re` harness fix branches.

### Catalog entry recommendation (this PR)

**Do not add a TOOLS.md / `data/tools.json` row in this PR.**

Rationale (ADR-0016 + Stage 0):

- TypeSafe Jev is **cloud SaaS** → fails local-first Stage 0; ADR already sets `catalog_tool: null` and defers re-score to **T-0123**.  
- First-party surface is already the **`jev` toolset** + `#230` scripts/skills (operator-integrated; treat as **I3-equivalent product middleware**, not a third-party catalog pin).  
- Adding a half-linked row would either break `make catalog-check` or silently reverse ADR-0016.

**When T-0123 opens:** either (a) keep null and document “first-party middleware”, or (b) add an **I1** awareness row for TypeSafe cloud + keep CUA/local as the I3 path — never require the key for smoke.

### Thin decision adapter (already mostly true; tighten in follow-up code PRs)

| Requirement | Current | Follow-up |
|-------------|---------|-----------|
| No SDK lock-in | Raw HTTP in `typesafe_evaluate` | Keep; optional later facade that can call SDK **or** HTTP |
| Model pin in-repo | `PFY_JEV_MODEL` default `jev-1.13.0` | Confirm against `GET /v1/models` when key exists; do not chase article-only ids blindly |
| Questions / criteria / thresholds versioned | Mostly inline in `pfy_jev_230.py` | Extract versioned JSON under e.g. `data/decision-gates/` (`schema_version`, gate id, criteria, conf gate) |
| Offline fallback | No key / `PFY_JEV_OFFLINE` → FAIL+next or CUA/mini-jev | Unchanged; org bots keep `org-spinny-decide` Ollama path |
| Org bridge | Separate repos | Optional: `ORG_DECIDE_BACKEND=pfy` shelling `./pfy decision` / CUA — **after** dogfood |

### Where it plugs in

1. **Model / tool router** — `./pfy decision route` over live models/lane/harness/toolset (already).  
2. **Eval triage** — shadow Choice on eval FAIL class (flake vs real vs env) using only I3/I2 green tools.  
3. **Org merge / route gates** — shadow beside Tester/Reviewer; never replace.  
4. **Tool-call danger** — classify beside write-guard; deny-list still code.

---

## 3. Dogfood plan

### Question

Can a **bot** (headless, nimo Shell) and a **human dev** each complete a real slice using pfy-deanery’s `./pfy` tooling (+ working catalog/toolsets) **in place of or wrapping** bare `grok -p`, with honest gates?

### First candidate slice (narrow, green deps only)

**Slice D1 — “Decision-aware docs/chore PR” (no product UI, no catalog HOLD lift)**

1. Isolated worktree under `~/DEVELOP/pfy-mentat/tmp/<bot-slice>/`.  
2. `./pfy toolset apply jev --harness grok --lane local` (no TypeSafe key).  
3. `./pfy decision smoke` + `python3 scripts/pfy_jev_230.py --selftest` must READY/ok.  
4. Implement a **docs-only or script-comment** change already allowed by DoD (example: add a shadow-log stub design note, or wire `org-spinny-decide` README cross-link) — **not** Loop picker, **not** eval-auto harness.  
5. Optional wrap: instead of raw `grok -p`, run:

```bash
# after toolset apply; still headless Build for the body
./pfy decision route   # log Choice; do not auto-act on conf low
grok -p "$PROMPT" --cwd "$WT" --always-approve
```

6. Human path: same slice via `./pfy launch decision cua-s1-forms` then Attach/Launch grok or OpenCode only (LOOP-243).

**Pass criteria (all required):**

| Metric | Pass |
|--------|------|
| Completion | PR opened from isolated worktree; main checkout untouched |
| Decision smoke | `./pfy decision smoke` READY; selftest ok |
| Gate | Existing Tester/Reviewer/CI rules unchanged; no claim Jev replaced them |
| Time | Wall clock ≤ 1.5× same slice with bare `grok -p` (or documented why) |
| Cost / turns | Record Bot turns + Build minutes + whether any TypeSafe tokens used (expect **0**) |
| Catalog honesty | Only used toolsets/tools that are implemented or I2+ as listed above |

**Fail / recover:**

| Failure | Recover |
|---------|---------|
| decision smoke FAIL | Stay on bare `grok -p`; file issue; do not block ship of unrelated work |
| toolset apply writes outside `$PFY_STATE_DIR` / harness home | Stop; revert; treat as product bug |
| Temptation to use Kolibri / HOLD rows | Skip; pick another slice |
| TypeSafe key still missing | Expected; local lane only |
| conf low on route | Escalate to human/LLM path; no silent auto-act |

### Second slice (only if D1 passes)

**D2 — Bot implements a tiny I3-touching fix** (e.g. ops typo / smoke script comment) with `attach mode orchestration` or `code-graph` **if** those smokes are green on the host that day. Same metrics. If code-graph MCP missing → SKIP (honest), not FAIL of Jev.

### Explicit non-goals for dogfood

- Creating a TypeSafe account or spending money.  
- Replacing Tester/Reviewer.  
- Merging Feature GO.  
- Touching PR #256 picker / eval-auto `re` fix branches.  
- Declaring pfy “replaces Build” before D1 metrics exist.

---

## 4. Integration sequence (recommended)

| Step | Work | Repo |
|-----:|------|------|
| 0 | This plan + PENDING-HANDOFF | pfy-deanery (this PR) |
| 1 | Shadow logger JSONL schema + one org gate (`push_hold`) dual-run vs Ollama | org-spinny-decide + optional pfy bridge |
| 2 | Versioned `data/decision-gates/*.json` extracted from `pfy_jev_230.py` | pfy-deanery |
| 3 | Bot skill update: prefer `./pfy toolset apply jev` before `grok -p` on pfy-deanery slices | box workflows / port-bot-doctrine |
| 4 | If key appears: one smoke `typesafe` call; compare to CUA; keep offline default | pfy-deanery |
| 5 | T-0123 catalog re-score (optional I1 cloud row) | pfy-deanery |

---

## 5. Blockers

| Blocker | Impact |
|---------|--------|
| No `TYPESAFE_API_KEY` / possible waitlist | Cloud Jev untested; local CUA + org-spinny remain the path |
| `typesafe-sdk` not installed | Irrelevant while HTTP adapter + offline default hold |
| Private GitHub code search empty | Inventory relied on nimo trees; re-run search when token indexes private code |
| ADR-0016 `catalog_tool: null` | Intentional; do not force a TOOLS.md row in a docs PR |
| PR #256 / eval-auto harness WIP | Stay clear; dogfood on green surfaces only |

---

## 6. References

- Official SDK: https://docs.typesafe.ai/sdk/python/ · PyPI `typesafe-sdk` 0.7.2 · https://jevwiki.ai/wiki/reference/python-sdk.md  
- TypeSafe intro: https://typesafe.ai/blog/introducing-system-one-models-and-jev  
- Skills: https://github.com/typesafe-ai/skills  
- In-repo: ADR-0016, `#230`, `scripts/pfy_jev_230.py`, `data/toolsets.json` (`jev`)
