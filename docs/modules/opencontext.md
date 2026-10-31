# Module: OpenContext handoff (`scripts/pfy_opencontext_205.py`)

**Purpose:** Prove `oc` capture/search/reuse on the host and hand the store env to FreeToken-first Attach OpenCode | Hermes | Grok | Codex | Claude. Cite #205.

## Human operator

- What: `./pfy context` runs the hello-world prove. Attach/start inherit `OPENCONTEXT_*` when `oc` is on PATH.
- How: [docs/ops/opencontext.md](../ops/opencontext.md)
- Failures: missing node/oc → `FAIL` + `npm install -g @aicontextlab/cli`. Search uses `--mode keyword` (no embedding key).
- Recovery: install CLI, re-run `./pfy context`. Do not start `oc ui` from pfy.

### Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `OPENCONTEXT_BIN` | child env (set by prove/export) | Absolute `oc` path |
| `OPENCONTEXT_CONTEXTS_ROOT` | env; default `~/.opencontext/contexts` | Context library |
| `OPENCONTEXT_DB_PATH` | env; default `~/.opencontext/opencontext.db` | SQLite store |
| `CI=1` | prove subprocess | Non-interactive `oc init --tools none` |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Agent

- Entry: `scripts/pfy_opencontext_205.py` (`--prove` / `--export-env` / `--selftest`); `./pfy context` → `--prove`.
- Callers: `scripts/pfy` (`cmd_context`, `apply_opencontext_env` in `exec_harness`); Attach `pfy_attach_usable_196.py`, `pfy_attach_usable_202.py`, `pfy_attach_usable_220.py`, `pfy_attach_usable_221.py`, and `pfylib/attach.py` (`open_opencode_session`, formerly `pfy_enterable_162_b.py`).
- Invariants: painted OpenContext verb operate-or-FAIL; Attach missing-oc is skip not false READY; no GUI in pfy chrome; catalog HOLD (no TOOLS.md row).
- ADR: ADR-0012 (simple launch) · ADR-0014 (FreeToken-first spine). Issue **#205** only.
- Do not: `oc init` in this repo (rewrites `AGENTS.md`); reopen #76; unpark #198.

## Architecture link

Operator-stack layer (`./pfy` affordance + attach child env), not catalog product surface. Stage-0 receipt lives under `sources/entries/`.
