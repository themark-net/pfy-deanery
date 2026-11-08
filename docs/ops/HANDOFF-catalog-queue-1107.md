# Handoff: catalog eval queue (2026-11-07)

Lane `bot/catfix-queue-1107`. Not pushed. This replaces the hand-built `tmp/evq/queue.tsv` process. That file and `tmp/evq/excluded.tsv` were read as column and exclusion examples. They were not edited.

## What landed

`scripts/catalog_eval_queue.py` reads every tool card under `data/stages/` plus `eval/catalog-queue/exclusions.tsv`, and writes `eval/catalog-queue/queue.tsv`. Same cards and the same exclusions produce the same bytes. When the bytes already match, the run leaves the file in place (temp file, then `os.replace`, skipped when nothing changed).

This generation: 129 tool cards (the registry file is skipped), 11 omitted because an exclusion row names them, 118 queued. Seven exclusion rows have no card, so they omit nothing and stay in the input: `monid`, `bespoke-nimble`, `qwen38-flash-next`, `eight-exits-agent-loop`, `five-repos-list-note`, `ruben-three-claude-skills`, `ai-engineering-toolkit`. Mode counts: trial 80, model 0, ref 38.

Row 4 is `agentgg`. Trial is rank 0, so every trial sorts before model and ref. Inside trial the slug order is Unicode code point order. The first three are `agent-beacon`, `agent-cage-pnnl`, and `agent-substrate`. `agent-substrate` sorts before `agentgg` because `-` is before `g`. `agentgg` is next, so it is row 4. A new card, a mode change, or a new exclusion can move it. The key is what makes it row 4 on these inputs.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md` and the `uses`, `features`, and `tags` on `data/stages/*.json` before writing code.

- `docs/eval/TOOLSET-RANKING.md` does not name a tool that builds this eval queue, a claim ledger, or an eval schedule. The 2026-11-07 and 2026-10-06 sections are priority notes, not a generator.
- `tmp/evq/queue.tsv` is the hand-built list this lane replaces. It is not an input.
- `scripts/pfy_catalog_ask_queue_209.py` and `scripts/pfy_live_org_queue_214.py` queue catalog asks and live GitHub issues. Different job. They were not extended.
- Brigade (`data/stages/brigade.json`) is a file ledger with an exclusive claim. The card records a 2026-11-07 probe (0 duplicate ids) and says not to wire a gate. It is the design reference for "what stops two runs doing the same work": identical bytes and an atomic replace. No Brigade runtime is vendored.
- The inputs are card fields: `integration_stage`, `intent`, `next_gate`, `uses`, `entry`, `tags`, and `catalog_tags`. `tier_ceiling`, `handoff_by`, `potential`, and `features` do not change membership or order.
- `pfylib.stage_registry.load_stages` was not imported. It expects a repo root, `_registry.json`, and a git date, and this lane must not edit that module. The script reads the flat directory the tests pass. Names that start with `_` are skipped.

No new stage card. This script is not a cataloged tool moving to I3. `scripts/catalog_check.py` is unchanged.

## Five questions

1. What triggers it? A person runs `python3 scripts/catalog_eval_queue.py` after a card change or an exclusion change. A later scheduler may read the generated file. This lane does not start one.
2. What does it do, and which services does it read and write? It reads `data/stages/*.json` and `eval/catalog-queue/exclusions.tsv`. It writes only `eval/catalog-queue/queue.tsv`. No hosted service. It does not write coverage, the dashboard, or VERDICT files.
3. What does it trigger next? Nothing. Later schedulers may consume the file. This lane starts no eval.
4. Where does a human re-enter? Add or change an exclusions row (a reason is required), or change the sort and mode rules in the script docstring. Do not hand-edit `queue.tsv`.
5. What stops two runs doing the same work? Sort and filter are pure functions of the cards and the exclusions. The same inputs always produce the same bytes. The publish step writes a temp file in the output directory and replaces the queue with `os.replace`. If the bytes already match, it does not replace the file. Two runs cannot publish two different queues from the same inputs. This lane does not touch outputs owned by the coverage, dashboard, or VERDICT lanes.

## Regenerate

```bash
python3 scripts/catalog_eval_queue.py
```

`--stages`, `--exclusions`, and `--out` override the defaults. The column, mode, and filter rules are in the script docstring and in `eval/catalog-queue/README.md`.

## Files

| path | role |
|------|------|
| `scripts/catalog_eval_queue.py` | builder |
| `eval/catalog-queue/exclusions.tsv` | input, 18 reasons copied from the Nov 7 exclusion list |
| `eval/catalog-queue/queue.tsv` | generated queue, 118 rows |
| `eval/catalog-queue/README.md` | columns, sort, mode, filters |
| `tests/test_catalog_eval_queue_determinism.py` | two runs, same bytes |
| `tests/test_catalog_eval_queue_order.py` | trial, then model, then ref, then slug |
| `tests/test_catalog_eval_queue_fail_recover.py` | missing field and malformed JSON leave the queue unpublished |
| `tests/test_catalog_eval_queue_exclusions.py` | a reason omits the slug; an empty reason does not publish |
| `docs/ops/HANDOFF-catalog-queue-1107.md` | this note |

## Mode on the current cards

The hand list labeled some tools `model` in prose. No current card has a `local-model` tag or a `model-probe` next gate, so the model band is empty and those tools sort as trial. `imcodes` was `ref` on the hand list. Its intent is `awareness` and its next gate does not contain the word reference, so it sorts as trial. Moving a tool into `model` or `ref` means changing the card or the documented rule, then regenerating.

Already-onboarded cards stay in the queue until an exclusion row says otherwise. Examples still queued: `grok-cli-bootstrap`, `project-process-bootstrap`, `write-guard-mcp`, `agent-cage-pnnl`, `skill-up`, `skillspector`. The stage letter is not a filter.

## Verify

Behavior tests: 5 tests, OK. They fail when the script is absent. `python3 scripts/catalog_check.py` exits 0 (55 TOOLS.md cards, 74 stage-only cards). `python3 scripts/check_no_encoded_payloads.py` exits 0. A second builder run printed `unchanged 118 rows, excluded 11`.

## Not in this lane

No push. No edits to `_registry.json`, other stage cards, `docs/eval/TOOLSET-RANKING.md`, `AGENTS.md`, Makefile, `.github/`, pregate, test select, the dashboard, VERDICT apply, or anything under `tmp/evq/`.
