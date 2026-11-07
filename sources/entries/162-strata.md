### Entry 162: Strata: local inference engine with OpenAI/Anthropic APIs (Strix Halo listed)

- **URL**: https://github.com/Niko1221/Strata (MIT, C++/desktop). Release tag `v0.2.11`, annotated tag points at commit `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d` (2026-11-05). Linux asset `Strata-0.2.11-linux-x86_64.AppImage`, size `305052152`, digest `sha256:9cac9be7f81ce92ca7fb0b839180bec73d454b8ae4b2bc0a724c0678c2e2119e`. GitHub API description: run powerful AI on your own computer; chat, code, and work with images locally. Upstream README also ships `strata-control` and DeepSeek V4.1 Flash packs, including HIP builds for AMD Radeon.
- **Date**: 2026-11-05 (daily X intake, window 2026-11-05T01:30Z to 2026-11-06T01:37Z)
- **Source / Poster**: watch-list posts by @yume_arasaki, https://x.com/yume_arasaki/status/2118381673230520569 and https://x.com/yume_arasaki/status/2118492058621272367 (engine link in reply https://x.com/yume_arasaki/status/2118382340179464486)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): a free, open-source local inference engine and desktop/Terminal host. No account needed. Serves OpenAI- and Anthropic-compatible APIs on localhost for coding tools. Models include Qwen3.8-Flash-Next and DeepSeek V4.1 Flash packs that spill weights to SSD when they do not fit in RAM. README hardware table lists AMD Ryzen AI Max (Strix Halo) on Windows for DeepSeek packs, plus NVIDIA RTX and Apple Silicon. HIP assets exist for Radeon (for example `strata-dsv41-*-linux-x86_64-hip-rx9070.tar.gz`).
- **Why it matters here**: nimo is AMD Strix Halo with a large RAM and VRAM carve-out and no NVIDIA. Strata is a candidate local host for frontier-class quant packs next to Ollama/llama.cpp, with an API surface coding agents already speak. The 2026-11-07 catch-up was the authorized live trial. It stayed I2. See Status.
- **Fit on nimo**: Static metadata check fits (CPU + network). Running the AppImage or a DeepSeek pack does not fit this smoke: the AppImage is about 305 MB, and DeepSeek packs are hundreds of GB on disk. This smoke does not launch either one and exits 2 after a matching pin. The 2026-11-07 trial later served the gfx1151 HIP engine with Qwen3.6. See Status.
- **Verified on the Grok Bot box** (2026-11-05): smoke not run against live GitHub in this PR authoring pass; stub tests cover the metadata path. On nimo, expect exit 2 with `FAIL_CANNOT_RUN_HERE` when the release JSON matches and the AppImage is not launched.
- **Findings**:
  - Pin is the Linux AppImage only. Control and DSV41 HIP tarballs are recorded as related assets, not as this smoke's pin.
  - Strix Halo is named in upstream docs for DeepSeek; that is their claim, not a measurement on Mark's machine.
  - A matching release is still exit 2. Exit 0 would mean the AppImage ran. It did not.
  - The 2026-11-07 catch-up is separate from this smoke. It installed terminal v0.2.12 under gitignored tmp/, served Qwen3.6 UD-Q4_K_XL on gfx1151, and stayed I2 on decode speed. It did not run the AppImage or DeepSeek. Weights were not committed.
- **Extracted Repos / Tools**: https://github.com/Niko1221/Strata · release `v0.2.11` · related HIP DeepSeek packs under the same release
- **TOOLS.md Link**: None. No TOOLS.md row and no `data/tools.json` row. Stage card `Strata` is I2 after the 2026-11-07 trial. The AppImage smoke is unchanged.
- **Smoke**: `python3 examples/x-intake-local/smoke_162.py`. Uses `run_isolated`, `find_bin`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads the release JSON through `$STRATA_FETCH_BIN` or a stdlib fetch of `https://api.github.com/repos/Niko1221/Strata/releases/tags/<tag>`. Pins `$STRATA_TAG`, `$STRATA_ASSET`, `$STRATA_SHA256`, `$STRATA_SIZE`, and `$STRATA_COMMIT`. Records `$STRATA_BIN` if staged and does not launch it. Does not download the AppImage. Receipt: `pipelines/smoke/strata/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_162` (7 stub tests).
- **Non-goals**: No AppImage download, no GUI launch, no paid key, no TOOLS.md row. The smoke does not download a model pack. The catch-up trial downloaded one GGUF under gitignored tmp/ and did not commit it. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | A later edit turns a metadata match into exit 0 | Keep exit 2 while the reason says the AppImage was not launched |
| Accidental 305 MB+ download | A script fetches the AppImage "to be sure" | The smoke reads the release JSON only |
| Disk blowout on a trial | DeepSeek packs need about 200 to 280 GB free | Do not download DeepSeek on this host. The Qwen3.6 trial used a 22.9 GB file and stayed I2 on decode speed |
| Pin drift | A newer tag replaces `v0.2.11` | The smoke checks this tag's asset digest |

- **Status**: Trial 2026-11-07 stayed I2. Terminal v0.2.12 (control and engine 0.1.58, gfx1151 HIP) served Unsloth Qwen3.6-35B-A3B UD-Q4_K_XL on nimo. Strata refused Ollama's `qwen3.6:35b` GGUF. Median decode was 51.86 tok/s against Ollama's 61.71 tok/s on the same prompts (0.84x, bar 0.90x). Tool calls were valid. `./pfy launch --headless` smoked that server when `LOCAL_OPENAI_BASE_URL` pointed at it. pfy does not start or stop Strata, and there is no `PFY_ENGINE=strata` path. The AppImage pin is still exit 2. Receipt: `eval/catchup-1107/strata/receipt.json`. No Feature GO.
