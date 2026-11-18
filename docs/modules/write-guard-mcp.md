# Module: harness/write-guard-mcp

**Purpose:** Thin **MCP + CLI** that mediates agent filesystem writes (`off` / `audit` / `enforce`) with secret deny-globs and JSONL audit - defense-in-depth **above** cage workspace bind-mounts.

## Operator: how to run

```bash
# Host unit selftest (no MCP required)
PYTHONPATH=harness/write-guard-mcp/src python3 -m write_guard selftest

# Editable install (MCP serve needs mcp + pyyaml)
cd harness/write-guard-mcp && python3 -m venv .venv && . .venv/bin/activate
pip install -e .
python -m write_guard serve   # stdio MCP

# Preferred proof for this catalog
make smoke-write-guard        # in agent-cage
```

| Mode | Behavior |
|------|----------|
| `audit` | **Default** (OQ-0009) - allow writes; log; flag secret globs |
| `enforce` | Deny outside roots / secrets / deny_write; delete default deny |
| `off` | Pass-through |

Package README: [harness/write-guard-mcp/README.md](../../harness/write-guard-mcp/README.md)  
Design: [docs/ops/write-guard-mcp-design.md](../ops/write-guard-mcp-design.md)

## Where variables live

| Variable | Role |
|----------|------|
| `WRITE_GUARD_MODE` | `off` \| `audit` \| `enforce` |
| `WRITE_GUARD_ROOTS` | Colon-separated roots (e.g. `/workspace`) |
| `WRITE_GUARD_POLICY` | Path to YAML policy (default `policy.default.yaml`) |
| Audit log | `audit_log` in policy (default `/workspace/.write-guard-audit.jsonl`) |

## Agent map

| Concern | Detail |
|---------|--------|
| **Tools** | `list_roots`, `list_dir`, `read_file`, `write_file`, `delete_file`, `write_status` |
| **Invariants** | Shell can still bypass MCP - keep cage L0; do not log file bodies |
| **ADR** | ADR-0007 |
| **mcp-host** | Overlay fragment exists but entry **disabled** (T-0043 parked). Stock cage **filesystem** MCP already handles workspace r/w; write-guard is policy/audit only |

## Verify

```bash
make smoke-write-guard
PYTHONPATH=harness/write-guard-mcp/src python3 -m unittest discover -s harness/write-guard-mcp/tests -v
```

## Not yet

- Enabling the mcp-host overlay by default (T-0043 parked)
