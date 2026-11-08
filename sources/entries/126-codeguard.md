### Entry 126: Project CodeGuard (CoSAI) — model-agnostic secure-coding rules for coding agents, plus a SARIF reviewer agent

- **URL**: https://github.com/cosai-oasis/project-codeguard (**CC-BY-4.0**, Markdown rules plus Python translators; about 353 stars at this read; checked at main commit `41160d54980b`, 2026-10-12, two commits after the v1.5.0 tag (tag commit `5bfe8f9`)). Supersedes https://github.com/project-codeguard/rules (still live) after Cisco donated the project to the Coalition for Secure AI.
- **Date**: 2026-10-17 (dev-skills investigation)
- **Source / Poster**: web search during the dev-skills investigation; Cisco announcement https://blogs.cisco.com/ai/announcing-new-framework-securing-ai-generated-code
- **Summary / Key Claims** (upstream README and site): secure-by-default rules used at plan, generate and review time. 23 core rules (crypto, input validation and injection, authn/authz, sessions, file handling and uploads, logging, data storage, privacy, supply chain, XML and serialization, MCP security, safe C functions, hardcoded credentials) plus 85 OWASP-cheat-sheet rules. Translators emit `.cursor/rules`, `.agents/rules`, OpenCode, Copilot and a Claude Code plugin. A read-only `codeguard-reviewer` agent scans a repo against the rules and writes SARIF 2.1.0.
- **Why it matters here**: a cheap, well-sourced baseline for the Reviewer bot and Build on web or service code. **Low fit for leasegrid's failure classes**: a grep of all rules found nothing on temp-file IPC, PID locks, pid reuse or AF_UNIX, so it does not replace a pfy systems-safety skill. Possibly borrow `codeguard-0-logging`, `codeguard-0-xml-and-serialization` and `codeguard-1-hardcoded-credentials` wording.
- **Fit on nimo**: plain files. A pinned release zip's rules under `~/DEVELOP/pfy-mentat/tmp/codeguard/`. The installer routes write into `.cursor/`, `.claude/` or repo rule dirs, so they are not used on nimo.
- **Verified on the Grok Bot box** (shallow clone in `/workspace`): 23 core plus 85 OWASP rule files; `skills/codeguard/SKILL.md` frontmatter valid (`name: codeguard`, 218-char description); the reviewer agent source is `sources/agents/codeguard-reviewer/AGENT.md`. Not run against a repo.
- **Extracted Repos / Tools**: https://github.com/cosai-oasis/project-codeguard · https://project-codeguard.org/getting-started/ · https://project-codeguard.org/codeguard-reviewer/
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: None in this slice (docs-only entry).
- **Non-goals**: No plugin install, no rules dropped into any product repo, no always-on rules in Build.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| False confidence | Rules are web-centric; desktop/systems bugs pass | Keep it a Reviewer reference; systems rules come from the pfy skill |
| Context cost | Always-on rules eat local-model context | Glob-scoped rules only, or reviewer-time only |
| Attribution | Rule text reused without credit | CC-BY-4.0: credit CoSAI and link the release when quoting |
| Two live repos | The superseded `project-codeguard/rules` repo drifts from the CoSAI one | Use the cosai-oasis URL and a pinned commit or tag |

- **Status**: Stayed I0 after the 2026-11-07 evq1107 probe (pin `41160d54980bab0618165485ade3cfd2ade93288`, pyproject `1.5.0`). Offline prefix pass caught the planted `ghp_` token and missed `shell=True`, a Python secret log, and a fetched-skill prompt injection. SARIF reviewer not run (host-agent instructions, no model). Not an H2 install gate. Not wired into a gate. No Feature GO.
