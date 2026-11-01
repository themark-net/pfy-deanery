# X intake 2026-10-31: handoff (Entries 150-152)

Daily X intake routine, window 2026-10-31T00:41Z to 2026-11-01T00:35Z. Sources: Mark's 40 latest bookmarks (1 new, off-core) and 16 watch-list posts (nothing from @tom_doerr in the window), plus repo links from @DanKornas reply threads. Three catalog entries at **I0**, three stdlib smoke scripts with unit-test files, and `.gitignore` lines for their receipts. Catalog-only; not a Feature GO and nothing here competes with the pfy-mentat MVP. Catalog HOLD 70-75 untouched. Branch cut from `main` at `c0d38af` (highest entry 149).

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 150 | [dsh-superagent](https://github.com/deepseek-ai/dsh-superagent-prototype) (MIT, research prototype) | DeepSeek's proactive one-repo agent; its attention-minimizing authorization and work-item model maps onto our bot org and pfy-mentat's autonomy loop. **Design reference only** | Static check yes; running it needs DSH, a model provider, a new GitHub account and `danger-full-access` presets, so no |
| 151 | [RoBrain](https://github.com/adelinamart/robrain) (Apache-2.0, v2.5.0) | Decision memory with structured vetoes and pre-task warnings, a Hermes provider, an offline deterministic bench. **Eval-auto trial candidate** against MemPalace (149) | Offline bench yes; full stack needs Docker Postgres + pgvector and a local OpenAI-compatible endpoint (unverified) |
| 152 | [Kanzo](https://github.com/emanuele-em/kanzo) (AGPL-3.0, v0.2.1) | Local kanban board + MCP server in one binary; a light shared task queue for Mark and agents | Expected yes (static musl binary, SQLite bundled) |

Files: `sources/entries/150-dsh-superagent.md`, `sources/entries/151-robrain.md`, `sources/entries/152-kanzo.md`, `examples/x-intake-local/smoke_150.py`, `smoke_151.py`, `smoke_152.py` (self-contained, stdlib only), `tests/test_x_intake_smoke_150.py` (15 tests), `tests/test_x_intake_smoke_151.py` (14), `tests/test_x_intake_smoke_152.py` (12), `.gitignore` lines for `pipelines/smoke/{dsh-superagent,robrain,kanzo}/`, and this handoff. No TOOLS.md rows, no `data/tools.json` rows. Written on the Grok Bot box and pushed through the GitHub connector. No PR, per Mark's 2026-10-19 rule. Catalog-only, so Tester is skipped per Mark's 2026-10-29 rule: gate is the nimo pregate plus a Reviewer PASS at the pinned head, then fast-forward `main`.

## How to gate

```sh
python3 -m unittest tests.test_x_intake_smoke_150 tests.test_x_intake_smoke_151 tests.test_x_intake_smoke_152   # 41 tests, no tools needed
python3 examples/x-intake-local/smoke_150.py   # exit 2 unless staged
python3 examples/x-intake-local/smoke_151.py   # exit 2 unless staged
python3 examples/x-intake-local/smoke_152.py   # exit 2 unless staged
python3 scripts/catalog_check.py
./scripts/pregate.sh <sha>                     # on nimo, from a scratch clone under ~/DEVELOP/pfy-mentat/tmp
```

Checked on the box: 41 unit tests OK, with bwrap on PATH and with it hidden; 8 of 8 hand mutants (dropping the flaky filter, the source-hash check, the node range, the recall pin, the offline marker, the outside-`--home` check, MCP id matching, the list check) caught. Smokes exit 2 with the default paths (nothing staged); pointed at staged copies in `/tmp` they PASS: 150 with one known-flaky warning (typecheck, 1196/1197 tests, build), 151 (recall 1.00 / 0.70 default, 1.00 / 1.00 lifecycle, 22 node tests), 152 (init, MCP create/list, both exports, nothing outside `--home`).

## Staging on nimo (optional, inside DEVELOP only, not done in this run)

Keep every cache inside DEVELOP: `S=~/DEVELOP/pfy-mentat/tmp` and run pnpm as `env COREPACK_HOME=$S/corepack XDG_DATA_HOME=$S/xdg/data XDG_CACHE_HOME=$S/xdg/cache pnpm ... --store-dir $S/pnpm-store`.

- 150: `git clone https://github.com/deepseek-ai/dsh-superagent-prototype $S/dsh-superagent && git -C $S/dsh-superagent checkout 6337fc823ce20251c8de8085948165c81aaa701e`, then `pnpm install --frozen-lockfile` there (with the env above). No `npm install -g`, no DSH.
- 151: `git clone https://github.com/adelinamart/robrain $S/robrain && git -C $S/robrain checkout ac53011016e5f7dd42bae9c00c1a9b7d207a68b8`, then `pnpm install --frozen-lockfile --filter "@robrain/vetobench..."`, `pnpm --filter @robrain/shared build`, `pnpm --filter @robrain/vetobench build`. No Docker, no `robrain up`.
- 152: download `kanzo-x86_64-unknown-linux-musl.tar.xz` from the v0.2.1 release, check sha256 `4fad8cb2052258ff47dd3c0f23572e22e36482eb11698d75068ef781e2d6884f`, and put the `kanzo` binary at `$S/kanzo/bin/kanzo`. Do not use `kanzo-installer.sh` (it installs outside DEVELOP).

## Triaged and skipped this run

- Clawboo: another multi-agent studio; orchestrators are already cataloged.
- OpenMausBot: open Grok Bot alternative with an agent VM; likely needs hosted keys. LATER.
- PR Cockpit: desktop PR review app, off-core.
- Gofannon: agent demo builder, off-core.
- Helix Foundry: company data graph, off-core.
- MOSS image model: already triaged.
- Off-core posts: the Muse do-not-call bookmark, Nebula promos, emotion-neuron research, an Altman DRAM quote, a Karpathy second-brain thread, a batch-nondeterminism explainer.

## Recommended next step (after the MVP)

RoBrain vs MemPalace through VetoBench's adapter interface: write 10 trap scenarios from pfy-mentat's own rejected approaches, run the offline layer for both, then `--live` with a local model on nimo. dsh-superagent stays a design reference (a short note mapping its authorization doc onto the autonomy loop); Kanzo is a later, optional queue trial.
