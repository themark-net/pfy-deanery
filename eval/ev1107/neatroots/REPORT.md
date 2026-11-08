# neatroots ev1107

Verdict: PROMOTE I2. `neatroots check` 0.2.9 ran offline on 11 exported runs, with all 13 library rules, and found a real error streak and a real repeated tool call. Nothing was wired into a gate.

## Pins

| Item | Value |
| --- | --- |
| Version | 0.2.9 (`cli.js --version` and `package.json`) |
| Bundle | `neatroots.tar.gz`, 17,215,448 bytes, sha256 `4c6c66ba65646080a0b6726dbbd2e1b9a5502e564beb501eb948a82e7c3de35a` (matches the release `.sha256`) |
| Tag | `v0.2.9`, commit `f82c31cf1d06ec457adf503919df59c2ee1bb964` |
| Node | 24.14.1, linux-x64, sha256 `84d38715d449447117d05c3e71acd78daa49d5b1bfa8aacf610303920c3322be` |
| Install | `~/.cache/pfy/tools/neatroots/` (`app/` bundle, `node/` tarball). `install.sh` was not run. `~/.neatroots` and `~/.local/bin/neatroots` were not created. |
| Isolation | `HOME`, `TMPDIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` under that cache path |

Library rules in force (from `neatroots check --json`): repeated-tool-call, tool-error-streak, llm-call-failed, runaway-loop, token-budget, secret-in-output, unrecovered-tool-failure, secret-in-tool-output, soft-tool-failure, context-growth, tool-cycle, run-failed, empty-final-answer. That is 13.

## Commands

```bash
# unpack only. HOME and TMPDIR stay under the cache path.
NODE=~/.cache/pfy/tools/neatroots/node/bin/node
CLI=~/.cache/pfy/tools/neatroots/app/neatroots/dist/cli.js
python3 scripts/grok_trace_export.py SOURCE -o eval/ev1107/neatroots/traces/NAME.json
HOME=~/.cache/pfy/tools/neatroots/home \
TMPDIR=~/.cache/pfy/tools/neatroots/tmp \
XDG_CONFIG_HOME=~/.cache/pfy/tools/neatroots/xdg/config \
XDG_CACHE_HOME=~/.cache/pfy/tools/neatroots/xdg/cache \
  "$NODE" "$CLI" check eval/ev1107/neatroots/traces/*.json --json
```

`grok --help` lists `--output-format` values `plain`, `json`, `streaming-json`, and `streaming-messages-json`. The JSON envelope used by `scripts/grill_ticket.py` carries `text`, `num_turns`, and `stopReason`. It does not carry tool calls. Tool calls are in the session `chat_history.jsonl`, with outcomes in `events.jsonl`. Those files were copied read-only into this worktree's `tmp/neatroots-src/` (gitignored) and then exported. No new `grok -p` call was made. A new headless call would be a hosted model, which this lane does not use, and the session JSON already has the structure the build logs lack.

Exporter wall time was about 0.04s on a driver log and 0.06s on a session of roughly 170 tool calls. `neatroots check` on all 11 traces exited 1 in 1.864s. Exit 1 means a rule fired. `errors` in the JSON was empty. Stderr was only the Node `NO_COLOR` / `FORCE_COLOR` warning.

## What was exported

