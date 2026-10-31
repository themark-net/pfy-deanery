# 09 splice close

Why picked: HANDOFF-pfy-local-build-mvp says the daemon splice threads emit ResourceWarning because they do not close the sockets. Type: code fix. The check is dogfood_gate.py on the throwaway. It sends bytes through _splice_sockets and requires both sockets to be closed after the call returns.

Gate before exit 1 (splice does not join and close). Gate after exit 0. Review accept. One attempt.

Human accept: yes. Both copies, the embedded bridge splice and _splice_sockets, join both pump threads and then close both sockets, ignoring OSError. The recv loop is unchanged. The caller still starts _splice_sockets on a daemon thread. The diff is 14 insertions in one file. A connection that is still blocked in recv when the process exits can still warn, because those daemon threads are killed on the way out. The finished connection, which is the warning the handoff named, now closes.

Wall: 85 seconds. Cloud commit 24e73be. Pushed false. worktree_removed true.
