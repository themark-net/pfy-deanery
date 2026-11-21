### Entry 207: llamafile: single-file local LLM runner built on llama.cpp and Cosmopolitan

- **URL**: https://github.com/mozilla-ai/llamafile (Apache-2.0 per the README, with its llama.cpp and whisper.cpp changes under MIT; GitHub reports NOASSERTION; C++). Checked at commit `334e66444a96d5429fd2d667301bd067029b1eb5` (2026-11-05 UTC; 2026-11-05 PT).
- **Date**: 2026-11-20 (daily X intake; post seen 2026-11-20 PT)
- **Source / Poster**: watch-list post by @alex_verem, https://x.com/alex_verem/status/2123823963428307006
- **Summary / Key Claims** (upstream README; their claims, not verified here): packages a model and its runtime into one executable that runs on several operating systems and CPU types, by combining llama.cpp with Cosmopolitan Libc. Newer releases track recent llama.cpp versions for current model support. The pinned commit adds decision-model support (`/v1/systemone`) in the CLI and chat modes. Latest release 0.10.6 (2026-09-15 UTC).
- **Why it matters here**: Deanery serves local models through Ollama. llamafile is a no-daemon, single-binary alternative for shipping a pinned model plus runtime to a lane or an eval as one artifact, and its decision-model endpoint is worth reading next to the local decision layer. It is a comparison target, not a replacement, until a trial shows a gain.
- **Fit on nimo**: runs as a user binary under `$PFY_TMP` with no install step and no NVIDIA dependency on CPU; the AMD GPU path on the Radeon 8060S is not checked here. No account or key is needed.
- **Verified** (2026-11-20): commit pin matched via `git ls-remote` and the GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 26.7k stars, created 2023-09-10 UTC, last push 2026-11-09 UTC.
  - Executables downloaded from model hubs are code, not data; any trial uses a binary built or fetched at a pinned release and checked by hash.
- **Extracted Repos / Tools**: https://github.com/mozilla-ai/llamafile
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/llamafile.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_207.py`. Commit-metadata only. Pins `$LLAMAFILE_COMMIT`. Fetches via `$LLAMAFILE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/llamafile/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_207` (7 stub tests).
- **Non-goals**: no system install, no replacement of Ollama without an eval-auto result, no unpinned executables, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Untrusted executable | A hub llamafile runs unchecked code | Pinned release only, hash checked, under `$PFY_TMP` |
| GPU path missing | Falls back to CPU and looks slow | Record backend in the trial receipt; compare like for like with Ollama |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: trial one pinned GGUF under `$PFY_TMP` against the same model in Ollama for tokens per second and backend; read the decision-model endpoint against the local decision layer.