The pk1107 `build-*.log` files and the cu1107 driver and pregate logs are the agent's closing prose. A search for `tool_call` in those logs found nothing. The exporter turns that prose into one workflow span. A log that starts with `Error:`, `Couldn't create session`, `[FAIL]`, or `OVERALL=FAIL` is status ERROR. A log that does not is status OK.

No `*.parked` marker exists under `tmp/pk1107` or `tmp/cu1107`. No lane there failed twice. The failure runs in the set are the ones those logs actually record: pk2 attempt 0 (session create failed before any tool call), pregate-pk1-0 (SIGTERM, OVERALL=FAIL), pregate-combo-0 (two checks FAIL), and the cu driver rebase conflict.

| Run | Source | Tool spans | Findings |
| --- | --- | --- | --- |
| build-pk1 | pk1107 narrative | 0 | none |
| build-pk2 | pk1107 narrative | 0 | none |
| build-pk2-attempt0 | failed session create | 0 | run-failed |
| build-pk3 | pk1107 narrative | 0 | none |
| build-pkr | pk1107 narrative | 0 | none |
| pregate-pk1-0 | pregate FAIL | 0 | run-failed |
| pregate-combo-0 | pregate FAIL | 0 | run-failed |
| driver-cu | rebase `error:` | 0 | run-failed |
| cloud-help-streak | session `01a193d0-e596-7c70-9df8-9e3bf7446e0b`, "Fix cloud help and log_path_for_receipt tests" | from chat history | tool-error-streak |
| local-build-grep | session `01a17b0c-fe73-75d2-a81e-6a5d0124f7ec`, local-build drop-in | 213 | repeated-tool-call, soft-tool-failure |
| mvp2-local-build | session `01a18073-ed9b-7a42-bda5-19d637fe6bcc`, MVP2 local-build | 166 | repeated-tool-call, runaway-loop |

Traces and the check JSON are under `eval/ev1107/neatroots/`. Strings that looked like keys were removed before write. A scan of the committed traces found no `sk-` token, `AKIA` id, `ghp_` token, PEM header, or the fixture marker `REDACTME`.

## Real signals

`tool-error-streak` on cloud-help-streak: `read_file` failed three times in a row. The finding count is 3. The recorded error is that `docs/ops/HANDOFF-mvp-intfix-1031.md` does not exist. The stored results start with `Error:` and are 198, 198, and 211 characters, so they are not the omission placeholder.

`repeated-tool-call` on local-build-grep: `grep` three times with the same arguments. The result text is `No matches found` (about 120 characters after the exporter's hash line). The path is `docs/ops/AUTONOMOUS-DECISIONS-2026-10-26.md` in the mvp-local-build worktree. That is the same call and the same result, three times.

## False positives and misses

`repeated-tool-call` on mvp2-local-build is not clean. `read_file` of `tmp/mvp2/tmp/mvp2-runs/logs/all-local.stdout` was stored nine times. Six of those bodies are the 31-character omission placeholder Grok writes when a tool result is too old. The other three bodies are 351, 435, and 487 characters and did not join the finding. The rule matched the placeholder, not six identical file reads. How it fails: old tool results collapse to one string, so same-output becomes true. How we recover: ignore that placeholder before comparing outputs, or keep the hash of the original body. The exporter already hashes what it was given. It cannot recover bytes the session store dropped.

`runaway-loop` on that same run counted 34 nonempty assistant messages. The library bar is 25 LLM calls. A long Build session crosses it without being stuck. Treat 25 as too low for this harness until we set our own YAML.

`soft-tool-failure` fired twice on local-build-grep (count 2). Several successful `read_file` and shell results contain `error:` because they quote a log or a traceback. The rule is doing what it says. For our logs that is mostly noise. A project rule would need to ignore outputs whose status is OK unless the error shape is a JSON error field.

`run-failed` on the four narrative failure logs is the exporter marking the root span ERROR from the log text. It is a real failed run only in the sense the log says so. It is not a tool error streak. The four successful build narratives had no findings, so a finished prose summary does not trip the rule by itself.

`secret-in-output` and `secret-in-tool-output` did not fire. The exporter removes key-shaped strings first, so those rules cannot see a secret we refused to write. That is the contract. A trace that still contains a key would be a bug in the exporter, not a miss in the library.

`unrecovered-tool-failure`, `llm-call-failed`, `token-budget`, `context-growth`, `tool-cycle`, and `empty-final-answer` did not fire. Token rules had nothing to count: the session JSON we read has no per-call token totals, and the exporter does not invent them.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: yes. skill-up grades case outcomes. The Hermes bake-off oracle counts failures by hand. This is the offline loop, repeat, and error-streak pass those do not do.
2. Operator leverage: yes. The check is one command. The glue is `scripts/grok_trace_export.py`.
3. Evidence: yes. This probe.
4. Blast radius: yes. Apache-2.0, 17 MB bundle, no weights, not the product runtime. `neatroots start`, `connect`, `install.sh`, Laya, and hosted models stayed off.

Modularity (all 4, for a local probe):

1. Local code needed: yes. The README does not show that `check` needs a writable `TMPDIR`, that `--checks` eats later file arguments, or that same-output breaks when Grok omits old tool bodies.
2. Bounded surface: yes. `neatroots check <files> --json`.
3. Isolatable: yes. Cache path only.
4. Reversible: yes. Delete the cache directory. The pin and this entry remain.

I3 is not the verdict. The value gate is met on paper, and we still stay at I2. The repeat rule false-positives on omitted tool bodies, soft-tool-failure is noisy on successful reads, and this lane does not wire a gate. An I3 card would also need `self_pipeline` once the uses text is classified as CI or review. It is not classified today (no `ci`, `test`, or `review` word on the card).

`tier_ceiling` is I2. It was I1 before this probe, the cap while no local check existed. The stage and the cap now match. A later catalog apply does not lower an existing ceiling.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Omitted tool body | Identical placeholder text fires repeated-tool-call | Drop that placeholder, or store a hash taken before Grok omits the body |
| Writable TMPDIR | `check` exits 2 with EROFS, same code as a bad file | Set `TMPDIR` to the cache tmp. Read stderr. |
| Secret in a log | A key lands in a committed trace | Exporter redacts before write and refuses to write if a marker remains. The unit test covers `sk-test-REDACTME-0000`. |
| Long outputs look alike | Clipping hides a tail and invents a repeat | The stored output keeps a sha256 of the full redacted text. A test uses two 500-character bodies that differ only at the end. |
| Error streak sticks | A later success is still ERROR | A tool_result with status ok replaces that span. The streak test expects three ERROR spans and a final OK. |
| Bracket log parsed as JSON | A pregate line `[FAIL]` is dropped | If the file is not JSON, it is a plain log. A test covers that. |
| Installer | `install.sh` writes `~/.neatroots` and agent configs | Unpack the bundle under the cache path. Do not run `install.sh`. |

## Next gate

Stay I2. Do not add a Make target, a pregate step, or a TOOLS.md row from this lane. The next proof is a small ignore-list for the omission placeholder, then a separate ticket if Mark wants `neatroots check` on an eval receipt.

## How it would run in the pipeline

1. Trigger: a finished Grok session, after the lane writes its receipt. Not on every keystroke.
2. Work: `grok_trace_export.py` reads that session's `chat_history.jsonl` and `events.jsonl` and writes one trace. `neatroots check` reads the trace and writes a findings JSON beside the receipt. It does not start a server, call a model, or write the repo.
3. Next: nothing automatic. A human reads the findings file.
4. Human re-entry: a repeated-tool-call whose result is the omission placeholder, a soft-tool-failure on a successful read, or any proposal to fail a gate on exit code 1.
5. Two runs: one trace path per session id. The check only reads that file. A second run writes a different findings file. It does not take the model lock.

## Tests

`python3 -m unittest tests.test_grok_trace_export tests.test_grok_trace_export_redact` : 8 tests, OK. They run the script as a subprocess. They do not call neatroots, the network, or a model. `python3 scripts/catalog_check.py` and `python3 scripts/check_no_encoded_payloads.py` were run with the card change.
