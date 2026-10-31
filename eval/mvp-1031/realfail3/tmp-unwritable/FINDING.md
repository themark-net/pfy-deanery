# FINDING: unwritable tmp becomes runner-crash

Lane mvp-realfail3-1031. This lane did not edit the runner.

## Command

Throwaway repo under this worktree's `tmp/realfail3-targets/tmp-unwritable` (not committed). `tmp/` was mode 555 before the run and was restored to mode 755 after it.

```text
./pfy build "In app.py change the line value = 0 to value = 1. Do not edit any other file. Do not commit." \
  --repo <throwaway> --base HEAD --retries 0 --no-review --timeout 30 \
  --test-cmd "<python> -c print gate-ok" \
  --receipt-dir eval/mvp-1031/realfail3/tmp-unwritable
```

## Receipt

`status` FAIL, `reason` runner-crash, `exit_code` 1, `branch` null, `commit` null, `recovery` empty. Attempt n is 0. The tail is `PermissionError` on `<throwaway>/tmp/cloud-build`. Gate before and after are null, so grok was not called. Caller HEAD and porcelain were unchanged. No `cloud/` branch.

## Expected

The failure table says that when the base ref cannot be checked out into a new worktree, the run exits 1 with `reason` `worktree-failed`. The caller status stays unchanged. That part held. The reason did not.

## Suggested fix

In `CloudBuild.prepare_worktree`, catch `OSError` around `dest.parent.mkdir` and `git worktree add`. Return `worktree-failed` instead of letting `main` record `runner-crash`. Keep exit 1, no branch, and an empty recovery. Add a behavior test whose `--repo` clone has `tmp/` mode 555 and asserts reason `worktree-failed`.

Do not apply this on the realfail3 branch. mvp-cloudfix-1031 owns the runner.
