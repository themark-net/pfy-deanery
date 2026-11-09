---
name: open-questions
description: >
  ToDo and Open Questions methodology: track open questions, TBDs, and
  parked decisions in a central project log with priorities and interconnections
  so multithreaded agent work can proceed without losing context. Use when the
  user runs /open-questions or /oq, says TBD, parking lot, track this question,
  decision can wait, open questions, or multithread status. Portable across
  projects.
argument-hint: "[list|add|answer|promote|scan] [id or text]"
---

# Open Questions & ToDo Tracking

You maintain a **living parking lot** for decisions and questions that need not block the current slice of work, while ensuring nothing important is lost across sessions or parallel agents.

## Goals

- Multithreaded work can mark items **TBD** with enough detail for another agent.
- One **central log** shows priorities and how items connect to the rest of the project.
- Answers that become architecture are **promoted** to `/adr` (not left only in chat).

## Step 0 — Resolve store

Git root of the active project. Then:

1. Prefer existing `docs/OPEN_QUESTIONS.md`.
2. Else create `docs/OPEN_QUESTIONS.md` using the central-log template from `references/template.md`.
3. For large or highly parallel work, also use detail files under `docs/open-questions/OQ-NNNN-slug.md` and keep one-line rows in the central log. In pfy-mentat itself these records are private: write them under `$PFY_OPS_ROOT/docs/open-questions/` and never commit them to the public repo.

Do not scatter open questions only in code comments or chat.

## Step 1 — Modes

| Mode | Behavior |
|------|----------|
| `list` / `scan` (default when asked for status) | Show open/tbd/blocked items sorted P0→P3; call out graph edges (Blocks / Blocked-by). |
| `add` | Create new OQ with full fields; assign next ID. |
| `answer` | The operator answered; write resolution + date; do not delete history. |
| `promote` | Answered architectural item → run ADR skill process; set status `promoted-to-adr` + ADR id. |
| `tbd` | Explicit park: status `tbd`, enough context for pickup. |

## Step 2 — Model

**Status:** `open` | `blocked` | `tbd` | `answered` | `promoted-to-adr` | `wont-do`

**Priority:**

| Level | Meaning |
|-------|---------|
| P0 | Blocks declared MVP / current critical path |
| P1 | Blocks next milestone |
| P2 | Important but not blocking |
| P3 | Someday / research |

**Interconnect fields (required on every OQ):**

- `Blocks:` what cannot finish until this is resolved (MVP smoke, feature X, …)
- `Blocked-by:` other OQ/ADR IDs or external deps
- `Related-ADR:` decision IDs if any
- `Related-code:` paths
- `Feature/runbook:` named workstream

## Step 3 — ID and write

1. Next ID = max existing `OQ-NNNN` + 1 (4 digits). Never reuse.
2. Add a **table row** to the central log.
3. Add a **detail section** in the same file (small projects) **or** a detail file (large). Detail must include: question, context, options if known, recommendation if any, resolution notes over time.

Templates: `references/template.md`. Methodology depth: `references/methodology.md`.

## Step 4 — Agent workflow (always)

1. **On multi-step feature start:** read `docs/OPEN_QUESTIONS.md` (at least the table). Surface P0/P1 items that touch the same code paths.
2. **Do not silently answer P0/P1** with a guess when the user should decide — ask, or leave `tbd` with options.
3. **When work uncovers a new question:** add an OQ immediately if it can wait; do not only leave a code `TODO` without a log entry for P0–P2.
4. **When answering:** append dated resolution; set status; if architectural → promote via `/adr`.
5. **Never delete** rows or detail history; strike through only via status change.

## Step 5 — Report

- Table of affected OQs (id, priority, status, title)
- Paths written
- Any promotions to ADR suggested or completed

## Anti-patterns

- Only filing questions in chat
- Closing OQs by deleting text
- P0 without a clear `Blocks:` target
- Answering architecture in OQ detail without an ADR when the choice is binding
