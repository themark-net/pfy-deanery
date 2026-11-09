# Grok CLI bootstrap

Replayable packaging of the **Grok CLI customizations** used with this catalog: portable agent skills, MCP code-memory wiring, and a safe config fragment.

This is the first concrete integration under `pfy-mentat` — not another third-party tool row alone, but the **operator environment** that ties Grok CLI + MCP memory + agent process skills into a stack you can rebuild on a new machine.

## How this fits the repository

| Repo goal | This bootstrap |
|-----------|----------------|
| Grok CLI as primary interface | Installs skills + config Grok actually loads |
| MCP-style code memory | Wires `codebase-memory-mcp` into `~/.grok/config.toml` |
| Reproducible integrations | `install.sh` is idempotent; pins recorded in `manifest.json` |
| Multithreaded agent pipelines | `adr` / `open-questions` / `docs` skills keep decisions & TBDs in-repo |
| Lean catalog | Skills vendored here (~small); binary MCP fetched optionally |

**Out of scope (intentionally):** Grok binary auth tokens, session history, marketplace office skills (docx/pptx), account-bound Grok.com GitHub tools.

## What gets installed

### First-party skills → `~/.grok/skills/`

| Skill | Role |
|-------|------|
| `adr` | Architecture Decision Resource process (`/adr`) |
| `docs` | Operator + agent module docs (`/docs`) |
| `open-questions` | Central TBD / parking lot (`/open-questions`, `/oq`) |
| `karpathy-guidelines` | Anti-overcomplication behavioral guidelines (MIT, from [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)) |
| `project-process` | Scaffold DESIGN / ADR / TODO / OQ / AGENTS into any repo (`/project-process`) — from sibling [../project-process/](../project-process/) |
| `catalog-docs` | **This catalog’s** documentation skill: README, triple-write TOOLS/json/x-posts, harness docs (`/catalog-docs`) |
| `one-shot` | Min-question delivery loop with cost ladder + lab prerequisites (`/one-shot`) |
| `investigate` | RCA Iron Law: hypothesis before fix (`/investigate`, T-0017) |
| `marketing-council` | Multi-advisor marketing perspectives (`/marketing-council`, T-0011) |
| `agent-loops` | Loop types + eight exits + Finn spec/build/review (`/agent-loops`, T-0050) |
| `hermes-feedback` | Self-improvement: auto-memory, auto-skill, curator (`/hermes-feedback`, T-0048) |
| `jev-decision` | Typed Choice/Score locks: CUA-S1-FORMS primary local, TypeSafe optional (`/jev-decision`, #230) |
| `prefer-behavior-and-fail-recover-tests` | Testing Trophy: sociable integration/E2E, no tautological units, fail and recover (`/prefer-behavior-and-fail-recover-tests`) |
| `ui-is-the-app-design-in-loop` | Operator UI is the app; design pack before product chrome (`/ui-is-the-app-design-in-loop`) |

### External skills path (not copied into `~/.grok/skills`)

| Path | Role |
|------|------|
| `skills-external/ponytail/` | Snapshot of [ponytail](https://github.com/DietrichGebert/ponytail) skills; registered via `[skills].paths` so Grok scans them |
| `skills-external/mattpocock/` | Curated [mattpocock/skills](https://github.com/mattpocock/skills) subset (tdd, code-review, to-spec); `[skills].paths` |

### Config (`~/.grok/config.toml`)

Idempotent merge (see `scripts/merge_config.py`):

- `[memory] enabled = true`
- `[mcp_servers.codebase-memory]` → `command = "codebase-memory-mcp"`
- `[skills].paths` += absolute path to `skills-external/ponytail`
- `[ui].permission_mode = "always-approve"` (disable with `--no-permission-mode`)

Backups: `config.toml.bak.<UTC timestamp>` on first real write.

### Optional binary

```bash
./install.sh --with-codebase-memory
```

Runs the official [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) installer with `--skip-config` (this repo owns Grok config).

## Quick start (new environment)

```bash
# 1. Install Grok CLI (if needed)
curl -fsSL https://x.ai/cli/install.sh | bash

# 2. Clone this catalog
git clone git@github.com:themark-net/pfy-mentat.git
cd pfy-mentat

# 3. Replay customizations
./bootstrap/grok-cli/install.sh --with-codebase-memory

# 4. Auth
grok login   # or: export XAI_API_KEY=...

# 5. New Grok session — skills + MCP should appear
grok
```

## Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | Print actions; config preview; no writes |
| `--skills-only` | Skills + config path wiring only |
| `--config-only` | Config merge only |
| `--mcp-only` | Optional binary install + config MCP section |
| `--with-codebase-memory` | Fetch `codebase-memory-mcp` binary |
| `--no-ponytail` | Do not register ponytail skills path |
| `--no-permission-mode` | Leave `ui.permission_mode` alone |
| `--force` | Reserved for overwrite semantics (skills always refreshed) |
| `--verify` | Run checks (also always runs at end of full install) |

Env overrides: `GROK_HOME`, `GROK_SKILLS_DIR`, `SKIP_PONYTAIL=1`, `SKIP_CODEBASE_MEMORY=1`.

## Layout

```
bootstrap/grok-cli/
├── README.md                 # this file
├── manifest.json             # pins, origins, fit notes
├── install.sh                # main entrypoint
├── config/
│   └── config.fragment.toml  # human-readable owned keys
├── scripts/
│   └── merge_config.py       # idempotent TOML section upsert
├── skills/                   # first-party (+ karpathy) → ~/.grok/skills/
│   ├── adr/
│   ├── docs/
│   ├── open-questions/
│   └── karpathy-guidelines/
└── skills-external/
    └── ponytail/             # scanned via skills.paths
```

## Refreshing after edits

1. Edit skills under `bootstrap/grok-cli/skills/` (source of truth for first-party).
2. Re-run `./bootstrap/grok-cli/install.sh --skills-only`.
3. Commit the skill changes in this repo so other machines replay them.

To refresh the ponytail snapshot from a local checkout:

```bash
rsync -a --delete /path/to/ponytail/skills/ bootstrap/grok-cli/skills-external/ponytail/
# update pinned_commit in manifest.json
./bootstrap/grok-cli/install.sh --skills-only
```

### Skill port policy (ADR-0009 hybrid)

| Kind | Location | How Grok sees it |
|------|----------|------------------|
| **Core (first-party)** | `skills/` | Copied into `~/.grok/skills/` on install |
| **External pack (ponytail model)** | `skills-external/<pack>/` | `[skills].paths` absolute path — **not** copied into `~/.grok/skills/` |
| **Docs-only** | TOOLS / AGENTS recipes | No install |

**Core** = process backbone we edit, small surface, default-on, license-safe (criteria in ADR-0009).  
**Bulk upstream** packs use the **same methods as ponytail** (snapshot + paths + pin + opt-out), not full-tree embed into first-party skills.

**T-0011 ports:** `marketing-council` (first-party) · `mattpocock` tdd/code-review/to-spec (`--no-mattpocock` to skip).  
**T-0017:** `investigate` first-party RCA skill (gstack method rewrite, not raw snapshot).  
**T-0050:** `agent-loops` first-party loop engineering (8 exits + 4 types + Finn + rubric; Entries 024/027/031/032/068).  
**T-0048:** `hermes-feedback` first-party pattern port (Hermes three loops → Grok memory/skills/curator; not Hermes runtime).  
**T-0126:** founder standings — `prefer-behavior-and-fail-recover-tests`, `ui-is-the-app-design-in-loop` (org skills are pointers).  
**Catalog pipeline:** `catalog-intake-dedupe`, `catalog-eval-lane`, `catalog-integrate-lane`, `catalog-apply-and-ceiling`, `catalog-loop-operator` (first-party; the loop and the lanes load them).  
**Verify skills:** `make smoke-grok-skills` · `make smoke-grok-skills INSTALLED=1` · [docs/ops/skill-verification.md](../../docs/ops/skill-verification.md)

## Relationship to catalog entries

See `TOOLS.md` / `data/tools.json` for scored entries:

- **Grok CLI bootstrap** (this package) — integration / pipeline component
- **codebase-memory-mcp** — Memory & RAG / MCP
- **ponytail** — coding agent skill pack (minimalism)
- **karpathy-guidelines** — coding agent guidelines

## Security notes

- No secrets in this tree.
- Installer never reads or writes `auth.json`.
- Config merge only upserts owned sections; review the backup if anything looks wrong.
- `--with-codebase-memory` pipes a remote install script — inspect upstream first if that is a concern; binary is also available from GitHub Releases.
