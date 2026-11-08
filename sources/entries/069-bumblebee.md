### Entry 069: Bumblebee — Read-only Developer Endpoint Scanner (MCP + Supply-Chain)

- **URL**: https://x.com/i/status/2079882269007937996
- **Date**: 2026-07-22
- **Poster**: Harman (@itsharmanjot)
- **Summary / Key Claims**: Perplexity open-sourced Bumblebee (first stable May 2026). Read-only Go scanner for on-disk package, extension, and developer-tool metadata (npm/pnpm/Yarn/Bun, PyPI, Go, RubyGems, Composer, IDE/browser extensions, **MCP host configs**). Answers "which machines show exposure to this known compromise right now?" Zero non-stdlib deps, NDJSON output, three profiles (baseline/project/deep). Designed for supply-chain incident response and MCP security workflows — the gap most agent setups currently ignore.
- **Extracted Repos / Tools**: https://github.com/perplexityai/bumblebee (Apache 2.0, ~2.1k stars)
- **TOOLS.md Link**: New row under **Tool Calling & Function Infrastructure** (or Security / MCP). Complements write-guard-mcp and destructive_command_guard. High pipeline value for any Grok CLI / agent-cage / MCP-heavy workstation.
- **Notes**: Stage 0 pass (concrete tool, local, open, agent-relevant). Strongest of the five in the source post for this catalog. Directly addresses MCP config trust model that is currently broken in most local agent setups. Recommend: catalog + evaluate for smoke in agent-cage (read-only, low risk). Pair with Hermes Bumblebee bridge patterns if present. Priority for T-004x security hardening track.
- **Status**: ev1107 PROMOTE I2. Pin v0.1.2 (cc57710eeaf685e7b89924a36c8583cad0a378fe). Advisory script scripts/pfy_mcp_scan.py. Not a gate.
