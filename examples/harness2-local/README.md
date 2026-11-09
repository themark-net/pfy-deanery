# harness2-local

Pinned local Harness² stage and the one-port sandbox around every OpenCode process. Setup is `stage.sh` only. It does not call `harness2-setup`, `harness2-check`, `harness2`, or `harness2-judge`. `env.sh` points caches, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` at `$W/tmp/state`. It also exports `OPENCODE_DISABLE_MODELS_FETCH` and the other five `OPENCODE_DISABLE_*` flags. OpenCode's startup fetch of `models.dev` has no route inside the sandbox, and that failure exits 0 with no POST. It sets `XDG_DATA_HOME` and `XDG_STATE_HOME` only when they are unset.

OpenCode at pin `23fb5e0516c99ac04a1aa46c193efda2e1b9bb24` reads its managed config directory from `/etc/opencode` on Linux (`packages/opencode/src/config/managed.ts:30`). `managedConfigDir()` at line 35 of that file uses `OPENCODE_TEST_MANAGED_CONFIG_DIR` when it is set. `packages/opencode/src/config/config.ts:619-623` merges `opencode.json` and `opencode.jsonc` from that directory when the directory exists. The sandbox always drops `OPENCODE_TEST_MANAGED_CONFIG_DIR`.

Upstream Proposer and the executor launcher set `XDG_DATA_HOME` and `XDG_STATE_HOME` to the call workspace (`cwd/.ocdata`, `cwd/.ocstate`). Those values win, because `$W/tmp/state` is read-only inside the sandbox. `sbun` reads `HARNESS2_RELAY_PORT` (the same variable `write_opencode_config` uses) and passes it as `--expose` and `--allow`. If the port is missing or not an integer from 1 to 65535, `sbun` exits 2 with `BLOCKED: relay port unknown` and does not start a call. The generated model options are temperature 0, seed 230, and `chat_template_kwargs.enable_thinking` false, so qwen3.6 returns `content` instead of spending the completion on `reasoning_content`. `drive.py` treats `GET /v1/models` as up when the body contains the OpenCode model name or the 64-character `HARNESS2_GGUF_SHA` (llama-server lists the blob digest). A trailing `/v1` on the endpoint is stripped once. The relay keeps a silent request open for 600 s. The watchdog waits 10 s between probes after a miss as well as after a success, and kills the call on 2 misses in a row. A checkout whose realpath is under `/tmp` or `/run` is refused before any mount (`BLOCKED: checkout under /tmp` or `/run`).

## Proposal branch

`propose.py` takes the mapped diff and the item 6 receipt. It scans the diff for token shapes, and for any value of a `PAID_KEYS` name in the environment that is at least 8 characters. A hit exits 2 and prints only the first 4 characters plus `***`.

A label leak in an added line exits 0. The receipt is `negative_finding: label-leak` with diff line numbers, and no branch is created. Bare label words do not block. They are listed under `Leak warnings:` in the commit body. The line `case 3 - A` does block. That is the accepted false positive.

The gate requires `install_mode` `workspace_config`, two base held-out runs and one final run of 16 cases, `temperature: 0` and `seed: 230` on every `POST` in `relay_log`, and a gain of at least 2 correct cases over the better base. When the two base runs differ by 2 or more, the gain must be larger than that gap. Wrong-but-confident must not rise. `parse_ok` must not drop.

A pass clones `main` from `--remote` into `--work-dir`, commits the diff with the before/after counts, and pushes `bot/h2-proposal-<YYYYMMDD>-<shortsha>`. An existing name gets a `-2` suffix, then `-3`. `main`, `master`, `stage`, `dev`, and `build/*` exit 2. The script does not merge and does not force-push.

```bash
python3 examples/harness2-local/propose.py \
  --receipt "$W/tmp/host-only/proposal-receipt.json" \
  --diff "$W/tmp/host-only/proposal.diff" \
  --remote <remote-with-main> \
  --work-dir "$W/tmp/proposal-work"
```

The tests use a bare repo under the worktree `tmp/propose-tests`.

`sbun` execs `sandbox.py` on the normal path, so a proposer SIGKILL of that pid also takes the relay (PDEATHSIG) and bwrap (`--die-with-parent`). The trace path (`HARNESS2_BUN_TRACE`) still waits, because it has to write an end line after the call.

## Live result (2026-10-20)

Held-out a1 and a2 were both 15/16, wrong-but-confident 1, parse_ok 1.0. The chain adopted an empty `LongTermMEMORY.md` at train-1 and did not change the tree again. Step c was 15/16. Gain 0. No proposal branch. Receipt: [pipelines/dogfood/harness2-local/receipt.json](../../pipelines/dogfood/harness2-local/receipt.json). Two calls truncated at `n_tokens` 32767. Context stayed 32768 (D25). Catalog row is I1, tier C, overall 59.

The build spec is a private ops note. The run log is a private ops note.
