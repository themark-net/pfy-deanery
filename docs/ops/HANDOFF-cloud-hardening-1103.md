# Handoff cloud-hardening-1103

Status: fix batch for the Tester and Reviewer FAIL on `533a634` landed. Branch `lanes/cloud-hardening-1103`. Worktree `~/DEVELOP/pfy-mentat/tmp/lanes-1103`. Fast-forward only. No merge to main, no PR.

Lanes ran through sandcastle-grok (`batches/fix-533.json`, `batches/fix-533b.json`). Exit tests were committed first and checked red on `533a634` for the stated reason.

## Done

| Item | SHA | What changed |
|------|-----|--------------|
| R4 behavior tests | `c1f9455`, `7db8c4f` | Star-import `tests/test_cloud_lane_import.py` and `tests/test_cloud_lane_c5.py` removed. `tests/test_cloud_lane_nofcntl.py` runs the real runner with fcntl blocked (`sys.modules['fcntl'] = None`), checks the lock is held while the gate runs and free after. |
| R2 recovery wording | `665bdb3` | No recovery line starts with `Mark:`. Each names the next action. Pins in tests and the saved mutant anchor in `eval/mutation-1031/cloud/run_mutants.py` updated to the new text. |
| B1, S1, S2, S3, R1, R3, root-only tmp | `77ae54c` | `gate_tree_manifest` lists paths from `git ls-files --cached --others --exclude-standard`, with the same skips as `files_changed` (root `tmp/` only, `__pycache__`/`.pyc`, `.pytest_cache`) plus git metadata. Ignored-but-tracked files stay covered, gitignored gate artifacts (`.coverage`, `.pytest_cache`) no longer fail, a deleted tracked file shows as missing. Exit test `tests/test_cloud_lane_manifest.py` kills M09 (base-gate check) and M10 (recheck), verified by applying each. The old any-depth skip set is gone; `__pycache__` is now dropped by `_omit_from_commit` (killed by the pycache test) and `.git`/`.git.private` by `_git_metadata_path` (killed only from `2b5fe59` on, see below). |
| B2 mode | `e54593a` | Manifest entries carry the git file mode, so a gate chmod (+x or -x) is gate-rewrote. An agent-made executable is still committed as 100755. Test `tests/test_cloud_lane_mode.py`. |
| Invalid UTF-8 crash | `43ba147`, `340344c` | A changed file that is not UTF-8 ends as `review-binary-change` with a recovery line, not runner-crash. Test `tests/test_cloud_lane_utf8.py`. |
| fcntl guard | `7db8c4f` | Missing fcntl: the build runs unlocked and prints a note, instead of runner-crash. |
| Reviewer a205d2b B1 | `d977d1f` | Real pytest gate test skips only when `sys.executable` cannot import pytest (`importlib.util.find_spec`). The ubuntu eval-structural job pip-installs pytest, so the test runs there. pytest is not installed on nimo, so it skips locally. |
| Reviewer a205d2b B2 | `2b5fe59` | `tests/test_cloud_lane_isolated_gitdir.py`: a worktree copy isolated by `_isolate_gitdir` runs `git status` (refreshing `.git.private/index`) and the manifest is unchanged. With `_git_metadata_path` returning False it fails (verified). |
| Reviewer a205d2b B4, wording | `e594949` | `gate_tree_manifest` fails closed when `git ls-files` exits nonzero: a unique marker makes the before/after compare differ, so the build ends gate-rewrote, before or after the gate. Test `tests/test_cloud_lane_lsfiles_fail.py` uses a PATH git shim while the gate rewrites `src/kept.py`. Gate-timeout recovery line capitalized, gate-rewrote line now also names the listing failure. |
| Tester a205d2b should-fixes | `359886c` | `_git` decodes with surrogateescape and `capture_diff` diffs one path at a time. A non-UTF-8 new file, non-UTF-8 OLD content, a deleted non-UTF-8 file, or a non-UTF-8 filename all end `review-binary-change` (test asserts that exact outcome). The filename case skips on filesystems that reject such names (nimo is utf8only) and runs in the ubuntu CI job. Tester probe r19 (fake git first on PATH, only ls-files exits 128, gate rewrites a file) is `tests/test_cloud_lane_lsfiles_fail.py`. |

## Notes, not fixed

- `files_changed` and `_omit_from_commit` still hold the skip rule twice. Sharing one source breaks saved replay diff g10 (its context is the `files_changed` body), so it was left; both lists are equal today.

- Lock scope: the lock is `<clone>/tmp/cloud-build.lock`, so two separate clones of the repo never block each other. Two worktrees of one clone that pass the same `--repo` do.
- p05/S4: deleting the lock file mid-build lets a second build take a fresh lock on a new inode, so two builds can run at once.
- S5: a SIGKILLed runner leaves its worktree, which the next run does not reap.

## How it fails and how it recovers

- gate-rewrote: the gate wrote, deleted, or chmodded a committable path (including nested `tmp/` dirs), or `git ls-files` failed. Recovery: make the gate check only, then rerun `./pfy build`.
- build-busy: another build holds this clone's lock. Recovery: wait, then rerun.
- review-binary-change: a changed file is not readable text. Recovery: drop or regenerate it as text, or commit it outside the cloud build.

## Gates

Pregate and CI results: see the commit that follows this doc in the run log, or the parent report.
