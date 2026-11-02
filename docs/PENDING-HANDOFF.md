## 2026-11-02: mvp-land-1031 (#306)

- Branch: `build/306-mvp-stack` (same tip pushed to `bot/mvp-land-1031` for CI). Not merged. No PR. Not a Feature GO. DevBot fast-forwards `main` after Tester+Reviewer PASS at the pinned SHA.
- Fixes for the Tester and Reviewer FAIL at `89cc0d2`: BX3 fail-closed review (`3a550e5`, `0d3c0fc`, `0e683b9`, `ff8b881` cherry-picked), Python 3.12 and shallow-clone test fixes, DevBot named for merges, Gom Jobbar spelling.
- Suite: eval-structural run 41527508885 at `07c9f63`: nimo 3.14 `Ran 1377` OK (skipped=17), Ubuntu 3.12 `Ran 1377` OK (skipped=109). The CI run and fresh shallow-clone pregate at the final pin are in the #306 report.
- Follow-ups: #307 (bare `./pfy` starts `ollama serve`), #308 (cloud review cuts the diff at 12000 chars).
- Handoff: [ops/HANDOFF-mvp-land-1031.md](ops/HANDOFF-mvp-land-1031.md). Decisions: [ops/AUTONOMOUS-DECISIONS-2026-11-02.md](ops/AUTONOMOUS-DECISIONS-2026-11-02.md).

## 2026-10-31: mvp-integrate-1031

- Branch: `bot/mvp-integrate-1031`. Not merged. No PR. No tag. Not a Feature GO. Catalog HOLD 70-75 stays.
- Demo: PASS. One cloud `./pfy build` on a temp fixture. Checker exit 0. Receipt [eval/mvp-1031/demo-receipt.json](../eval/mvp-1031/demo-receipt.json). Fixture branch `cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z` at `ebef4238a7eff8f938747623f7920b3fde74e586`. The integrate checkout was not the task target.
- Suite: `nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .` with `TMPDIR` on this worktree `tmp/`. Ran 1048 tests in 668.761s. Failures 2, skipped 16. Details in the handoff.
- Handoff: [ops/HANDOFF-mvp-integrate-1031.md](ops/HANDOFF-mvp-integrate-1031.md). Report: [../eval/mvp-1031/REPORT.md](../eval/mvp-1031/REPORT.md).
- Pregate not run: host busy.

## 2026-10-19: Hermes Agent bake-off (Entry 134)

- **Branch:** `bot/hermes-eval` (worktree `/home/mark/DEVELOP/pfy-mentat/tmp/hermes-eval`). Landed on `main` by fast-forward after the Tester and Reviewer gate (no-PR flow). Not a Feature GO. Mark chooses Hermes as the bot interface (wiring pending; see the handoff).
- **Verdict:** NO-WIN. Hermes 26/27 vs `opencode run` 25/27 on `qwen3.6:35b` (+3.70 pp, need +10). Valid tool-call rate 82.61% vs 97.83%. Hermes p50 8.75s vs 47.38s. Wilson intervals overlap.
- **Handoff:** [eval/HERMES-EVAL-HANDOFF.md](eval/HERMES-EVAL-HANDOFF.md). Write-up [eval/hermes-vs-current.md](eval/hermes-vs-current.md). Entry 134. Item C (adapter plan) skipped.
- **Isolation:** `~/.hermes` untouched. OpenClaw inactive and disabled. Model: the scored run left it loaded (`results.json` `model_unloaded: false`); the session cleanup unloaded it afterwards (see the handoff). `./tmp/` left in place.

## 2026-10-09 — orch-decisions-1009 decide-and-ship

