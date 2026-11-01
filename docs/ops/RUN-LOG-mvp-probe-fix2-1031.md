# RUN LOG mvp-probe-fix2-1031

Launch: 2026-11-01T00:35:26Z
Wall cap: 2026-11-01T08:15:26Z for new items (8h from launch is 2026-11-01T08:35:26Z; leave 20 minutes). Sunday 2026-11-02T02:00Z is later, so the 8h cap binds.
Base: `origin/bot/mvp3-review-retry` at `d2521b5` (unchanged after fetch).
Branch: `bot/mvp-probe-fix2-1031`
HEAD at launch: `0486712` (lane drop-in only).
Evidence (read only): `/home/mark/DEVELOP/pfy-mentat/tmp/mvp3/tmp/evidence/mvp3-6664713`

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): every Tester probe from the 6664713 FAIL, plus the five named variants, has a recorded result at d2521b5. Each probe that passes the tip wrongly has a failing behavior test and the smallest fix on this branch, then the probe fails closed.
1 Goal met:                  probe table in the handoff, each FINDING commit green on its targeted test
2 Turn cap:                  8 fix iterations on one finding; a new finding resets that count
3 Budget cap:                cloud Grok only; no local model; no spend beyond this session
4 Wall clock:                2026-11-01T08:15:26Z new-item stop; handoff by 2026-11-01T08:35:26Z
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. No merge, no PR, no force push. Push only this bot/ branch.
7 Error threshold:           3 consecutive same test failures, then stop that area
8 External event:            stop if origin/bot/mvp3-review-retry moves and the probe target is no longer d2521b5; re-read the tip first
Loop type:                   goal
Human gate:                  push the branch only; Tester plus Reviewer for runtime changes
```

Drop-in exits (also checked before every item): wall cap, lane empty, no progress, host pressure (MemAvailable under 16 GiB, or load over 64 for 5 minutes), red base (record and skip that area, do not stop the lane).

## Orchestrator plan

Overview: Re-run the 6664713 Tester probes against the mvp3 fix2 tip in a scratch repo under this worktree, then run the five named variants (hardlink, symlink to a directory, rename plus edit, NFC vs NFD, gate mode bits). A wrong pass becomes a behavior test and the smallest fix on this branch only.

Phases:
- exits | docs/ops/RUN-LOG-mvp-probe-fix2-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-probe-fix2-1031.md | exit card committed | none | general
- reprobe | tmp/probe (gitignored) | original probes judged at the tip | exits | general
- variants | tmp/probe | five variant families judged | reprobe | general
- fixes | scripts/pfy_build_local.py, tests/test_pfy_build_local.py, tests/test_pfy_build_local_review.py | each FINDING fails closed | variants | general
- handoff | docs/ops/HANDOFF-mvp-probe-fix2-1031.md | probe table and state line | fixes | general

Risks:
- A probe that never builds the filesystem object looks like a hold. The stub records whether the link or mode change was created.
- Host pressure pauses the lane. Check mem and load before each fix.
- Do not edit other worktrees or push `bot/mvp3-review-retry`.

## Items

- exits | 8ce94e3 | none | exit card pushed
- reprobe | scratch tmp/probe/results.jsonl | 29 CLI probes at d2521b5 | 4 judge flags, 2 real findings (mode bit, hardlink). Holds: e5c, g1, g2, s7 rename, s7 rename+edit, s7 across dir, s7 old name unlisted, s7 swap, s8 NFC, s8 NFD, s8 emoji, s8 unicode dir, s8 NFC-allow vs NFD file, symlink-to-dir, relative symlink, replace src, M10 variants, M17 retries 5, gate delete, gate extra file, mode 0600. s7 low-similarity and NFC+NFD pair were judge/host false flags (decisions 6 and 7).
- bx1-mode | 29da017 | nice python3 -m unittest tests.test_pfy_build_local_review (38 OK in 84.393s on the tree that also has the hardlink tests) | pass
- bx2-hardlink | 915edf0 | same module, 38 OK in 84.393s; the three hardlink tests plus the mode and symlink neighbors were also OK in 4.904s | pass

## Progress

Host at the hardlink commit: MemAvailable about 69 GiB, load about 3.4 on 32 cores. origin/bot/mvp3-review-retry still d2521b5.
Pregate not run: the lane drop-in says do not run scripts/pregate.sh.
state: lane empty | two findings fixed (29da017 mode bit, 915edf0 hardlink); named probes have no remaining wrong pass | tests: review module 38 OK | err: none
