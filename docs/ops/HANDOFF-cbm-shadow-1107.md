# Handoff: codebase-memory shadow selection (bot/cbm-shadow-1107)

## What changed

- `scripts/cbm_shadow.py` runs `test_select.py` and `codebase-memory-mcp cli detect_changes --scope tests` on one base and head. It appends one JSONL record and exits 0. `PFY_CBM_SHADOW=0` writes nothing. A missing binary is one line, `cbm_error: binary missing`.
- `scripts/pregate.sh` launches that script from the end of `cleanup`, after the orphan reaper, via `setsid`. The launch does not wait. The gate exit is unchanged.
- `tests/test_cbm_shadow.py` uses a fake binary. A detect failure and a 30 s sleep leave the gate exit alone, a disagreement is logged with both sets, a risky path logs `run_all`, and the disable flag does not run the binary.
- `docs/ops/CBM-SHADOW-1107.md` is the nimo report. `docs/ops/MODULAR-CI.md` has a short Shadow selection note.
- `data/stages/codebase-memory-mcp.json` stays I2. Evidence points at the shadow report. `self_pipeline.status` is `applied` with that doc as evidence.
- `tests/test_stage_registry.py` still matches the split snapshot. Evidence lines appended after that snapshot are allowed only when the original tokens stay in front.

`scripts/run_tests.py`, `scripts/test_select.py`, `scripts/test_cache.py`, and `scripts/ci_selected_tests.sh` are unchanged. The selector still does not read the binary. The hook was re-applied after `9bfc82f` (light jobs, `scripts/tool_cache.sh`) moved cleanup. It is still the last step, after the orphan reaper.

## Catalog check

Before the hook: `docs/eval/TOOLSET-RANKING.md` and `data/stages/codebase-memory-mcp.json`. codebase-memory-mcp is I2 and the primary impact source (`code-graph` toolset). Chiasmus (entry 140) overlaps and is I0, so it is not wired. The gate stays `scripts/test_select.py`. `data/catalog_stage_handoff.json` was not edited. `catalog_stage_eval.py --apply` was not run.

I3 is not met. The card's `next_gate` says to promote only when `make smoke-codebase-memory` is the operator path of record. This shadow is report-only. The self-pipeline rule blocks I3 for a tool whose uses, features, or tags cover CI, testing, or review unless `self_pipeline` is set. This card is not classified (tags are mcp, code-memory, local-first, rag; features are `mcp` and `code graph`). It stays I2 anyway. The applied field records that the shadow runs in this repo's pregate.

## Measured

Hook, 30 calls: no-op 0.148 ms, disabled 0.149 ms, detached launch 0.456 ms. The ten real runs are in `docs/ops/CBM-SHADOW-1107.md`: agreement 5/10, run_all 4/10, cbm errors 0/10, only-in-cbm empty. Binary 0.9.0 returned the changed test files and did not walk to importers.

Risky, release, and secret paths still force `full` in `test_select`. The shadow does not narrow that.

## Commands

```bash
python3 scripts/cbm_shadow.py --base <parent> --head <sha>
python3 scripts/cbm_shadow.py --report
python3 -m unittest tests.test_cbm_shadow -q
python3 scripts/catalog_check.py
```

`PFY_CBM_SHADOW=0` skips the side process. Log default: `~/.cache/pfy/cbm-shadow/selections.jsonl`. Cache database: `~/.cache/pfy/cbm-shadow/db`.
