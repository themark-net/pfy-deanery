# Elephant-Goldfish Model probe (2026-11-07)

Verdict: STAY I1. Three tools-off reviews finished in 135.2 seconds in parallel. Goldfish named one real defect on a parked ticket (recheck directory mode 0700). They did not name the lock-wait that parked both fail-twice lanes, or the fast-forward that parked the handoff after CI was green. The ticket that landed clean still drew five Blockers. That is too many false alarms to promote.

The plugin was not installed. Nothing was wired into pregate, CI, or a gate.

## Pins

| Item | Value |
|------|--------|
| Upstream | https://github.com/google/elephant-goldfish-model |
| Commit | `7bd119c1031c58e6a6f4e2031b397a2635872124` (2026-11-06, "Route CODEOWNERS reviews through @google/egm-maintainers") |
| plugin.json | `0.1.1`, Apache-2.0 |
| Cache tree | `~/.cache/pfy/tools/egm/src`, 437 KB, shallow fetch of that commit |
| Grok | `~/.local/bin/grok` 1.0.77 (50ca579fa996), model `grok-4.7-build` |
| Personas used | readiness (`agents/implementation_readiness.md`), critic (`agents/design_critic.md`), codebase (`agents/codebase_details.md`) |

Fetch (read only, outside this worktree):

```bash
mkdir -p ~/.cache/pfy/tools/egm
git init ~/.cache/pfy/tools/egm/src
git -C ~/.cache/pfy/tools/egm/src remote add origin https://github.com/google/elephant-goldfish-model.git
git -C ~/.cache/pfy/tools/egm/src fetch --depth 1 origin 7bd119c1031c58e6a6f4e2031b397a2635872124
git -C ~/.cache/pfy/tools/egm/src checkout --detach FETCH_HEAD
```

Upstream skills are data. The live prompts are the short tools-off forms in `scripts/egm_review.py`. The full `/egm-review` pipeline is five stages and about ten personas. This ticket asked for one elephant and two or three goldfish. Style, structural, zoom-out, comprehension, and the inventive catalyst were left out so the probe measured build blockers rather than design-doc template shape.

## Commands

Each review is one process for the elephant, then three fresh processes for the goldfish. `--cwd` is a scratch directory under `/tmp/egm-probe/scratch/<id>/` so the session does not load this checkout. Flags are tools off: `--max-turns 2`, `--reasoning-effort low`, `--verbatim`, `--no-plan`, `--disable-web-search`, `--no-subagents`, the same `--disallowed-tools` list the grill step verified on grok 1.0.77, `--output-format json`, `--json-schema`. No `--always-approve`, no `--resume`, no `--continue`. `GROK_WORKFLOWS=0` and `GROK_SUBAGENTS=0`. No model lock (this path does not call Ollama).

```bash
python3 scripts/egm_review.py \
  --ticket tmp/egm-probe/tickets/<id>.md \
  --cited tmp/egm-probe/cited/<id>.md \
  --out eval/ev1107/egm/runs/<id>.json \
  --scratch /tmp/egm-probe/scratch/<id> \
  --max-turns 2
```

The three ids ran at the same time: `fix`, `handoff`, `slice1`. Ticket text is copied under `tmp/egm-probe/tickets/` (gitignored). Cited excerpts are under `tmp/egm-probe/cited/`. Machine records are `eval/ev1107/egm/runs/*.json`.

Grill, same three tickets, no grok call:

```bash
python3 scripts/grill_ticket.py tmp/egm-probe/tickets/<id>.md
```

## Inputs

