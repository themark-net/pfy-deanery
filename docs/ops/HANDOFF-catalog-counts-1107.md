# Handoff: catalog counts (2026-11-07)

Branch: `bot/catfix-counts-1107`. Base: `95857d32` (`origin/main` when this lane started). Not pushed.

## What landed

One script, `scripts/catalog_counts.py`, reads `data/stages/*.json` and ignores `_registry.json` when counting tools. Stage cards are the source of truth. It writes:

1. the `coverage` field only in `data/stages/_registry.json`
2. `pipelines/catalog/dashboard.latest.md`
3. `pipelines/catalog/counts.latest.json`

`scripts/catalog_dashboard.py` is a shim over that script. It does not read `data/tools.json`. `pfylib/stage_registry.py` was not changed. `load_stages` still returns the assembled document (`coverage` `129 tools registered`, `version` `1.3`, 129 tools).

On this tree the generator set coverage to `129 tools registered` (130 JSON files in `data/stages`, minus the registry). Stage counts: I0 47, I1 60, I2 16, I3 6. I2+ is 22. The progress file also has `per_intent` (31 intents), `missing_fields` (uses 2, features 5, potential 2, non_goals 2, next_gate 2, evidence 3, tier_ceiling 5), and `cards_sha256`.

## Catalog-first

Searched `docs/eval/TOOLSET-RANKING.md` and `uses` / `features` / `tags` on `data/stages/*.json` before writing code.

No cataloged tool generates these counts. TOOLSET-RANKING ranks what to integrate next. It has no count, dashboard, or progress generator.

Card hits that look similar and do not do this job:

- Squadra mentions "dashboard or selftest" as its own product surface.
- OpenClaude-Portable mentions a "localhost dashboard token".
- Rulora's next gate mentions a no-progress probe exit.

In-tree pieces, and what this lane did with them:

- `scripts/catalog_dashboard.py` (GAP-04) wrote the dashboard from `data/tools.json`. It is now a shim. There is not a second counter.
- `scripts/catalog_stage_eval.py` prints stage, ceiling, potential, and evidence. It does not write counts. Left alone.
- `scripts/catalog_check.py` checks registry consistency. Left alone. It passed after the coverage update (`stage_cards=55`, `stage_only=74`, 129 cards in all).
- `pfylib/stage_registry.py` (`load_stages`, `write_registry`, `write_tool`). Not modified. The counts script writes the registry path from `--registry` so a fixture does not have to use the repo layout. `load_stages` stays backward compatible.
- `tmp/catalog-audit/catalog_progress.py` (outside this repo, not edited) already computed card count, per-stage, per-intent, missing fields, I2+, and the coverage string from cards, plus git history. This lane copies the card-count family only. It does not copy the history, verdict, or queue parts.

## Five questions

1. What triggers it? A nightly systemd user timer on nimo at 04:17 America/Los_Angeles (`OnCalendar=*-*-* 04:17:00`), plus a manual `python3 scripts/catalog_counts.py`. `python3 scripts/catalog_dashboard.py` is the same run.
2. What does it do, and which services does it read and write? It reads `data/stages/*.json`. It writes the registry `coverage` field, `pipelines/catalog/dashboard.latest.md`, and `pipelines/catalog/counts.latest.json`. No hosted service, no account, no model.
3. What does it trigger next? Nothing. The unit is `Type=oneshot`. Humans or later docs read the generated files.
4. Where does a human re-enter? A timer failure (`journalctl --user -u catalog-counts.service`), a malformed card (non-zero exit, that card path on stderr, previous coverage, dashboard, and progress bytes left in place), or counts that disagree with `ls data/stages/*.json` after subtracting `_registry.json`.
5. What stops two runs doing the same work? The script is deterministic: same cards produce the same bytes. It stores a sha256 of the card filenames and raw bytes as `cards_sha256`. When that hash matches and the three output files already equal the rendered bytes, the run exits 0 and does not rewrite them. Writes that do happen use a temp file plus rename. No flock. `Type=oneshot` so systemd does not overlap two starts of this unit. This lane owns those output paths.

To force a rewrite after a hand edit, delete `pipelines/catalog/counts.latest.json` or change a card.

## Regenerate

From the repo root:

```bash
python3 scripts/catalog_counts.py
```

Fixture flags: `--cards`, `--registry`, `--dashboard`, `--progress`.

## Timer install (no sudo)

Done on nimo as the current user. Commands:

```bash
mkdir -p ~/.config/systemd/user
cp ops/systemd/catalog-counts.service ~/.config/systemd/user/
cp ops/systemd/catalog-counts.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now catalog-counts.timer
```

Result: `catalog-counts.timer` is enabled and active (waiting). Next trigger: Sun 2026-11-08 04:17:00 PST. `enable --now` armed the timer. It did not start the oneshot. `Nice=10`. The unit does not start a bot or a model.

`WorkingDirectory` and `ExecStart` use `%h/DEVELOP/pfy-mentat`. This lane did not write that checkout. `scripts/catalog_counts.py` was absent there at install time. The 04:17 run writes nothing and exits non-zero until that checkout contains the script. After the file is there, a run updates only the three generated outputs, and it is a no-op when the cards match the stored hash.

## Files

- `scripts/catalog_counts.py`
- `scripts/catalog_dashboard.py`
- `data/stages/_registry.json` (`coverage` only, `85 tools registered` to `129 tools registered`)
- `pipelines/catalog/dashboard.latest.md`
- `pipelines/catalog/counts.latest.json`
- `ops/systemd/catalog-counts.service`
- `ops/systemd/catalog-counts.timer`
- `tests/test_catalog_counts_idempotent.py`
- `tests/test_catalog_counts_fail_recover.py`
- `tests/test_catalog_counts_from_cards.py`
- `tests/test_catalog_dashboard_uses_cards.py`
- `docs/ops/HANDOFF-catalog-counts-1107.md`

## Tests

- `python3 -m unittest` on the four tests above: OK
- `python3 -m py_compile scripts/catalog_counts.py scripts/catalog_dashboard.py`: OK
- `python3 scripts/catalog_check.py`: PASS
- `python3 scripts/check_no_encoded_payloads.py`: PASS
- A second `python3 scripts/catalog_counts.py` on this worktree left registry, dashboard, and progress mtimes and bytes unchanged.

No full suite. No model lane. Not pushed.
