# Handoff: catalog verdicts (2026-11-07)

Lane `bot/catfix-verdicts-1107`. Not pushed. SkillSpector stays at I3. Bumblebee stays at I2. This lane does not demote any card.

## What landed

`scripts/catalog_apply_verdict.py` reads a `VERDICT.json` and one stage card. The JSON is canonical. It carries `metric`, `threshold`, `value_gate`, `modularity_gate`, and `proposed_stage`. The schema is `docs/ops/VERDICT.schema.json`. `--write-one-line` generates the old one-line `VERDICT` from those fields. The first token is `PROMOTE`, `STAY`, or `DEMOTE`. A hand-written one-line is not a second source.

Apply writes `integration_stage` only when `proposed_stage` is within the allowed ceiling. A stage above the ceiling exits nonzero, prints `above-ceiling`, and does not write the card. The same legal verdict a second time leaves the card bytes unchanged.

`--scan` writes `eval/catalog-verdicts/CEILING-MISMATCHES.md` and prints the same text. It does not write cards. The same cards produce the same report. Exit 0 means the scan finished. Mismatches are flags, not a red gate. Mark decides demotions.

Allowed stage is the lower of the evidence ceiling and `tier_ceiling` when the card has one. `tier_ceiling` is a cap. It does not raise weaker evidence. Evidence is the card's `evidence` list only:

- I3: an item starts with `make:` or `path:`.
- I2: a measured probe (`results.json`, `check-results.json`, `*-results.json`, `*-bench.json`, `receipt.json`, `receipt:`, `tools/_probe/`, `probe:`).
- I1: any other listed artifact (notes, pin, entry, report, scan summary, VERDICT, summary, script).
- I0: the list is empty.

On apply, a failing modularity gate caps the write at I1. A failing value gate caps the write at I2. I3 and I4 need both gates. A CI, testing, or review tool cannot go above I2 unless `self_pipeline` passes the same check as `scripts/catalog_check.py`. Apply and scan call `self_pipeline_problems`, which uses `pipeline_role_hits`. That check does not promote a card. This lane did not edit that script.

New verdict `intent` values must be in the enum or an alias. Enum: `awareness`, `catalog_default`, `staged_evaluation`, `ad_hoc_probe`, `onboard`, `embedded`. Aliases: `staged_eval` -> `staged_evaluation`, `adhoc_probe` -> `ad_hoc_probe`, `ad-hoc-probe` -> `ad_hoc_probe`, `ad-hoc_probe` -> `ad_hoc_probe`. Stored card intents are left as they are, including one-offs. The report lists those one-offs. This scan found 38.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, `scripts/catalog_stage_eval.py`, `scripts/catalog_check.py`, and the `uses`, `features`, and `tags` on `data/stages/*.json` before writing code.

- `docs/eval/TOOLSET-RANKING.md` records trials in the retired monolith and under `eval/catchup-1107/`. It does not write a structured verdict or refuse a stage.
- `scripts/catalog_stage_eval.py` recomputes `tier_ceiling` from TOOLS.md and posture. The ceiling is a cap, not a promotion. It does not change `integration_stage` just because the ceiling allows it. This lane reuses that cap. It does not copy the ceiling onto the stage.
- `scripts/catalog_check.py` checks the card shape and `self_pipeline` for an I3 or I4 tool whose uses, features, or tags cover CI, testing, or review. This lane calls `self_pipeline_problems` and `pipeline_role_hits`. It does not edit that script.
- One-line `eval/**/VERDICT` files already use `PROMOTE`, `STAY`, or `DEMOTE`. This lane keeps that shape and generates it from JSON.
- No stage card's uses cover "write VERDICT.json and refuse an illegal stage". SkillSpector is a static skill scan. Bumblebee is a lockfile and MCP-config scan. Neither enforces `integration_stage`.

No new stage card. This script is not a cataloged tool moving to I3.

## Five questions

1. What triggers it? An eval that finishes a probe writes `VERDICT.json` and runs the apply script. A person can also run `--scan` against the current cards.
2. What does it do, and which services does it read and write? It reads the verdict JSON, one `data/stages/<slug>.json` card (or every card on scan), and the schema. A legal apply writes that card's `integration_stage`. An illegal apply writes nothing and exits nonzero. Scan writes `eval/catalog-verdicts/CEILING-MISMATCHES.md`. No hosted service. It does not write coverage, the dashboard, or the eval queue.
3. What does it trigger next? Later evals can call the same script. `catalog_check.py` is unchanged. This lane does not add a CI job.
4. Where does a human re-enter? Any ceiling flag below. Mark decides demotions. A refused illegal promotion also stops an eval from writing a bad stage. One-off intents stay until a person edits that card.
5. What stops two runs doing the same work? Apply is deterministic. The same legal verdict twice leaves the card byte-identical the second time. An illegal stage is never written. The mismatch report is a pure function of the cards, so two scans with the same cards print the same flags. This lane does not write `_registry.json` coverage, `pipelines/catalog/dashboard.latest.md`, or `eval/catalog-queue/queue.tsv`, so it does not collide with the counts or queue lanes.

