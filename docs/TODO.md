## Done / shipping

- #230 Jev-style decision layer (CUA-S1-FORMS primary local; TypeSafe optional)
- #228 Gab cloud lane + local recommend sync

# TODO — next steps

**Purpose:** Single ordered work queue for humans and agents.  
**Design:** [DESIGN.md](DESIGN.md) · **ADRs:** [adr/](adr/README.md) · **Open questions:** [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)


## G8 — Simple harness-agnostic launch (2026-07-31)

| ID | Item | Status |
|----|------|--------|
| T-0100 | Epic: `./pfy` simple surface + harness registry | **done** (MVP) · [#53](https://github.com/themark-net/pfy-mentat/issues/53) |
| T-0101 | Ollama adapter complete in `pfy start` (health, default model) | **done** · [#54](https://github.com/themark-net/pfy-mentat/issues/54) |
| T-0102 | OpenCode host adapter (skill path + local OpenAI-compat base_url) | **done** · [#55](https://github.com/themark-net/pfy-mentat/issues/55) |
| T-0103 | Hermes integrated installer adapter | open · [#56](https://github.com/themark-net/pfy-mentat/issues/56) |
| T-0104 | Claude Code adapter | open · [#57](https://github.com/themark-net/pfy-mentat/issues/57) |
| T-0105 | Codex adapter | open · [#58](https://github.com/themark-net/pfy-mentat/issues/58) |
| T-0106 | Gemini / Google harness adapter | open · [#59](https://github.com/themark-net/pfy-mentat/issues/59) |
| T-0107 | Exo optional lab path | open · [#60](https://github.com/themark-net/pfy-mentat/issues/60) |
| T-0108 | Continue + Ollama recipe | open · [#61](https://github.com/themark-net/pfy-mentat/issues/61) |
| T-0109 | Fold agent-cage into `pfy stage --lab` | open · [#62](https://github.com/themark-net/pfy-mentat/issues/62) |
| T-0110 | Pluggable local runtime (llama-swap / Shimmy / Ollama) | **doing** (partial) · [#76](https://github.com/themark-net/pfy-mentat/issues/76) |

Authority: ADR-0012 · ADR-0014 · issues labeled `harness-adapter`.

## GitHub issues (synced 2026-07-30)

Active work is also tracked as issues: https://github.com/themark-net/pfy-mentat/issues

| TODO | Issue | Priority |
|------|-------|----------|
| T-0090 | [#1](https://github.com/themark-net/pfy-mentat/issues/1) | P0 |
| T-0110 | [#76](https://github.com/themark-net/pfy-mentat/issues/76) | P1 doing/partial |
| T-0091 | [#2](https://github.com/themark-net/pfy-mentat/issues/2) | P1 doing |
| T-0070 | [#3](https://github.com/themark-net/pfy-mentat/issues/3) | P1 doing |
| T-0074 | [#4](https://github.com/themark-net/pfy-mentat/issues/4) | P1 doing |
| T-0075 | [#5](https://github.com/themark-net/pfy-mentat/issues/5) | P2 |
| T-0076 | [#6](https://github.com/themark-net/pfy-mentat/issues/6) | P2 |
| T-0081 | [#7](https://github.com/themark-net/pfy-mentat/issues/7) | P2 |
| T-0040 | [#8](https://github.com/themark-net/pfy-mentat/issues/8) | P2 |
| T-0094 | [#9](https://github.com/themark-net/pfy-mentat/issues/9) | P3 |
| T-0095 | [#10](https://github.com/themark-net/pfy-mentat/issues/10) | P3 |
| T-0064 | [#11](https://github.com/themark-net/pfy-mentat/issues/11) | P3 parked |
| T-0043 | [#12](https://github.com/themark-net/pfy-mentat/issues/12) | P3 parked |
| T-0062 | [#13](https://github.com/themark-net/pfy-mentat/issues/13) | P3 |
| T-0046 | [#14](https://github.com/themark-net/pfy-mentat/issues/14) | P3 |
| T-0007 | [#15](https://github.com/themark-net/pfy-mentat/issues/15) | P3 |
| T-0002 | [#16](https://github.com/themark-net/pfy-mentat/issues/16) | P3 |
| T-0005 | [#21](https://github.com/themark-net/pfy-mentat/issues/21) | P2 todo |
| T-0004 | [#22](https://github.com/themark-net/pfy-mentat/issues/22) | P2 **done** |
| T-0015 | [#23](https://github.com/themark-net/pfy-mentat/issues/23) | P3 **done** |
| T-0016 | [#24](https://github.com/themark-net/pfy-mentat/issues/24) | P2 todo |
| T-0075 | [#5](https://github.com/themark-net/pfy-mentat/issues/5) | P2 **done** |
| T-0007 | [#15](https://github.com/themark-net/pfy-mentat/issues/15) | P3 **done** |
| golden_replay | [#31](https://github.com/themark-net/pfy-mentat/issues/31) | P1 **done** |

**Catalog follow-ups:** [#25](https://github.com/themark-net/pfy-mentat/issues/25) Laguna · [#26](https://github.com/themark-net/pfy-mentat/issues/26) asm · [#27](https://github.com/themark-net/pfy-mentat/issues/27) claude-codex-settings · [#28](https://github.com/themark-net/pfy-mentat/issues/28) MUE-X  
**OQ batch:** [#29](https://github.com/themark-net/pfy-mentat/issues/29)

## Qualification model

| Field | Values | Meaning |
|-------|--------|---------|
| **Priority** | `P0` / `P1` / `P2` / `P3` | P0 = blocks current critical path · P1 = next milestone · P2 = important not blocking · P3 = someday |
| **Status** | `todo` \| `doing` \| `blocked` \| `done` \| `cancelled` | Active work only in **Active** table; finished rows move to **Done** |
| **Open questions** | `OQ-NNNN` or `—` | **Required** if Status is `blocked` or if work needs a human decision before P0/P1 can finish |
| **Depends** | T-IDs | Optional ordering edges |

**Rules**

1. Every `blocked` row **must** cite an OQ (or external blocker named in Notes).
2. Every OQ that blocks work should appear in at least one Active TODO’s **Open questions** column.
3. Do not invent architecture in a TODO — settle with `/adr`.
4. Never delete history; move finished rows to **Done**.
5. New tool integrations: register env vars in `bootstrap/env/REGISTRY.md`; prefer smokes **inside agent-cage**.

---

## Active (sorted P0 → P3)

**Session (2026-07-26):** **T-0096** dual-tier orchestrator (high-first default). Smoke: `make smoke-voice-orchestrate`.

### Active — design / coding + local path (agent may pick freely)

| ID | Priority | Status | Item | Open questions | Depends | Notes |
|----|----------|--------|------|----------------|---------|-------|

| T-0110 | P1 | doing | **Pluggable local runtime** (OpenAI-compat: llama-swap / Shimmy / Ollama) | — | ADR-0014 | [#76](https://github.com/themark-net/pfy-mentat/issues/76) stays OPEN · detector + registry + shimmy last in `./pfy up`; T-0101 Ollama named start done · [#202](https://github.com/themark-net/pfy-mentat/issues/202) Attach Grok usable slice |
| T-0091 | P1 | doing | **Voice path** polish (session sticky / MCP deep) | — | ADR-0012 | [#2](https://github.com/themark-net/pfy-mentat/issues/2) · Orchestrator shipped; optional TTS |
| T-0092 | P1 | done | Voice auto-agent local opencode path | — | T-0091 4b | still: `VOICE_AUTO_AGENT=opencode` |
| T-0093 | P1 | done | Tools-capable Ollama select + tool-split | — | T-0080 | `eval-select-tools-model` |
| T-0096 | P1 | done | **Dual-tier orchestrator** high↔low (`VOICE_ROUTE=high-first` default) | — | T-0092, T-0093 | [voice-orchestrator.md](ops/voice-orchestrator.md); `smoke-voice-orchestrate` |
| T-0094 | P3 | todo | Optional short **local TTS** status (not duplex) | — | T-0092 | [#9](https://github.com/themark-net/pfy-mentat/issues/9) · Kokoro/piper after local agent path green |
| T-0095 | P3 | todo | Catalog Stage 0: Pipecat / LiveKit / freeapp (ref only) | — | ADR-0012 | [#10](https://github.com/themark-net/pfy-mentat/issues/10) · No primary install |
| T-0070 | P1 | doing | Grow design/coding **skills + structural eval** (more text scorers) | — | T-0065 | [#3](https://github.com/themark-net/pfy-mentat/issues/3) · Keep `eval-structural` green |
| T-0074 | P1 | doing | Implement-lane via `make eval-auto` (fit-select + candidates) | — | — | [#4](https://github.com/themark-net/pfy-mentat/issues/4) · deepseek-coder:6.7b lab-proven |
| T-0075 | P2 | done | More structural scorers: ADR shape, open-question row shape | — | T-0070 | [#5](https://github.com/themark-net/pfy-mentat/issues/5) **done** |
| T-0076 | P2 | todo | Wire mattpocock to-spec/tdd checklist into structural or skill cross-links | — | — | [#6](https://github.com/themark-net/pfy-mentat/issues/6) · paths pack already installed |
| T-0081 | P2 | todo | Optional OpenCode-in-cage smoke | — | T-0080 | [#7](https://github.com/themark-net/pfy-mentat/issues/7) · After host smoke green |
| T-0040 | P2 | todo | Broader multi-CLI parity notes (Claude Code) | — | T-0080 | [#8](https://github.com/themark-net/pfy-mentat/issues/8) · OpenCode first |

### Active — parked (env / not this track)

| ID | Priority | Status | Item | Open questions | Depends | Notes |
|----|----------|--------|------|----------------|---------|-------|
| T-0064 | P3 | todo | Auth file-mount EBUSY (grok-home dir) | — | T-0045 | [#11](https://github.com/themark-net/pfy-mentat/issues/11) · Env polish |
| T-0043 | P3 | todo | Write-guard mcp-host wiring | — | T-0031 | [#12](https://github.com/themark-net/pfy-mentat/issues/12) · Parked |
| T-0062 | P3 | todo | Laguna local model DoD | — | — | [#13](https://github.com/themark-net/pfy-mentat/issues/13) · Hardware-gated |
| T-0046 | P3 | todo | Re-evaluate AgenC | [ADR-0010](adr/0010-reject-agenc-as-primary-runtime.md) | T-0044 | [#14](https://github.com/themark-net/pfy-mentat/issues/14) |
| T-0007 | P3 | todo | adr-tools companion docs | — | — | [#15](https://github.com/themark-net/pfy-mentat/issues/15) |
| T-0002 | P3 | todo | Aggregate synthesis | — | — | [#16](https://github.com/themark-net/pfy-mentat/issues/16) |

### Active — follow-ups (OQs answered; not blocked)

| ID | Priority | Status | Item | Open questions | Depends | Notes |
|----|----------|--------|------|----------------|---------|-------|
| T-0016 | P2 | todo | colibri/large model lab under 250GB pool | — | OQ-0008 | [#24](https://github.com/themark-net/pfy-mentat/issues/24) |
| T-0005 | P2 | todo | Apply integration-stages broadly | — | OQ-0003 | [#21](https://github.com/themark-net/pfy-mentat/issues/21) · partial |
| T-0124 | P2 | todo | Fold OpenCode enterable (`pfy_enterable_162*`) behind `pfylib/attach.py`; retire `_legacy` as remaining scripts move | — | T-0121 | OpenCode attach is still its own path; four usable shims already delegate |

---

## Done

| ID | Priority | Status | Item | Notes |
|----|----------|--------|------|-------|
| T-0090 | P0 | done | Minimal product levers: default `make help` is onboard / stage / ship | `make help-platform` holds cage, smoke, eval · [#1](https://github.com/themark-net/pfy-mentat/issues/1) · [product-operator-surface.md](ops/product-operator-surface.md) |
| T-0121 | P1 | done | Attach clones → `pfylib/attach.py` + remaining `plan()` bodies wrap legacy scripts (no rewrite) | `data/harnesses.json[].attach`; shims `pfy_attach_usable_{196,202,220,221}`; planners in `pfylib/toolsets.py`; leftover OpenCode 162 = T-0124 |
| T-0125 | P1 | done | Loop UI: catalog modules + live local/cloud hedge | `pfylib/loop_paint.py`; HTML+tk LOCAL COMPUTE \| CLOUD ORCHESTRATION + MODULES; Launch session applies enabled modules |
| T-0120 | P1 | done | Toolset × harness matrix + jev reference `plan()`/`apply()` | `data/toolsets.json` · `pfylib/`; stacked PRs on this branch |
| T-0075 | P2 | done | ADR + OQ structural scorers | #5; tasks 006/007 |
| T-0007 | P3 | done | adr-tools companion docs | #15; docs/ops/adr-tools-companion.md |
| T-0004 | P2 | done | ATG coupling I1 submodule-later | #22; docs/ops/atg-coupling.md |
| T-0015 | P3 | done | Antigravity catalog-only skip install | #23; antigravity-catalog-posture.md |
| — | P1 | done | golden_replay deterministic lane | #31; make eval-golden |
| — | P1 | done | OpenContext `oc` usable handoff (Stage-0 + nimo hello-world + `./pfy context`) | [#205](https://github.com/themark-net/pfy-mentat/issues/205) · catalog HOLD · #198 parked |
| — | P1 | done | Attach mode `bare` \| `orchestration` \| `code-graph` (using: paint + operate-or-FAIL handoff) | [#208](https://github.com/themark-net/pfy-mentat/issues/208) · catalog HOLD · #198 parked · do not reopen #76 |
| — | P1 | done | Recommend / try local models beyond already-pulled (Engine + `./pfy models recommend\|try`) | [#207](https://github.com/themark-net/pfy-mentat/issues/207) · catalog HOLD · #198 parked · do not reopen #76 |
| — | P1 | done | Catalog pick → ask attached TUI / queue org (Tools browse, not scores-only) | [#209](https://github.com/themark-net/pfy-mentat/issues/209) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| — | P1 | done | Live org queue from Tools: real GitHub issue + open/closed/PR status | [#214](https://github.com/themark-net/pfy-mentat/issues/214) · catalog HOLD 70–75 · #198 parked · #76 CLOSED |
| — | P1 | done | Deepen Attach orchestration: multi-step local loops + Loop evidence (not thin inject) | [#213](https://github.com/themark-net/pfy-mentat/issues/213) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| — | P1 | done | Attach code-graph Axon usable path (or codebase-memory equivalent, painted) | [#215](https://github.com/themark-net/pfy-mentat/issues/215) · catalog HOLD 70–75 (do not merge PR #75) · #198 parked · #76 CLOSED |
| — | P1 | done | Attach Codex usable FreeToken-first session (HTML+tk; prove models+smoke) | [#220](https://github.com/themark-net/pfy-mentat/issues/220) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| — | P1 | done | Attach Claude usable FreeToken-first session (HTML+tk; prove models+smoke) | [#221](https://github.com/themark-net/pfy-mentat/issues/221) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| — | P1 | done | Operator launch wizard on Loop: compose then Launch session (HTML+tk) | [#225](https://github.com/themark-net/pfy-mentat/issues/225) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| — | P1 | done | Session compose: honest lane + enabled toolsets + in-TUI how-to brief | [#224](https://github.com/themark-net/pfy-mentat/issues/224) · catalog HOLD 70–75 · #198 parked · do not reopen #76 |
| T-0050 | P2 | done | First-party `/agent-loops` skill (8 exits + 4 types + Finn + rubric) | `bootstrap/grok-cli/skills/agent-loops/`; Entries 024/027/031/032/068; pairs with `/one-shot` |
| T-0048 | P2 | done | Hermes feedback loops as first-party Grok skill | `bootstrap/grok-cli/skills/hermes-feedback/`; Entry 048 pattern port; not Hermes runtime |
| T-0051 | P2 | done | First-party skill structural smoke + verification docs | `make smoke-grok-skills`; `bootstrap/grok-cli/scripts/verify_skills.py`; `docs/ops/skill-verification.md` |
| T-0052 | P2 | done | Cage first-party skills install on `cage-grok` + project `.grok/skills` sync | `grok-skills-install`; workspace-sync mirrors bootstrap skills |
| T-0053 | P2 | done | codebase-memory vs Graphify decision + Graphify B-tier catalog row | `docs/evaluation/codebase-memory-vs-graphify.md`; tools.json v0.4.6 |
| T-0054 | P2 | done | Loop engineering ops map + one-shot DoDs H/I/J | `docs/ops/loop-engineering.md`; one-shot-example-dods |
| T-0055 | P2 | done | Auto-Company pattern extract (no runtime) | `docs/ops/auto-company-patterns.md` |
| T-0060 | P2 | done | 8-exits eval task scaffold + deterministic scorer | `examples/eval-harness/tasks/003-exit-card-checklist/`; fixtures in structural lane |
| T-0065 | P1 | done | Structural eval lane (no LLM) + design-coding rubric + decision inventory | `make eval-structural`; `data/eval-lanes.json`; human-decision-inventory |
| T-0082 | P1 | done | ADR-0011 hybrid Grok/OpenCode/Ollama + local-cloud-split ops + opencode adapter | `docs/adr/0011-…`; `docs/ops/local-cloud-split.md`; `bootstrap/opencode/` |
| T-0080 | P1 | done | OpenCode + Ollama host smoke (skills + config + completion) | `make smoke-opencode-ollama`; `examples/opencode-ollama/`; opencode CLI optional |
| T-0085 | P0 | done | Worker/monitor dual-session recipe | `make worker-stage`; `/worker-monitor` skill; `docs/ops/worker-monitor.md` |
| T-0126 | P2 | done | Port founder standings into portable skills SoT | `prefer-behavior-and-fail-recover-tests`, `ui-is-the-app-design-in-loop`, `best-effort-and-bot-budget-build-max`; `docs/ops/port-bot-doctrine-to-pfy-sot.md`; catalog HOLD; no Feature GO; no issue |
| T-0071 | P2 | done | Bumblebee coding-safety assist docs | `docs/ops/bumblebee-coding-safety.md` |
| T-0072 | P2 | done | MUE-X pattern extract (no evolve) | `docs/ops/mue-x-patterns.md` |
| T-0073 | P2 | done | LEANN/Memvid memory assist patterns | `docs/ops/memory-assist-patterns.md` |
| T-0030 | P0 | done | Env registry + profiles | merged main |
| T-0022 | P1 | done | Grok-in-image overlay | feature/agent-cage-grok-image merged; OIDC auth import |
| T-0000 | — | done | Process docs bootstrap | ADR-0001 |
| T-B001 | — | done | Grok CLI bootstrap | ADR-0004 |
| T-B002 | — | done | project-process scaffold | |
| T-B003 | — | done | `/catalog-docs` skill + README v0.4 | |
| T-0010 | P0 | done | Catalog hygiene Phase 0 | |
| T-0001 | P1 | done | Seed placeholder reconcile | OQ-0001 answered |
| T-0020 | P0 | done | agent-cage lab baseline (up-mcp + policy tests pass) | Operator smoke 2026-07-12; UX on main |
| T-0021 | P1 | done | Cage tool smokes **inside cage** (LiteLLM, MCP memory, repowise) | LiteLLM + codebase-memory + repowise; `make smoke-context-tools` |
| T-0013 | P1 | done | repowise smoke vs codebase-memory (prefer in-cage) | pipelines/smoke/context-tools-compare.md; both smokes green 2026-07-12 |
| T-0031 | P1 | done | **Write-guard MCP implement** (stdio server + cage overlay) | harness/write-guard-mcp v0.1; make smoke-write-guard; OQ-0009 audit default |
| T-0032 | P1 | done | **One-shot skill polish + example DoDs** for cage/tool smokes | docs/ops/one-shot-example-dods.md; skill points at make smoke-* |
| T-0006 | P2 | done | Module docs bootstrap + harness via `/catalog-docs` | docs/modules/* for grok-cli, project-process, agent-cage, write-guard, smokes |
| T-0011 | P1 | done | Phase 1 skill ports: marketing-council first-party + mattpocock paths subset | ADR-0009; council in skills/; mattpocock tdd/code-review/to-spec via paths |
| T-0014 | P2 | done | gstack role-pattern skills / AGENTS recipes (docs-first, not full embed) | docs/ops/gstack-role-recipes.md + AGENTS role router |
| T-0017 | P2 | done | First-party `investigate` RCA skill (gstack method rewrite) | bootstrap/grok-cli/skills/investigate/; not raw snapshot |
| T-0012 | P1 | done | LiteLLM recipes by DEPLOY_PROFILE (local / balanced / max) | config/litellm/{local-only,balanced,max-performance}.yaml + cage smoke |
| T-0003 | P1 | done | Eval harness MVP (OQ-0002 option 5) | tier0 smokes + tier1 scored task; make eval-mvp; DSPy deferred |
| T-0041 | P1 | done | Eval harness v0.2: multi-task suite + multi-model matrix | 002-fix-sum-evens; make eval-suite/matrix/v02; 3×2 matrix green |
| T-0044 | P1 | done | AgenC install experiment + smoke (then demoted) | Trial only; **ADR-0010** rejects as primary; host uninstalled; catalog B/watch |
| T-0045 | P1 | done | Grok Build in agent-cage + filesystem MCP on catalog workspace | `make cage-workspace-sync` / `cage-grok-ready`; project `.grok` → mcp-host filesystem |
| T-0047 | P1 | done | Cage Grok session resumption (persist + host→cage import) | `grok-state/sessions` mount; `cage-grok-sessions-import-host`; `cage-grok-resume` |
| T-0042 | P2 | done | Catalog re-score + absorb S-tier clusters; recover sources 001–055 | TOOLS.md + tools.json v0.4.2; eval-framework Grok-first; setup-local-agent-env rewritten |


## How to use

1. Scan **Open questions**; do not silently answer P0/P1.
2. Pick highest-priority non-blocked Active row.
3. Uncertainty → OQ; set TODO `blocked` if needed.
4. Architecture → `/adr`.
5. Finish → **Done** table (and close linked GitHub issue).
