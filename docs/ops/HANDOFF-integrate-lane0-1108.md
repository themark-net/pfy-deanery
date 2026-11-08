# Handoff: I2 to I3 integrate lane (2026-11-08)

Lane `bot/integrate-lane0-1108`. Not pushed. No pull request. No card `integration_stage` changed. No `tier_ceiling` raised. No real integration ran. The three tool lanes that follow this one use [INTEGRATE.md](INTEGRATE.md).

## What landed

- [INTEGRATE.md](INTEGRATE.md): intake, ticket, lane run, landing, receipt, stage apply, human re-entry.
- [integrate/TEMPLATE.md](integrate/TEMPLATE.md): the six ticket questions.
- `scripts/integrate_intake.py`: open I2 cards, table and `--json`. Ceilings are read only.
- `scripts/integrate_lane.sh`: one slug, worktree `bot/integrate-<slug>-<date>`, no pull request. `tmp/integrate/<slug>.dispatched` is created before fetch, worktree, grok, or push. A second start exits 2. Land is `git fetch origin && git merge-base --is-ancestor origin/main <sha> && git push origin <sha>:refs/heads/main`, with rebase and retry when main is not an ancestor. Markers: `LANDED_<slug>`, `<slug>.done`, `<slug>.parked`, `progress.md`. `tmp/STOP` parks.
- `scripts/catalog_apply_verdict.py`: I3 and I4 need a valid main-run receipt. I4 also needs a `submodule:` or `subtree:` item (`missing-embed` otherwise). `make:` and `path:` do not reach I3. Scan flags current I3 cards and does not demote them. `tier_ceiling` and `self_pipeline` caps stay.
- One link line in [integration-stages.md](integration-stages.md).

Receipt path: `eval/integrate/<slug>/receipt.json`. `run_kind` is `pipeline` or `gate`. `main_sha` must be an ancestor of `origin/main`. A branch SHA is `receipt-sha-not-on-main`. Missing git or `origin/main` is `git-unavailable`. Bad JSON or a bad `run_kind` is `receipt-malformed`. No receipt file is `missing-main-receipt`. A ceiling below the target is `tier_ceiling` even when the receipt is valid.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, and the `uses`, `features`, and `tags` on `data/stages/*.json` before writing code.

- TOOLSET-RANKING ranks llama.cpp server mode, atg-framework, and destructive_command_guard as catalog rows. It does not run a tool on main or write `eval/integrate/<slug>/receipt.json`. The 2026-11-07 catch-up section does not name an I2-to-I3 driver.
- `integration-stages.md` defines I3 as onboard. It tells agents not to flip `integration_stage` because the ceiling allows it. It does not check a main-run receipt. This lane adds one link line and leaves the rest of that file alone.
- kanbots (`uses`: fan coding CLIs into git worktrees, tags include `#worktree`) is I1 with `tier_ceiling` I1. The 2026-11-07 probe dispatched 0 CLIs. It does not write a main-run receipt.
- Brigade (`uses`: file ledger with an exclusive claim) is I0 with `tier_ceiling` I1. The probe said not to wire a gate. The dispatched marker is the lock this driver uses.
- SkillSpector and Bumblebee scan skills and configs. Neither enforces `integration_stage`.
- destructive_command_guard, Sandlock, and llama.cpp ngram-mod are the three I2 tools queued behind this process. Each `tier_ceiling` is I1. This lane does not raise those ceilings and does not edit `scripts/integrations/`.
- No card's uses are "take an I2 tool, run it on main, and refuse I3 without a receipt." This lane does not add a stage card.

## Five questions

1. What triggers it? A person runs `scripts/integrate_lane.sh --slug <slug>` for a row from `python3 scripts/integrate_intake.py`. This lane does not start a scheduler.
2. What does it do, and which services does it read and write? It reads the ticket, `data/stages/<slug>.json`, and `origin/main`. It writes `tmp/integrate/` markers and a worktree. On a fast-forward it pushes that SHA to `origin/main`. The child lane writes the wiring and `eval/integrate/<slug>/receipt.json`. Stage apply reads the receipt and may write `integration_stage` only when the ceiling and the receipt allow it. No hosted model in the tests. The driver calls `grok` on PATH when a real lane runs.
3. What does it trigger next? The child lane's real pipeline or gate run on main, then `catalog_apply_verdict.py` once the receipt is on main. `--scan` flags cards that are already I3 or I4 without a receipt. It does not add a CI job.
4. Where does a human re-enter? Mark, when `tier_ceiling` is below I3. Mark, when `--scan` flags an I3 or I4 card. A person, to delete `tmp/integrate/<slug>.dispatched` after reading `<slug>.parked`. `tmp/STOP` parks the driver.
5. What stops two runs doing the same work? `tmp/integrate/<slug>.dispatched`, created with noclobber before fetch, worktree, grok, or push. A second start for that slug exits 2. The land push is a fast-forward. A rejected push rebases and retries up to 3 times, then parks.

