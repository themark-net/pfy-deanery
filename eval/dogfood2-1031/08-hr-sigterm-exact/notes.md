# 08 harnessrouter SIGTERM exact argv

Why picked: run 07 left the container-cleanup gap open. Its gate required the substring ` volume rm ` with a leading space, so a correct line `volume rm -f pfy-hr-smoke` failed and a `docker -- volume rm` line passed. This run requires the two logged argument lines exactly, and rejects a leading `--`. Same product file. Not a second copy of the 07 gate.

Gate before exit 1 (return code -15). Gate after, on this branch: the exact test plus four existing harnessrouter cleanup tests, 5 OK in 11.881s. Review accept. One attempt. Wall 891 seconds.

Diff: 1 file, 18 insertions, 1 deletion (19 changed lines). Patch is 3423 characters, under the 12000 character review cap. This run is below the 2 file and 60 line aim. It does not show truncation.

Human accept: yes. SIGTERM raises inside the try, the existing finally still runs `rm -f pfy-hr-smoke` and `volume rm -f pfy-hr-smoke`, and the function returns 1 with reason `SIGTERM during docker run`. The handler is restored before those removals. A clean cleanup, a cleanup timeout, and a non-zero rm or volume rm still pass their existing tests.

Cloud commit subject is the task text cut at 72 characters ("the harne"). Cherry-picked as e8a216a with the Built-by trailer. The behavior test was written before the run and is added on this branch in the following commit. Do not hand-edit the subject or the produced function.

Pushed false on the cloud branch. worktree_removed true.
