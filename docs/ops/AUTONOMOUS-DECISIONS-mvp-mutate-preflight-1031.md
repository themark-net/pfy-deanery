# Autonomous decisions: mvp-mutate-preflight-1031

1. 2026-10-31T22:38:45Z | Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: bind the loop to the drop-in exit list, the exit card in `docs/ops/RUN-LOG-mvp-mutate-preflight-1031.md`, and `docs/ops/HANDOFF-mvp-mutate-preflight-1031.md`, and follow `prefer-behavior-and-fail-recover-tests`. Alternative: stop and ask. Why: the drop-in says not to ask, and it already names the exits and the handoff path.

2. 2026-10-31T22:38:45Z | Choice: the lead implements this lane in this worktree. Spawn only the project-map agent, which writes `.project-map/` (gitignored). Alternative: spawn implementation agents in more worktrees under `tmp/`. Why: the drop-in forbids any other worktree under `tmp/` and a second writer on this branch would race the required push. The mutation harness is one workstream.

3. 2026-10-31T22:38:45Z | Choice: do not edit `pfylib/build_preflight.py`, `tests/test_build_preflight.py`, `eval/mvp-1031/check_receipt.py`, or `tests/test_mvp_1031_receipt.py`. Add `eval/mutation-1031/preflight/` and `tests/test_mut_preflight_*.py`. Alternative: extend the round-1 test modules. Why: the plan matrix gives those files to other lanes. The drop-in says to use the cloud mutation method, which added a new harness and a new survivor-test module.

4. 2026-10-31T22:38:45Z | Choice: one harness scores both files. Each mutant names its target. `--baseline-only` runs `tests.test_build_preflight` and `tests.test_mvp_1031_receipt`. The after round also runs `tests.test_mut_preflight_*` except the harness. Alternative: two harnesses. Why: the cloud runner is one script, and the suites are fast enough to run together.

5. 2026-10-31T22:38:45Z | Choice: include one equivalent mutant (`rc == 0 or rc == 0.0`, which cannot change a real exit code because `0.0 == 0`). Record it as equivalent if it survives. Do not add a test that passes on both versions. Alternative: drop it to force a zero-survivor after count. Why: the drop-in asks for an equivalence record when a survivor is not a real gap.

6. 2026-10-31T22:38:45Z | Choice: do not run `scripts/pregate.sh`. Alternative: run it once at the end if the GitHub runner is idle. Why: the lane header says the operator runs it. The later "at most once" line is a ceiling. Handoff will say pregate was not run.

7. 2026-10-31T22:52:00Z | Choice: add a second mutant pass (P10, R13-R20) for branches the first 18 did not touch: 429 inside a token, a JSON array, a commit suffix, an uppercase commit, a review string, usage, non-utf8 bytes, schema case, and a non-string gate. Alternative: stop at 18 once those survivors were killed. Why: the lane says to keep taking the next gap that fits, and these checks still accept a bad receipt or mis-classify 429 under the product suites. R20 stays alive if the only gate test is an empty string.

8. 2026-10-31T23:00:00Z | Choice: stop the catalog at 27 mutants. P9 stays as the one equivalent survivor. Alternative: keep adding narrower mutants of the same two functions. Why: the drop-in DoD is met (at least 15 meaningful mutants, every other survivor killed, before and after counts published). The product files belong to other lanes. Another pass would repeat the same method without a new gap.
