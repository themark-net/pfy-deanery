# Module: Claude Code adapter

**Purpose:** Exec `claude` from `./pfy start claude` / `./pfy start claude-code`. Inference via `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector when ready (`OPENAI_BASE_URL` defaults to that). Do not invent Claude-specific flags. Optional skills-external / claude-unified-agents path is documentation only; this adapter does not vendor Claude.

## Entry

```bash
./pfy harness use claude-code
./pfy start claude
./pfy start claude-code
python3 scripts/pfy-board.py --start claude
python3 scripts/pfy_attach_usable_221.py --prove "$LOCAL_OPENAI_BASE_URL"
python3 scripts/pfy_attach_usable_221.py --selftest
```

Detect: `claude` on PATH (`which_bin` looks for `claude`). `claude-code` is a SIDECAR_OK alias of `claude`.

**Attach usable (#221):** HTML+tk **Attach claude** (and `python3 scripts/pfy-board.py --start claude`) re-probes FreeToken-first (`:1919`), sets child `LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL` to the live detect base, then proves models list + one smoke (`pfy_attach_usable_221.prove_developer_usable`, same bar as OpenCode #193 / Hermes #196 / Grok #202 / Codex #220) before `ok:True` / READY / “attached”. Failures: `usable:false`, session/attach state cleared, FAIL + next (`Launch env or ./pfy up`). Missing Claude: FAIL + the registry installer `curl -fsSL https://claude.ai/install.sh | bash` (never a silent stub success). No credentials in paint/logs. Loop paints `attached=claude` plus session reach and `using: <mode>`. One attach at a time. No Env nav tab.

CLI `./pfy start claude` / `./pfy start claude-code` uses the same honesty: no live engine → FAIL + next (does not exec); prove (`python3 scripts/pfy_attach_usable_221.py --prove $LOCAL_OPENAI_BASE_URL`) must pass before exec. Inspect equivalent: `./pfy models` (list) + Test model / `--prove` (smoke).

**Attach mode (#208 / #213 / #215):** `bare` hands off prompt/env. `orchestration` starts a multi-step local loop (`/agent-loops` + prove + monitor evidence). `code-graph` needs Axon CLI (`AXON_BIN`); MCP-only is unwired for Claude → FAIL + `pip install axoniq` / Attach grok or opencode. [attach-mode.md](../ops/attach-mode.md) · [code-graph.md](code-graph.md).

Missing binary: FAIL attach -- claude missing, issue #57, installer from `data/harnesses.json` `setup` (also `attach.next_install`), exit 2. `./pfy start claude` does not run the installer. No fake ready. Credentials/2FA are owner-only and never painted.

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude   # login in the CLI
```

Official docs: [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Agent

- Entry: `scripts/pfy_attach_usable_221.py` (`--prove` / `--selftest`); board `open_enterable_claude_session` / `start_sidecar("claude")` (`claude-code` alias).
- Callers: HTML+tk Attach; `POST /start id=claude`; `./pfy start claude` / `claude-code` payload.
- Invariants: prove models list + smoke before attached paint; SIDECAR_OK includes `claude` and `claude-code`; operate-or-FAIL on mode; catalog 70–75 HOLD; do not reopen #76; #198 parked; LIVE_HARD_OFF.
- Issue **#221** only.

## Not yet

- Vendoring Claude into git
- Invented Anthropic/Claude env flags
- Other harness adapters
