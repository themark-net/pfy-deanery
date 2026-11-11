# atg-framework evaluation (2026-10-06)

**Evaluated:** `~/DEVELOP/atg-framework` `main` @ `29bca8a` (v0.2.0). Read-only. The founder Build checkout had uncommitted edits in `docs/{NEXT,OPEN_QUESTIONS,TODO,USING}.md`; tests ran on a copy in `/tmp/atg-eval-copy`.
**Paper:** Zhang, Chen, Huang, Cui, Ji, Wang (2026), *Atomic Task Graph: A Unified Framework for Agentic Planning and Execution*, arXiv:2607.01942. atg-framework is an independent reimplementation, not an author release (Decision 0020: no author SDK exists).
**Verified here:** `uv run pytest -q -m "not integration"` → **35 passed, 1 deselected** (0.4 s). `examples/toy_parallel.py` (offline) → `mock total={'value': 25} waves=2 parallel=2`. No live model was loaded: the host is running a GLM-4.5-Air bench.

## Verdict (5 lines)

1. **(a) Not yet a standalone PoC of the paper.** The whole loop is in the code (compile → thought experiment → parallel execute → LCA-localized repair), but it has only been shown working with a scripted `MockLLM`. All three live compiles on 2026-10-05 failed.
2. **The paper's claims are unmeasured.** There is no baseline (linear/ReAct or global replan), no task suite, and no hallucinated-action or steps metric. ALFWorld, WebShop and ScienceWorld are deferred by Decision 0018.
3. **It needs an LLM endpoint.** The native client is Ollama-only (`/api/chat` + `format` schema). A llama-server, Lemonade or vLLM server can only be reached through the optional LiteLLM extra (`ATG_MODEL=openai/<name>` + `OPENAI_API_BASE`), and that path has not been tested. A ~60-line stdlib OpenAI-compatible client is the missing piece.
4. **(b) Adapt it for pfy-deanery; don't embed it.** The useful parts for pfy are (i) a compile bench built on pfy's local-bench harness, (ii) the decision lane acting as ATG's judge, and (iii) an opt-in `atg` loop kind under the `orchestration` toolset. Skip the parallel executor for model work: nimo holds one big model at a time.
5. **Stale catalog card.** pfy's ATG card still says "No runnable core" (I1, `docs_only`). The trigger it named has fired. Refresh the card in pfy-mentat. Promote it to I2 (probe) only after one live compile exits 0.

## Paper components: implemented vs missing

| Paper concept (§) | atg-framework | State |
|---|---|---|
| Task / Tool / Node / Edge / DAG | `types.py`, `graph.py` (stdlib DAG, frozen Pydantic nodes), `tools.py` (OpenAI-style JSON schema + callable) | Implemented, unit-tested |
| Refinement history | `history.py` full snapshots, `persist.py` atomic JSON checkpoint | Implemented |
| Recursive compile + interface preservation | `planner.compile_task` (max_depth 6), `validation.py` parent/subgraph interface checks; edges naming ids outside the child set are dropped | Implemented. **Mock only.** Live compile 0/3 |
| Thought experiment (pre-execution check) | `thought.py` structural rules + opt-in LLM judge (`ATG_JUDGE=1`) | Structural rules tested. Judge never run live |
| Dependency-driven parallel execution | `executor.py` ready queue + `runner.py` thread runner; metrics `waves`, `max_parallel`, `nodes_frozen_reused` | Implemented, tested (width, freeze reuse, failure isolation) |
| Minimal subgraph repair (LCA in history) | `repair.py` `lowest_common_ancestor` + downstream cone; nodes outside the region are frozen; `max_repairs`=2 covers both thought and runtime failures | Implemented, tested with mock. Widening on a repeated failure is **not** implemented (OQ-0016, by decision) |
| Node-local context (anti-hallucination) | Per-node prompts in planner and repair | Partial. Not measured |
| Paper environments (ALFWorld / WebShop / ScienceWorld) | — | **Missing, deferred** (Decision 0018) |
| Paper metrics (reward, steps, hallucinated-action rate) and baselines | `metrics.py` has waves, tool_calls, max_parallel, failures, repairs, frozen reuse and judge disagreements. No LLM-call count, steps or hallucination metric | **Missing** |
| LangGraph / DSPy interop | `integrations/` one-way callables, no imports | Stub-level |

## Minimal PoC run

| Step | Task | Model | Command (in atg-framework) |
|---|---|---|---|
| 0 offline | Two-branch sum, scripted model | MockLLM | `uv run python examples/toy_parallel.py` ✅ today |
| 1 live toy | Same task, real compile | `qwen2.5:14b` (atg NEXT.md step 1) | `uv run python examples/toy_parallel.py --live --model qwen2.5:14b --only` (only when `ollama ps` is empty) |
| 2 local worker | Same task | `qwen3.6:35b` (pfy bench: 79.2 % typed Choice, about 95 tok/s) | same command with `--model qwen3.6:35b`. atg NEXT.md currently says not to use 35b for the toy check. **That conflict needs a decision.** |
| 3 paper-shaped PoC | 8–12 synthetic tool DAGs with injected tool failures. Compare ATG localized repair against a global-replan baseline (`max_repairs`, with the region forced to the whole graph) and against a sequential runner | best of step 1/2 | New `examples/poc_suite.py` (not in tree). It reports success, LLM calls, tool calls, frozen reuse and wall time per arm |

