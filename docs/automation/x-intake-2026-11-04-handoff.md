# X intake 2026-11-04: handoff (Entries 154-161)

`origin/main` took 153 for DeepSeek-V4.1-Flash (`sources/entries/153-deepseek-v4.1-flash-1017-gguf.md`). This branch's 153-158 used the same numbers with different filenames, so `catalog_check` would reject the tree. They moved up by one, to 154-159. Main's 150-153 files were not edited. The TOOLS.md row "X Entry 153" stays the DeepSeek receipt. Catalog HOLD 70-75 was not touched. No Feature GO.

The merge of `origin/main` (`529be53655383858b81bd778604601b01b358e51`) into this branch was clean and is `0bbfecf`. Git auto-merged `.gitignore` and `examples/x-intake-local/smoke.py`. There were no conflict markers to append.

The earlier move (150-152 to 153-155 on 2026-11-02) is in [x-intake-2026-11-02-handoff.md](x-intake-2026-11-02-handoff.md). The branch name `catalog/x-intake-153-158` in that note is the name of that day's branch.

## Entries that moved

| Was | Now | Tool |
|-----|-----|------|
| 153 | 154 | dsh-superagent |
| 154 | 155 | RoBrain |
| 155 | 156 | Kanzo |
| 156 | 157 | SysKnife |
| 157 | 158 | Emdash |
| 158 | 159 | Skills Manager |

Filenames, smoke scripts, tests, receipt paths, `.gitignore` lines, the ids inside those files, and the rows in the 2026-10-31 and 2026-11-02 handoffs use the new numbers. A search for the old ids (`153-dsh-superagent`, `154-robrain`, `155-kanzo`, `156-sysknife`, `157-emdash`, `158-skills-manager`, `smoke_153.py`, `test_x_intake_smoke_153`) finds nothing.

## New entries

Both are I0. No TOOLS.md row, no `data/tools.json` row, no stage card.

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 160 | [agentplay](https://github.com/Entelligence-AI/agentplay) (Apache-2.0, Python, `agentplay==0.2.6`) | Local no-key replay of a coding-agent session as a map and a timeline. Useful once Build reviews and merges on green. It reads Claude Code, Codex, Cursor, and OpenCode transcripts. It does not read Grok Build sessions under `~/.grok`. | Python 3.14 is here. No GPU. The pin installs into a venv under this worktree's `tmp/`. |
| 161 | [agentgg](https://github.com/agentgg-dev/agentgg) (Apache-2.0, TypeScript, `agentgg@0.1.29`, Node 20+) | Local agentic SAST over a repo or a PR diff, with your own model. A security pass next to the mattpocock `code-review` skill for a risky change. Not a replacement for that review. | Node 22 is here. Ollama was already up. The smoke used the smallest local model and did not pull. |

Source posts: [agentplay](https://x.com/DanKornas/status/2117926316578079141), [agentgg](https://x.com/DanKornas/status/2117835752990036316).

Pins: agentplay tag `v0.2.6` commit `ff5f83e37063a38ec55ab7dd2b0fcdc435f4a72c`. `main` was `b5fcffe889933cbcf28515d2ccc9d3567b22274b` (Goose parser) and is not the pin. The published wheel sha256 is recorded; the smoke checks the version string, not the file hash. agentgg commit `20cca9c1896ef4fee26c93a8730c0f46e4ca44d6` (`Release v0.1.29`). The npm package is about 158 MB.

Files: `sources/entries/160-agentplay.md`, `161-agentgg.md`, `examples/x-intake-local/smoke_160.py`, `smoke_161.py` (they call `run_isolated`, `pinned`, and `timeout_reason`, and pass `kill_on_exit=True`), `tests/test_x_intake_smoke_160.py` (8), `tests/test_x_intake_smoke_161.py` (10), `.gitignore` lines for `pipelines/smoke/{agentplay,agentgg}/`, and a short section in `examples/x-intake-local/README.md`.

## Smoke results on nimo (2026-11-04)

Host: AMD Strix Halo, Radeon 8060S, no NVIDIA. No sudo, no install outside `~/DEVELOP`, no new account, no paid key. Python 3.14.4. Node v22.23.0. npm 11.12.1. Ollama was already answering on `127.0.0.1:11434`. Nothing was listening on `127.0.0.1:8080`.

| Entry | Exit | Verdict | Reason |
|------|------|---------|--------|
| 160 | 0 | PASS | Reason field is empty on the pass path. `--version` contained `0.2.6`, `--help` succeeded, `import` of one synthetic `agentplay/v1` map and `list --json` showed `local:claude-code:pfy-smoke-160`. `view` was not run. `AGENTPLAY_NO_NETWORK=1` and a temp `HOME` were set on every child. The venv was under `tmp/xintake-160/` and was removed. |
| 161 | 0 | PASS | Reason field is empty on the pass path. Wall time about 31 seconds, including the npm install and the scan. `--version` contained `0.1.29`. The scan used `deepseek-coder:latest` (smallest already-installed local model). One remote cloud model was skipped. `checks.scan` is `finished`. No API key, no `--live-validate`, no hosted app. |

An earlier agentgg run the same day exited 1. The synthetic agent file had no `description`, and the loader rejects that. The fixture was corrected and the re-run exited 0. That earlier run installed `agentgg-agents` v0.1.41 (266 agents, about 1.7 MB) into the scratch `HOME`, not the real home. The passing run used a fresh scratch home, so the same install step ran before the scan. The scan report was not kept.

Real-HOME one-level names each smoke watches were unchanged on the passing runs. A change would have forced exit 1.

## Tests and gates

- New smoke tests: `python3 -m unittest tests.test_x_intake_smoke_160 tests.test_x_intake_smoke_161` — 18 tests, OK.
- Full unittest discover inside the dirty-tree pregate (`ubuntu-parity`), before this file existed: 1525 tests in 925.450s, FAILED (failures=1, skipped=107). The only failure was `tests.test_docs_hygiene.DocsHygieneTests.test_docs_relative_links_resolve`, because the 2026-10-31 and 2026-11-02 handoffs already linked this file.
- The same pregate's `eval-structural` discover reported 1525 tests, failures=1, skipped=18. Its summary does not name the test. That discover started before this file existed. After this file existed, `python3 -m unittest tests.test_docs_hygiene` passed (2 tests, OK).
- `python3 scripts/catalog_check.py`: PASS (`catalog-check slim-subset ok`, n_json=8, toolsets=8, linked=2, catalog_tool=null:6, tools_md=53, stage_cards=53, i1_cards_open=0, stage_only=4).
- Dirty-tree `scripts/pregate.sh --in-place --allow-dirty` before the commit: lint PASS, ci-parity PASS, gate-hash FAIL because the renumber and the new tests were not committed yet. That failure is the dirty tree, not a bad gate file. The clean pregate is on the commit that contains this file.

## Left open

- agentplay does not read `~/.grok`. A Build session is not visible to it.
- agentplay's pass is `import` of a synthetic map, not a parse of a real Claude Code, Codex, Cursor, or OpenCode transcript.
- agentgg is not wired into the review gate. The scan was one comment fixture, one turn, with `deepseek-coder:latest`. It was not a scan of this repo.
- The first agentgg scan installs the official agent pack into the scratch home. This slice did not vendor that pack.
- Entries 154-156 stay unstaged on nimo. Their smokes still exit 2 until a clone or binary is placed under `tmp/`.
- SysKnife still has no cargo and no staged binary. Emdash stays a metadata receipt.
