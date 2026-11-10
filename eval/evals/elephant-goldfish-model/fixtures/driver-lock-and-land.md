## Driver lock and land step

The lane driver that ran this ticket. The ticket does not name this file. This excerpt is the lock and the land step. ROOT is the repo root. WT is the lane worktree. LOCK is $ROOT/tmp/heavy-1030.lock.

```
pregate(){ local sha=$1
  while pgrep -x Runner.Worker >/dev/null; do sleep 60; done
  ( cd "$WT" && TMPDIR=$WT/tmp flock -w 1800 "$LOCK" nice -n 19 scripts/pregate.sh "$sha" > "$WT/tmp/pregate-$sha.log" 2>&1 )
  grep -q 'OVERALL=PASS' "$WT/tmp/pregate-$sha.log"
}

ff(){ ( cd "$WT" && git fetch -q origin && git merge-base --is-ancestor origin/main "$1" && git push -q origin "$1:refs/heads/main" ) }
```

In the slice loop, a pregate failure increments the fail count and continues. After CI is green, ff is the land step. Success logs LANDED. Failure logs `FF failed (main moved?)`, increments the fail count, and rebases onto origin/main. A rebase that cannot start aborts and leaves the loop. After two failures the driver writes PARKED.

flock -w 1800 starts scripts/pregate.sh only after the lock is free. The log file is the stdout of that script. grep looks for OVERALL=PASS in that log. A wait that ends before the script runs leaves the log empty, and grep then fails.
