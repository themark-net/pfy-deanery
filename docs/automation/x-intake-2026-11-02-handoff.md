# X intake 2026-11-02: handoff (Entries 154-159)

On 2026-11-04 these entries moved from 153-158 to 154-159 because origin/main took 153 for DeepSeek-V4.1-Flash (`sources/entries/153-deepseek-v4.1-flash-1017-gguf.md`). The filenames and table rows below are the numbers after that move. See [x-intake-2026-11-04-handoff.md](x-intake-2026-11-04-handoff.md).

Numbers 150-152 on this branch moved to 153-155 on 2026-11-02, then to 154-156 on 2026-11-04. `origin/main` had taken 150, 151, and 152 for Pipecat, LiveKit, and freeapp (Stage-0 FAIL / I0 receipts). The merge of `origin/main` (`2a74482`) into `catalog/x-intake-153-158` was clean and is `2b9e7f2`. Filenames did not collide, so there was nothing to append. Main's 150-152 files stay as the merge wrote them.

This branch's three files are now `sources/entries/154-dsh-superagent.md`, `sources/entries/155-robrain.md`, and `sources/entries/156-kanzo.md`, with matching `smoke_154.py`, `smoke_155.py`, `smoke_156.py` and tests. The 2026-10-31 writeup is [x-intake-2026-10-31-handoff.md](x-intake-2026-10-31-handoff.md).

Three new I0 entries, 157-159, are below. No TOOLS.md rows, no `data/tools.json` rows, no stage cards, no Feature GO. Catalog HOLD 70-75 untouched. Not merged to main. `catalog/x-intake-150-152` was not updated.

## Entries that moved

| Entry | Tool | What changed |
|------|------|----------------|
| 154 | [dsh-superagent](https://github.com/deepseek-ai/dsh-superagent-prototype) | Same I0 design-reference note. Smoke and tests renamed. |
| 155 | [RoBrain](https://github.com/adelinamart/robrain) | Same I0 eval-auto candidate note. Smoke and tests renamed. |
| 156 | [Kanzo](https://github.com/emanuele-em/kanzo) | Same I0 local kanban note. Smoke and tests renamed. |

Unit tests for those three: `python3 -m unittest tests.test_x_intake_smoke_154 tests.test_x_intake_smoke_155 tests.test_x_intake_smoke_156` — 41 tests, OK. Live smokes were not re-staged. With nothing under `tmp/`, they still exit 2.

## New entries

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 157 | [SysKnife](https://github.com/lacs-project/sysknife) (MIT, Rust, CLI 0.30.0) | Typed, approval-gated, Ed25519-audited Linux actions. The model picks an action; the daemon builds the command. Compare with Entry 041 `destructive_command_guard`. Not a replacement. | The CLI needs no GPU. This machine has no cargo, so the smoke exits 2. |
| 158 | [Emdash](https://github.com/generalaction/emdash) (Apache-2.0, Electron, tag v1.2.10) | Several coding agents at once, one worktree per task, any provider. Compare with this repo's worktree harness. | Metadata check only. The GUI was not launched. |
| 159 | [Skills Manager](https://github.com/shenysun/skills-manager) (MIT, TypeScript, `skills-manager-cli@2026.10.27-1`) | One CLI installs skills and can distribute them to many agents. Compare with `bootstrap/grok-cli/skills/`. | Node 22 is here. Help and `list` ran in a scratch dir under `tmp/`. |

Source posts: [SysKnife](https://x.com/DanKornas/status/2117178905559715995), [Emdash](https://x.com/DanKornas/status/2117382748692197498), [Skills Manager](https://x.com/DanKornas/status/2117314826049306660).

Files: `sources/entries/157-sysknife.md`, `158-emdash.md`, `159-skills-manager.md`, `examples/x-intake-local/smoke_157.py`, `smoke_158.py`, `smoke_159.py` (they call `run_isolated` / `find_bin` / `pinned` / `timeout_reason` and pass `kill_on_exit=True`), `tests/test_x_intake_smoke_157.py` (8), `tests/test_x_intake_smoke_158.py` (7), `tests/test_x_intake_smoke_159.py` (8), `.gitignore` lines for `pipelines/smoke/{sysknife,emdash,skills-manager}/`, a short section in `examples/x-intake-local/README.md`, and `kill_on_exit` on `run_isolated` in `examples/x-intake-local/smoke.py` (default remains off, so older smokes that leave a child alive are unchanged).

## Smoke results on nimo (2026-11-02)

Host: AMD Strix Halo, Radeon 8060S, no NVIDIA. No sudo, no install outside `~/DEVELOP`, no new account, no paid key. Node v22.23.0 at `/usr/bin/node`. npm at `~/.npm-global/bin/npm` (already installed). `bwrap` at `/usr/bin/bwrap`. `cargo` and `rustc` are not on PATH.

| Entry | Exit | Verdict | Reason |
|------|------|---------|--------|
| 157 | 2 | FAIL_CANNOT_RUN_HERE | sysknife is not staged and cargo is not available; not downloading a release binary and not building |
| 158 | 2 | FAIL_CANNOT_RUN_HERE | Linux release asset `emdash-x86_64.AppImage` matches pin v1.2.10 (sha256 `274586c70ba70466667fa811c5ead49610493859bed8c51e4f9abc0850c26d7d`, 233276140 bytes) at commit `ab766e8fbb436584dcf0f299740e79d559b8ed31`; Emdash is an Electron GUI desktop app and was not launched |
| 159 | 0 | PASS | Reason field is empty on the pass path. `--version` matched `2026.10.27-1`, `--help` succeeded, `list --home` on a scratch hub exited 0 (`checks.list` = `listed`). npm cache and HOME were under this worktree's `tmp/xintake-159/`. Scratch removed after the run. Bootstrap was not run. |

The Emdash AppImage was not downloaded. SysKnife's planner dry-run was not started. Skills Manager did not write the watched real-HOME paths.

## Tests and gates

- 154-156 unit tests: 41 OK.
- 157-159 unit tests: 23 OK (missing binary or node exits 2, a hang is killed, a forked grandchild does not survive, a real-HOME write fails the run, receipts are gitignored).
- Full unittest on this worktree: `python3 -m unittest discover -s tests -t .` ran 1050 tests in 643.583s, OK (skipped=16).
- `python3 scripts/catalog_check.py`: PASS (`catalog-check slim-subset ok`, 52 TOOLS.md rows, 52 stage cards, no duplicate entry numbers).
- `scripts/pregate.sh` runs on the commit that contains this file. The default run skips the suite check because the suite above already ran.

## Left open

- SysKnife still needs a pinned clone (under `~/DEVELOP/pfy-mentat/tmp/sysknife` or `$SYSKNIFE_DIR`) and cargo before the dry-run can run. This slice did not install Rust and did not download a release binary.
- Emdash stays a metadata receipt. Do not fetch the 233 MB AppImage for a catalog smoke.
- Skills Manager was not bootstrapped and was not asked to distribute into real agent homes. The portable skills tree is unchanged.
- Entries 154-156 are still unstaged on nimo.
- No merge to main. `catalog/x-intake-150-152` stays where it was.
