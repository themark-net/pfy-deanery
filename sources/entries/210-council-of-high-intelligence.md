### Entry 210: Council of High Intelligence: structured multi-persona deliberation for hard decisions

- **URL**: https://github.com/0xNyk/council-of-high-intelligence (MIT; skill/plugin pack, Markdown plus shell installer). Checked at commit `2a2fd011d6cf89240a3d7ceba35ac559b67caa20` (2026-11-23 UTC; 2026-11-22 PT). About 4.9k stars at this read.
- **Date**: 2026-11-27 (daily X intake; watch post seen 2026-11-27 PT)
- **Source / Poster**: watch-list post by @tom_doerr, https://x.com/tom_doerr/status/2126289693629108281
- **Summary / Key Claims** (upstream README; their claims, not verified here): a `/council` command that gives a hard question to deliberately different analytical personas (18 member contracts under `agents/`), keeps their first positions independent, forces direct disagreement, and returns a verdict that keeps dissent, unresolved questions, kill criteria and the next concrete action. Modes: full council, `--quick` panel, `--duo` dialectic, named triads and profiles. Host mirrors for Claude Code, Codex, Gemini CLI and OpenCode.
- **Why it matters here**: Deanery's decision layer routes and gates choices. This is a ready-made pattern for the rare high-stakes decision (escalate vs decide, irreversible choices): independent first positions, forced dissent, kill criteria in the verdict. Worth reading as a design reference and a possible `--duo` trial on local models, not as a default path for routine decisions.
- **Fit on nimo**: prompt and skill files only, no GPU need of its own. Provider routing detects an `ollama` executable, so seats can run on local models (OpenCode host or Ollama seats); the example seat map names paid hosted models, which we would replace with local ones. No account or key is needed for the Ollama path. Installer writes under `~/.claude`, `~/.codex`, `~/.gemini` or `~/.config/opencode`; any trial must point those `--*-dir` flags under `$PFY_TMP`.
- **Verified** (2026-11-27): commit pin matched via the GitHub commits API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - `install.sh` supports `--dry-run` and per-host target dirs (`--claude-dir`, `--codex-dir`, `--gemini-dir`, `--opencode-dir`).
  - `/council --dry-route` previews seat routing without running a council.
  - Related: marketing-council skill (pfy-deanery `sources/x-posts.md` entry 004) and cedr's multi-vendor review council (entry 168).
- **Extracted Repos / Tools**: https://github.com/0xNyk/council-of-high-intelligence
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/council-of-high-intelligence.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_210.py`. Commit-metadata only. Pins `$COUNCIL_HI_COMMIT`. Fetches via `$COUNCIL_HI_FETCH_BIN` or the stdlib GitHub commits API. Does not clone or install. Receipt: `pipelines/smoke/council-hi/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_210` (7 stub tests).
- **Non-goals**: no install into real agent homes, no paid provider seats, no change to Deanery routing without an eval-auto result. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Pin match becomes exit 0 | Keep exit 2 while it is not installed |
| Cost blowup | A full council fans out to many seats per question | Trial `--duo` or `--quick` only, on local models, on a handful of past decisions |
| Paid seats sneak in | Example seat map points at hosted models | Use an explicit local seat map; Ollama path only |
| Writes to real agent homes | Installer default targets `~/.claude` and others | Pass `--*-dir` under `$PFY_TMP` and `--dry-run` first |
| Pin drift | The repo is updated | Smoke checks this commit |

- **Status**: Cataloged I0. Next step: read the SKILL.md and member contracts, then a small `--duo` trial on local models over a few logged Deanery decisions against the current single-pass decision layer, under `$PFY_TMP`.