Pass bar for "PoC for the paper": step 1 or 2 exits 0 with sink `{'value': 25}` and `max_parallel >= 2`, and step 3 shows fewer LLM and tool calls for localized repair than for global replan at equal success. Step 3 is not blocked by Decision 0018: it uses synthetic tools, not paper environments.

## Blockers

1. **Live compile reliability.** On 2026-10-05: `llama3.1:8b` hit the 180 s timeout, `qwen2.5:14b` produced an edge naming the parent id (since fixed by dropping it), and `gemma4` omitted `value` at the sink. There is no bench yet of which local tag compiles valid DAGs.
2. **Host contention.** The GLM-4.5-Air bench and openclaw `glm-4.7-flash` at 128k ctx hold Ollama, and nimo locked up on 10-05 under mixed load. Live runs need a quiet host (MemAvailable ≥ size + 25 GiB).
3. **Endpoint coverage.** `OllamaClient` is native Ollama only. `qwen3-coder-next` (83.3 %, 51 GB) only runs through `llama-server --no-mmap` (pfy Entry 092, `pipelines/dogfood/local-bench-4/run_nommap_server.sh`), which is OpenAI-compatible. Lemonade is up on :13305 (OpenAI-compatible, no model loaded). vLLM ROCm is not installed. Today atg can reach these only through LiteLLM (`uv sync --extra llm`, `ATG_MODEL=openai/<served-name>`, `OPENAI_API_BASE=http://127.0.0.1:<port>/v1`, dummy `OPENAI_API_KEY`). That path is untested, and `response_format=<pydantic>` support varies by server.
4. **No measurement harness** for paper claims (step 3).

No paid key is needed anywhere. Everything above runs on local models.

## (b) pfy-deanery integration points

| # | atg piece | pfy-deanery counterpart | Call | Size | Risks |
|---|---|---|---|---|---|
| 1 | **Compile bench** (how often a model emits a valid DAG, sink correct, repairs used) | `examples/local-bench/bench.py`, `pipelines/dogfood/local-bench-*` (48-case #230 harness, PeakSampler, receipts) | **Adopt** the pfy harness pattern for an `atg-compile` case set (about 10 tasks). It answers blocker 1 with the same receipts and memory floor | S–M (~200 LOC + receipt) | Host contention: reuse the one-model-at-a-time and 16 GiB floor rules |
| 2 | Thought-experiment judge (`judge_llm`) | Decision lane: `./pfy decision`, CUA-S1-FORMS, `scripts/pfy_jev_230.py` typed Choice/Score | **Adapt**: judge = typed Choice {execute, repair:<node-id>} through the decision lane instead of free-form text | M (~150 LOC + adapter in pfy, no atg core change) | CUA-S1-FORMS is a form-fill specialist. Measure it on judge cases before trusting it |
| 3 | `run_task` loop (compile → check → execute → repair) | `orchestration` toolset (`/agent-loops`, `scripts/pfy_orchestration_213.py`, FreeToken :1919) | **Adapt**: opt-in `--loop-kind atg` that runs `run_task` against registered pfy tools. Off the default path (stage non-goal: no pipeline hard dependency) | M (~300–500 LOC + E2E) | Live compile unproven. Two loop engines to maintain |
| 4 | `ToolRegistry` (JSON schema + callable) | `data/toolsets.json`, `data/harnesses.json`, `make smoke-*` targets | **Adapt** later: generate a registry from smoke and eval targets so a catalog stage probe (clone → install → smoke → score) is one DAG with frozen reuse on re-run | S–M | A plain make/cache gets most of the value. Do this only after #3 proves out |
| 5 | History JSON + `Metrics` | Evidence receipts (`receipt.json`, `loop-evidence.json`) | **Adopt** as the evidence shape for #1 and #3 | S | None significant |
| 6 | Parallel ready-queue executor | Bench and dogfood pipelines | **Skip** for model calls: nimo serves one large model at a time, so parallel width buys nothing and raises lockup risk. Fine for cheap non-LLM tools | — | — |
| 7 | Package coupling (submodule / `pip -e`) | OQ-0004, `data/tool_integration_stages.json` (I1 `submodule_later`) | **Skip now.** Probe by path (`~/DEVELOP/atg-framework`, pinned SHA) | — | Embedding before the live gate violates the stage non-goals |
| 8 | Catalog card refresh | TOOLS.md ATG row, `tool_integration_stages.json` ("No runnable core"), `docs/ops/atg-coupling.md` | **Adopt now** (follow atg `docs/ops/pfy-mentat-handoff.md` gate table). Card text: "runnable, unit-green, live unproven". Stage stays I1 until a live pass | S | Triple-write gap: no `data/tools.json` ATG object |
| 9 | LangGraph / DSPy adapters | Gom Jabbar uses DSPy. pfy core does not | **Skip** in pfy | — | — |

## (c) Recommended next step (Grok Build prompt)

Run a private ops note. It adds a stdlib OpenAI-compatible client (`ATG_BASE_URL`), a fail-and-recover test against a local fake server, and `examples/poc_suite.py` (localized repair vs global replan vs sequential, mock first), then runs the live step 1/2 when `ollama ps` is empty. Follow it with a private ops note (catalog card refresh + `atg-compile` bench lane).
