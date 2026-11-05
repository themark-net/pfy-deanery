# F1 new test files cannot land

Severity: high for this dogfood lane. The lane examples include a missing behavior test. The runner cannot commit one.

Evidence: run `02-enterable-test`. Command and receipt are in that directory.

- Exit 1. Summary line: `FAIL tests-tampered branch=none`.
- Receipt status `FAIL`, reason `tests-tampered`, exit_code 1, branch null, commit null.
- Attempts 1, 2, and 3 are all `FAIL` / `tests-tampered`.
- `gate.before.exit` is 1. `gate.after` was not recorded. The after-gate does not run once a test path is new or edited.
- `worktree_removed` is true. The correct one-line fix and the new test were deleted.

The cloud lane locked this on purpose. `tests/test_pfy_build_cloud.py` `test_changed_test_file_fails_before_the_gate` writes `tests/test_sneak.py` and expects reason `tests-tampered`. Handoff `docs/ops/HANDOFF-mvp-cloud-1031.md` says a new or changed test file is tests-tampered before the gate runs again.

Suggested change for lane mvp-cloud-1031 (do not apply it here):

In `tests_tampered`, keep rejecting a base test file that was edited or deleted. Stop rejecting a test path that did not exist in the base snapshot. Update `test_changed_test_file_fails_before_the_gate` in the same change: an edit or delete of an existing test still fails, and a brand new `tests/test_*.py` is allowed through to the gate. This lane does not edit `scripts/pfy_build_cloud.py` or `tests/test_pfy_build_cloud.py`.

Sketch, not applied:

```
def tests_tampered(worktree, snap):
    bad = []
    for rel, digest in snap.items():
        path = worktree / rel
        if not path.is_file() or sha256(path) != digest:
            bad.append(rel)
    return bad
```

The second loop that flags every path in the current snapshot that was not in `snap` is the part to delete.
