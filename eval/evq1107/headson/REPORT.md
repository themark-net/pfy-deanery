# headson evq1107 (2026-11-07)

Verdict: PROMOTE I2. Pinned `hson` 0.17.1 kept valid JSON and every top-level key on 6/6 documents from this repo inside a 1024-byte document. `head -c 1024` parsed 0/6. A generic `jq` shrink kept the keys on 5/5 JSON files and still left the local-bench receipt at 8626 bytes. The same run shows the limits: 3/6 stdout sizes are 1025 because of one trailing newline, `--grep` can leave the cap, and a planted FAIL row id was kept in 0 preview modes. Gap H1's with/without harness score is unchanged. Nothing was wired into a gate.

## Catalog tools on the same job

The job is a byte-budgeted head/tail for JSON and YAML, so a local model can see the shape of a large document. The lane's MVP gap is H1: harness2 showed no gain, and there is no repeatable with/without score for pfy against plain Build. Context trimming is the part of that gap this tool can touch. The score itself stays with skill-up.

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks skill-up for H1 and does not mention headson. Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` have no byte-budget JSON preview. The probe scanned `uses`, `features`, `tags`, and `catalog_tags` for context, token, preview, trim, budget, yaml, memory, and head. 23 cards matched. None of them is a JSON/YAML byte-cap CLI.

| Tool | Stage | What it already covers | How headson compares |
|------|-------|------------------------|----------------------|
| skill-up | I3 | With/without score. The catch-up trial was 5/5 on both arms (delta 0). | Owns the H1 score. headson does not grade a harness. |
| harness2 | I1 | Local harness edit trial. The ranking records no gain, which is why H1 is open. | Different job. This probe does not re-score it. |
| Charlotte | I0 | Token-bounded browser pages for local models. | Pages from a browser. This probe trims files already on disk. |
| repowise | I2 | Context packing. The card says it overlaps codebase-memory. | A repo packer. It has no per-file byte cap for one JSON document. |
| Ruben Hassid context/token hacks | I0 | Token-saving prompts. The card says it is not a tool we run. | Notes. No binary. |
| TeaQL Agent Kit | I0 | Agent context and verification policy patterns. | Patterns. |
| Harness Score | I0 | Offline grade of harness files. One category in the uses line is context. | A grade. It does not trim a receipt. |
| Kolibri-1 | I0 | Long-context local weights. | A bigger window. |
| Laguna S 2.1 | I1 | Large local coding weights. | A bigger window. |
| Overtime | I0 | Wake layer. The matched word is a daily spend budget. | Different budget. |
| Pi-Harness | I0 | Desktop control plane. The matched word is a policy budget. | Different budget. |
| OpenQodex | I1 | A finding must cite a scanner token. | The word token is a citation check. |
| `head -c` and `jq` 1.8.1 | on this box, no stage card | The paste baseline and a generic first-element shrink. | Measured below. headson wins the hard cap on the bench receipt. jq still finds a row by id. |

The other token hits are memory stores or code memory: Auto-Company, Chroma (or LanceDB), codebase-memory-mcp (I2), Graphify, Grok CLI bootstrap, Hermes Agent (feedback loops), imcodes, LEANN, MemPalace, Memvid, MUE-X, opencode-mem, RoBrain. headson does not store memory and does not replace codebase-memory-mcp.

It beats `head -c` on every document in this probe, and it beats the generic jq shrink on the receipt we would actually paste. It does not beat jq at row lookup, and it does not beat skill-up at the H1 score.

## Pins

Install root: `~/.cache/pfy/tools/headson/`. The child process HOME, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` were directories under that root. No global install. `~/.local/state/headson` on the login home was absent before and after (`real_home_untouched` true). `--explore` was not used.

