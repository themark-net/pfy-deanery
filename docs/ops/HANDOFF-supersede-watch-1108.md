# Handoff: supersede watch (2026-11-08)

## Done
- Owner rule "no reinvention, stop and adopt if someone does the full suite better" is in AGENTS.md (North star), docs/DESIGN.md section 1 and docs/ops/supersede-watch.md.
- `data/supersede-watchlist.json`: 10 near-matches with coverage of track, catalog, evaluate, integrate, verdict, reason, last check.
- `scripts/supersede_check.py`: validates the watchlist, lists supersede candidates (2+ parts), lists stale entries, fails with STOP if any project covers all four parts in full without a replace_us verdict. `--parts` is the intake hook.
- Suite overlap is a Phase 0 step in docs/evaluation-framework.md.
- Tests: tests/test_supersede_check.py (6 behavior tests: committed file passes, full-suite forces STOP, bad replace_us fails, stale is reported, bad data fails, intake hook).

## Verdict on 2026-11-08
Nothing replaces pfy-mentat. Closest: Flux (Nairon-AI, dormant) and X Patrol Deploy (tiny). Adopt-part candidates: Decision Hub eval cases and security grade, Argusic does-it-run verdicts as I2 prior evidence.

## Not done, for the catalog loop owner
- Hook for the catalog loop (not edited here, another worker owns those files): each hourly run can call `python3 scripts/supersede_check.py`; on exit 1 put a STOP decision in the approval queue; when it prints `stale:` lines, queue one recheck lane (web, GitHub and X reads, no installs) that updates coverage and last_checked.
- Intake does not tag `#supersede-candidate` on its own yet. Wire `--parts` into the intake/dedupe skill when that lands.
- Sandcastle has no stage card even though sandcastle-grok runs our lanes. Add one through normal intake.
- AgenC has no sources/entries file; the stage card is the record.
