# Module: `./pfy` (`scripts/pfy`)

**Purpose:** Product door (G8 / ADR-0012). One CLI: setup, status, bare start = native operator window (inference → env-stage → window; no harness exec), named start still execs a harness, models inspect, harness select.

## Entry

```bash
./pfy                    # inference → env-stage → native window
./pfy help
./pfy setup [local-only|balanced|max-performance]
./pfy status
./pfy start [harness]    # no name: native window; named: exec that harness (Attach mode #208)
./pfy up                 # same as bare ./pfy
./pfy board [--open]     # alias of the native window (Tauri / webkit / tk); --open browser hatch only
./pfy harness list|use <id>|show [id]
./pfy models
./pfy models pull <name>    # live engine (FreeToken records; Ollama pulls; llama skip)
./pfy models recommend      # ranked host-fit models not yet pulled (#207)
./pfy models try [name]     # pull top/named recommendation — operate-or-FAIL (#207)
./pfy catalog               # usable catalog browse subset (#209)
./pfy catalog ask [name]    # ask attached TUI to implement for next launch
./pfy catalog queue [name]  # REAL GitHub issue Design→DevBot (#214)
./pfy catalog status        # queued items + open/closed/PR
./pfy launch               # Loop wizard Launch session (#225/#224)
./pfy launch compose       # honest lane + enabled-tool paint (#224)
./pfy decision smoke       # #230 CUA-S1-FORMS typed Choice (Mark-free)
./pfy launch brief         # write in-session AGENTS/prompt card (#224)
./pfy context              # OpenContext oc prove (#205); FAIL if node/oc missing
./pfy code-graph           # Axon prove or codebase-memory equivalent (#215)
./pfy axon                 # alias of code-graph
./pfy toolset matrix       # toolset × harness implemented|partial|stub grid (ADR-0017)
./pfy toolset plan jev --harness opencode   # env/files/brief plan, or STUB + next (exit 3)
./pfy hedge decide --task bulk|hard|interactive   # local first; cloud within PFY_CLOUD_BUDGET
./pfy stage | eval | ship
```

Root `./pfy` is a 100755 wrapper that execs `scripts/pfy`. Detector is invoked with `bash`.

**Attach mode (#208 / #213 / #215):** HTML+tk select `bare` | `orchestration` | `code-graph`; paint `using: <mode>`. Orchestration starts a multi-step local loop (prove or FAIL+next) and Loop shows last evidence. Code-graph hands Axon or paints `path=codebase-memory (not axon)`. Named start and in-window Attach (OpenCode | Hermes | Grok | Codex | Claude) hand off skills/AGENTS/prompts/env or FAIL+next. [attach-mode.md](attach-mode.md) · [code-graph.md](code-graph.md).

**Attach Codex usable (#220):** HTML+tk **Attach codex** and `./pfy start codex` prove models list + one smoke on the FreeToken-first live base before attached paint / exec. Missing Codex is FAIL + installer, never a silent stub. [codex-adapter.md](codex-adapter.md).

**Attach Claude usable (#221):** HTML+tk **Attach claude** and `./pfy start claude` / `claude-code` prove models list + one smoke on the FreeToken-first live base before attached paint / exec. Missing Claude is FAIL + `curl -fsSL https://claude.ai/install.sh | bash`, never a silent stub. [claude-code-adapter.md](claude-code-adapter.md).

**Recommend / try (#207):** Engine + `./pfy models recommend` ranks host-fit models not yet pulled. `try` pulls one FreeToken-first (operate-or-FAIL). Handoff: engine pin · Attach re-probe · TUI reload. [recommend-models.md](recommend-models.md).

**Catalog ask / queue (#209 / #214):** Tools browse (usable subset, not scores-only). Ask attached TUI to implement for next launch (prompt/artifact). **Queue for org** creates a real GitHub issue and paints open/closed/PR. HOLD 70–75 not auto-lifted. [catalog-ask-queue.md](catalog-ask-queue.md) · [live-org-queue.md](live-org-queue.md).

**Toolset handoff + hedge (ADR-0017):** `toolset` / `hedge` verbs are a thin `exec python3 "$ROOT/pfylib/cli.py"` dispatch; all logic and tests live in `pfylib/`. +2 top-level verbs against T-0090's ≤3-lever target — the tension is OQ-0012's to resolve. [pfylib.md](pfylib.md).

**Decision layer (#230):** Loop toggle `off | CUA-S1-FORMS | TypeSafe | mini-jev`. Typed Choice/Score; CUA-S1-FORMS is primary local (Mark-free smoke). TypeSafe key optional. Honesty `decision ≠ gab auto ≠ local`. [jev-230.md](jev-230.md).

**Launch wizard (#225) / session compose (#224) / Loop modules (T-0125):** Loop paints **LOCAL COMPUTE | CLOUD ORCHESTRATION** plus gathered catalog **MODULES**. Hedge chooses the lane; Launch session applies enabled modules into an enterable TUI (proof). Attach X is on the Attach tab. Window stay-open. HTML+tk. No Env nav tab. [launch-wizard.md](launch-wizard.md) · [session-compose.md](session-compose.md) · [pfylib.md](pfylib.md).

## Not yet

- Health-wait + default-model complete for Ollama (`./pfy start` still fire-and-forget serve)
- Remaining harness adapters (gemini, exo, continue, agent-cage)
- Treating `./pfy models` as success