- Release tag `headson-v0.17.1`. The tag peels to commit `26ccc98d9e90150ff4c2d9a7299f7ad85544cd23`, the short sha in the entry.
- Tarball `hson-x86_64-unknown-linux-musl.tar.gz`, sha256 `90f5880efcacd16000e12e6f461e7e486ea56636d2f67243de2a65160006ac58`. Matches the entry.
- Binary sha256 `1a5920a7088db2f2eaf3e53c588fb5133b020a4b9aa417631977e16ead136422`. Matches the entry. `hson --version` printed `hson 0.17.1`. ELF static-pie, 6380896 bytes.
- Cache tree `du -sb` is 15917642 bytes (about 15.2 MB), under the 50 MB I2 copy limit. The tree holds the tarball, the binary, and the derived receipt under `tmp/`.
- License file at that commit: MIT.
- `jq` on this box: 1.8.1. No extra install.

## Commands

```bash
# tarball from the v0.17.1 release, sha256 checked, unpacked under
# ~/.cache/pfy/tools/headson/src/, copied to bin/hson
python3 eval/evq1107/headson/probe.py
```

The probe builds one receipt in the cache tmp from `data/stages/*.json` (108 cards; `_registry.json` and `headson.json` excluded), 3000 rows, one `verdict` of FAIL at id 2500. Needle collisions in the other rows: 0. It then previews that file and five repo files at `-c 1024 -f json -t strict --no-color`, with `-i json` or `-i yaml`. Modes are default, `--head`, `--tail`, `--grep FAIL`, and `--capped-grep FAIL`, plus `head -c 1024` and, for JSON, a jq shrink that keeps every object key, the first array element, and the first 40 characters of each string. The default `hson` command is run twice. Numbers are `eval/evq1107/headson/results.json`. Wall clock for the scored run: 0.5183 s.

## Numbers

Document cap means: exit 0, JSON parses, every top-level key is present, and the bytes before one trailing newline are <= 1024. Stdout cap counts that newline too.

| Document | Input bytes | Keys kept | hson payload | hson stdout | head parses | jq stdout | jq document cap |
|----------|------------:|----------:|-------------:|------------:|:-----------:|----------:|:---------------:|
| pipelines/dogfood/local-bench/receipt.json | 216155 | 31/31 | 1011 | 1012 | no | 8626 | no |
| eval/ev1107/neatroots/traces/session-local-build-grep.json | 210675 | 6/6 | 1024 | 1025 | no | 367 | yes |
| docs/ops/grill-samples/TICKET-pk2.md.grill.json | 84572 | 11/11 | 1009 | 1010 | no | 1029 | no |
| data/decision-gates/laya-trial.cases.v0.json | 36381 | 9/9 | 1024 | 1025 | no | 698 | yes |
| .github/workflows/eval-structural.yml | 9046 | 4/4 | 1016 | 1017 | no |  |  |
| derived data/stages receipt | 277495 | 3/3 | 1024 | 1025 | no | 216 | yes |

- Document cap: hson 6/6, head 0/6, jq shrink 3/5 JSON files. jq kept every top-level key on all 5 JSON files.
- Stdout cap: hson 3/6. The three misses are stdout 1025 with payload 1024. Each extra byte is the trailing newline.
- Default preview rerun was byte-identical on 6/6. The slowest default pair was the neatroots trace at 0.0607 s for both runs. The bench receipt pair was 0.0253 s.
- Derived default sample ids: 0, 1, 254, 255, 256, 728. Id 2500 was absent.
- `--head` on that receipt: ids 0, 1, 254, 255, 256, 511. Id 0 is kept. It is not the first six rows. Id 2500 was absent.
- `--tail` kept ids 2995 through 2999, including the last id 2999. Id 2500 was absent.
- `--grep FAIL` on the derived receipt: stdout 1064, the FAIL value was kept, id 2500 was absent. Sample ids: 0, 1, 1498, 1499, 1500, 2999.
- `--capped-grep FAIL` on that receipt: payload 1023, document cap passed, id 2500 absent.
- `--grep FAIL` on the neatroots trace: stdout 17130, keys 6/6, the needle was kept. `--capped-grep` on that trace kept 1/6 keys (`children` only) and dropped the needle.

