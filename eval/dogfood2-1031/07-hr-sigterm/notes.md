# 07 harnessrouter SIGTERM

Why picked: docs/automation/x-intake-2026-10-16-handoff.md says SIGTERM to the harnessrouter smoke still leaves the container behind. Type: one product file, examples/x-intake-local/smoke_122_124.py. The gate was committed only on the throwaway (f033d34). It is saved here as gate.py and is not collected by tests/.

Gate before: exit 1, return code -15, empty stdout. That is the process dying on the signal.

Attempts 3.
1. FAIL tests. The model said both removals were logged as their own lines (`rm -f pfy-hr-smoke` and `volume rm -f pfy-hr-smoke`). The gate looks for the substring ` volume rm ` with a leading space, and a line that starts with `volume rm` does not contain that leading space.
2. PASS-REJECTED. Review reject. The SIGTERM volume command was `docker -- volume rm -f pfy-hr-smoke`. The `--` creates the leading space the gate checks. The task requires `docker volume rm -f pfy-hr-smoke`.
3. TIMEOUT. The retry was still reading the smoke when the default 1200s grok call ended. Receipt status TIMEOUT, exit_code 3, review.verdict null.

Wall 2942 seconds. Cloudfix 90d3c6e. No product commit. The runner removed the cloud worktree, and the attempt tails do not contain a unified diff. diff.patch records that. Pushed false.

Human accept: no. There is no commit to hand to Mark. The review was right to reject the `--` form. The lane gate was the reason attempt 1 failed a cleanup that the model described as the real commands.
