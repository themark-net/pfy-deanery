# FINDING: reap leaves the live grok process

Lane mvp-cloud-1031. This lane did not edit the runner.

## Command

Throwaway repo under this worktree's `tmp/targets/sigkill-reap` (not committed).

```text
./pfy build "Add a one line comment at the top of app.py that says hello from pfy." \
  --repo <throwaway> --base HEAD --retries 0 --no-review --timeout 180 \
  --test-cmd "python3 -c 'print(\"gate-ok\")'" \
  --receipt-dir eval/mvp-1031/realfail/sigkill-reap
```

After `comm` showed `grok`, this lane sent SIGKILL to the runner pid it had started (1717246). Build exit was -9. Then:

```text
./pfy build --reap --repo <throwaway>
```

Reap exit was 0. Stdout: `reaped: reaped 1717246, aborted sigkill-reap`.

## Receipt excerpt

`status` `ABORTED`, `reason` `no-receipt`, `exit_code` 1, `branch` null, `commit` null, `attempts` [].

## What matched

The planted `tmp/local-build.pids.json` bytes were unchanged. The sleep process this lane started was still alive after reap. No `cloud/` branch. Caller HEAD and status unchanged.

## What failed

`pidfile-at-kill.json` recorded `agent_pgid` 1717258. The live grok pid was 1717259, and 1717258 was not a live descendant (it is the already-exited gate pid). Reap signals only the recorded pgids, so grok 1717259 was still alive after reap. This lane then stopped that pid. It did not signal any other process.

`save_pid` runs at the start of `grok_call`, before `run_command` assigns `state.agent_pgid`. A SIGKILL in the middle of the grok call therefore leaves a stale agent id in `tmp/cloud-build.pids.json`.

## Suggested fix

`suggested.patch`. Pass `on_start=self.save_pid` into `run_command` and call it after `Popen` sets `state.agent_pgid`, before `communicate`. Reap already signals `agent_pgid`. Do not apply this patch on the realfail branch.
