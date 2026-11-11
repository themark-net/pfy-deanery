# ATG coupling (Atomic Task Graph prototype)

**Status:** I2 probe 2026-10-06. The 2026-08-06 snapshot below is superseded.  
**Prototype:** https://github.com/themark-net/atg-framework  
**Paper:** Zhang, Chen, Huang, Cui, Ji, and Wang (2026), arXiv:2607.01942. This repo is an independent reimplementation. It is not official ATG code and it does not claim the paper's benchmark numbers.  
**Pinned checkout:** branch `main` @ `543e778ed24fbf3fc903eb961feb627039019832`. Point `ATG_REPO` or `--atg-repo` at a clean checkout or worktree of atg `main` at that SHA. There is no default path. The live receipt was taken at `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16` on `build/atg-finish` (2/10 valid DAGs, 2/10 sink-correct, I2), before the report commit. The I2 score (2/10 valid, 2/10 sink-correct) was taken at 86d1b890 on build/atg-finish and has not been re-run at the main pin 543e778.  
**Entry:** [101](../../sources/entries/101-atg-compile.md). Entry 095 is Qwen3.8-Flash-Next.  
**Integration stage:** **I2**. Not I3. Submodule later stays an intent, not an instruction.  
**Reviews:** 2026-08-06 → issue #30 (stay I1). 2026-10-06 → live atg-compile exit 0 with 2/10 sinks correct, promote to I2 only.

## Run the bench

| Name | Where | Purpose |
|------|--------|---------|
| `ATG_REPO` | environment, or `--atg-repo` | Required. Clean checkout or worktree of atg `main` at the pinned SHA. |
| `--base-url` | flag, or `ATG_BASE_URL` | OpenAI-compatible endpoint. Ollama is `http://127.0.0.1:11434`. |
| `--model` | flag, or `ATG_MODEL` | One model. Default `qwen3.6:35b`. |

```bash
ATG_REPO=/path/to/atg \
  python3 examples/atg-compile/bench.py \
  --base-url http://127.0.0.1:11434 \
  --model qwen3.6:35b
```

Unset `ATG_REPO` exits 2 and writes no receipt. If HEAD is not the pin, the bench exits 2 the same way. Point `ATG_REPO` at the pin and retry. Scoring, cases, and catalog stage stay I2.

## 2026-10-06 snapshot

Called by path from `examples/atg-compile/bench.py`. Not vendored. Not on the eval-harness or cage default path. Default model stays `qwen3.6:35b` on Ollama. `qwen3-coder-next` is opt-in via the `llamacpp-nommap` lane.

### Offline checks (this session)

Worktree was dirty (`examples/poc_suite.py`, `docs/ops/RUN-LOG-atg-finish.md`). HEAD matched the pin.

| Command | Result |
|---------|--------|
| `.venv/bin/python -m pytest -q -m "not integration"` | **40 passed, 1 deselected** (2.43 s) |
| `.venv/bin/python examples/toy_parallel.py` | `mock total={'value': 25} waves=2 parallel=2` exit 0 |
| Live atg-compile, Ollama `qwen3.6:35b`, `--case-timeout 180` | Exit 0. 2/10 valid, 2/10 sink-correct (`ac-01-mul-six-seven`, `ac-08-parallel-sums`), repairs 0, wall 478s. Receipt `pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json`. |
| `qwen3-coder-next` via `llamacpp-nommap` | Not loaded. Blob 48.19 GiB plus 25 GiB exceeded MemAvailable (65.3 GiB). |

### Gate table

| Gate | Reading | Counts? |
|------|---------|---------|
| Gap fill | Explicit compile, parallel tool waves, freeze, and localized repair. pfy's primary loop does not ship this library. LangGraph overlaps "run a DAG". The distinct piece is repair and freeze for a small local model. No first-party skill does that. | Partial |
| Operator leverage | Offline `run_task` is one import. The new bench is a measurement, not a shorter default pipeline. | No |
| Evidence | Live atg-compile exit 0 with two sink-correct cases. Offline suite also green. | Yes, as a probe |
| Blast radius | MIT. No model weights. Safe while it stays off primary orchestration and off the default cage and eval-harness. | Yes, with those constraints |

Modularity, if a later session copies or imports the repo: one Python package, entry `run_task`, reversible by deleting the pin. That is small. It does not satisfy I3.

**Chosen stage:** I2 probe. The live pass is two correct sinks out of ten, not a reason to move to I3.

### Non-goals (repeated)

- Do not call ATG from eval-harness or the cage by default.
- Do not treat ATG as primary orchestration (Grok, OpenCode, and skills stay primary).
- Do not vendor `src/atg` or add a submodule in this change.
- Do not claim pfy reproduced ALFWorld, WebShop, or a GPT-4 comparison.

## Relationship to pfy-deanery

| Concern | Policy |
|---------|--------|
| Catalog | List ATG as research/prototype; link atg-framework |
| Code coupling today | Bench calls the pinned checkout by path. No pipeline hard dependency. No Make smoke and no eval-harness import require ATG |
| Future embed | **Submodule (I4)** only after I3 value+modularity gates ([integration-stages.md](integration-stages.md)) |
| Weights / large assets | N/A (code/method, not model weights) |

## Non-goals (now)

- Do not force symbolic submodule while prototype is still in development.  
- Do not call ATG from eval-harness or cage by default.  
- Do not treat ATG as primary orchestration (Grok + OpenCode + skills remain primary).

## Uses / features / potential (I1 card)

| Field | Content |
|-------|---------|
| **Uses** | Compile, parallel tool waves, freeze, and localized repair. Independent reimplementation of Zhang et al. (2026). |
| **Features** | DAG compile, localized repair, OpenAI-compatible client |
| **Potential** | Measured probe: 2/10 sinks correct on `qwen3.6:35b` |
| **Non-goals** | Primary runtime; I3 from this probe; immediate I4 |

## 2026-08-06 maturity snapshot (issue #30) — superseded

The paragraph below described a tree with no `src/atg/`. That is no longer true. It stays as history. Do not use it as the current maturity statement.

- atg-framework remains **docs-only**: ARCHITECTURE, DECISIONS 0001–0010, OPEN_QUESTIONS, TODO, attribution. No `src/atg/`, no pyproject, no tests, no examples.
- Phase 0 complete; Phase 1 skeleton (graph/types/history/validation + green pytest) **not started**.
- Working tree size trivial (≪ 50 MB). No open issues on the prototype repo.
- **Decision:** stay **I1**. I2 probe has nothing executable to probe. Value + modularity gates for I3 unmet. Do not plan I4.
- **Next trigger:** after Phase-1 runnable skeleton lands, or explicit re-request. No calendar auto-reminder required.
