# RUN-LOG mvp-timeoutfix-1031

Lane: cloud-runner findings from late dogfood (wave 5).
Branch: `bot/mvp-timeoutfix-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-timeoutfix-1031`
Base: `origin/bot/mvp-cloudfix-1031` (merge `origin/bot/mvp-integrate-1031` first; merge cloudfix again before each push).
Launch: 2026-11-01T00:00:55Z (2026-10-31 17:00:55 PT).
Binding wall: 2026-11-01T08:00:55Z (8h from launch). Sunday 2026-11-02T02:00Z is later, so the 8h cap binds.
Handoff buffer: stop new items at 2026-11-01T07:40:55Z.
Host at launch: MemAvailable 75982500 kB (~72 GiB), load 3.03 / 4.88 / 5.86, 32 cores. Under pressure limits.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     dogfood2 row 07 review-reject no longer ends as TIMEOUT; receipt reason and recovery match the outcome; time budget holds. Every cloud-runner finding in gom-dogfood wave 5, selfhost2, and dogfood2 that is not already fixed on origin/bot/mvp-cloudfix-1031 is fixed or logged skipped, each with a behavior or fail/recover test. Poll those three branches until 60 quiet minutes.
1 Goal met:                  targeted unittest modules green for each code change; run log item lines; handoff written
2 Turn cap:                  8 code items, then handoff. Polls do not count as code turns.
3 Budget cap:                cloud Grok session only. No local model. No --local. No spend beyond this session.
4 Wall clock:                2026-11-01T08:00:55Z, or 2026-11-02T02:00Z, whichever first. Leave 20 minutes for the handoff.
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. Do not ask. Conservative decision logged, then continue.
7 Error threshold:           3 consecutive same test or merge failures, then stop
8 External event:            a finding already fixed on origin/bot/mvp-cloudfix-1031 or origin/main is skipped, not reimplemented
Loop type:                   goal, with a 20-minute time poll of the three dogfood branches
Human gate:                  no merge to main, no PR, no tags. Push only bot/mvp-timeoutfix-1031.
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-timeoutfix-1031.md` are the binding. Decision logged.

## Phases

Overview: Merge the integrate tip, confirm why a review reject became a cloud TIMEOUT (exit 3, gate -15), fix receipt reason and recovery inside the time budget, then take every still-open cloud-runner finding from the three late dogfood branches. One function per change on `scripts/pfy_build_cloud.py`. Merge cloudfix before each push. Poll every 20 minutes. Stop after 60 quiet minutes or a wall exit.

- exits | docs/ops/RUN-LOG-mvp-timeoutfix-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-timeoutfix-1031.md | exit card on the branch | none | general
- merge-integrate | merge only | `origin/bot/mvp-integrate-1031` merged, never rebased | exits | general
- row07-timeout | scripts/pfy_build_cloud.py (one function) plus its behavior test | review-rejected does not surface as TIMEOUT; receipt reason and recovery are right; time budget respected | merge-integrate | investigate then general
- dogfood-findings | same cloud runner file, one function per finding, plus behavior tests | each cloud-runner finding from gom-dogfood wave 5, selfhost2, and dogfood2 is fixed or recorded as already on cloudfix | row07-timeout | general
- poll | read-only fetch of the three branches | 60 minutes with no new cloud-runner finding, or wall cap | dogfood-findings | general
- handoff | docs/ops/HANDOFF-mvp-timeoutfix-1031.md and this log | state line and handoff pushed | any exit | general

Risks:
- Live cloudfix lane edits `scripts/pfy_build_cloud.py`. Mitigation: one function per change, merge `origin/bot/mvp-cloudfix-1031` before each push, abort the push on a conflict I cannot resolve inside that one function.
- Integrate pass 3 may still be moving. Mitigation: merge the tip that fetch returns; do not rebase; if the merge conflicts outside this lane's files, record a cross-lane request and keep the conflict out of product code I do not own.
- A fix that needs a new architecture decision. Mitigation: OQ draft in the handoff, skip the item.
- Sub-agents on this worktree would collide on the hot file. Mitigation: lead does the code in this worktree. `project-map` may write only `.project-map/`.

## Item log

Format: `item | commit | tests | result`

(none yet)