- **Branch:** `build/orch-decisions-1009` (worktree `/home/mark/DEVELOP/pfy-mentat/tmp/orch-decisions-1009`). Not merged. Not a Feature GO. Catalog HOLD 70–75. eval-harness untouched. #76 stays closed.
- **Landed:** x-intake HOME isolation, timeout receipts (exit 1), full harness sha256 `68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397`, three smoke receipt dirs gitignored; agent-substrate bundle setup line; atg bench `integration_stage` defaults to `unscored`; TODO dedupe; T-0076 skill cross-links (Refs #6, not closed); T-0040 Claude Code notes (Refs #8, not closed).
- **Decisions:** 11 lines in [ops/AUTONOMOUS-DECISIONS-2026-10-09.md](ops/AUTONOMOUS-DECISIONS-2026-10-09.md).
- **Verify:** unittest 184 OK skipped=4 → 190 OK skipped=4. `make eval-structural` PASS. `catalog_check` PASS n_json=7. `make smoke-grok-skills` PASS.
- **PR:** `gh` is not logged in. Body [ops/PR-BODY-orch-decisions-1009.md](ops/PR-BODY-orch-decisions-1009.md). Compare https://github.com/themark-net/pfy-mentat/compare/main...build/orch-decisions-1009 . Handoff [ops/HANDOFF-orch-decisions-1009-2026-10-09.md](ops/HANDOFF-orch-decisions-1009-2026-10-09.md). Do not merge until Tester and Reviewer PASS at the head SHA in that handoff.

## 2026-10-08 — atg-compile entry 101, atg `main` pin

- **Entry:** 101, [sources/entries/101-atg-compile.md](../sources/entries/101-atg-compile.md). Qwen3.8-Flash-Next stays Entry 095. Not a Feature GO. Catalog HOLD 70–75. Stage stays **I2** (not I3). eval-harness untouched.
- **Pin:** atg `main` @ `543e778ed24fbf3fc903eb961feb627039019832`. Live receipt stays honest: scored at `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16` on `build/atg-finish`, 2/10 valid DAGs, 2/10 sink-correct, I2. The I2 score (2/10 valid, 2/10 sink-correct) was taken at 86d1b890 on build/atg-finish and has not been re-run at the main pin 543e778. Receipt `pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json`.
- **Bench:** `ATG_REPO` or `--atg-repo` is required. No default checkout path. Point it at a clean checkout or worktree of atg `main` at the pin. If HEAD is not the pin, the bench exits 2 and writes no receipt.

```bash
ATG_REPO=/path/to/atg \
  python3 examples/atg-compile/bench.py \
  --base-url http://127.0.0.1:11434 \
  --model qwen3.6:35b
```

- **Guard:** `python3 scripts/catalog_check.py` fails when two `sources/entries/NNN-*.md` files share an NNN prefix.
- **CI:** The atg e2e and endpoint-down bench tests skip unless `ATG_REPO` is set. The nimo runner env is deliberately unchanged; changing it needs Mark's OK.
- **Operator note:** [docs/ops/atg-coupling.md](ops/atg-coupling.md).

## 2026-10-06 — atg-compile live probe (I2, coder-next blocked)

- **Branch / worktree:** `build/local-lane-atg` · `/home/mark/DEVELOP/pfy-mentat/tmp/build-local-lane`. Not merged. Not a Feature GO. Catalog HOLD 70–75. eval-harness untouched.
- **Live:** Ollama `qwen3.6:35b`, quiet host, `--case-timeout 180`, pin `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16`. Exit 0. 2/10 valid, 2/10 sink-correct (`ac-01-mul-six-seven`, `ac-08-parallel-sums`), repairs 0, wall 478s. Receipt `pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json`. Model unloaded with `keep_alive: 0`.
- **Stage:** I2. The receipt JSON still says `integration_stage: I1` because the bench writes that constant. The catalog card was updated after the score. Not I3.
- **coder-next:** not loaded. Blob 51,741,599,936 bytes. MemAvailable 65.3 GiB after the 35B unload. Lane rule is size + 25 GiB.
- **Entry:** [sources/entries/101-atg-compile.md](../sources/entries/101-atg-compile.md) (renumbered; Entry 095 is Qwen3.8-Flash-Next). Credit Zhang et al. (2026), arXiv:2607.01942. Not official code. Not a paper-benchmark claim.
- **PR body:** `/tmp/pr-pfy-local-lane.md`. `gh` is not logged in on this host. Compare URL is in that body. Do not merge.

## 2026-10-06 — llamacpp-nommap lane + atg-compile bench (I1, live not run)

- **Branch / worktree:** `build/local-lane-atg` · `/home/mark/DEVELOP/pfy-mentat/tmp/build-local-lane`. Not pushed. Not a Feature GO. Catalog HOLD 70–75. eval-harness untouched.
- **Lane:** `llamacpp-nommap` in `data/eval-lanes.json` and `pfylib/hedge.py` (start, `GET /v1/models`, stop, GGUF path). Default model stays `qwen3.6:35b` on Ollama. `qwen3-coder-next` is opt-in. MemAvailable < model size + 25 GiB → exit 2, no spawn. This session did not start the server.
- **Bench:** `examples/atg-compile/bench.py`, 10 cases in `data/decision-gates/atg-compile.cases.v0.json`. Calls atg by path. That session scored `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16` on `build/atg-finish`. Current pin and run command are in the 2026-10-08 section.
- **Catalog:** ATG card refreshed at **I1**, not I2. `tools.json` object added (scores copied from TOOLS.md, not re-scored). No new sources entry: this is not an X seed; Entry 001 was not rewritten. Credit Zhang et al. (2026), arXiv:2607.01942. Independent reimplementation. Not official ATG code. Not a paper-benchmark claim.
- **Live:** not run. Parent held `qwen3.6:35b`. No invented live numbers. Writeup: [docs/dogfood/ATG-COMPILE-RESULTS.md](dogfood/ATG-COMPILE-RESULTS.md).
- **Verify:** `python3 -m unittest discover -s tests -t .` → 179 OK, 2 skipped. `make eval-structural` → PASS (same 179). `python3 scripts/catalog_check.py` → PASS `n_json=7`. Fake-server bench: 1 valid / 1 invalid, exit 0. Endpoint down: exit 2, no receipt. Memory floor: injected 1.000 GiB → exit 2.
- **atg offline (dirty pin tree):** pytest 40 passed, 1 deselected. Toy sink `{'value': 25}`.
- **Next:** T-0127 when the host is quiet. PR body is `/tmp/pr-pfy-local-lane.md` for the parent. Do not merge.

## 2026-10-06 — atg-framework eval + Build drop-ins (Entry 093)

- **Branch:** `bot/atg-eval`. Docs only. Handoff: [eval/ATG-EVAL-HANDOFF.md](eval/ATG-EVAL-HANDOFF.md).
- **atg verdict:** loop in code, 35 unit tests green, live compile unproven (0/3). Not yet a paper PoC. pfy: adapt (compile bench, decision-lane judge, opt-in loop kind), do not embed. ATG stays I1. Card text is stale.
- **Drop-ins:** `docs/build-dropins/` (atg-framework first). Mark: pick the live toy model (qwen2.5:14b vs qwen3.6:35b). Not a Feature GO.

## local-bench-5 / Entry 094 (2026-10-06 PT) — supersedes stale ~22 GB “hardware edge”

**Edge (corrected):**
| Path | Reliable | Notes |
|------|----------|-------|
| Ollama defaults | ~22 GB (`qwen3.6:35b`) for *ready* big-MoE loads | 51GB double-hold still fails under Ollama mmap+GTT |
| llama-server `--no-mmap` + UMA | **51 GB coder-next** Choice OK; **65 GB gpt-oss** loads; **73 GB GLM-Air** loads but **degenerate output** | Real Strix Halo ceiling ≫ 22 GB once double-load avoided |

**Runtime for atg:** prefer **Ollama + qwen3.6:35b** (decode ~96 tok/s, 79.2% Choice). Alternate: llama-server ROCm `--no-mmap -rea off` (same accuracy, ~57 decode). Avoid GLM-Air / gpt-oss for typed #230. vLLM blocked until ROCm matches wheel (7.1 vs rocm723) + hipsparselt/rocprofiler-sdk.

**gpt-oss wbc:** 4 (Entry 092 no-mmap receipt), not “-”.

## local-bench-4 no-double-load (2026-10-06 PT)

- PR #273 extended: llama-server ROCm `--no-mmap` proves 51GB coder-next RAN (not 22GB hardware edge).
- atg: keep qwen3.6:35b / qwen3-coder:30b + CUA-S1-FORMS; stretch coder-next only via no-mmap path.
- Air still incomplete pull; openclaw glm@128k stalls documented.

# Pending handoff

Git plus this file is the handoff when another checkout may be open. Do not commit, reset, or stash on an open founder Build branch.

## 2026-10-05 — Local-bench 4 edge probe (Entry 092 / #230)

**Env:** OLLAMA_LOAD_TIMEOUT=30m + MemoryHigh=85G verified. Stacks on #272 (`96cdc73`).

**Edge (stale pre-#273 no-mmap — see Entry 094 header):** Ollama-default big-MoE ready-path still ~22 GB; no-mmap raises hardware edge to 51GB+ (GLM-Air loads but quality fail).

**atg-framework:** coding → `qwen3.6:35b` / fallback `qwen3-coder:30b`; decision → CUA-S1-FORMS.

**Harness:** runner RSS fix (exe EACCES); outdir tests call helpers. Not a Feature GO.


## 2026-10-05 — Local-bench 3 MemoryHigh=85G (Entry 091 / #230)

**Context:** Mark raised ollama `MemoryHigh` to **85G**; #271 merged as `357e3c6`. Branch `bot/local-bench-3`. Mid-slice nimo lockup + concurrent **atg-framework** Grok Build → big MoEs **deferred: host contention**; MemAvailable floor **16 GiB**.

**Measured:** `qwen3.6:35b` RAN 79.2% / 0% esc / parse_ok 48. `qwen3-coder-next` + `gpt-oss:120b` DROP (ollama llama-server start timeout). GLM-4.5-Air skipped.

**Models to point atg-framework at:** local coding **`qwen3.6:35b`** (fallback `qwen3-coder:30b`); local decision **CUA-S1-FORMS**; avoid glm-4.7-flash / gpt-oss / coder-next / GLM-Air until `OLLAMA_LOAD_TIMEOUT` raised + quiet-host rebench.

**Mark approvals:** `OLLAMA_LOAD_TIMEOUT≈30m` in ollama drop-in; pause openclaw 128k loads during big benches. Not a Feature GO.


## 2026-10-05 — Local-bench 2 post carve + GLM shortlist (Entry 090 / #230)

**Done (bot worktree `bot/local-bench-2`):** Re-ran Entry 089 harness after Mark's BIOS VRAM 16 GiB + GTT ~96 GiB. Documented ollama `MemoryHigh=40G` blocker. GLM shortlist (4.5-Air fits weights ≤90 GB but blocked by MemoryHigh; 5.3-Flash / full 4.5–4.6 / GLM-5 do not fit usable ≤90 GB). glm-4.7-flash autopsy = typos not thinking-token parse. Challenger `qwen3.6:35b` pulled (~22 GB).

**Mark approvals needed:** Raise/remove `ollama.service` drop-in `MemoryHigh=40G` to use GTT for gpt-oss:120b / qwen3-coder-next / GLM-4.5-Air Q4. Do not change BIOS/kernel again unless asked.

**Not a Feature GO.** Catalog HOLD 70–75. CUA-S1-FORMS stays primary local.


## 2026-10-06 — Local-inference bench on nimo (Entry 089 / #230 case set)

- **Branch / worktree:** `bot/local-bench` · `/home/mark/DEVELOP/pfy-mentat/tmp/local-bench`.
- **Landed:** stdlib harness `examples/local-bench/bench.py`; receipt `pipelines/dogfood/local-bench/receipt.json`; writeup [docs/dogfood/LOCAL-BENCH-RESULTS.md](dogfood/LOCAL-BENCH-RESULTS.md); sources [089](../sources/entries/089-local-inference-bench.md) at **I0 / trial-ran**. Catalog HOLD 70–75. No GUI. No TOOLS.md row. **Not a Feature GO.** CUA-S1-FORMS stays primary local. No BIOS/kernel/sysctl change.
- **Live (nimo, Ollama 0.30.8, ctx 2048, same 48 cases, gate 0.85):** 1.5b 54.2% / 0% esc / 22 wbc / 117 decode tok/s; glm-4.7-flash 39.6% / 33.3% / 13 / 53 tok/s; **qwen3-coder:30b 79.2% / 2.1% / 10 / 65 tok/s** (18 GB, 100% GPU); stretch qwen3-coder-next 83.3% / 2.1% / 7 / 18 tok/s (52 GB, 89% GPU). gpt-oss:120b skipped (65 GB > 64 GiB carve). Unloaded after. Baselines: CUA 56.3%/22.9%/16 wbc; Laya english 62.5%/100%/0.
- **Run on nimo now:** `qwen3-coder:30b` as the coding worker; 1.5b for smokes; next only when quality > tok/s. Decision default stays CUA-S1-FORMS.
- **Verify:** `python3 -m unittest tests.test_local_bench` · `python3 scripts/catalog_check.py` · `make eval-structural` · `python3 -m unittest discover -s tests -t .`
- **Next:** orchestrator commit/push/PR. Do not merge / contact gates. Do not apply BIOS/GTT knobs without Mark.

## 2026-10-06 — Laya shadow second-opinion (Entry 086 follow-up / #230 / ADR-0016)

- **Branch / worktree:** `bot/laya-shadow` · `/home/mark/DEVELOP/pfy-mentat/tmp/laya-shadow`.
- **Landed:** `PFY_JEV_LAYA_SHADOW` opt-in (default off). CUA-S1-FORMS stays `PRIMARY_LOCAL`. When flag is on and CUA would auto-act, Laya **english** shadows the choice; disagree or Laya error → escalate (exit 3). No silent auto-act. Cloud TypeSafe refused.
- **Measure (nimo, same 48 cases):** catch **9/16**, false-escalate **4/21**, miss 7/16, shadow p50 **0.185 s** / p95 **0.260 s**, HWM **2867668 KB**. Verdict RAN. Flag stays off. Not a Feature GO. Catalog HOLD 70–75. No GUI.
- **Writeup:** [docs/dogfood/LAYA-SHADOW-RESULTS.md](dogfood/LAYA-SHADOW-RESULTS.md). Receipt `pipelines/dogfood/laya-shadow/receipt.json`.
- **Verify:** `python3 -m unittest tests.test_laya_shadow tests.test_laya_trial_086 tests.test_jev_decision_skill tests.test_pfy_build_p` · `python3 scripts/pfy_jev_230.py --selftest` · `python3 scripts/catalog_check.py` · `make eval-structural`.
- **Next:** orchestrator commit/push/PR. Do not merge / contact gates. Do not turn the flag on by default.

## 2026-10-06 — Laya eval-auto trial (Entry 086 / #230 / ADR-0016)

- **Branch / worktree:** `bot/laya-trial` · `/home/mark/DEVELOP/pfy-mentat/tmp/laya-trial`.
- **Trial:** verdict **RAN** on nimo (48 cases, gate 0.85). Keep **CUA-S1-FORMS** as default. No lane change. Not a Feature GO. Catalog HOLD 70–75. No GUI.
- **Writeup:** [docs/dogfood/LAYA-TRIAL-RESULTS.md](dogfood/LAYA-TRIAL-RESULTS.md). Receipt `pipelines/dogfood/laya-trial/receipt.json`.
- **Next:** merge when gates green. Shadow second opinion: **done** on `bot/laya-shadow` (flag off by default). See [LAYA-SHADOW-RESULTS.md](dogfood/LAYA-SHADOW-RESULTS.md).

## 2026-10-05 — D4 Reviewer fix round (#266 / #265, CEO hold)

- **Branch / worktree:** `bot/dogfood-d4-265` · `/home/mark/DEVELOP/pfy-mentat/tmp/dogfood-d4-265`. No `./pfy build -p` / no live Grok (CEO hold).
- **Fixes:** (1) `test_this_host_bundled_link_under_measured_bound` opt-in via `PFY_HOST_BUNDLED_TEST=1` (checked before any `~/.grok` access; skip if bundled absent; drop host-specific 2.78M cap). (2) isolated `auth.json` forced `0600`, home `0700`; grok-home under receipt stamp persists for audit (gitignored). (3) D4-RESULTS token-gap note + outer-bot edit list.
- **Verify:** `make catalog-check` · `make eval-structural` · `PFY_HOST_BUNDLED_TEST` unset · `python3 -m unittest discover -s tests -t .` (G0-equivalent). Portable `SkillsBundleTests` still FAIL on `a8977c33`.
- **Next:** green G0 on ubuntu-latest; do not merge until Reviewer re-check.

## 2026-10-05 — Dogfood D4 bundled expose without user skills (#265)

- **Branch:** `bot/dogfood-d4-265` (from `a8977c33`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/dogfood-d4-265`.
- **Landed:** isolated Build home **byte-copies** `bundled/` (no symlinks; dest chmod a-w); no `~/.grok/skills` copy; receipt `skills_bundle_*`; missing bundled → fail closed; write-through test. [docs/dogfood/D4-RESULTS.md](dogfood/D4-RESULTS.md).
- **Safety:** Run1 file-symlinks mutated real `~/.grok/bundled` (skills hash unchanged). Run2 switched to copies; subsequent live left both trees stable at post-incident hashes.
- **Live (copy):** ~6.5s, 1 call, **17 816** tokens vs D3 tiny **14 959** / D2 **623 246**.
- **Verify:** `make catalog-check` · `make eval-structural` · `python3 -m unittest tests.test_pfy_build_p tests.test_jev_decision_skill`
- **Next:** optional SKILL.md-only allowlist copy to shrink receipt grok-home; Mark may want to refresh `~/.grok/bundled` from Grok install after the symlink incident.


## 2026-10-05 — Dogfood D3 trimmed build preamble (#263)

- **Branch:** `bot/dogfood-d3-263` (from `cbda54a`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/dogfood-d3-263`.
- **Landed:** trimmed `./pfy build -p` preamble + isolated child GROK_HOME; `PFY_BUILD_FULL_PREAMBLE=1`; receipt preamble size fields; tests; [docs/dogfood/D3-RESULTS.md](dogfood/D3-RESULTS.md).
- **Live trimmed measure:** ~6s, 1 turn / 1 call, **14 959** total tokens vs D2 **623 246**; route escalate exit 3; preamble_tokens_est **87**.
- **Out of scope:** GUI, catalog HOLD 70–75, Feature GO, merge.
- **Verify:** `make catalog-check` · `make eval-structural` · `python3 -m unittest tests.test_pfy_build_p tests.test_jev_decision_skill`
- **Next:** done in D4 as byte copies. Do not symlink `bundled/` into the isolated home (that write-through changed the real tree).

## 2026-10-05 — Dogfood D2 bot lane (`./pfy build -p` real implement)

- **Branch:** `bot/dogfood-d2-0310654` (from main after #261). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/dogfood-d2`.
- **Landed:** jev-decision skill prefers `./pfy build -p` + route exit **3**=escalate; project mirror `.grok/skills/jev-decision/`; `tests/test_jev_decision_skill.py`; modules Failure-modes ESCALATE wording; [docs/dogfood/D2-RESULTS.md](dogfood/D2-RESULTS.md) + `pipelines/dogfood/build/20261005T071051Z/` receipt.
- **Path:** one `./pfy build -p` run completed implement (~203s, 1 turn / 13 model calls). TypeSafe tokens **0**.
- **Out of scope:** GUI, #258/#256, catalog HOLD 70–75, live TypeSafe, Feature GO, merge.
- **Verify:** `make catalog-check` · `make eval-structural` · `python3 -m unittest tests.test_jev_decision_skill tests.test_pfy_build_p`
- **Next:** Review D2; optional live `push_hold` dual-run shadow; human D1-dev lane still open.

## 2026-10-05 — D1 friction fixes (`./pfy build -p` + route escalate exit)

- **Branch:** `fix/d1-friction-pfy-build-p` (from main `682aa20`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/d1-friction-fix-20261005`.
- **Landed:** `scripts/pfy_build_p.py` + `./pfy build -p`; route conf-low → exit **3** / `verdict: escalate`; docs follow-up in [docs/dogfood/D1-RESULTS.md](dogfood/D1-RESULTS.md); tests `tests/test_pfy_build_p.py`.
- **Closes:** D1 friction (plain output-format wrap, escalate≠broken, real receipt.jsonl). Empty D1 `pipelines/dogfood/d1/receipt.jsonl` left historical.
- **Out of scope:** GUI, #258, TypeSafe spend, Feature GO, merge.
- **Verify:** `make catalog-check` · `make eval-structural` · `make smoke-product-levers` · `python3 -m unittest tests.test_pfy_build_p`
- **Next:** merge when checks green; optional bot skill to prefer `./pfy build -p` over bare `grok -p`.

## 2026-10-05 — Dogfood D1 bot lane (jev toolset + wrapped grok -p)

- **Branch:** `dogfood/d1-jev-pfy-wrap` (from main `29b74ac`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/dogfood-d1-20261004`.
- **Landed:** `data/decision-gates/` (README + `push_hold.shadow.v0.json`), ops/handoff cross-links, [docs/dogfood/D1-RESULTS.md](dogfood/D1-RESULTS.md) + `pipelines/dogfood/d1/` receipt.
- **Path:** `./pfy toolset apply jev --harness grok --lane local` → smoke/selftest READY → `./pfy decision route` conf-low (shadow escalate, no auto-act) → `grok -p` body (~125s, 1 turn). TypeSafe tokens **0**.
- **Out of scope:** D1 human-dev lane (Mark at keyboard), #258, Kolibri, catalog HOLD 70–75, live TypeSafe, Feature GO, merge.
- **Next:** Review D1 results; optional live shadow dual-run for `push_hold`.

## 2026-10-04 — Jev decision layer × org bots × pfy dogfood plan

- **Branch:** `docs/jev-decision-layer-and-pfy-dogfood` (from main `c0d9072`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/jev-dogfood-plan-20261004`.
- **Ask:** Figure out existing Jev/TypeSafe usage; plan integration with Grok Bot org + Grok Build on nimo and pfy-mentat; dogfood whether `./pfy` can replace/augment bare `grok -p` for bots and a human (Mark / Bleeping Blank).
- **Landed (docs-only):** [docs/design/JEV-DECISION-LAYER-AND-PFY-DOGFOOD.md](design/JEV-DECISION-LAYER-AND-PFY-DOGFOOD.md) — inventory, decision table (keep-in-code vs Jev-style vs LLM), catalog posture (`jev` toolset stays `catalog_tool: null` per ADR-0016; no TOOLS.md row in this PR), thin-adapter notes, dogfood slice **D1**, blockers (no `TYPESAFE_API_KEY`).
- **Already wired (not new code):** `#230` / ADR-0016 / `scripts/pfy_jev_230.py` / `./pfy decision` / toolset `jev`. Local smoke READY; TypeSafe cloud optional and **unkeyed** on nimo. Org side: `themark-net/org-spinny-decide` + box skill `org-spinny-decide` (Ollama, explicitly not cloud TypeSafe).
- **Out of scope:** live TypeSafe calls, new TypeSafe account/spend, catalog HOLD 70–75, PR #256 Loop agent-picker split, eval-auto `NameError: re` fix branches, Feature GO, merging.
- **Next:** (1) Done — plan merged as #259 @ `29b74ac`. (2) D1 bot lane ran — stub in `data/decision-gates/` + [docs/dogfood/D1-RESULTS.md](dogfood/D1-RESULTS.md). (3) Shadow-log bridge for `push_hold` (live dual-run) still next. (4) T-0123 if/when catalog re-score for TypeSafe cloud is wanted.

## 2026-10-04 — PR #256 follow-up: split Loop picker + harness extract fix

- **PR #256 branch:** `build/pfy-cli-catalog-cards-0925` — CLI/catalog/eval only (no `gui/`, no `pfy-gui.py`, no `loop_paint.py`).
- **Split-off (draft PR #258):** `build/loop-agent-picker-0925` — Sep 25 Loop agent-picker / compose-from-Loop / "Open … with …" CTA. Conflicts with LOOP-243 design lock on main. Needs a Design pack before review.
- **Harness bug:** `extract_python` dropped leading `import re` before `def` → live `NameError: re` on 012-slugify (pre-existing on main). Fixed + `tests/test_extract_python.py`.
- **ensure_compose_defaults:** stayed with the picker branch (tied to Loop agent selection / GUI).
- **Eval-auto:** WIP kept; passes with gate `deepseek-coder:6.7b` after extract fix.

## 2026-10-04 — land Sep 25 Grok Build: CLI catalog cards + eval-auto

- **Branch:** `build/pfy-cli-catalog-cards-0925` (rebased onto current `origin/main`)
- **Backup:** `backup/main-local-20261004` @ pre-rebase `3afd13b`; WIP snapshot `backup/wip-uncommitted-20261004`
- **What the Build session did (Sep 25) — kept here:**
  1. **pfy CLI harness polish** — short product help; shimmy last after ollama; ollama start health + default model; share Hermes/Claude/Codex installers between CLI and Attach; read Gemini/Exo installers from registry; Continue recipe names direct vs cage filesystem.
  2. **Catalog stage cards** — every TOOLS.md row must have an integration-stage card; handoff cards for stage rows.
  3. **Eval-auto** — `scripts/eval_auto_candidates.py` + `eval-auto.sh` candidate loop + receipt (T-0074); `013-stage-card` structural scorer (T-0070).
- **Moved out:** Loop/GUI agent-picker → draft PR #258.
- **Verify:** `make catalog-check` · `make eval-structural` · `make smoke-product-levers` · `EVAL_AUTO_REQUIRE_OLLAMA=1 make eval-auto`.
- **Next:** merge when checks green. Do not auto-lift catalog HOLD entries 70–75.

## 2026-10-04 — Kolibri-1 catalog + local smoke lab (Entry 085)

- **Branch:** `bot/kolibri-1` (from main `53b24ec`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/kolibri-1`. Operator ask: "Add to pfy-mentat. Pull it and test." (X post 2106306843052052616)
- **Landed:** `sources/entries/085-kolibri-1.md` (084 is taken by open PR #254), a TOOLS.md row (B, 72, public-docs scores), a `data/tools.json` row + `data/tool_integration_stages.json` (I0), `examples/kolibri1-llamacpp/` (build/download/serve/smoke), `make smoke-kolibri1`, and the receipt `pipelines/smoke/kolibri1/latest.json`.
- **Paths checked:** (a) Community GGUFs exist, but every one needs a llama.cpp source patch; stock llama.cpp and Ollama have no `kolibri1` (llama.cpp#29922 open). The smallest is `Eliasfpv28/Kolibri-1-Q3_K_S-GGUF` at 33.87 GB. (b) The only other registered machine, GROKBOT-WIN, is offline; nimo is AMD Strix Halo (Radeon 8060S, 64 GiB VRAM carve-out, 61 GiB RAM, no NVIDIA). (c) Kolibri is not on OpenRouter and has no HF inference-provider mapping. No Aleph Alpha, OpenRouter, or HF key names are in nimo env or `.env`.
- **Done on nimo:** Patched llama.cpp CPU backend built under `tmp/kolibri-runtime/build-cpu`. GGUF download was started then **stopped and deleted** (too big for nimo). Meta-only under `tmp/models/Kolibri-1-meta/`. Smoke at PR time: `FAIL_NO_BACKEND` (honest).
- **Next:** Kolibri-1 stays **watch-only at I0**. Mark: too big for nimo; watching for newer/smaller models. No Vulkan build; do not re-download weights or promote to I1.
- **Out of scope:** catalog 70–75 HOLD, other open PRs, Feature GO.

## 2026-10-02 — #198 Ix Stage-0 receipt

- **Branch:** `bot/ix-198-stage0` (isolated worktree). This slice is [#198](https://github.com/themark-net/pfy-mentat/issues/198) only. Do not push. No Feature GO.
- **Verdict:** Stage-0 FAIL / I0 awareness. Receipt: [sources/entries/084-ix.md](../sources/entries/084-ix.md). No TOOLS.md row and no `data/tools.json` row.
- **Shown:** Ix `LICENSE` is Apache-2.0 (commercial/research, not copyleft). README hello-world is `ix map .` then `ix explain AuthService` (cited, not run). Quickstart command is `curl -fsSL https://ix-infra.com/install.sh | sh`.
- **Not shown:** a fresh Ubuntu/Mac setup under 5 minutes. The installer says the Docker Desktop download is ~700MB and may take a few minutes, then the image pull may take a few minutes. macOS first launch waits up to 5 minutes before that pull. `arangodb:3.12.11` is Business Source License 1.1 (internal use allowed). It is not vendored.
- **Unchanged:** `TOOLS.md`, `data/tools.json`, pfy runtime, product UI, Make targets, env registry.
- **Verify:** `python3 scripts/pfy_ix_198.py` (exit 0). The check fails if the receipt is missing, if the status claims Stage-0 PASS without license/quickstart/hello-world evidence or while those timing quotes remain, or if product files attach Ix.
- **Risks:** A PASS while the timing quotes remain is a false pass — the check exits 1; promote only with a timed fresh log. Stripping the quotes without re-reading `scripts/install/install.sh` at pin `48687b5b403051f520c54cd14e01f90ddd444bc7` hides the same failure — re-read the installer before any PASS. Reading Apache as covering Arango misses BSL 1.1 — re-read that LICENSE before any embed. Treating the cited `ix map` as a live run hides a broken release — run it outside this repo before a catalog row. A product-file attach is reverted; entry 084 stays the artifact.
- **Next:** leave Ix at I0. Re-time the install outside this repo before any catalog row. Do not pull images or weights on this branch.

## 2026-09-28 — founder standings into portable skills SoT

- **Branch:** `bot/skills-port-standings-20260928` (from main `bd35bad`)
- **Prior:** stalled `bot/skills-port-standings-20260925` @ `d262300` cherry-picked here. That branch was never a PR. Do not force-push `main`.
- **Landed:** `prefer-behavior-and-fail-recover-tests`, `ui-is-the-app-design-in-loop`, `best-effort-and-bot-budget-build-max`
- **SoT:** `bootstrap/grok-cli/skills/<name>/` (org bot skills stay pointers). Project mirror: `.grok/skills/`.
- **Out of scope:** catalog 70–75 HOLD, LIVE_HARD_OFF, product UI, Feature GO.
- **Verify:** `make smoke-grok-skills`
- **Next:** merge the docs/skills PR when checks are green. Pattern: [port-bot-doctrine-to-pfy-sot.md](ops/port-bot-doctrine-to-pfy-sot.md).