The YAML keys checked were `name`, `on`, `concurrency`, and `jobs` from column-0 lines. hson kept all four.

## Gates

Value gate for I3 needs 3 of 4. This probe has 4. I3 is still the wrong stage for this lane: there is no skill, no make smoke pointed at this pin, and no application to our own pipeline. The ticket allows I3 only with a repeatable script plus self_pipeline evidence, and it forbids gate wiring.

1. Gap fill: yes for the paste. No catalog card trims one JSON or YAML file to a byte cap. `head -c` parsed 0/6. The jq shrink left the 216155-byte bench receipt at 8626 bytes, and hson returned it at 1011 bytes with 31/31 keys. The H1 score gap stays open. skill-up already owns that score.
2. Operator leverage: yes for a prompt preview. One static binary, no account, the whole probe in 0.5183 s. A caller can point at the cache pin the same day. The leverage stops at shape. Row id 2500 was in 0 preview modes.
3. Evidence: yes. Offline pin check, this report, `results.json`, and `tests/test_headson_probe.py`.
4. Blast radius: yes. MIT, 6380896-byte static binary, cache tree 15917642 bytes, no model, no daemon, login home untouched.

Modularity, all four, for the cache copy:

1. Local code needed: yes. The newline, the grep overrun, and the sample ids showed up only when the binary ran.
2. Bounded surface: yes. One binary, `hson`.
3. Isolatable: yes. The cache path is not the product runtime.
4. Reversible: yes. Deleting the cache leaves the pin, the entry, and this report.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Trailing newline | 3/6 previews are 1025 bytes on stdout while the JSON document is 1024 | Strip one trailing newline when the pipe itself must fit. The bytes before that newline are the JSON document the probe parsed |
| `--grep` over the cap | Derived grep was 1064 bytes. The trace grep was 17130 bytes | Skip `--grep` when the cap is hard. `--capped-grep` stayed in budget and dropped the match |
| Lost row | Default, `--head`, `--tail`, `--grep`, and `--capped-grep` all omitted id 2500. `--head` still sampled ids 254, 255, 256, and 511 | Use the preview for shape. Query the row with jq |
| `--capped-grep` drops keys | The trace kept `children` and dropped the other five top-level keys | Use the default preview when every top-level key has to stay |
| Explore sessions | `--explore` writes session state under the home directory | Do not pass it. This run left `~/.local/state/headson` absent |
| Upstream churn | A later release can change the sample or the newline | Stay on 0.17.1 and the binary sha256 above |

## Next gate

Stay I2. A later ticket can add a caller for this cache pin. That caller uses `-c` and `-t strict`, strips one trailing newline when the pipe must fit, and does not pass `--grep` for a hard cap. jq stays the row lookup. H1's with/without score stays on skill-up. No gate wiring from this lane.

## How this tool would run in the pipeline

1. What triggers it? A caller is about to place a JSON or YAML document into a local-model prompt and the file is over the byte budget. No CI job starts it. This lane adds no hook.
2. What does it do, and which services does it read and write? It reads the local file and writes stdout. No network, no account, no model. The binary stays under `~/.cache/pfy/tools/headson/`. `--explore` would write session state. The caller leaves that flag off.
3. What does it trigger next? Nothing. The caller uses the preview. When the row id is missing, a separate jq command reads that row. No downstream job starts.
4. Where does a human re-enter? When the preview has the shape and not the row, or when a grep preview is over the cap. A skill or any gate waits for a later ticket. This lane does not add one.
5. What stops two runs doing the same work? Without `--explore` the CLI is stateless. The same file and the same flags matched byte for byte on 6/6 reruns. There is no shared queue. This measurement itself was one worktree and one branch.
