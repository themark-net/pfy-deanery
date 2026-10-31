# Autonomous decisions pfy-followups-1030

Run A on `bot/pfy-followups-1030`. No questions asked. One line per decision.

1. Choice: the lead executes every item in this worktree, in order, and does not spawn implementation sub-agents. Alternatives: parallel sub-agents on `build/<phase>` worktrees, or shared-checkout sub-agents. Why: the request forbids other worktrees, requires a push of this branch after every item, and the run log, TODO, and handoff are shared files.

2. Choice: follow `repo-handoff-doc-required` and `write-loop-exits-first` as the drop-in already states them (handoff doc on every exit; exit card in the run log before item work) plus `.grok/skills/agent-loops`. Alternatives: block until those skill files appear. Why: no `SKILL.md` with either name is in this checkout or `~/.grok/skills`. `prefer-behavior-and-fail-recover-tests` is present and is followed.

3. Choice: item 1 (MVP-2 reviewer follow-ups) gets prose edits only, with no new test module. Alternatives: a string-match unit test over the handoff. Why: that test would restate the prose and is the tautological kind the behavior skill forbids. Docs-only changes have no code path to fail.

4. Choice: add a `Known gaps` section to `docs/ops/HANDOFF-mvp2-trial.md` for the prove-red receipt gap. Alternatives: bury the gap in the existing Commands section only. Why: the reviewer named "Known gaps" and the file had no such section.

5. Choice: the required `/proc` and `/dev/shm` check runs before `bwrap_ok`. Alternatives: check bwrap first, or only add the flags and let bwrap fail. Why: a missing mount must exit 2 with the bind reason on a host that also has no bwrap, and the existing no-bwrap test still sees the bwrap reason when the mounts exist. There is no unsandboxed path.

6. Choice: the writable real HOME is an `extra_binds` argument that `main()` never passes. The in-process test passes it. Alternatives: keep `PFY_SMOKE_REAL_HOME_BIND`, or drop the real-HOME test. Why: the request forbids a production env hook, and the test must still observe a real write. Entry 148 keeps its own hook; this item did not require a shared change.

7. Choice: `test_version_pin_exit_2` skips without bwrap (`needs_bwrap`) and asserts the pin reason. Alternatives: check the version outside bwrap so GitHub runs the assertion. Why: the probe runs inside bwrap. An exit-code-only assertion was passing on GitHub for the bwrap reason.

8. Choice: the bare checked-at date becomes `2026-10-25T04:41:28Z`, the public GitHub committer timestamp for `84582fb`. Alternatives: leave it bare, or label it PT. Why: the Date line already has PT. The parenthetical date had no zone. The API value is the zone we can actually cite.

9. Choice: the mutation table is the 13 mutants this run applied, with the killing test names taken from that run (13 killed, 0 survived). Alternatives: keep the old 8-row "all killed" sentence. Why: the request says recompute and do not guess. The old sentence had no count.

10. Choice: the image-pin helper exits 1 with "PyYAML is not importable; refusing to skip the workflow image pin check" when `import yaml` fails. Fixture parse tests skip in that case. A PYTHONPATH shadow test always proves the missing-import path. Alternatives: vendor PyYAML, pip-install it on G0, or apt-install python3-yaml. Why: nimo has PyYAML 6.0.3. The published ubuntu-24.04 runner apt list includes libyaml-dev and yamllint and does not include python3-yaml. G0 runs `actions/setup-python` 3.12 before unittest, so an apt package would not be on that interpreter. A missing parser must not pass. GitHub-hosted runs-on must be exactly ubuntu-24.04 (string or a one-element list). A self-hosted label list with no GitHub-hosted image passes. A list that also contains ubuntu-latest fails. A reusable workflow job (`uses:`, no runs-on) is not a runner. A job with neither fails closed. Pregate `--only lint` stays in place. Measured RUN_ROOT and scratch are 52 characters here, under the default 60, so the lint call does not raise PREGATE_MAX_ROOT_LEN.

11. Choice: skip a new `pfy build --local` code change this run. Alternatives: edit `build_local` or `parse_args` for a known gap (assertion neutralization, unsandboxed test gate, rehash window). Why: `origin/bot/mvp3-review-retry` rewrites those regions (review-and-retry). The named loose ends are either already handled by `--reap`, need a model run, or were left as known gaps on purpose. No receipts, flags, or error text outside those hunks were still open.

12. Choice: OpenCode's open path is `attach.open_opencode_session`, and `open_session` stays the four-harness body. Alternatives: send OpenCode through `open_session`, or leave `pfy_enterable_162_b.py` as its own copy. Why: the OpenCode path writes config, skills, and tools env, then re-applies the probed base so a tools-env pin cannot win. `open_session` does not do that. The four captured contracts stay untouched. `config_dir` is null so `harness_home("opencode")` stays unset. `_legacy` still loads the other scripts.

13. Choice: stop after T-0070, T-0081, and T-0074 are skipped in a row. Alternatives: invent a new structural scorer, start docker for an OpenCode-in-cage smoke, or run `make eval-auto`. Why: exit 3 is three skips with no new information. The named 013 scorer already exists. Cage smoke is docker, and MVP-3 pid 1695827 is alive. Eval-auto runs a local model. The candidate fallback is already tested.
