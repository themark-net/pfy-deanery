# Module: bootstrap/project-process

**Purpose:** Scaffold **DESIGN / multi-file ADR / TODO / open questions / AGENTS** into any repo so multi-session agents share process without re-litigating decisions.

## Operator: how to run

```bash
mkdir -p ~/work/my-app && cd ~/work/my-app && git init
/path/to/pfy-mentat/bootstrap/project-process/init.sh . \
  --name my-app \
  --vision "One-line product vision" \
  --install-skills
```

Or in Grok (after grok-cli install): `/project-process init .`

| Piece | Role |
|-------|------|
| `init.sh` | Copy templates into target repo |
| `templates/` | DESIGN, ADR-0001 sample, TODO, OQ, AGENTS |
| `skills/project-process/` | Skill for agents to re-run / explain process |

Package README: [bootstrap/project-process/README.md](../../bootstrap/project-process/README.md)

## Where variables live

No runtime secrets. Optional skill install uses Grok skills paths from grok-cli bootstrap.

## Agent map

| Concern | Detail |
|---------|--------|
| **Invariants** | ADR always includes **rejected alternatives**; TODO links OQs when blocked |
| **Do not** | Invent architecture in TODO - promote via `/adr` |
| **ADR** | ADR-0001 (process docs bootstrap) |
| **Skill** | `/project-process`, `/adr`, `/open-questions` |

## Verify

```bash
test -f docs/DESIGN.md && test -d docs/adr && test -f docs/TODO.md
```
