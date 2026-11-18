### Entry 192: book-to-skill: distill a book or document folder into an on-demand agent skill

- **URL**: https://github.com/virgiliojr94/book-to-skill (MIT, Python). Checked at commit `e7bb659d3261491c8b28793dcb9102fa64a46c22` (2026-11-03).
- **Date**: 2026-11-14 (daily X intake)
- **Source / Poster**: watch-list post by @tom_doerr, https://x.com/tom_doerr/status/2121471758234501493
- **Summary / Key Claims** (upstream README; their claims, not verified here): `/book-to-skill <path|folder|glob> [skill-name]` turns PDF, EPUB, DOCX, MD, HTML, RTF or MOBI sources into one skill with frameworks, decision rules, anti-patterns and per-chapter files, so the agent loads the right chapter on demand. Claims 24x-51x fewer tokens than putting the book in context (measured in its `docs/performance.md`). Writes to the cross-agent `~/.agents/skills/<slug>/` root (Copilot CLI, Amp, Codex, OpenCode, OpenClaw; Hermes and Claude Code variants). Analyze-only, generate-from-analysis and update modes; optional publish to GitHub. `scripts/extract.py --check` lists missing extractors.
- **Why it matters here**: Deanery wants product docs and goals (not code) to drive eval prompts, and wants catalog knowledge (e.g. 190 Learn Harness Engineering) usable by lanes without stuffing context. This is a cheap way to turn those doc sets into skills that a local model can page through, and its token claim is directly testable against the current "paste the doc" approach.
- **Fit on nimo**: runs inside the host agent (the agent does the distilling, so it uses whatever model the lane uses, local or cloud). Extractors are pip packages (`pdftotext`, `pypdf`, optional `docling`) in a venv under `$PFY_ROOT`. No GPU of its own.
- **Verified on the Grok Bot box** (2026-11-14): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 37.9k stars, last push 2026-11-08.
  - Default install target is the shared `~/.agents/skills/` root, which every agent on the machine reads; direct output to a scratch skills dir instead.
  - Optional GitHub publish step must stay off (no accounts, no publishing).
- **Extracted Repos / Tools**: https://github.com/virgiliojr94/book-to-skill
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_192.py`. Commit-metadata only. Pins `$BOOKTOSKILL_COMMIT`. Fetches via `$BOOKTOSKILL_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/booktoskill/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_192` (7 stub tests).
- **Non-goals**: no writes to the real `~/.agents/skills`, `~/.claude/skills` or `~/.grok/skills`, no GitHub publish, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Skill lands in shared homes | Default target is `~/.agents/skills/` | Run in an isolated HOME under `$PFY_ROOT` |
| Distilled skill is wrong | Model invents rules the source doesn't state | Spot-check against the source; keep analyze-only first |
| Publish step fires | Converter pushes the skill to GitHub | Never pass the publish option; no tokens in the sandbox |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto converting the Deanery product docs (DESIGN, ARCHITECTURE, evaluation framework) into one skill in a scratch HOME, then answering ten fixed questions with the local default model, skill vs plain doc paste, scored on correctness and prompt tokens.
