---
name: catalog-docs
description: >
  Document and keep consistent the pfy-deanery catalog repository:
  process docs (DESIGN/ADR/TODO/OQ), TOOLS.md + data/tools.json + sources
  triple-write, bootstrap packages, agent-cage harness, CONTRIBUTING, and
  README. Use when the user runs /catalog-docs, asks to document this repo,
  update README, sync catalog after an X seed, write module/ops docs for
  bootstrap or harness, or audit documentation drift. Not for generic
  third-party project docs (use /docs there).
argument-hint: "[audit|readme|tool|seed|module|harness|status] [path or name]"
---

# catalog-docs — Documentation for pfy-deanery

You are the **repository documentation skill** for this catalog only. Keep humans and agents oriented; never leave catalog claims without matching files.

## When to run

- User invokes `/catalog-docs` (or `/docs` while clearly in this repo and wanting catalog-wide docs).
- After adding an X seed, tool row, bootstrap package, or harness target.
- README/status/structure drift from disk.
- Before a PR that changes public operator paths.

## Mandatory map (read before writing)

| Concern | Authority |
|---------|-----------|
| Goals / shape | `docs/DESIGN.md` |
| Binding *why* | `docs/adr/` |
| Work queue | `docs/TODO.md` |
| TBDs | `docs/OPEN_QUESTIONS.md` |
| Agent rules | `AGENTS.md` |
| Scores table | `TOOLS.md` |
| Structured catalog | `data/tools.json` (**must parse as JSON**) |
| X seeds | `sources/x-posts.md` |
| Aggregates | `sources/aggregates.md` |
| Rubric | `CATEGORIZATION.md` |
| Pin/subtree policy | `SUBTREES.md` |
| Contrib rules | `CONTRIBUTING.md` |
| Grok operator env | `bootstrap/grok-cli/` |
| Process scaffold | `bootstrap/project-process/` |
| Container lab | `harness/agent-cage/` |
| Integration plan | a private ops note |
| Harness framework | `docs/ops/harness-integration-framework.md` |

## Modes

### `audit` (default when asked “is docs OK?”)

1. `python3 -c "import json; json.load(open('data/tools.json'))"` — fail if invalid.
2. List tools in `data/tools.json` vs rows in `TOOLS.md` vs claims in latest `sources/x-posts.md` entries.
3. Flag **triple-write gaps**: processed X entry without TOOLS.md row and tools.json object (or vice versa).
4. Check README structure tree and status bullets against real paths (`harness/`, `bootstrap/`, `docs/ops/`).
5. Report: OK / drift list with paths; offer to fix in the same turn if user wants.

### `readme`

Update `README.md` so it always has:

1. One-line purpose + goals (short)
2. Process docs table (DESIGN / ADR / TODO / OQ / AGENTS)
3. **Current status** (version bullets; no stale “placeholder only” if seeds exist)
4. Bootstrap (grok-cli + project-process)
5. **Container harness** (`harness/agent-cage` Make targets)
6. Repository structure tree matching disk
7. Skills list (including `/catalog-docs`)
8. Pointers to TOOLS.md and CONTRIBUTING
9. Next steps → `docs/TODO.md` only (do not invent a parallel queue)

### `tool <name>`

Document a catalog tool after integration:

1. Ensure triple-write: `sources/x-posts.md` (if from X) + `TOOLS.md` row + `data/tools.json` entry with scores, tier, tags, pin/bootstrap path, notes.
2. Validate JSON.
3. If integrated via harness, add notes under TOOLS + optional `docs/ops/` or `examples/` pointer.
4. Link ADR/OQ/TODO IDs when relevant.

### `seed`

After a new X post / paper intake:

1. Append Entry NNN to `sources/x-posts.md` using existing format.
2. Score with `CATEGORIZATION.md`.
3. Add TOOLS.md + tools.json **in the same change**.
4. Set status `processed` only when all three exist.
5. Add TODO row if implementation remains.

### `module <path>`

Operator + agent module doc under `docs/modules/` (or ops runbook under `docs/ops/`) for:

- `bootstrap/grok-cli` → `docs/modules/bootstrap-grok-cli.md`
- `bootstrap/project-process` → `docs/modules/bootstrap-project-process.md`
- `harness/agent-cage` → `docs/modules/harness-agent-cage.md`
- `harness/write-guard-mcp` → `docs/modules/write-guard-mcp.md`
- `examples/` smokes → `docs/modules/examples-smokes.md`

Use the portable `/docs` module template fields: how to run, env/vars table, entry points, invariants, ADR links. Index: `docs/modules/README.md`.

### `harness`

Document or refresh agent-cage operator path:

- `make doctor | setup | up | up-mcp | shell | test | down | smoke-host`
- Pin file + clone location
- How other tools are tested inside the cage (`docs/ops/harness-integration-framework.md`)
- Update README harness section if commands changed

### `status`

Refresh README “Current Status” and DESIGN § delivered vs near-term from git tree + TODO — no marketing fluff.

## Hard rules

1. **Triple-write** for catalog tools: x-posts (if seeded) + TOOLS.md + tools.json.
2. **Never** claim “cataloged” without JSON that `json.load`s.
3. Prefer **pins** over subtrees (ADR-0003); document bootstrap_path when first-party.
4. Process pivots → `/adr`; open TBDs → `/open-questions`; work items → `docs/TODO.md`.
5. Do not put secrets in docs.
6. Keep README as the **map**; deep detail lives under `docs/` and package READMEs.

## After writing

- List paths created/updated
- Confirm tools.json parses
- Mention slash: `/catalog-docs`, `/skills catalog-docs`

## Anti-patterns

- Updating only x-posts.md and saying the tool is cataloged
- README status frozen on old v0.2 while harness/skills exist
- Duplicating full TOOLS tables inside README
- Generic `/docs` module prose that ignores catalog triple-write
