### Entry 105: anti-slop — SKILL.md rule packs that filter generic AI UI, copy, and code comments

- **URL**: https://github.com/miqdadbadjuber/anti-slop (MIT, Markdown skill folders plus a small Node installer CLI, about 5,595 stars at this read, v3.2.20, checked at commit `388cbe3b6c37`)
- **Date**: 2026-10-09 (daily X intake)
- **Source / Poster**: @tom_doerr, https://x.com/tom_doerr/status/2108404495306694915
- **Summary / Key Claims** (upstream README): "A filter, not a style guide." 38 mandatory rules (R-01 to R-38) in three tiers (Hard Gate, Purpose-Gate, Quality Locks), a "Liveliness Toolkit", and a mandatory PASS/FAIL Delivery Gate report before anything ships. Six skills, one per concern: `antislop` (core, always loaded), `antislop-ui`, `antislop-copywriting`, `antislop-human` (contrast, keyboard, focus; includes a Python contrast checker and a contrast MCP script), `antislop-layoutmobile`, `antislop-code` (remove generic AI comments, never touch the code). Two modes: During (guide the build) and After (numbered audit findings, you approve fixes). Direction is supposed to come from your own `DESIGN.md`. Installs via `npx antislop-ai`, `npx skills add`, per-harness plugins, or the single `antislop.md` file.
- **Fit on nimo**: Plain files; no GPU, no model, no service. A clone under `~/DEVELOP/pfy-mentat/tmp/anti-slop` is enough to read or point a harness at. The installer writes into harness skill folders and `~/.config/antislop/settings.json`, which are outside `~/DEVELOP`, so it is not used.
- **Verified on the Grok Bot box** (shallow clone in `/tmp`): all six `skills/*/SKILL.md` open with frontmatter whose `name` is lowercase-hyphen and equals its folder, with a non-empty `description` under 1024 chars (each also sets `allowed-tools`). Upstream's own `node scripts/check-repo.mjs` passed 13/13 checks (manifests, rule/gate cross-references, frontmatter, version agreement). Not verified: whether the rules actually improve output from our models; that needs a with/without run. The smoke below PASSed there.
- **Why it matters here**: Directly usable by the Design Bot and Reviewer lanes. Design Bot could load `antislop` + `antislop-ui` while building GUI work, and Reviewer could run the After-mode audit (or its Delivery Gate) as a checklist on GUI and docs PRs. `antislop-copywriting` and `antislop-code` overlap our own handoff-doc and comment hygiene rules, so they are a cheap source of named patterns to borrow.
- **Extracted Repos / Tools**: https://github.com/miqdadbadjuber/anti-slop · https://skills.sh/miqdadbadjuber/anti-slop · https://github.com/miqdadbadjuber/anti-slop/blob/main/GUIDE.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_103_105.py --entry antislop`. Uses `$ANTISLOP_DIR`, then `~/DEVELOP/pfy-mentat/tmp/anti-slop`. Exits 2 when there's no clone. First checks that its validator rejects two synthetic bad skills, then validates every `skills/*/SKILL.md` and requires the core `antislop` skill. FAILs on any invalid frontmatter. Receipt: `pipelines/smoke/antislop/latest.json`.
- **Non-goals**: No `npx antislop-ai`, no plugin installs, no global settings file, no copying skills into pfy-mentat's skill packs yet (those stay pfy-owned).
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Rule bloat | Core skill is long (`antislop.md` alone is about 57 KB) and eats context on small local models | Load only the core + one concern skill; measure tokens before wiring into a lane |
| Taste conflicts | Rules fight our own design direction or doc conventions | Upstream says direction comes from `DESIGN.md`; keep ours authoritative and treat antislop as a filter only |
| Every-session prompt | Default asks During/After each session, which stalls unattended runs | Pin the mode in the lane prompt; don't use the global settings file |
| Upstream churn | Skill names or frontmatter change | Smoke FAILs on frontmatter; pin the checked commit |

- **Status**: STAY I0 (eval/evq1107/anti-slop/VERDICT, 2026-11-07). Pin `388cbe3b6c37d5175b9f460015bb092ef9e34894` is v3.2.20, one commit after tag v3.2.20. Not installed into a harness.
