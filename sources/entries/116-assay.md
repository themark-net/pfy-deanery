### Entry 116: assay — deterministic, no-LLM QA CLI that opens a web page in Chromium and uses every control

- **URL**: https://github.com/awss1i/assay (MIT, Python, 104 stars at this read; PyPI `assay-ui` 0.3.0)
- **Date**: 2026-10-13 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2110131959187812774
- **Summary / Key Claims** (upstream README, `assay --help`): "An agent-native QA CLI for web pages. Deterministic, no tests to write, no LLM." It opens a local page in Chromium, finds every control, plans checks from them, uses them, and reports what went wrong, grouping repeats ("same finding as C003"). `--json` prints the whole run; `--one-line` gives a summary an agent can quote; `--surface` lists controls without running checks; `--if-page` is for after-edit hooks. A skill covers fifteen harnesses.
- **Why it matters here**: Tester FAILs a pfy-mentat GUI PR that was not actually launched and used. assay is a cheap, repeatable first pass over a built page with no model and no key: it catches buttons that throw, broken requests and console errors before a human-style launch check. It adds to Tester's launch check rather than replacing it.
- **Fit on nimo**: Yes. A venv under `~/DEVELOP/pfy-mentat/tmp/assay/venv` and Chromium under `tmp/assay/ms-playwright` (set `PLAYWRIGHT_BROWSERS_PATH`; about 690 MB with the headless shell and ffmpeg). Don't let it download into `~/.cache` on nimo.
- **Verified on the Grok Bot box** (bubblewrap read-only root, no network, temp HOME and TMPDIR): a working counter page passed 3 of 3 checks (exit 0); a page whose button calls an undefined function failed 2 checks naming "undefinedFn is not defined", the second grouped as the same finding (exit 1). It needs a writable `TMPDIR` (Playwright's mkdtemp fails on a read-only `/tmp`).
- **Finding**: a button that does nothing at all was not flagged: three checks passed with "the visible text is unchanged". The README demo shows a no-change failure on a drag list, so silent no-ops are caught only in some cases. A link to a missing page showed up in `console_errors` but its click check passed. The smoke records `dead_button_flagged` without failing.
- **Extracted Repos / Tools**: https://github.com/awss1i/assay · https://github.com/awss1i/assay/blob/main/docs/harnesses.md
- **TOOLS.md Link**: None yet. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_115_116.py --entry assay`. Uses `$ASSAY_BIN` or `~/DEVELOP/pfy-mentat/tmp/assay/venv/bin/assay`, version pinned 0.3.0, Chromium from `$PLAYWRIGHT_BROWSERS_PATH` or `tmp/assay/ms-playwright` (exit 2 if missing; never downloads). Every subprocess, including `assay --version`, goes through `run_isolated` (clean env, temp HOME). Page runs add bwrap with `--unshare-pid` when that flag works. Receipt: `pipelines/smoke/assay/latest.json`.
- **Non-goals**: No skill or plugin installed, no hook wiring, no Tester change in this slice.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Silent no-op controls pass | Dead buttons look fine | Keep Tester's real launch check; treat assay as a pre-check |
| Chromium download | 690 MB into `~/.cache` | Pin `PLAYWRIGHT_BROWSERS_PATH` under `tmp/`; smoke refuses to download |
| Pages needing a server or login | Local file checks miss app state | Point it at a built static page or a dev server URL in a trial |

- **Status**: STAY I1 after the 2026-11-07 nimo probe (`eval/evq1107/assay/`). Pin PyPI `assay-ui` 0.3.0, wheel sha256 `148b05a0a83426394d239d9595dbbc26b1d50dd4cdee0ac638c73caef49ba63b`, git tag `v0.3.0` commit `29bb1331c9b53bd1cd323eeb9dbc351f04187c1c`. The operator page passed 31/31 in 39.095s while `/launch` returned HTTP 501. Planted defects were caught 1/4. The Tauri binary is absent. Not a gate. No Feature GO.
