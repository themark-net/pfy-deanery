# Module: lane spend (`./pfy lanes spend`)

**Architecture layer:** Product door `./pfy` ([ADR-0012](../adr/0012-simple-harness-agnostic-launch.md)). Read-only report beside the door. It is not the hedge credit ledger and it does not change local inference.
**Code:** `pfylib/lane_spend.py` (dispatch from `scripts/pfy` and `pfylib/cli.py`)
**Related:** [pfy.md](pfy.md). No separate ADR. The dollars-per-point rate is an operator knob, not a stack default.

## Operator

### What it does

Sums Grok Build spend recorded on this machine so a coordinator can stop opening lanes near the weekly cap. Each session lives at `<sessions>/<percent-encoded cwd>/<session id>/`.

A finished session contributes `usage.json` field `session.costUsdTicks` divided by 1e10 (USD). A session that has not written `usage.json` yet is still open. The command reads `updates.jsonl` and keeps the usage object with the highest `costUsdTicks`, otherwise the highest `totalTokens`. Ticks use the same 1e10 conversion. With no ticks, the estimate is `totalTokens / 1e6 * 0.062` USD. If `totalTokens` is absent, input tokens plus output tokens are used. Cached tokens are not added again.

The lane name is the path segment after the last `DEVELOP` in that encoded cwd (the worktree directory). Other cwds use the last path segment.

One point on the weekly Build meter is 4.40 USD unless you pass another rate. Give the percent the Grok UI showed and the time of that reading. Projected percent is that baseline plus dollars at or after the baseline time, divided by the dollars-per-point rate. Sessions earlier than the baseline stay in the totals and stay out of the projection. The time used is `updatedAt` when `usage.json` has one, otherwise the timestamp on the `updates.jsonl` line, otherwise the mtime of the file that supplied the dollars.

At or above the threshold (default 75) the process exits 1 and prints a line that starts with `STOP`.

### How to run

```bash
./pfy lanes spend
./pfy lanes spend --glob '*1115*' --json
./pfy lanes spend --glob '*1115*' \
  --baseline-percent 49 \
  --baseline-time 2026-11-15T08:12:00Z
./pfy lanes spend --sessions /path/to/sessions --since 2026-11-15T00:00:00Z \
  --usd-per-point 4.40 --threshold 75
```

Quote `--glob` so the shell does not expand it. The pattern is matched against the encoded directory name, the decoded cwd, and the lane name.

| Exit | Meaning |
|------|---------|
| 0 | Report finished, and the projection is under the threshold (or no baseline was given, so the threshold is not applied) |
| 1 | Projected percent is at or above the threshold. Do not start another lane. |
| 2 | Arguments are wrong, or `--sessions` does not exist |

`--json` prints one JSON object on stdout. The `STOP` line is on stderr so the JSON stays valid. Without `--json`, the same sentence is the last line of the report.

A missing default sessions directory (no `--sessions`, and `~/.grok/sessions` is absent) is an empty report and exit 0. A missing `--sessions` path is exit 2.

### Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| `problem: malformed usage.json for <id>` | `usage.json` is truncated or not JSON | The rest of the report still runs. If `updates.jsonl` has spend, that spend is used and the problem says so. |
| `live~$` on a lane you thought was finished | The session has not written `usage.json` | Wait until it exits. Ticks already in `updates.jsonl` are used when present. |
| A session is in the total but not in the projection | Its `updatedAt` or file mtime is before the baseline | Expected. Widen nothing unless that spend really is new. |
| `sessions dir not found` | `--sessions` path is wrong | Exit 2. Nothing was summed. |
| `STOP projected ... threshold 75.00%` | The projection is at or above the cap | Do not start another lane. Raise `--threshold` only when you mean to. |
| Dollars look low on an open session | `updates.jsonl` has neither ticks nor tokens | The session is `live-est` at $0 or `missing`. Check the problem lines. |

### Configuration

| Name | Where | Purpose |
|------|-------|---------|
| `--usd-per-point`, `PFY_LANE_USD_PER_POINT` | flag overrides env | USD per weekly-cap point. Default `4.40` in `pfylib/lane_spend.py` |
| `--threshold`, `PFY_LANE_SPEND_THRESHOLD` | flag overrides env | Stop when the projected percent is at or above this. Default `75` |
| `--baseline-percent`, `--baseline-time` | flags, both or neither | UI reading and the ISO time it was taken |
| `--since` | flag | Drop sessions older than this ISO time |
| `--glob` | flag | Limit which worktrees are read |
| `--sessions` | flag | Sessions root. Default is `$GROK_HOME/sessions` when `GROK_HOME` is set, else `~/.grok/sessions` |
| `USD_PER_MILLION_TOKENS` | constant `0.062` in `pfylib/lane_spend.py` | Token blend used only when an in-flight usage object has no `costUsdTicks` |

The command does not read `auth.json`, `config.toml`, or `~/.grok/config.toml`. It does not write under the sessions root. It does not call the network. Hedge credits (`./pfy hedge ledger`) are a different unit and are not consulted.

## Agent

### Entry points

- `./pfy lanes spend` dispatches to `python3 pfylib/cli.py lanes spend`
- `python3 -m pfylib lanes spend`
- `pfylib.lane_spend.scan_sessions`, `build_report`, `cmd_spend`

### Data shapes

- Session directory: `<root>/<percent-encoded absolute cwd>/<session id>/`
- `usage.json`: object with `updatedAt` (ISO, fractional seconds allowed) and `session.costUsdTicks` (int, 1 USD = 1e10 ticks), `session.totalTokens`
- `updates.jsonl`: one JSON object per line. Usage is at `params.update.usage` or top-level `usage`. `timestamp` is unix seconds. The same tick and token fields apply.
- Report JSON: `lanes[]` (`lane`, `cwd`, `done_usd`, `live_usd`, `total_usd`), `sessions[]` (`id`, `status` of `done`, `live`, `live-est`, `malformed`, or `missing`, `usd`, `estimated`, `tokens`, `time`, `in_baseline_delta`), `total_done_usd`, `total_live_usd`, `total_usd`, `since_baseline_usd`, `added_points`, `projected_percent`, `stop`, `threshold`, `problems`, `message`

### Callers / callees

- `scripts/pfy` `lanes)` execs `pfylib/cli.py`
- `pfylib/cli.py` `register` adds the parser and calls `cmd_spend`
- `lane_spend` uses the stdlib only (`json`, `pathlib`, `urllib.parse`, `decimal`). No hedge, no catalog, no HTTP.

### Invariants

- `costUsdTicks / 1e10` is USD, for `usage.json` and for `updates.jsonl`
- Token dollars are used only when that usage object has no ticks
- A point is `usd_per_point` dollars (default 4.40). Projected percent = baseline percent + (USD at or after the baseline) / usd_per_point
- The threshold comparison uses the percent rounded to hundredths, the same numbers the `STOP` line prints. Equal to the threshold stops.
- Exit 1 only for that stop. Exit 2 only for bad arguments or an explicit missing sessions directory
- Only files named `usage.json` or `updates.jsonl` are opened, and only when the resolved path stays inside the sessions root and inside that session directory

### Extension points

- `--usd-per-point` and `--threshold` (and the two env vars) when the weekly meter moves
- `--glob` and `--since` for which sessions enter the report. The projection then keeps the subset at or after the baseline

### Do not

- Do not read `auth.json`, chat transcripts, or `config.toml`
- Do not write, rename, or delete anything under the sessions root
- Do not fold this USD into the hedge credit ledger
- Do not POST the report or shell out to `grok`
- Do not treat a missing `usage.json` as a crash. Open sessions are normal.
