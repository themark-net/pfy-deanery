# 03 smoke137-timeout

Human: reject.

Why: the diff is the right timeout check (import `timeout_problem`, return 2 before the entry, docstring sentence, `tree_hash` untouched). It is not landed. At fetch time, `origin/bot/mvp-selfhost2-1031` already had `1faa9fd` ("Hash smoke 137 fixture symlinks as readlink text") on `examples/x-intake-local/smoke_137_139.py`. That lane owns the file. This lane does not edit a file another lane owns.

Cloud commit: 141b4c0c0ca3adc023d60b47c9b33412824bd6aa (left on the throwaway clone, not cherry-picked)
Landed: none
Wall seconds: 113
Attempts: 1
Review: accept
Exit: 0
Failure class: cross-lane

FINDING-D3-01: the bad-timeout early return is still missing on this tip. The rejected diff is `diff.patch`. selfhost2's hunk is `tree_hash` around line 135. These hunks do not overlap. An integrator can apply the timeout check after `1faa9fd` lands.

The red gate `tests/test_smoke_137_bad_timeout.py` was dropped before push so the branch does not carry a failing test.

Fail that was not landed: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 still reaches the neatroots prereq miss.
Recover: none on this branch. The entry still runs.
