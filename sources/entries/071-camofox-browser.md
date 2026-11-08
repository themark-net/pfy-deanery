### Entry 071: Camofox Browser — Anti-Detection Browser Server for AI Agents

- **URL**: https://x.com/i/status/2079882269007937996
- **Date**: 2026-07-22
- **Poster**: Harman (@itsharmanjot)
- **Summary / Key Claims**: Camofox Browser is the exact engine running inside a real production product (jo / askjo.ai), not a demo. Wraps Camoufox (Firefox fork with C++-level fingerprint spoofing) in a REST API designed for agents: accessibility snapshots, stable element refs, multi-session, MCP variants. Bypasses Cloudflare/Google bot detection where Playwright stealth plugins fail. Production-proven.
- **Extracted Repos / Tools**: Primary: https://github.com/jo-inc/camofox-browser (~6k stars). Related: redf0x1/camofox-browser, redf0x1/camofox-mcp (MCP server with 47 tools).
- **TOOLS.md Link**: New row under **Tool Calling & Function Infrastructure** or Coding & Dev Agents (browser tool). Complements any agent that needs real-web access without immediate blocks. High synergy with Grok CLI + agent-cage for web research / form / extraction workflows.
- **Notes**: Stage 0 pass. Production pedigree is the differentiator the source post emphasizes. Local-first path exists (npm / Docker). MCP surface makes it immediately usable by Claude/Cursor/Grok-style agents. Recommend: catalog + evaluate Docker smoke inside agent-cage; consider as default stealth browser option for agent web tools. Watch for credential / session isolation practices.
- **Status**: STAY I1 reference (read 2026-11-07). Pin `39c82094013480b373df6600d44c7f036f58356e` is `@askjo/camofox-browser@1.18.1` (tag `v1.18.1`), MIT. No install, no script, no code copy. Gap W stays the Tauri operator window. Catalog 70-75 stays HOLD. Receipt: `eval/evq1107/camofox-browser/REPORT.md`. No Feature GO.