## Flags (stages not changed)

Scanned 129 cards. 14 are above the allowed ceiling. Required names:

- SkillSpector: stage I3, evidence ceiling I1, tier_ceiling I3, allowed I1. Evidence is an entry, notes, a pin, a scan summary, and a report. `self_pipeline` is null. tier_ceiling I3 does not raise that evidence. `integration_stage` is still I3.
- Bumblebee: stage I2, evidence ceiling I1, tier_ceiling I1, allowed I1. Evidence is notes, a pin, a report, a VERDICT, and `scripts/pfy_mcp_scan.py`. tier_ceiling I1 agrees with the evidence. `integration_stage` is still I2.

The other flags, also left in place:

- skill-up: I3 vs allowed I1. Evidence is a summary, a report, and an entry. The applied `self_pipeline` record does not raise that evidence.
- repowise: I2 vs allowed I1. Evidence is `make:smoke-repowise` (I3), and tier_ceiling I1 caps it. The smoke path is stronger than the tier cap. The cap still wins.
- HiRoute: I2 vs allowed I1. Evidence is an entry and a report. tier_ceiling I1 agrees.
- Sandlock, Sponsio, destructive_command_guard, llama.cpp ngram-mod, opencode-mem, taste-skill: stage I2, probe evidence supports I2, tier_ceiling I1 caps the allowed stage at I1.
- Antigravity-Manager: stage I1, notes only, tier_ceiling I0 caps the allowed stage at I0.
- MLX + MLX-LM and llama.cpp (server mode): stage I1, evidence list empty (I0). tier_ceiling I1 does not raise an empty list.

## Run

```bash
python3 scripts/catalog_apply_verdict.py --scan
python3 scripts/catalog_apply_verdict.py --scan --report eval/catalog-verdicts/CEILING-MISMATCHES.md
python3 scripts/catalog_apply_verdict.py --card data/stages/widget.json --verdict eval/widget/VERDICT.json --write-one-line eval/widget/VERDICT
```

`--root` overrides the repo for a scan. Apply prints the generated one-line on stdout. Refusals go to stderr and start with `refused:`.

## Tests

```bash
python3 -m unittest tests.test_catalog_verdict_idempotent tests.test_catalog_verdict_oneline tests.test_catalog_verdict_ceiling_refuse tests.test_catalog_verdict_intent_enum tests.test_catalog_verdict_fail_recover tests.test_catalog_verdict_mismatch
python3 scripts/catalog_check.py
python3 scripts/check_no_encoded_payloads.py
```

Behavior tests drive the script as a subprocess against temp cards. A legal promote writes the new stage. A second apply is byte-identical. An illegal promote above the ceiling is refused and the card bytes stay the same. A Scan Only fixture (notes, scan summary, report) is flagged and not demoted. A Probe Cap fixture at I2 with tier_ceiling I1 is flagged and not demoted. Malformed JSON, a missing card, and a stage above the ceiling each fail, then a corrected run writes a legal stage.

## Files

- `docs/ops/VERDICT.schema.json`
- `docs/ops/HANDOFF-catalog-verdicts-1107.md`
- `scripts/catalog_apply_verdict.py`
- `eval/catalog-verdicts/CEILING-MISMATCHES.md`
- `tests/test_catalog_verdict_idempotent.py`
- `tests/test_catalog_verdict_oneline.py`
- `tests/test_catalog_verdict_ceiling_refuse.py`
- `tests/test_catalog_verdict_intent_enum.py`
- `tests/test_catalog_verdict_fail_recover.py`
- `tests/test_catalog_verdict_mismatch.py`

Not edited: `data/stages/_registry.json`, stage cards (including SkillSpector and Bumblebee), `pipelines/catalog/dashboard.latest.md`, `scripts/catalog_dashboard.py`, `scripts/catalog_eval_queue.py`, `docs/eval/TOOLSET-RANKING.md`, `AGENTS.md`, `Makefile`, `.github/`.
