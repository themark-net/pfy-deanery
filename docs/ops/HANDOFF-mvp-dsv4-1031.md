# Handoff: mvp-dsv4-1031 DeepSeek-V4.1-Flash-1017

Branch `bot/mvp-dsv4-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dsv4-1031`. Base `6664713`. No PR, no merge, no tag.

## Verdict

NO-GO as a local default.

The Unsloth repo exists: `unsloth/DeepSeek-V4.1-Flash-1017-GGUF` (sha `8a6ec9cf118e`). The claim post is https://x.com/0x0SojalSec/status/2116263439681417554. The Unsloth post is https://x.com/UnslothAI/status/2116156587404562491. The "Claude Sonnet 5.5 level" sentence was not measured. The smallest quant, UD-IQ1_S, is 232979608420 bytes. Plus 8 GiB context that is 241569543012 bytes. nimo RAM+VRAM is 132524449792 bytes. Shortfall 109045093220 bytes. Disk would have allowed the download. No file was downloaded. No server was started.

Report: `eval/mvp-1031/dsv4/REPORT.md`. Receipt: `eval/mvp-1031/dsv4/fit-receipt.json`.

## Items done

| Item | Result | SHA |
|------|--------|-----|
| Exit card before model work | `docs/ops/RUN-LOG-mvp-dsv4-1031.md` | filled after commit |
| Find repo and measure host | Found. No quant fits. | filled after commit |
| Catalog I0 row | TOOLS.md, stage card, handoff JSON, entry 153 | filled after commit |
| Report and receipt | fit math, baselines copied, tasks not run | filled after commit |

Skipped on purpose: download, serve, smoke, the six-task `./pfy build --local` pass. Reason: fit gate.

## Comparison (no new task run)

| Arm | Gate | Loop accept | Human accept | Wall |
|-----|------|-------------|--------------|------|
| MVP-3 local | 5/6 | 5/6 | 4/6 | 3859.9 s |
| MVP-2 cloud | 6/6 | 6/6 | 6/6 | 583.6 s |
| This GGUF | not run | not run | not run | 0 s |

## Test evidence

Catalog lint and the two catalog tests named in the run log. No runtime code changed, so no new test module. The receipt's `fits` field is false and the byte fields recompute to the same shortfall.

## How this fails / how we recover

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Download starts anyway | 233 GB fills the 250 GB pool and the box OOMs on a full swap | Do not download. Catalog row is I0 and NO-GO |
| Engram mmap is treated as a fit | Load of the backbone still wants about 122 GiB plus context against about 71 GiB MemAvailable | Keep counting the whole file until a drop-in says otherwise |
| This NO-GO is read as a quality result | A bigger host never gets an MVP-3 pass | Quality is unverified. Re-run one locked pass only after the byte check passes |

## Cross-lane requests

None. This lane edited shared catalog files because the drop-in requires the catalog entry: `TOOLS.md`, `data/tool_integration_stages.json`, `data/catalog_stage_handoff.json`, `sources/entries/153-deepseek-v4.1-flash-1017-gguf.md`. Entry 153 was free at fetch time (150-152 exist on other branches). A parallel lane that also appends those files can conflict on merge.

## Gate

Docs, eval, and catalog only. Pregate plus Reviewer. Pregate was not run: the drop-in says the operator runs it. Runner.Worker was empty at 2026-11-01T00:04:13Z.

## Next step

Leave the local default where MVP-3 left it. Reconsider this GGUF only on a host whose RAM+VRAM exceeds the chosen quant plus 8 GiB, with at least 50 GB free after download, and with room in the 250 GB weight pool. Then one `./pfy build --local` pass on `eval/mvp3/`.

## Loop

Exit: lane empty. The fit gate closed the only item this lane can run. No further MVP row fits these rules.
