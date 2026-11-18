# Harness: agent-cage (PNNL)

Primary **containerized agent sandbox** for this catalog. Version images, isolate network/MCP, and run integration tests against other tools without polluting the host.

**Upstream:** https://github.com/pnnl/agent-cage  
**Pin (source):** `PINNED_COMMIT`  
**Runtime project (CLI):** `$AGENTCAGE_DIR` default **`~/.agentcage`** (created by `agentcage init`)

## What went wrong in a typical first session

| Symptom | Cause | Fix |
|---------|--------|-----|
| `Could not find Agent Cage project directory` | Ran `agentcage` from the **catalog** repo root | `agentcage init` once, **or** `export AGENTCAGE_DIR=~/.agentcage` |
| `make test` → No rule to make target | Ran `make` from catalog root without our root Makefile (or old tree) | `make cage-test` from root, or `cd harness/agent-cage && make test` |
| `make agentcage` fails | No such target | Use `make cage-up-mcp` / `make cage-test` |
| Tests FAIL `service "agent" is not running` | Ran `test` before `up` | `make cage-up-mcp` (wait for build), then `make cage-test` |
| Empty status table | Project exists but nothing started | `agentcage up` or `make cage-up-mcp` |

## Quick start (copy/paste)

From **catalog repo root** (recommended):

```bash
export PATH="$HOME/.local/bin:$PATH"
cd $PFY_ROOT
git pull origin main   # or your feature branch

make cage-doctor
make cage-setup        # CLI + optional pinned source clone
make cage-init         # materialize ~/.agentcage (once per machine)
make cage-up-mcp       # START containers — first build can take a long time
make cage-status
make cage-test
make cage-shell        # Ubuntu agent; /workspace is host ~/.agentcage/workspace
make cage-down         # when finished
```

Equivalent from this directory:

```bash
cd harness/agent-cage
make setup && make init && make up-mcp && make test
```

Direct CLI (after init):

```bash
export PATH="$HOME/.local/bin:$PATH"
export AGENTCAGE_DIR="$HOME/.agentcage"   # optional if default
agentcage up --mcp
agentcage status
agentcage test --quick
agentcage shell
agentcage down
```

## Two directories (do not confuse them)

| Path | Role |
|------|------|
| `~/.local/share/pfy-mentat/agent-cage` | Optional **source pin** checkout (editable CLI install) |
| `~/.agentcage` | **Runtime project** for compose/policies/workspace (`agentcage init`) |

The CLI looks for: `AGENTCAGE_DIR` env → walk up for compose → else `~/.agentcage`.

## Integration testing rule (this catalog)

**New integration work for catalog tools should be exercised inside the cage** (versioned images + MCP + network policy), not only on the host:

1. `make cage-up-mcp`
2. `make cage-shell` → install/pin tool under `/workspace` (or mount)
3. Run smoke commands; capture notes in TOOLS.md / `pipelines/smoke/<tool>/`
4. `make cage-down` when done

Host-only checks (`make cage-smoke-host`) validate pins/JSON/docker — not a substitute for cage smokes.

See [docs/ops/harness-integration-framework.md](../../docs/ops/harness-integration-framework.md).

## Targets

| Target | Action |
|--------|--------|
| `doctor` | docker, compose, agentcage, AGENTCAGE_DIR |
| `setup` | clone pin + install CLI |
| `init` | `agentcage init --path $AGENTCAGE_DIR` |
| `up` / `up-mcp` | start stack |
| `status` / `test` / `shell` / `down` | operate |
| `smoke-host` | no containers |
| `smoke-integration` | init if needed → up-mcp → test |

Repo root mirrors these as `make cage-*`.

## Grok

- **Host Grok:** always fine for catalog work.
- **Grok-in-image:** optional versioned overlay — see [overlays/grok/README.md](overlays/grok/README.md).

```bash
make grok-overlay-install
make grok-overlay-build
# XAI_API_KEY in ~/.agentcage/.env
make grok-up
make grok-smoke    # grok --version inside container
```
