---
name: project-process
description: >
  Scaffold or audit the portable project process layout: master DESIGN,
  multi-file ADRs (with rejected alternatives), central TODO, open questions,
  and AGENTS.md. Use when the user runs /project-process, /init-process,
  "scaffold process docs", "new project process", "bootstrap ADR TODO OQ",
  or starts a greenfield repo and wants the pfy-deanery process standard.
argument-hint: "[init|audit|refresh-skills] [path]"
---

# Project process — scaffold & audit

You install and maintain the **lightweight process framework** so new projects get DESIGN + ADR + TODO + open questions without re-specifying them.

## Layout (source of truth)

| Artifact | Path |
|----------|------|
| Design (goals) | `docs/DESIGN.md` |
| Architecture snapshot | `docs/ARCHITECTURE.md` |
| ADRs | `docs/adr/README.md` + `docs/adr/NNNN-*.md` |
| TODO | `docs/TODO.md` |
| Open questions | `docs/OPEN_QUESTIONS.md` + optional `docs/open-questions/` |
| Agent entry | `AGENTS.md` |

Portable package in the catalog repo:

`bootstrap/project-process/` (`init.sh` + `templates/` + this skill)

Companion skills: `/adr`, `/open-questions`, `/docs` (from `bootstrap/grok-cli/skills/`).

## Modes

### `init` [path] (default for greenfield / “set up process”)

1. Resolve target = path or git root of cwd.
2. Prefer running the package script when available:

```bash
# From pfy-deanery clone:
./bootstrap/project-process/init.sh <target> --name <name>
# Optional:
./bootstrap/project-process/init.sh --install-skills
```

3. If the script is **not** on disk (skills-only install), **copy the same structure** from skill knowledge using templates:
   - Create files listed above.
   - First ADR-0001 = process bootstrap (Accepted) with rejected alternatives: chat-only, issues-only, single giant DECISIONS.md-only.
   - Seed TODO T-0000 done + T-0001 fill DESIGN; seed one example OQ marked tbd or replace with real ones.
4. Do **not** overwrite existing DESIGN/ADR files unless user says force; merge carefully.
5. Report paths written and next human edits (vision/goals).

### `audit`

1. Check git root for presence of DESIGN, ARCHITECTURE, adr/README, TODO, OPEN_QUESTIONS, AGENTS.md.
2. List missing pieces; offer to init only missing files.
3. Flag anti-patterns: second decision log, ADRs without rejected alternatives, P0 OQs only in chat, TODO with no OQ when blocked.

### `refresh-skills`

Install/update process skills into `~/.grok/skills/` from:

- this skill’s package (`project-process`)
- sibling `bootstrap/grok-cli/skills/{adr,docs,open-questions}` when present

Or run `init.sh --install-skills`.

## Relationship to other skills

| Skill | Role |
|-------|------|
| `/project-process` | **Create/audit the layout** in a repo |
| `/adr` | Write/supersede individual decisions |
| `/open-questions` | Maintain OQ index and detail |
| `/docs` | Module/ops/architecture documentation quality |

## Quality bar

- ADRs always include **1–3 rejected alternatives** with reasons.
- TODO items that are blocked link an OQ ID.
- No secrets in process docs.
- Prefer multi-file `docs/adr/`; do not add `docs/DECISIONS.md` alongside it.

## Report

- Mode run
- Paths created/updated/skipped
- Missing process pieces (if audit)
- Suggested first domain ADR / OQs
