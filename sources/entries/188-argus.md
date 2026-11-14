### Entry 188: Argus: black-box red-team probes for agents, MCP tool poisoning and skills, with SARIF output

- **URL**: https://github.com/gy15901580825/Argus (Apache-2.0, Python 3.11+, PyPI `argus-probe` 1.13.0). Checked at commit `1f052e3c86c380b312c0b59df4795d7125807a84` (2026-11-13).
- **Date**: 2026-11-13 (daily X intake; deferred from the 2026-11-12 run as the top pick)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120916035150758359
- **Summary / Key Claims** (upstream README; their claims, not verified here): runs 272 adversarial probes (OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF mappings, garak wrappers) against an agent over the wire, as a black box. Includes a hostile MCP testbed (poisoned tool descriptions, look-alike tools, a tool list that turns hostile after trust, credential-fishing tools) whose verdicts come from recorded tool calls rather than a model reading the reply; `scan-skill` installs a skill in a throwaway container and watches for decoy-secret reads, risky commands and outbound requests. `argus-probe quickstart` runs against a built-in vulnerable demo agent with no API key. Findings come out as SARIF 2.1.0, JUnit XML and HTML.
- **Why it matters here**: the catalog loop pulls in third-party skills and MCP servers and promotes read-only tools on machine-checked rules. Argus is an existing, rule-mappable way to probe a candidate skill or MCP server before promotion instead of writing in-house injection checks. Its SARIF output fits a predefined pass/fail rule.
- **Fit on nimo**: CPU-only for the probes and testbeds. The LLM judge defaults to a cloud model, but Ollama and any OpenAI-compatible endpoint are listed, so point the judge at the local default model. pip into a venv under `~/DEVELOP`; `scan-skill` needs a container runtime.
- **Verified on the Grok Bot box** (2026-11-13): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 209 stars, PyPI 1.13.0, last push 2026-11-13 (very active, young project).
  - Payment-agent probes (mock x402 merchant) are out of scope here; leave them off.
  - `scan-skill` as documented targets Claude Code; using it with other agent homes would need checking.
- **Extracted Repos / Tools**: https://github.com/gy15901580825/Argus
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_188.py`. Commit-metadata only. Pins `$ARGUS_COMMIT`. Fetches via `$ARGUS_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/argus/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_188` (7 stub tests).
- **Non-goals**: no cloud judge, no API keys, no probes against any live or external agent, no payment testbed, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Cloud spend | Judge defaults to a hosted model | Set the judge to the local Ollama endpoint before any run |
| Hostile content escapes | Probe content or a scanned skill touches the real home | Run testbeds and `scan-skill` only in a throwaway container |
| Pin drift | `main` moves daily | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto running `argus-probe quickstart` and `mcp-trap` in a container on nimo with the local judge, then `scan-skill` on two catalog skills, and compare findings with what the current catalog checks catch.
