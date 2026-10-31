# Run log mvp-freshclone-1031

Lane: first-day experience on a fresh clone. Branch `bot/mvp-freshclone-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-freshclone-1031`. Base `origin/bot/mvp-integrate-1031` (tip at launch recorded below). Launch observed `2026-10-31T23:25:38Z`.

LOOP EXIT CARD
════════════════════════════════════════
Goal (success criteria):     A git clone of origin/bot/mvp-integrate-1031 under this worktree tmp/fresh/ is walked using only README, a quickstart the clone actually contains, ./pfy build --help, and the daily card. Every gap is written down. Each gap this lane may own is fixed in a doc or a CLI message, with a behavior or fail/recover test when code changes, then the fixed step is re-run. A small real ./pfy build task runs in a throwaway clone. No --local. No pregate.sh. Real GROK_HOME auth is reused and never printed.
1 Goal met:                  gap list in this log, re-walk notes, and targeted tests for any code change. Not a model claim.
2 Turn cap:                  8 items after the exit card. The walk is item 1. Fixes are the next items. Stop at 8 even if more gaps remain, and list the rest in the handoff.
3 Budget cap:                cloud Grok only. No local model. No --local. One real ./pfy build of a small task. No second cloud build if the first returns a receipt or a clear auth/rate-limit failure.
4 Wall clock:                8 hours from launch (2026-11-01T07:25:38Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Stop new items at 2026-11-01T07:05:38Z so the handoff has 20 minutes. Check before every item.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped.
6 Human interrupt:           user stop. Do not ask questions. Conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive same failure, or the no-progress rule, then stop.
8 External event:            if origin/bot/mvp-freshclone-1031 moves under another writer, stop and record it. If origin/bot/mvp-integrate-1031 moves, the walk stays on the tip fetched at clone time.
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Push only bot/mvp-freshclone-1031.
════════════════════════════════════════

Drop-in exits (binding, same run):

1. Wall cap as in the card above.
2. Lane empty: no item left that fits this lane and these rules.
3. No progress: same failure twice with no new information, or 3 items skipped in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-freshclone-1031.md` are the binding. Decision logged.

Host at launch: MemAvailable about 51.8 GiB. Load 4.75, 4.33, 4.31 on 32 cores. Under the pressure line.

Overview: Mark clones the integration branch and follows only the user-facing docs. This lane does that walk, records every missing step, wrong command, confusing message, unstated assumption, and slow step, then fixes the gaps it is allowed to touch and re-walks those steps.

Phases:

- exits | docs/ops/RUN-LOG-mvp-freshclone-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-freshclone-1031.md | card and decisions exist before the clone | none | lead
- naive-walk | tmp/fresh/ (gitignored clone of origin/bot/mvp-integrate-1031) | every documented step run; gap list appended here | exits | lead
- fixes | docs or scripts/pfy help text, plus a behavior test when code changes | each owned gap closed or recorded as a cross-lane request | naive-walk | lead
- rewalk | same commands as the fixed steps | fixed steps match the new text | fixes | lead
- handoff | docs/ops/HANDOFF-mvp-freshclone-1031.md, this log | final state line, commit, push | all prior | lead

Risks:

- A real ./pfy build spends a cloud call and may print auth errors. Mitigation: one small task, logs under tmp/, never cat auth.json, redact secrets before the run log.
- README, the quickstart, and the daily card are owned by other lanes. Mitigation: do not edit those owned paths. Cross-lane request instead. CLI help is in scope and kept to the build help text because mvp-dogfood-fix-1031 also edits scripts/pfy.
- The fresh clone is not a worktree of this branch, so fixes are re-walked by copying the changed files into the clone or by re-running the command from this worktree against a throwaway target. Mitigation: say which tree each re-walk used.
- Host pressure. Mitigation: nice -n 19 on tests. No full discover. No pregate unless the runner is idle at the end.
- Em or en dashes in new prose. Mitigation: ASCII hyphens only.

Items:

(none yet)

state: exits written | tests: none yet | files: 2 | err: none
