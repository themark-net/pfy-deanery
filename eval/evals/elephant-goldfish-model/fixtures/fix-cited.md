Cited excerpts for the recheck ticket. Source commit 83d204bede34634cb719e4600127e43c52052b52, the parent of the fix. Line numbers that jump mean unchanged lines were left out. Do not treat a missing line number as a missing file.

## scripts/pfy_build_cloud.py lines 1-12

```
1|#!/usr/bin/env python3
2|"""pfy build "<task>": daily cloud Grok build.
3|
4|The checkout this process was started from is never switched, reset, stashed,
5|or committed. Work happens in a detached git worktree at a short 0700
6|path outside /tmp and /run. The default is /var/tmp/pfyb-<stamp>-<pid>.
7|Nothing is pushed and no PR is opened. This runner does not read auth.json
8|and does not start a local model.
```

## scripts/pfy_build_cloud.py prepare_worktree lines 2136-2170

```
2136|    def prepare_worktree(self) -> str | None:
2137|        dest = short_worktree_path(self.stamp)
2141|        try:
2142|            dest.parent.mkdir(parents=True, exist_ok=True)
2147|            # Create the directory first so /var/tmp never holds a 0755 tree.
2148|            # git worktree add accepts an empty directory and keeps its mode.
2149|            dest.mkdir()
2150|            os.chmod(dest, 0o700)
2151|            proc = _git(self.repo, ["worktree", "add", "--detach", str(dest), self.base_sha])
2162|        self.worktree = dest
2164|            os.chmod(dest, 0o700)
2165|            (dest / "tmp").mkdir(parents=True, exist_ok=True)
2170|        return None
```

## scripts/pfy_build_cloud.py recheck_sha lines 1708-1772

```
1708|    def recheck_sha(self, sha: str) -> tuple[str | None, str]:
1709|        """Run the gate on a fresh extract of sha. None means it passed."""
1711|            return "commit-recheck-failed", "archive failed"
1712|        dest = self.repo / "tmp" / ("recheck-" + sha[:12])
1716|            archived = subprocess.run(
1717|                ["git", "-C", str(self.worktree), "archive", sha],
1723|            dest.mkdir(parents=True, exist_ok=True)
1724|            extracted = subprocess.run(
1725|                ["tar", "-x", "-C", str(dest)],
1732|            # The extract has no .git. Without one, git walks up to the caller
1733|            # repo and a gate that runs git sees the parent tree. A nested
1734|            # repo whose index is the archive keeps that walk inside the extract.
1735|            hooks = dest.parent / ("recheck-hooks-" + sha[:12])
1736|            hooks.mkdir(parents=True, exist_ok=True)
1748|                "core.hooksPath=%s" % hooks,
1750|            init = subprocess.run([*git_base, "init", "-q"], capture_output=True, check=False)
1753|                [*git_base, "commit", "-q", "--allow-empty", "-m", "recheck"],
1761|            if again.get("aborted") == "timeout":
1762|                return "timeout", tail
1763|            if self.state.interrupted or again.get("aborted") == "interrupted":
1764|                return "interrupted", tail
1765|            if again.get("rewrote"):
1766|                return "gate-rewrote", tail
1767|            if again.get("exit") != 0 or not again.get("started"):
1768|                return "commit-recheck-failed", tail
1769|            return None, tail
1770|        finally:
1771|            shutil.rmtree(dest, ignore_errors=True)
1772|            shutil.rmtree(dest.parent / ("recheck-hooks-" + sha[:12]), ignore_errors=True)
```

## tests/test_docs_hygiene.py lines 62-71

The history check runs `git rev-parse --is-shallow-repository`. If stdout is `true` it returns before `git cat-file -e <sha>:<rel>` for commits 7197200 and c0d9072. A non-shallow repo does not skip.

## tests/test_handoff_headless_1105.py lines 56-64 and 107-112

`_shallow()` is `git rev-parse --is-shallow-repository`. `test_handoff_cites_the_landed_commits` calls `skipTest` only when that command prints `true`. Otherwise it looks up each landed subject in `git log` and requires the SHA in the note.

## tests/test_dogfood2_1031_report.py lines 47-55 and 88-98

`_shallow(repo)` is the same rev-parse check. `test_real_tree_matches_receipts_and_trailers` skips only when the repo is shallow AND a referenced commit is missing (`git cat-file -e <sha>^{commit}`). A full clone still runs the checker.

## docs/ops/pfy-build-daily.md

The ticket names this file as a doc to update. The cited table row for review records `impact.source` as `codebase-memory-mcp`, `tree-sitter-analyzer`, or `git-grep`. It does not describe `recheck_sha`.

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
