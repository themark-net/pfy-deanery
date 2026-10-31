# FINDING: logged-out grok became no-change

Lane mvp-cloud-1031. This lane did not edit the runner. The real `~/.grok/auth.json` was not read and is not in this directory.

## Command

```text
HOME=<worktree>/tmp/targets/empty-home \
XDG_CONFIG_HOME=<that>/empty-home/.config \
XDG_DATA_HOME=<that>/empty-home/.local/share \
XDG_CACHE_HOME=<that>/empty-home/.cache \
strace -f -e trace=openat,open \
  ./pfy build "Create kept.py containing value = 1." \
  --repo <throwaway> --base HEAD --retries 0 --no-review --timeout 45 \
  --test-cmd "python3 -c 'print(\"gate-ok\")'" \
  --receipt-dir eval/mvp-1031/realfail/auth-failure
```

`HOME` and the three `XDG_*` dirs were empty directories created for this run. No `XAI_API_KEY`, `GROK_API_KEY`, or other `*_API_KEY` / `TOKEN` / `*_SECRET` variables were set, so none were dropped. Real grok. The full strace was deleted after the `auth.json` lines were copied to `auth-opens.txt`.

## Result

Process exit 1. Receipt `status` `FAIL`, `reason` `no-change`, `exit_code` 1, `branch` null, `recovery` `""`. One attempt, same reason. `output_tail` is grok's logged-out help:

```text
Not signed in. To authenticate without a browser, run:
  grok login --device-code
Alternatively, set the XAI_API_KEY environment variable or run `grok login` ...
```

No cloud branch. Caller HEAD and status unchanged. The gate before and after printed `gate-ok` and exited 0, because the empty diff still runs the gate.

The DoD row expects exit 1, `reason` `unauthenticated`, recovery text `run grok once to log in, then rerun the same ./pfy build`, and no read of `auth.json` by the runner.

`auth-opens.txt` has 25 `openat` lines. Every one is `ENOENT` on `<empty-home>/.grok/auth.json`. The real credential path does not appear. Nothing was read. `classify_cloud_failure` opens no file.

## Why

`classify_cloud_failure` returns `other` immediately when the grok exit code is 0, before it looks at the text. On a non-zero exit the regex is `unauthenticated|not logged in|please log in|auth.json`. The live text is `Not signed in`, which misses that regex. Either exit code therefore falls through. The worktree diff was empty, so the attempt is recorded as `no-change` with recovery `""`. The receipt does not store grok's own exit code, so this run does not say which of the two misses fired. Both miss this text.

## Suggested fix

`suggested.patch` adds `not signed in` and classifies that phrase even when grok exits 0. The `auth.json` filename stays on the non-zero path so a successful reply that mentions the filename is not treated as logged out. Do not apply this patch on the realfail branch.
