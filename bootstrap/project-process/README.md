# Project process bootstrap

Replayable **new-project process kit**: master design, ADR log (with rejected alternatives), central TODO, open questions, and `AGENTS.md` — plus Grok skills so agents keep the structure alive.

Use this when starting a repo so you never re-specify the process by hand.

## What you get

| Piece | Mechanism |
|-------|-----------|
| **Scaffold** | `init.sh` copies templates into a target project |
| **Skills** | `project-process` (+ `adr`, `docs`, `open-questions` from sibling grok-cli package) |
| **Templates** | `templates/` — DESIGN, ARCHITECTURE, ADR-0001, TODO, OQ, AGENTS |

## Quick start (new project)

```bash
# From a pfy-deanery checkout:
mkdir -p ~/work/my-app && cd ~/work/my-app && git init

/path/to/pfy-mentat/bootstrap/project-process/init.sh . \
  --name my-app \
  --vision "One-line product vision" \
  --install-skills
```

Or with Grok already using catalog skills:

```text
/project-process init .
```

## Full operator environment (skills + MCP + this process)

```bash
./bootstrap/grok-cli/install.sh --with-codebase-memory
./bootstrap/project-process/init.sh --install-skills
./bootstrap/project-process/init.sh /path/to/new-or-existing-repo --name <name>
```

`grok-cli/install.sh` can also pull in the `project-process` skill (see wiring below).

## Flags

| Flag | Effect |
|------|--------|
| `--name NAME` | Project name in templates |
| `--vision TEXT` | One-line vision for DESIGN/ARCHITECTURE |
| `--force` | Overwrite existing scaffold files |
| `--dry-run` | Print only |
| `--install-skills` | Install skills to `~/.grok/skills` |

## Layout after init

```text
AGENTS.md
docs/
  DESIGN.md
  ARCHITECTURE.md
  TODO.md
  OPEN_QUESTIONS.md
  adr/
    README.md
    0001-process-docs-bootstrap.md
  open-questions/
  modules/
  ops/
```

## Evaluation vs heavier tools

See [skills/project-process/references/evaluation.md](skills/project-process/references/evaluation.md).

**Verdict:** markdown + skills is **sufficient** for agent-driven repos; optional later: `adr-tools` CLI, enforcement plugins. Do not block on SaaS process platforms.

## Relationship to grok-cli bootstrap

| Package | Responsibility |
|---------|----------------|
| `bootstrap/grok-cli/` | Operator machine: skills paths, MCP memory, config |
| `bootstrap/project-process/` | **Per-repo** process files + process skills |

Both are first-party integration packages in this catalog.
