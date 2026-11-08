# Bumblebee MCP and package scan

Advisory check for a package lockfile exposure and for MCP host JSON. It runs the pinned Bumblebee binary when one is present, and it reads MCP JSON itself. It does not install packages, start servers, or block a commit.

The binary pin is v0.1.2, commit `cc57710eeaf685e7b89924a36c8583cad0a378fe`, installed under `~/.cache/pfy/tools/bumblebee/`. This doc does not add a make target, a pregate step, or a CI job.

## Operator

```bash
PFY_BUMBLEBEE_BIN=~/.cache/pfy/tools/bumblebee/bumblebee \
  python3 scripts/pfy_mcp_scan.py \
  --root /path/to/fixture-or-worktree \
  --catalog ~/.cache/pfy/tools/bumblebee/threat_intel \
  --out /tmp/bumblebee-receipt.json
```

`--root` is required. The command refuses `$HOME` and a root whose first directory under `$HOME` is `.grok`, `.claude`, `.codex`, `.config`, or `.local`. Pass the worktree or a fixture directory you built. Do not point it at the real home.

The child process gets a scratch `HOME` and scratch XDG directories. Those directories are removed when the scan returns.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | No package finding and no local MCP advisory. |
| 1 | At least one advisory. The command prints the kind, the server or package, and the file. |
| 2 | The root was refused, an MCP file was not readable JSON, the binary is missing, or the scanner output was not NDJSON. The command prints a next step. |

A git selector (`github:`, `gitlab:`, `git+`, `git@`, `git://`) in an MCP command or arg is an advisory. A non-empty env value whose key looks like a token, secret, password, or credential is an advisory. The command prints the key name and never the value. If the scanner echoes a value seen in one of those keys, and the value is at least 4 characters, the receipt replaces it with `[redacted]`. Shorter values are not substituted, so a one-character replace cannot blank ordinary text. The key is still named.

Bumblebee itself matches an exposure catalog by exact ecosystem, name, and version. A clean version of a bad package name is not a finding. A bare `package.json` or `pyproject.toml` is not a lockfile, and v0.1.2 does not inventory it.

## What this does not do

It does not replace write-guard. write-guard mediates writes. This check reads lockfiles and MCP JSON. It does not parse Codex `config.toml` or other non-JSON MCP configs. It is not a gate.
