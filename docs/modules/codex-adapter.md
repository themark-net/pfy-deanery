# Module: Codex adapter

**Purpose:** Exec `codex` from `./pfy start codex`. Inference via `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector when ready (`OPENAI_BASE_URL` defaults to that). Do not invent Codex-specific flags.

## Entry

```bash
./pfy harness use codex
./pfy start codex
python3 scripts/pfy-board.py --start codex
python3 scripts/pfy_attach_usable_220.py --prove "$LOCAL_OPENAI_BASE_URL"
python3 scripts/pfy_attach_usable_220.py --selftest
```

Detect: `codex` on PATH (or `$HOME/.local/bin/codex`).

**Attach usable (#220):** HTML+tk **Attach codex** (and `python3 scripts/pfy-board.py --start codex`) re-probes FreeToken-first (`:1919`), sets child `LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL` to the live detect base, then proves models list + one smoke (`pfy_attach_usable_220.prove_developer_usable`, same bar as OpenCode #193 / Hermes #196 / Grok #202) before `ok:True` / READY / “attached”. Failures: `usable:false`, session/attach state cleared, FAIL + next (`Launch env or ./pfy up`). Missing Codex: FAIL + installer one-liner (never a silent stub success). No credentials in paint/logs. Loop paints `attached=codex` plus session reach and `using: <mode>`. One attach at a time. No Env nav tab.

CLI `./pfy start codex` uses the same honesty: no live engine → FAIL + next (does not exec); prove (`python3 scripts/pfy_attach_usable_220.py --prove $LOCAL_OPENAI_BASE_URL`) must pass before exec. Inspect equivalent: `./pfy models` (list) + Test model / `--prove` (smoke).

**Attach mode (#208 / #213 / #215):** `bare` hands off prompt/env. `orchestration` starts a multi-step local loop (`/agent-loops` + prove + monitor evidence). `code-graph` needs Axon CLI (`AXON_BIN`); MCP-only is unwired for Codex → FAIL + `pip install axoniq` / Attach grok or opencode. [attach-mode.md](../ops/attach-mode.md) · [code-graph.md](code-graph.md).

Missing binary: FAIL attach -- codex missing, issue #58, installer from `data/harnesses.json` `setup` (also `attach.next_install`), exit 2. `./pfy start codex` does not run the installer. No fake ready. Credentials/2FA are owner-only and never painted.

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex   # login in the CLI
```

Upstream: [openai/codex](https://github.com/openai/codex)

## Agent

- Entry: `scripts/pfy_attach_usable_220.py` (`--prove` / `--selftest`); board `open_enterable_codex_session` / `start_sidecar("codex")`.
- Callers: HTML+tk Attach; `POST /start id=codex`; `./pfy start codex` payload.
- Invariants: prove models list + smoke before attached paint; SIDECAR_OK includes `codex`; operate-or-FAIL on mode; catalog 70–75 HOLD; do not reopen #76; #198 parked; LIVE_HARD_OFF.
- Issue **#220** only.

## Not yet

- Vendoring Codex into git
- Invented Codex flags
- Other harness adapters
