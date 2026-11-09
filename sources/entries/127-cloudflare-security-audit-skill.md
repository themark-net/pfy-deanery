### Entry 127: Cloudflare security-audit skill — six-phase agent audit with adversarial verifiers and schema-checked findings

- **URL**: https://github.com/cloudflare/security-audit-skill (MIT, Markdown skill plus zero-dependency Node validators; about 30,641 stars at this read; checked at commit `c1c8a8c14710`, 2026-09-14)
- **Date**: 2026-10-17 (dev-skills investigation)
- **Source / Poster**: @tom_doerr, https://x.com/tom_doerr/status/2107170336227655985 (also @JeremyCMorgan, https://x.com/JeremyCMorgan/status/2103786859822260352)
- **Summary / Key Claims** (upstream README and `SKILL.md`): turns a coding agent into an auditor in six phases: reconnaissance (architecture, trust boundaries, `coverage-ledger.json`), coverage-led hunting by isolated parallel agents, validation by a fresh agent that tries to disprove each candidate, structured `findings.json` checked against `report-schema.json`, independent per-finding re-verification, and a target-neutral `REPORT.md`. Has a lighter "guidance mode" for focused questions. Domain companions include `DESKTOP-MOBILE-AND-LOCAL-IPC.md`, `MEMORY-SAFETY-AND-BINARY.md`, `SUPPLY-CHAIN-AND-RELEASE.md` and `RESOURCE-EXHAUSTION-AND-AVAILABILITY.md`.
- **Why it matters here**: (1) its **local-IPC companion** covers IPC peer authentication, world-writable socket paths, reused handles and local-file TOCTOU, which is exactly the leasegrid `--join` `/tmp` socket class (it does not cover PID locks or pid reuse). That makes it a good Reviewer reference now. (2) The full audit is a candidate pre-release deep review for desktop apps (leasegrid-c, pfy GUI). The "finder never verifies its own finding" rule matches our Tester/Reviewer split.
- **Fit on nimo**: files under `~/DEVELOP/pfy-mentat/tmp/security-audit-skill/`; validators need Node.js. Full mode needs an agent that can run parallel sub-agents (Grok Build `/orchestrate` or Cursor). Guidance mode works in any harness. Don't use `npx skills add` (it writes host skill dirs).
- **Verified on the Grok Bot box** (shallow clone, Node 20.19.2): `node --test validate-findings.test.cjs validate-coverage-ledger.test.cjs` gave 65/65 pass; `SKILL.md` frontmatter valid (`name: security-audit`). Not run as an audit.
- **Extracted Repos / Tools**: https://github.com/cloudflare/security-audit-skill · https://github.com/cloudflare/security-audit-skill/blob/main/skills/security-audit/DESKTOP-MOBILE-AND-LOCAL-IPC.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: None committed in this slice. A future smoke could run the two validator test files under a temp HOME (stdlib Node only).
- **Non-goals**: No `npx skills add`, no full audit of any repo yet, no live probing (upstream also forbids it).
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Cost and time | Full mode spawns 8–12+ agents | Guidance mode by default; full audit only before a release, on a throwaway worktree |
| Local model can't fan out | Hunters/validators collapse into one context | Run full mode in Grok Build or Cursor; local models only for guidance |
| Noise in gates | Unverified candidates reach a PR | Gate only on `confirmed` records; `needs_validation` goes to the handoff |
| Upstream churn | Phase files or schema change | Pin the commit; the validator tests must pass on the pin |

- **Status**: STAY I0 (2026-11-07 nimo). Pin `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` is installed under the tool cache. Upstream validator tests 65/65. Schema gate blocked 0/1 planted skill hazards. Not an H2 install gate. See `ops:eval/evq1107/cloudflare-security-audit-skill/REPORT.md`.
