# Fix: ./pfy build commit recheck fails on every build (trial hit 3h timeout)

Root cause (diagnosed from tmp/br1106 trial): recheck_sha() in scripts/pfy_build_cloud.py (~line 1708)
builds the recheck copy with git archive + tar + git init and a single 'recheck' commit. That repo is not
shallow, so history tests that skip only on shallow clones fail on every build:
tests/test_docs_hygiene.py (~63), tests/test_handoff_headless_1105.py (~58), tests/test_dogfood2_1031_report.py (~49).
The agent is then told to fix failures it did not cause. On top of that each attempt runs the full suite
(~16-21 min) about four times (post-change gate, flake gate, recheck, retries), so 3h runs out.

Implement:
1. Build the recheck copy with `git worktree add --detach <dest> <sha>` from self.worktree's repo (real
   history, still isolated, own temp dir, no hooks inherited), and always `git worktree remove --force` +
   prune in finally. Keep the gate-rewrote / timeout / interrupted semantics. Make the three history tests
   (and any other test that reads git history for a fixed commit) skip when the target commit is missing
   (`git cat-file -e <sha>^{commit}` fails), not only on a shallow flag.
2. On recheck failure, recheck the base SHA too (same mechanism). If base fails the same way (same failing
   tests or both fail), stop with a distinct environment-error status (e.g. "recheck-env-failed") in the
   receipt and do NOT feed it back to the agent or retry.
3. For docs-only diffs (every changed path is docs/** or *.md, no code/tests/config), skip the flake gate
   and overlap/reuse so the full suite runs at most twice per attempt.
Behavior tests (real git repos in temp dirs, no tautological mocks):
- recheck passes on a docs-only diff in a non-shallow repo whose history lacks the commits the history
  tests reference (single-commit-like setup);
- a base-also-fails case returns the env-error status with no retry and no agent re-prompt;
- docs-only diff runs the suite at most twice (count gate invocations);
- recheck worktree is cleaned up on success, failure and exception.
Update docs/ops/pfy-build-daily.md briefly (ASCII hyphens, no em dashes) and the CHANGELOG if one is used.
