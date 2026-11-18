### Entry 197: decision-cascade: local decision engine with calibrated typed outputs and cheap-to-strong escalation

- **URL**: https://github.com/slavabars/decision-cascade (Apache-2.0, Python). Checked at commit `3a48f955745ed5dbb136eebd36b46db6fdf749a4` (2026-11-17 UTC; 2026-11-16 PT).
- **Date**: 2026-11-16 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122410934316544192
- **Summary / Key Claims** (upstream README; their claims, not verified here): instead of asking an LLM to write an answer, small local decision heads return typed, calibrated answers (Noul yes/no, Choice, Score) over a FastAPI server (`pip install decision-cascade`, Python 3.11+, no GPU or trained weights needed for the quick start). Uncertain questions escalate to a stronger remote or local model, optionally driven by an error budget (`DECISION_CASCADE_RISK_BUDGET`). Reports temperature-scaling calibration (ECE 0.144 to 0.024 on AG News) and RouterBench accuracy 0.542 at p50 21 ms; stable 1.7.0 API contract. Primary README is Russian; README.en.md exists.
- **Why it matters here**: Deanery's decision and routing layer (org-spinny-decide style push/hold/route gates, catalog-fit triage, local vs cloud model choice) currently asks a local LLM for text. This is the "decide, don't generate" pattern with calibration and a cost-aware escalation budget, which maps onto cost-before-spend and local-first routing.
- **Fit on nimo**: venv under `$PFY_ROOT`; CPU is enough for the heads; escalation target can be the local Ollama/vLLM model (OpenAI-compatible endpoint) so no paid keys.
- **Verified on the Grok Bot box** (2026-11-16): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 75 stars, pushed 2026-11-14.
  - Quick-start encoder example is `openai-community/gpt2` from Hugging Face (a small download, not an OpenAI API key).
  - Heads must be trained on our outcomes before they help; needs a labelled set of past gate decisions.
- **Extracted Repos / Tools**: https://github.com/slavabars/decision-cascade
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_197.py`. Commit-metadata only. Pins `$DECISION_CASCADE_COMMIT`. Fetches via `$DECISION_CASCADE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/decisioncascade/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_197` (7 stub tests).
- **Non-goals**: no remote escalation provider with paid keys, no server exposed off-host, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Overconfident gate | Heads trained on too few decisions | Shadow mode only; compare against current decider before any switch |
| Paid escalation | Escalation target set to a cloud API | Point escalation at the local OpenAI-compatible endpoint |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto in shadow mode against the current local-LLM decider on logged gate decisions (accuracy, calibration, latency, escalation rate).
