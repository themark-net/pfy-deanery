### Entry 133: headson (`hson`) — structure-aware head/tail for JSON, YAML and text within a strict byte budget

- **URL**: https://github.com/kantord/headson (MIT, Rust; 257 stars at this read; release `headson-v0.17.1`, 2026-09-06, tag at `26ccc98d9e90`)
- **Date**: 2026-10-19 (daily X intake, window 2026-10-18T00:36Z to 2026-10-20T00:36Z)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2112011858437685499 (repo link in the reply https://x.com/DanKornas/status/2112012044379812064)
- **Summary / Key Claims** (upstream README at 0.17.1): `head`/`tail` that keep structure. `hson -c <bytes>` previews JSON, YAML, source and text within an output budget, keeping keys and a sample of array items instead of cutting mid-object. `-f json -t strict` emits valid JSON; `--tail` favours the end of arrays; `--grep` keeps matching values in view. Also a Python library.
- **Why it matters here**: our bots and Build sessions keep pasting large JSON (smoke receipts, MCP results, `gh api` output, benchmark logs) into context, and `head -c` breaks the structure. A budgeted, valid-JSON preview is a cheap context saver for skills and for the local models on nimo, which have smaller windows. It is a plain CLI, so any harness can use it.
- **Fit on nimo**: Yes. One static musl binary under `~/DEVELOP/pfy-mentat/tmp/headson/hson` (6.4 MB). No service, no config.
- **Verified on the Grok Bot box** (tarball `hson-x86_64-unknown-linux-musl.tar.gz` sha256 `90f5880efcacd16000e12e6f461e7e486ea56636d2f67243de2a65160006ac58`; binary sha256 `1a5920a7088db2f2eaf3e53c588fb5133b020a4b9aa417631977e16ead136422`; `hson --version` 0.17.1; bubblewrap 0.12.0, no network, temp HOME): smoke PASS. A 315,843-byte JSON fixture (3,000 result rows, one FAIL) became a 600-byte strict-JSON preview with the top-level keys `run`, `results`, `meta` and the first row kept; a rerun was byte-identical; `--tail` kept the last row; `--grep FAIL` kept the FAIL value. Fixture, temp HOME and the watched real-HOME dir (`~/.local/state/headson`) unchanged.
- **Findings**:
  - **`--grep` can go over the budget**: with `-c 600` the grep preview was 658 bytes, since matches are kept even when they don't fit. Callers that need a hard cap should truncate after.
  - The grep match kept the FAIL value but **not its row's `id`** (`{"verdict": "FAIL"}`), so it shows that a failure exists, not which row. Use `jq` to find the row.
  - The head preview samples across the array (ids 0, 149, 150, 449), not the first N rows; fine for shape, wrong for "first ten results".
- **Extracted Repos / Tools**: https://github.com/kantord/headson · https://github.com/kantord/headson/releases/tag/headson-v0.17.1
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_131_133.py --entry headson`. Looks up `$HSON_BIN`, then `tmp/headson/hson`, then PATH; version pinned to 0.17.1 (`$HSON_VERSION`). One temp fixture; never reads a real file. Receipt: `pipelines/smoke/headson/latest.json`.
- **Non-goals**: No skill or hook wired in yet, no Python package install, no system install.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Budget overrun | `--grep` output exceeds `-c` | Truncate after, or skip `--grep` where the cap is hard |
| Lost context | A sampled preview hides the row an agent needs | Use it for shape only; query exact rows with `jq` |
| Upstream churn | Preview format changes between versions | Pin the version; the smoke checks valid JSON and kept keys |

- **Status**: PROMOTE I2 on 2026-11-07 (evq1107). Pinned hson 0.17.1 under ~/.cache/pfy/tools/headson/. Document cap 6/6 at 1024 bytes with every top-level key; head -c parsed 0/6. Stdout is 1025 on 3/6 because of one trailing newline. Not wired into a gate. See ops:eval/evq1107/headson/REPORT.md.
