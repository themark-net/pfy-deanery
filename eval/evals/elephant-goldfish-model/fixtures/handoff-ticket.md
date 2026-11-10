# Handoff: docs/HANDOFF-build-review-1106.md
Write the handoff for this lane: what landed (cite SHAs from git log), the real ./pfy build trial result
(read tmp/trial/receipt.json and tmp/trial/trial.meta: status, reason, wall, commit/branch), which
cataloged tools made it in (codebase-memory-mcp and/or Tree-sitter Analyzer, and the fallback), commands a
bot runs, and a "Still open" list. ASCII hyphens only, no em dashes. Point docs/HANDOFF-headless-1105.md at
it. Add a small exit test that the note exists and names the cap env var and the impact source. Commit.
