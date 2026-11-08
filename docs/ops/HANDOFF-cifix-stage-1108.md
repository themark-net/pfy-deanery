# Handoff: stage assembly matches the cards (2026-11-08)

Lane `bot/cifix-stage-1108`. Not pushed. No pull request. No stage card edit. No ceiling edit. No secret, trading, deploy, or release change.

## Symptom

On a full-history tree, `tests.test_stage_registry` failed `test_assembled_document_matches_legacy_monolith`. The same test passed on a depth-1 clone. `make eval-structural` on the last main commits stayed green.

## Root cause

The assembler is not drifting. `load_stages` copies each `data/stages/<slug>.json` body (the `name` becomes the key). At HEAD that is 129 tools, field for field, including `integration_stage` and `tier_ceiling`. `_registry.json` already says `129 tools registered`. Nothing derived needed a rewrite.

The test oracle was the retired monolith. `git log -1 -- data/tool_integration_stages.json` is `953a7018` (the delete). The blob it loaded was `953a7018^` (`b239a588`), 85 tools. After that split the cards moved: 44 tools exist only on the cards, 56 shared cards differ, 13 `integration_stage` values moved, and neatroots `tier_ceiling` went from I1 to I2. The comparison allowed a stripped `self_pipeline` and an evidence prefix. It did not allow those card edits. Cards stay the source of truth. Stages and ceilings were not rewound.

When `git log` cannot see that blob, the old test returned after three sample stages (`Kolibri-1` I0, ATG I2, Pipecat I0) and a count of at least 85. That is a pass. A depth-1 clone of this tree printed no revision and the old test was OK in 0.006s.

## CI discrepancy

Two gaps, both checked on this tree.

1. Shallow checkout. `.github/workflows/eval-structural.yml` uses `actions/checkout` with the default depth of 1. The unittest step runs before the later unshallow, and that unshallow only covers the dogfood2 and patch-id audits. On a depth-1 clone the strict compare did not run. The same two new tests passed there in 0.054s and compared every card.

2. Selection. `ccedca59` and `719999a1` are docs only, so `test_select` is mode `structural` with 0 modules. `1794a8ce` and `aa84daad` are mode `full` (259 modules, the stage test included). A full run still passed on CI because of the shallow skip above. Card edits missed the test for a second reason: 119 of 130 `data/stages/*.json` files were mode `structural`. A basename hit selected some other module and still omitted `tests.test_stage_registry` (9 files). `data/stages/agenc.json` is now mode `affected` with only `tests.test_stage_registry`. `data/stages/bumblebee.json` keeps `tests.test_catalog_verdict_mismatch` and adds the assembly test. `pfylib/stage_registry.py` stays mode `affected` for the three modules that import it. Stage cards are not a `core_globs` entry.

## What changed

- The assembly check reads the card JSON itself and compares every field to `load_stages`. It does not call git. A copy with no `.git` still has to match. Flipping `integration_stage` and `tier_ceiling` on that copy shows up on that tool only. The repo cards are unchanged.
- `scripts/test_select.py` adds `tests/test_stage_registry.py` when a `data/stages/*.json` path changes and that file is in the tree. Other data files stay structural when nothing names them.
- `config/test_select.json` comment and `docs/ops/MODULAR-CI.md` say so.

## Catalog-first

`docs/eval/TOOLSET-RANKING.md` still lists codebase-memory-mcp as the code graph and Chiasmus as an overlap that is not the selector. This lane did not wire either one. The gate stays `scripts/test_select.py`. No stage card was edited. No new catalog tool.

## Five questions

1. What triggers it? A push, pull request, schedule, or `workflow_dispatch` of eval-structural runs `scripts/ci_selected_tests.sh`, which calls `scripts/test_select.py`. A change under `data/stages/` now adds the assembly test to that selection.
2. What does it do, and which services does it read and write? The selector reads the diff, `config/test_select.json`, and the Python sources. It writes a selection JSON on the runner. The assembly test reads `data/stages`. It does not write the repo cards. No hosted service, no account, no model.
3. What does it trigger next? Mode `affected` runs the selected modules, then the cache record on nimo when the tree is clean. Mode `structural` still runs the structural checks and no unittest modules.
4. Where does a human re-enter? A real assertion failure exits 1 from `scripts/run_tests.py`. Card stages and ceilings are still edited by hand. No new prompt.
5. What stops two runs doing the same work? The existing cache key (tree SHA, selector config hash, Python, host class) is unchanged. A shard does not record. Ubuntu does not read the cache.

## Evidence

Red, before the selector change: `test_stage_card_selects_the_assembly_test_only` failed with mode `structural` against `affected`.

Red, before the oracle change, full history: `test_assembled_document_matches_legacy_monolith` failed. The diff was 302296 characters, assembled 129 tools versus monolith 85.

Green, after the fix:

- `python3 -m py_compile` on `scripts/test_select.py`, `tests/test_stage_registry.py`, and `tests/test_test_select.py`.
- `json` load of `config/test_select.json`.
- `python3 -m unittest tests.test_stage_registry tests.test_test_select`: 16 tests, OK.
- Depth-1 clone, same two assembly tests, OK. `git rev-parse --is-shallow-repository` was `true`.
- `data/stages` has no diff.

`python3 scripts/grill_ticket.py tmp/TICKET.md --paths scripts/test_select.py config/test_select.json docs/ops/MODULAR-CI.md tests/test_stage_registry.py tests/test_test_select.py` exited 0. 5 questions, 1 exit test, turns 2. The generated test walks `config/test_select.json` for the substrings `test_stage_registry.py` and `stage_registry`. That stays green if the selector stops adding the module and the comment is left behind, so it was not installed. The same assertion is `tests.test_test_select.TestSelectTests.test_stage_card_selects_the_assembly_test_only`, which runs `scripts/test_select.py` and expects that one module. `docs/ops/MODULAR-CI.md` already says light jobs take no global lock. The receipt is ignored `tmp/TICKET.md.grill.json`.

`python3 scripts/test_select.py --paths` on the files in this commit: mode `full`, reason the core globs `config/test_select.json` and `scripts/test_select.py`, 259 modules, the same set as `scripts/run_tests.py --list`, including `tests.test_stage_registry`. One run: `TMPDIR=$PWD/tmp/stage-repro python3 scripts/run_tests.py --receipt tmp/stage-repro/receipt.json` with that list. `modules=259 failed=0 skips=19 seconds=503.00 jobs=16`, exit 0. `tests.test_stage_registry` passed in that run (0.19s). HEAD was still `origin/main`, so `--base origin/main --head HEAD` would have been mode `none` until this commit. The path list is the commit. No workflow YAML changed. `config/test_select.json` parsed. The three Python files compiled.

## Limitations

- A docs-only commit is still mode `structural` and does not run this test. The next card edit or assembler edit does.
- `last_updated` is still computed from `git log` when no card has a date field. The equality check does not use it. On a copy with no git history the field can be absent. Tool fields still have to match.
- No push. The coordinator lands after its own check.
