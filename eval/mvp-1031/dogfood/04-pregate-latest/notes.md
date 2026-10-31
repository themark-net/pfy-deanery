# 04 pregate latest summary

Why picked: HANDOFF-pregate says tmp/pregate-latest-summary.md is overwritten by whichever pregate finishes last. START_EPOCH already exists. Type: code fix in scripts/pregate.sh. The check is dogfood_gate.py on the throwaway, not a new file under tests/.

Gate before exit 1 (missing latest_summary_is_newer). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The function is real, not a comment near the copy. It returns success only when the shared file contains "- start epoch: N" with N greater than START_EPOCH. A missing file, a file with no such line, or an older or equal epoch returns failure, and the existing cp still runs. On success the script prints the exact skip line to stderr and does not copy. write_summary emits the epoch line. No new flock, which the task forbade, so two runs that both pass the check before either copy can still clobber. That residual race is the gap the task left open. Mark would accept this commit as the asked change.

Wall: 289 seconds. Cloud commit daa83e5. Pushed false. worktree_removed true.
