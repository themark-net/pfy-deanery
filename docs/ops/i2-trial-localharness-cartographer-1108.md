# I2 trial plan: LocalHarness and Cartographer

**Status:** waiting for approval. This lane did not run it. No fetch, no second model, no client install.

Both shallow clones at the card pins are under 50 MB (LocalHarness 20M, Cartographer 28M, git included) and contain no weight files. A later probe can be a throwaway directory. It is not a `tools/_probe` copy until this plan is approved and the numbers below exist.

## Shared rules

1. What triggers it: a person approves this file. Until then nothing launches.
2. What it does: one already-served model, one fixed task, two arms. It reads the endpoint that is already up. It writes a receipt under a throwaway directory. It does not write `~/.local`, `~/.localharness`, or a real agent home.
3. What it triggers next: nothing automatic. A person reads the receipt and decides stay I1 or open a real I2 probe.
4. Where a human re-enters: the approval, and the reading of wall time and tool-call success.
5. What stops two runs: one receipt path per tool, created with noclobber. A second start sees the receipt and exits.

`LIVE_HARD_OFF` stays true. If the tool offers a download, abort and record `fetch-offered`. Do not pass a pull larger than the usual cap.

## LocalHarness

Pin `5af7511ce8f8f799f74de877698e4c4aec0dec45`.

Attach to the OpenAI-compatible server that is already serving the worker model (`LOCAL_CODER_MODEL` when that process is up). Do not run `localharness start` in a mode that searches for a model to fetch. Point `HOME` and `UV_TOOL_DIR` at the throwaway directory. Leave the mobile and dispatch plugins off.

Same task on both arms: a small edit in a throwaway git repo with a known tool sequence (read a file, change one line, stop). Arm A is the current local worker pointed at that same server. Arm B is LocalHarness pointed at that same server.

Record wall time, tool calls that returned a usable result, and tool calls attempted. Also plant one destructive shell command in the task text and record whether the gate denied it while the ordinary edit still landed.

Stop at 20 minutes and record `timeout`. A timeout is a fail for that arm, not a reason to retry on a larger model.

How it fails: the attach path still offers a download, or the gate blocks the ordinary edit. Recovery: kill only the throwaway processes, keep the receipt, leave the card at I1.

## Cartographer

Pin `f96e5d9f7b0ae8506ce5470e35372546a70ea292`.

Do not run `setup`. Do not use the public demo. `HOME` is the throwaway directory. Create an empty local git repo and serve it with `cartographer serve --kb` on stdio, or skip the arm if the binary cannot be built without extra downloads.

Plant one sentence that is not in the pfy-deanery tree. A second process reads it back through the MCP read path. Time that round trip.

Controls, same sentence:

- `rg` on the pfy-deanery tree should miss it.
- opencode-mem is a different store. Do not expect this sentence to appear there unless the trial wrote it there on purpose. If that arm is included, it gets its own planted salt, as in `eval/evq1107/opencode-mem/`.
- codebase-memory-mcp gets a code question (a symbol that exists in this repo). Cartographer should miss that symbol. The code graph should miss the planted wiki sentence.

Record wall time and whether a page with a broken link was refused by the write path. A refusal of a bad page is a pass for the gate. A refusal of the planted good page is a fail.

How it fails: `setup` or `connect` touches a real client config. Recovery: the throwaway `HOME` is the only home on the command line. If a real path changes, stop and restore from the receipt's path list. Leave the card at I1.

## What this plan does not decide

It does not adopt LocalHarness as the operator harness (ADR-0011). It does not add a supersede-watchlist row. It does not raise either card past I1. Promotion still goes through `scripts/catalog_apply_verdict.py` on a later verdict that includes a measured run.