## Intake on the current cards

`python3 scripts/integrate_intake.py` (15 open I2 cards). `atomic-task-graph-atg` is I2 and is not in this list: its evidence contains `receipt:pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json`. That string is a probe receipt, not `eval/integrate/<slug>/receipt.json`. This lane does not edit the card.

| slug | tier_ceiling | flag |
| --- | --- | --- |
| bumblebee | I1 | tier_ceiling below I3: needs Mark |
| codebase-memory-mcp | I3 | |
| destructive-command-guard | I1 | tier_ceiling below I3: needs Mark |
| headson | I2 | tier_ceiling below I3: needs Mark |
| hiroute | I1 | tier_ceiling below I3: needs Mark |
| litellm | I3 | |
| llama-cpp-ngram-mod | I1 | tier_ceiling below I3: needs Mark |
| neatroots | I2 | tier_ceiling below I3: needs Mark |
| ollama | I3 | |
| opencode-mem | I1 | tier_ceiling below I3: needs Mark |
| repowise | I1 | tier_ceiling below I3: needs Mark |
| sandlock | I1 | tier_ceiling below I3: needs Mark |
| sponsio | I1 | tier_ceiling below I3: needs Mark |
| strata | I3 | |
| taste-skill | I1 | tier_ceiling below I3: needs Mark |

## tier_ceiling below I3 (needs Mark)

These I2 cards cannot reach I3 until Mark raises the ceiling. A valid receipt would still return `tier_ceiling`.

- bumblebee (I1)
- destructive-command-guard (I1)
- headson (I2)
- hiroute (I1)
- llama-cpp-ngram-mod (I1)
- neatroots (I2)
- opencode-mem (I1)
- repowise (I1)
- sandlock (I1)
- sponsio (I1)
- taste-skill (I1)

destructive-command-guard, sandlock, and llama-cpp-ngram-mod are the three lanes that start after this process. They need Mark before I3.

Open I2 cards whose ceiling is already I3: codebase-memory-mcp, litellm, ollama, strata. This lane did not ticket them and did not run them.

## I3 cards the new rule flags

`--scan` reports 18 mismatches (was 14). The four new rows are I3 cards whose evidence was only `make:` or `path:`. All six current I3 cards are flagged. None were demoted. `git diff --stat data/stages` is empty.

| Tool | Stage | Evidence ceiling | Tier ceiling | Allowed | Code |
| --- | --- | --- | --- | --- | --- |
| Grok CLI bootstrap | I3 | I2 | I3 | I2 | missing-main-receipt |
| SkillSpector | I3 | I1 | I3 | I1 | missing-main-receipt |
| agent-cage (PNNL) | I3 | I2 | I3 | I2 | missing-main-receipt |
| project-process bootstrap | I3 | I2 | I3 | I2 | missing-main-receipt |
| skill-up | I3 | I1 | I3 | I1 | missing-main-receipt |
| write-guard-mcp | I3 | I2 | I3 | I2 | missing-main-receipt |

The other 12 mismatches are the previous ceiling flags (tier cap or notes-only evidence). They are not new receipt codes, because those cards are below I3. repowise stays in that set. Its evidence ceiling is now I2 (`make:` is an operator path), down from I3. `tier_ceiling` I1 still caps it. The card was not edited.

## Run

```bash
python3 scripts/integrate_intake.py
python3 scripts/integrate_intake.py --json
bash -n scripts/integrate_lane.sh
python3 -m unittest tests.test_integrate_intake tests.test_integrate_intake_fail tests.test_integrate_lane_dispatched tests.test_integrate_lane_land tests.test_catalog_apply_verdict_receipt tests.test_catalog_verdict_mismatch tests.test_catalog_verdict_ceiling_refuse tests.test_catalog_verdict_fail_recover tests.test_catalog_verdict_idempotent
python3 scripts/catalog_apply_verdict.py --scan
python3 scripts/catalog_check.py
python3 scripts/check_no_encoded_payloads.py
```

The lane driver was not run against this repo or `origin/main`. Tests use a fake grok and a local bare remote.

## Not done

No stage card edited. No `tier_ceiling` edited. `scripts/integrations/` not edited. No real grok, no push, no pull request.
