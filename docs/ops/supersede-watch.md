# Supersede watch: no reinvention

**Owner rule (Mark, 2026-11-08):** pfy-mentat does not reinvent. If another project does the full suite better, we stop work and use theirs.

## The suite

pfy-mentat is only worth building while no one else does all four parts together:

| Part | Means |
|------|-------|
| track | Watches outside sources (X first, then GitHub and feeds) for new tools on its own |
| catalog | One deduped catalog, a record and stage card per tool |
| evaluate | Scores each tool's claims against a rubric of improvement vectors, with staged evidence I0-I4 |
| integrate | Wires the tool in for real, proves it with a run on main, local-first |

Harnesses (Grok Build, OpenCode, Hermes, AgenC), skill packs and skill registries come close on one or two parts. They are things we catalog and adopt, not reasons to stop.

## Rules

1. `data/supersede-watchlist.json` lists each near-match: repo, coverage per part (none, partial, full), verdict (`replace_us`, `adopt_part`, `watch`), reason, last check date.
2. A project covering two or more parts, partial counting, is a **supersede candidate**. Each recheck reads its README and changelog again, not just the star count.
3. A project at full on all four parts makes `scripts/supersede_check.py` fail with STOP. That goes to Mark as a real decision: stop and adopt, adopt parts, or keep going with a written reason. Never silently.
4. `replace_us` needs all four parts full. Lower verdicts can adopt a part through the normal catalog path (stage card, I-stages).
5. Intake and eval: when a new tool covers two or more parts, tag it `#supersede-candidate` in `sources/` and TOOLS.md and add it to the watchlist. `python3 scripts/supersede_check.py --parts track,catalog` gives the answer.
6. Recheck every 30 days (`recheck_days`), or right away when a watched project ships a release that adds a part. Stale entries show in `supersede_check.py` output.

## Last check (2026-11-08)

No project covers all four. The closest are Flux by Nairon-AI (X radar, deduped recommendations, install and verify; dormant since May, recommendations repo gone) and X Patrol Deploy (X feed triage and auto-install for OpenClaw). Neither scores improvement vectors or proves integration with a run. Hermes improves from its own sessions, not from outside tools. Sandcastle, Pocock's skills, OpenCode and AgenC are parts we already use or watch. Details are in the watchlist.
