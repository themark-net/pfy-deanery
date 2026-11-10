Cited excerpts for the build-review handoff ticket. These are the fields and lines the ticket names. Do not treat an omitted paragraph as a missing file.

## Trial receipt fields

File the ticket names: tmp/trial/receipt.json. Fields a reader of that file would use:

- status: TIMEOUT
- reason: timeout
- exit_code: 3
- wall_seconds: 10802.404
- commit: null
- branch: null
- impact.source: git-grep
- worktree_removed: the key exists on the receipt (boolean not repeated here)
- gate.after.exit: 124

## tmp/trial/trial.meta

```
exit=3 wall_s=10803
```

## git log --oneline at 72bec83 (slice 2, before this handoff)

```
72bec83 Put cloud build worktrees on a short path and allow ordinary test edits.
d6729c8 Review cloud builds one file at a time.
8a587e2 docs: local-lab runs nightly at 04:15 UTC
3d1ca36 F5: cap local-lab steps and start at 04:15 UTC (#310)
315bfd0 Skip the handoff SHA check on a shallow checkout.
b4ccf17 Document how a bot runs headless launch, status, stop, and build.
```

## docs/HANDOFF-headless-1105.md opening at 72bec83

```
# Handoff: headless bot use (2026-11-05)

How a bot launches a pfy session with no display, checks it, stops it, and runs the daily cloud build. The feature commits below are on main. This note does not change those commands.

## Commands a bot runs

./pfy launch --headless
./pfy launch status
./pfy launch stop
```

The file exists. The ticket says to point this note at the new handoff.

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