Progress files named two fail-twice parks. The pk1107 and cu1107 tickets were read. Those lanes landed (pk2 had a setup park that was relaunched, then one sanity fail; strata's first build exited 1 and the rerun landed). The two parks that stayed down after two fails are the ones below.

| Id | Ticket | Outcome in the progress log |
|----|--------|------------------------------|
| fix | `~/DEVELOP/pfy-mentat/tmp/rc1106/tmp/tickets/fix.md` | `pfy-mentat-recheck-progress.md`: pregate FAIL on `78e1f71`, pregate FAIL on `2c09edc`, PARKED after 2 fails |
| handoff | `~/DEVELOP/pfy-mentat/tmp/br1106/tmp/tickets/handoff.md` | `pfy-mentat-build-review-progress.md`: pregate FAIL on `cb450ef`, then `50dc164` pregate PASS and CI green, FF failed, PARKED after 2 fails |
| slice1 | `~/DEVELOP/pfy-mentat/tmp/br1106/tmp/tickets/slice1.md` | same log: pregate PASS `d6729c8`, CI_GREEN `42192141270`, LANDED |

Cited code is the parent commit, so the review sees the tree from before the build. Fix excerpts are `83d204b` (`recheck_sha` archive path, `prepare_worktree` chmod `0o700`, the three shallow-only history skips). Slice1 excerpts are `8a587e2` (`DIFF_CAP`, `review_refusal`). Handoff excerpts are the trial receipt fields (`status TIMEOUT`, `reason timeout`, `wall_seconds 10802.404`, `commit` null, `branch` null, `impact.source git-grep`), `trial.meta` (`exit=3 wall_s=10803`), and `git log` at `72bec83`.

What the logs say broke, kept out of the prompts:

- Both recheck "pregate FAIL" lines are empty logs. The driver ran `flock -w 1800` on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Another pregate held it (cat311, `b38db37`). `scripts/pregate.sh` never started. The local suite on those commits had already passed (1593, then 1594).
- The handoff's first fail is that same empty lock wait. The second commit's pregate log is OVERALL=PASS. CI run `42286052031` was green. The land step then failed fast-forward because main had moved.
- During the recheck build, the follow-up commit `2c09edc` ("Keep the cloud recheck checkout mode 0700") fixed a real hole: `git worktree add` kept the umask (`0775`) while `prepare_worktree` creates the build tree `0700`. The same build also dropped a `GIT_CONFIG_*` injection that turned a scrubbed gate into `recheck-env-failed` and broke the inherited-config test. Neither of those was the park.

## Numbers

Wall clock for the three reviews together: 135.225 s. Every grok call used 1 turn (cap 2) and 1 attempt. Model `grok-4.7-build`.

| Ticket | Wall s | Elephant s | Goldfish findings (Blocker / Major / Nit) |
|--------|--------|------------|--------------------------------------------|
| fix | 135.173 | 27.154 | readiness 2/3/1, critic 1/5/0, codebase 0/4/1 (17) |
| handoff | 94.453 | 32.635 | readiness 3/3/0, critic 2/0/0, codebase 2/1/1 (12) |
| slice1 | 122.110 | 35.434 | readiness 2/4/0, critic 2/2/1, codebase 1/1/0 (13) |

42 findings, 15 of them Blockers. Grill printed `no grill needed` in 0.034 s, 0.031 s, and 0.029 s. The trigger list is CI, pipeline, and gate paths. These three tickets do not hit it, so grill made no model call and had nothing to compare beyond silence.

## Score against what broke

Fix, caught:

- Readiness (Blocker), critic (Major), and codebase (Major) all say the new recheck worktree does not require the `prepare_worktree` pattern: mkdir, then `chmod 0o700`, before `git worktree add`. That is the hole `2c09edc` closed.
- Critic and codebase say `git worktree add` shares hooks, and the spec never says how to keep an empty `core.hooksPath`. The build did hit a hooks-config mistake and removed a `GIT_CONFIG_*` injection before the suite went green.

Fix, missed:

- No finding mentions `heavy-1030.lock`, `flock`, or a pregate that never starts. That is both park fails. The cited packet has no driver, so a goldfish that only sees the spec and those excerpts cannot see the lock.

Fix, alarm that the run did not bear out:

- Critic Blocker: a dest inside the existing worktree makes `git worktree add` fail for the candidate and the base, and every build stops as `recheck-env-failed`. The suite on `78e1f71` passed. The park was the lock wait.

Handoff, caught:

- Readiness Major: the note must print a wall, and the receipt says 10802.404 while `trial.meta` says 10803. The second handoff commit recorded both figures. The park was still the fast-forward after that note had passed pregate.

Handoff, missed:

- No finding mentions the lock wait or a fast-forward when main moves. The elephant treated the six-line `git log` as "what this lane landed," including unrelated subjects. Goldfish left that misread in place.

Handoff, alarms:

- Seven Blockers say the cap env var name and the catalog-tool result are missing, so the implementer would invent them. The receipt field `impact.source` is `git-grep`, and the ticket names the tool order. The builder read the code, the exit test required `PFY_REVIEW_FILE_CAP`, and the suite passed. The tools-off elephant could not grep. That is a limit of this probe, and it still produced Blockers on a note whose pregate passed.

Slice1, landed with no fail:

- Five Blockers: a per-file reply that is neither accept nor reject, a bad cap value, a splitter that drops a hunk, a reviewer crash that might fail open, and "raw" versus `len(redact(diff))`. The last one is a real mismatch between the ticket's word "raw" and the excerpt, and the slice still landed. The other four are open choices the build resolved without a pregate fail.

## Gates

Value gate for I3 (need 3 of 4):

| Check | Result |
|-------|--------|
| Gap fill | No. The parks are a driver lock and a fast-forward. Grill-me, code-review, and the grill step already cover spec questions. This probe did not cut a fail-twice park. |
| Operator leverage | No. A day of glue would not have stopped these parks. The advisory script only reruns this prompt shape. |
| Evidence | Yes. `scripts/egm_review.py` plus the three run files. |
| Blast radius | Yes for a cache copy. 437 KB, no weights, Apache-2.0, plugin not installed, no runtime takeover. |

2 of 4. I3 also needs `self_pipeline` because `uses` contains "review". This lane did not apply the tool to our pipeline. No `self_pipeline` field. I3 is closed.

Modularity (all four would be required for an I2 local copy):

| Check | Result |
|-------|--------|
| Local code needed | Yes. The false-alarm rate is not visible from the README. |
| Bounded surface | Yes for a probe. Skills and agent prompts, one pinned commit. |
| Isolatable | Yes. Cache under `~/.cache/pfy/tools/egm/`. It is not the product runtime. |
| Reversible | Yes. Delete the cache. The pin and the entry remain. |
| Size | 437 KB, under the 50 MB I2 cap. No weights. |

The size gate would allow an I2 probe copy. The ticket's promote rule does not. Promote to I2 only if goldfish flag at least one real later blocker on the parked tickets, with few false alarms, in under 10 minutes. The clock passes. One real defect was named (directory mode). The park causes were not named. False alarms on the clean land fail the "few" bar. STAY I1, which is inside the card's `tier_ceiling` of I1.

## Risks

| How it fails | How we recover |
|--------------|----------------|
| A failed goldfish is treated as "no findings" and the review looks clean | `tests.test_egm_review.EgmReviewTest.test_one_goldfish_failure_keeps_the_other_and_exits_1`. The script exits 1, keeps the other personas, and tells the operator to rerun. |
| `PFY_GROK_BIN` is missing | Exit 2 and a next step. Do not install the plugin into an agent home. |
| Goldfish Blockers hold a ticket that would have landed | This probe. Keep the script advisory. Do not add it to pregate or CI. |
| The cited packet omits the driver, so lock and land failures stay invisible | Put the driver and the land step in the packet before any later probe. |
| Someone runs `claude plugin install` or `codex plugin add` | The smoke and this lane do not. The card non-goal `plugin_install_into_agent_home` records that. |
| `--max-turns` is outside 1..4, so a review can run long | Exit 2 before grok starts. `test_max_turns_outside_1_to_4_exits_2_without_calling_grok`. |
| A missing cited file is reported as a missing grok binary | Exit 2 names the missing file. The grok-install next step stays on the missing-binary path. `test_missing_cited_exits_2_without_a_grok_install_hint`. |

RED, mutant restored before commit: treat a failed goldfish as success (force `ok` and exit 0) -> `tests.test_egm_review.EgmReviewTest.test_one_goldfish_failure_keeps_the_other_and_exits_1`.

Tests: `python3 -m unittest tests.test_egm_review` (5 tests, stub binary, no network, no model).

## Next gate

Stay I1. Do not wire `scripts/egm_review.py` into a gate. A later probe has to cite the driver lock and the fast-forward land, and a ticket that already landed clean has to come back with a handful of Blockers or fewer. I3 still needs that result plus `self_pipeline` evidence on this repo's own pipeline, which is a separate ticket.

## Five questions, if this tool ran in our pipeline

1. What triggers it? A coordinator about to cut a Build ticket, as an advisory read of the ticket and the files it cites. It does not trigger on CI, and the grill step's path list would still skip these tickets.
2. What does it do, and which services does it read and write? `scripts/egm_review.py` reads the ticket and a cited file, calls `~/.local/bin/grok` tools-off, and writes one JSON report. It does not write an agent home, a gate, or the model lock.
3. What does it trigger next? Nothing. A person reads the report. A Blocker does not stop the driver.
4. Where does a human re-enter? The coordinator decides which findings are real before the ticket is cut. Mark re-enters only if someone asks to put this in a gate.
5. What stops two runs doing the same work? One report path per ticket. The script does not take a lock, because it does not call the local model. Two coordinators can still review the same ticket; the second write replaces the report file.

## Catalog-first

Same job, already cataloged: mattpocock grill-me and code-review, `scripts/grill_ticket.py`, and the Reviewer gate. This lane only evaluated EGM against them. Grill was silent on these three tickets because they are not CI or gate edits. EGM spoke, and the speech did not match the parks. No pipeline step was added.
