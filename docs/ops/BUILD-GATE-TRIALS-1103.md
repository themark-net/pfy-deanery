# Build-gates lane trials (2026-11-03)

All numbers below are single runs measured on nimo tonight. No sudo was used.

## (a) Headroom (tool-output compression)

- Repo: https://github.com/headroomlabs-ai/headroom (PyPI `headroom-ai`, version 0.42.0).
- Install without sudo: `python3 -m venv ~/DEVELOP/_vendor/headroom-venv` then
  `pip install "headroom-ai[proxy]"` (the plain package lacks fastapi for the proxy). Works on Python 3.14.
- `headroom wrap grok` exists but registers an MCP server in `~/.grok/config.toml`, which is
  shared with Mark's live grok session. Not used. Instead: `HOME=<scratch> headroom proxy
  --port 18787 --openai-api-url https://api.x.ai --mode token`, then one headless call with
  `GROK_MODELS_BASE_URL=http://127.0.0.1:18787/v1 grok -p ...`. No config files changed.
- It works with grok headless: the proxied call answered correctly with normal auth.
- A/B, same prompt (`git log --stat -80` in sandcastle-grok, name the most frequent path), 2 turns each:

| | input tokens | cache read | total tokens | cost |
|---|---|---|---|---|
| direct | 21,651 | 23,424 | 45,722 | $0.0200 |
| via Headroom | 19,983 | 19,712 | 39,752 | $0.0188 |

  Proxy `/stats`: 2 of 3 requests compressed, 1,174 tokens removed of 41,776 (2.7%).
  Grok's own read/grep/edit tools are on Headroom's exclude list, so only shell output is
  compressed. One sample; turn-level noise is larger than the effect.
- A full-lane measurement was not run (it would cost a Build lane and needs the proxy up
  for the whole run). Verdict: works, low savings on git/text output; worth a lane trial only
  for JSON-heavy or log-heavy jobs. Catalog it, do not adopt yet.

## (b) mattpocock/skills /grill-me as a pre-ticket step

- `/grill-me` (skills/productivity/grill-me) just calls the `grilling` skill: rounds of
  numbered questions over the design-tree frontier, each with a recommended answer.
- Trial: one headless `grok -p` with the grilling skill text plus the G1 ticket body,
  told to emit one round and stop.
  - First try (`--max-turns 3`, tools allowed): it spent all turns exploring, no questions. $0.030.
  - Second try (no tools, `--max-turns 12`): 14 questions in 1 turn, 173 s, $0.037.
- Value: Q4 ("drop stale verdicts before a re-run") named a real fail-open the exit test
  missed. The landed runner did reuse an old raw PASS when a re-run wrote nothing; a test
  went red and the fix landed in 268247d. Most other questions restated the ticket.
- Recommendation for sandcastle-grok: optional `grill` step before a batch is cut. The
  coordinator (not Mark) answers with the recommended answers or overrides, and any answer
  that changes behavior becomes an exit-test case. Run it with tools off and a hard turn cap.
