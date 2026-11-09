# CBM shadow report (2026-11-07)

Report-only comparison of `scripts/test_select.py` and codebase-memory-mcp `detect_changes` on the same diff. This is not a gate. The selector source stays `ast`.

## Invocation

Binary: `~/.local/bin/codebase-memory-mcp` 0.9.0. Catalog pin `ee68144af5453addda995a27cce8142999f318fb` in `examples/codebase-memory-mcp/pins.env`. `scripts/tool_cache.sh` looks in `${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin` when that copy is executable. On this host that path is absent, so the shadow uses `~/.local/bin`.

```text
CBM_CACHE_DIR=${PFY_CBM_SHADOW_CACHE:-$HOME/.cache/pfy/cbm-shadow}/db
CBM_MEM_BUDGET_MB=8192
CBM_WORKERS=2
CBM_LOG_LEVEL=error
codebase-memory-mcp cli index_repository \
    --repo-path $HOME/.cache/pfy/cbm-shadow/wt \
    --name pfy-mentat-cbm-shadow --mode fast
codebase-memory-mcp cli detect_changes \
    --project pfy-mentat-cbm-shadow --scope tests \
    --since <base-sha> --depth 2
```

On 0.9.0, `scope` other than `symbols` or `impact` returns changed files and does not walk callers (`handle_detect_changes`). The shadow still passes `--scope tests`. A later binary that returns `tests`, `test_files`, `selected_tests`, or `impacted_symbols` with `is_test` is recorded too. The compared tree is a detached worktree at `~/.cache/pfy/cbm-shadow/wt`. The caller's checkout is not moved.

## Index

One fast index of the cache worktree at `31c373b`: 1.88 s wall, including the detach checkout, status `indexed`, 19238 nodes, 48919 edges. The ten runs below reused that database. `index_s` is 0.0 on every record.

## Hook wall time

Same bash process, 30 calls, a temp repo and a fake binary:

| cleanup tail | 30 calls | each |
|---|---:|---:|
| `true` (before the launch) | 4.44 ms | 0.148 ms |
| `launch_cbm_shadow` with `PFY_CBM_SHADOW=0` | 4.46 ms | 0.149 ms |
| `launch_cbm_shadow` detached | 13.68 ms | 0.456 ms |

The detach adds about 0.3 ms on the pregate process. The shadow's own work runs after the exit. On these ten commits, `test_select` took 0.85 to 0.94 s and `detect_changes` took 0.041 to 0.048 s. A behavior test sleeps 30 s inside the fake `detect_changes`: the passing gate stays exit 0, the failing gate stays exit 1, and the hook returns in under 2 s.

## Real runs

Host nimo, 2026-11-07. Last 10 first-parent commits of `origin/main`, each against its parent. Log: `~/.cache/pfy/cbm-shadow/selections.jsonl`. Every run exited 0. No cbm error and no timeout. Sum of `test_select_s` 8.836 s. Sum of `cbm_s` 0.442 s.

`python3 scripts/cbm_shadow.py --report`:

```text
log: $HOME/.cache/pfy/cbm-shadow/selections.jsonl
invocation: codebase-memory-mcp cli detect_changes --project pfy-mentat-cbm-shadow --scope tests --since <base-sha> --depth 2
records: 10
agreement: 5/10 records (5/10 with a cbm answer)
run_all: 4/10
cbm errors or timeouts: 0/10
top only-in-cbm:
  (none)
top only-in-test_select:
  5 tests/test_catalog_entry_numbers.py
  4 tests/test_adapter_install_symlink.py
  4 tests/test_adapter_symlink_file_ops.py
  4 tests/test_adapter_tree_hash_symlink.py
  4 tests/test_agentdescent_snap.py
  4 tests/test_agentdescent_trial_harness.py
  4 tests/test_atg_compile_bench.py
  4 tests/test_attach.py
  4 tests/test_bare_pfy_no_daemon.py
  4 tests/test_bot_interface.py
cbm-only tests that later failed a full run:
  no data in the log
```

On every commit the cbm set was exactly the changed `tests/test_*.py` files. `only-in-cbm` was empty. Agreement is 5/10:

- Five agreed. Two were docs-only (`structural`, both sets empty). Three selected only the changed test file, and cbm named that same file.
- Four were `run_all` (core globs such as `.github/**`, `scripts/pregate.sh`, `scripts/test_select.py`, `Makefile`, or an unknown path). `test_select` listed the whole suite (171 to 176 modules). cbm listed the changed test files only (1 to 5). Using that cbm set as the suite would have skipped the full run those commits require.
- One `affected` disagreement: `79c083e` (changes include `scripts/catalog_check.py` and two tests). `test_select` also named `tests/test_catalog_entry_numbers.py`, which references `scripts/catalog_check.py`. cbm did not.

No record has `later_failed`. This report cannot name a cbm-only test that later failed a full run.

## Recommendation

Keep shadowing. Do not promote this to a gate, and do not move the codebase-memory-mcp card to I3.

On these ten commits the binary never named a test that `test_select` skipped, so the shadow did not catch a wrong skip. It also must not replace the selector: the four full commits would have dropped the suite the core and risky rules exist to run. The hook is about 0.3 ms on the gate process, failures stay in the log, and `PFY_CBM_SHADOW=0` turns it off. Re-read the log if a newer binary's `--scope tests` starts listing impacted tests. Promote only after that binary shows only-in-cbm tests that the selector skipped and that a full run then failed. Until then the gate stays `test_select`.
