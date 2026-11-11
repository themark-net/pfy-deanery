# Documentation map — pfy-deanery

Quick index for `/catalog-docs`.

## Human entry

| Doc | Role |
|-----|------|
| `README.md` | Map: goals, status, bootstrap, harness, structure |
| `CONTRIBUTING.md` | How to add seeds/tools |
| `TOOLS.md` | Scored catalog table |
| `CATEGORIZATION.md` | Rubric |
| `SUBTREES.md` | Pin vs subtree policy |

## Process (agents + humans)

| Doc | Role |
|-----|------|
| `AGENTS.md` | Mandatory reads + workflow practices |
| `docs/DESIGN.md` | Master design |
| `docs/ARCHITECTURE.md` | Snapshot |
| `docs/adr/` | Decisions + rejected alternatives |
| `docs/TODO.md` | Work queue |
| `docs/OPEN_QUESTIONS.md` | Parking lot |
| `docs/ops/*` | Plans, DEPLOY, one-shot DoDs, harness framework |
| `docs/modules/*` | First-party package maps (bootstrap, cage, write-guard, smokes) |
| `docs/automation/*` | Standing monitors (e.g. tom-doer) |

## Packages

| Path | Role |
|------|------|
| `bootstrap/grok-cli/` | Operator Grok skills + MCP + config install → `docs/modules/bootstrap-grok-cli.md` |
| `bootstrap/project-process/` | Scaffold DESIGN/ADR/TODO/OQ into any repo → `docs/modules/bootstrap-project-process.md` |
| `harness/agent-cage/` | Container sandbox lab (Make) → `docs/modules/harness-agent-cage.md` |
| `harness/write-guard-mcp/` | Write mediation MCP → `docs/modules/write-guard-mcp.md` |
| `examples/` + `pipelines/smoke/` | In-cage smokes → `docs/modules/examples-smokes.md` |

## Skills (slash)

| Skill | Purpose |
|-------|---------|
| `/catalog-docs` | This repo’s documentation skill |
| `/docs` | Portable module/ops docs |
| `/adr` | Decisions |
| `/open-questions` | TBDs |
| `/project-process` | Scaffold process into a repo |

## Triple-write checklist (every tool seed)

- [ ] `sources/x-posts.md` Entry NNN (if from X/paper/social)
- [ ] `TOOLS.md` table row with scores + notes
- [ ] `data/tools.json` object; `python3 -c "import json; json.load(open('data/tools.json'))"`
- [ ] Status `processed` only when all present
