# 07 pregate lock

Why picked: HANDOFF-pregate says one pregate per host is not coordinated, so concurrent runs can prune each other's worktrees. Type: code fix in scripts/pregate.sh. The check is dogfood_gate.py on the throwaway. It holds the lock in one process and requires the second claim to return 2 with stderr "pregate busy", while the holder stays alive.

Gate before exit 1 (missing pregate_claim_lock). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The function matches the task. flock -n on an fd opened on $MAIN_ROOT/tmp/pregate.lock, return 2, exact busy line, no kill. The call is after the whitespace die2 and before RUN_TS, so a busy lock stops the script before it prunes. The lock is per MAIN_ROOT, so a pregate of a different repo is not blocked. That is the scope the task set. The holder process is not signalled.

Wall: 94 seconds. Cloud commit f7d00a2. Pushed false. worktree_removed true.
