# AGENTS.md — {{PROJECT_NAME}}

Instructions for coding agents working in this repository.

## Mandatory reads (before non-trivial design or multi-step work)

1. [docs/DESIGN.md](docs/DESIGN.md) — goals, shape, non-goals, process model
2. [docs/adr/README.md](docs/adr/README.md) — decision index (open ADRs that touch your area)
3. [docs/TODO.md](docs/TODO.md) — next steps
4. [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) — do not silently “solve” P0/P1 OQs

## Process rules

| Situation | Action |
|-----------|--------|
| Architecture pivot / hard-to-reverse choice | Write **ADR** under `docs/adr/` with **rejected alternatives** (`/adr`) |
| Uncertain / can wait / needs human | **Open question** in central index; optional detail or in-context note citing `OQ-NNNN` (`/open-questions`) |
| Implementation work item | Update **TODO** row; link OQs when blocked |
| Non-trivial module change | Operator + agent docs (`/docs`) |

Before a new or changed pipeline, CI, or gate step, check the catalog for a tool that already covers the job, then answer the five software-factory questions: trigger, what it reads and writes, what it triggers next, where a human re-enters, and what stops two runs doing the same work.

## Do not

- Re-propose designs rejected in ADRs without a superseding ADR and new context
- Leave P0–P2 questions only in chat
- Commit secrets, API keys, or credentials
- Create a second decision log outside `docs/adr/`

## Skills (install via pfy-mentat bootstrap)

- `/adr` — Architecture Decision Records
- `/open-questions` / `/oq` — TBD parking lot
- `/docs` — operator + agent module documentation
- `/project-process` — re-scaffold or audit this layout
- `/one-shot` — unattended until DoD green (when lab allows)
- Optional paths packs: ponytail, mattpocock (tdd / code-review / to-spec)

## Role router (gstack-style stages, no gstack install)

Think → Plan → Build → Review → Test → Ship → Reflect:

| Stage | Prefer |
|-------|--------|
| Think / product | Challenge scope → `/adr` or `/open-questions` |
| Plan | `to-spec` (if installed) + written DoD |
| Build | Surgical implement; `/one-shot` only with DoD + lab |
| Debug | `/investigate` — no fix without root-cause hypothesis |
| Review | `code-review` (if installed); second persona optional |
| Test | Project tests + integration lab if any |
| Ship | Feature branch → green → merge |
| Reflect | Update TODO/OQ; heal docs |

Full recipes live in the pfy-mentat catalog: `docs/ops/gstack-role-recipes.md`.
