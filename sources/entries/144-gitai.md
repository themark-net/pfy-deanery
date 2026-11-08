### Entry 144: gitai: an open, Scion-style Git server where many agents land short changes on one branch

- **URL**: https://github.com/feder-cr/git-ai (MIT per README; Go, a fork of GitLab's Gitaly). Tag `v0.3.1` at commit `914e481ef057ca7b9dc9a5a7338d96bca16790e1` (tag created 2026-10-22T22:32Z); the history has 319 commits.
- **Date**: 2026-10-22 (daily X intake, window 2026-10-22T00:37Z to 2026-10-23T00:36Z)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2113087690073682159 (repo link in the reply https://x.com/DanKornas/status/2113087874468123122)
- **Summary / Key Claims** (upstream README; all their claims, nothing verified): an open implementation of the design Anthropic described for its internal Scion source-control system. A server (`gitaly` in standalone mode) plus `graft` client: sparse clones that fetch only the paths asked for, blame and history answered and memoized on the server, lands that rebase onto the tip with a compare-and-swap instead of a merge queue (concurrent lands batched), an ordered changeset log clients can watch, per-agent tokens with an RPC allowlist and branch policies, optional conflict resolution by any resolver (an LLM's proposal lands only if a configured `verify.command` passes on the exact tree), `graft-verify` to bisect and revert a breaking change, and a verified object cache (`graft-cache`). Their banner claims 200 of 250 changes landed by 50 agents racing on one branch, against 100 for plain git. The server itself never calls a model.
- **Why it matters here**: pfy-mentat's orchestrator runs parallel Build workers in separate worktrees and then merges by hand, and Mark's no-PR rule means branches fast-forward main after a double PASS. gitai's land-with-CAS plus per-agent branch policy is the piece we lack for many short agent changes on one branch, and its `verify.command` gate matches how Tester gates a pinned sha.
- **Fit on nimo**: Probably, but heavy. It builds Gitaly and a bundled Git from source (`make build`: Go 1.26, make, meson, ninja and Git's build deps); no GPU, no keys, SQLite storage works locally. Everything would live under `~/DEVELOP/pfy-mentat/tmp/gitai`. The quickstart opens Unix sockets in its work dir and a metrics port on 127.0.0.1:9236.
- **Verified on the Grok Bot box**: nothing beyond reading. `make build` could not run (the box has Go 1.27.2 but no make, meson or ninja), and the smoke exits 2 with that reason. The smoke logic is exercised only by stub tests.
- **Findings**:
  - **The quickstart always runs `make build`** before anything else. The smoke runs the repo's own `examples/graft/quickstart.sh` with a `make` shim that accepts only `-C <repo> build` and does nothing, so a smoke never builds.
  - The quickstart's own pass signal is weak (it prints "denied as expected" and reads history), so the smoke checks the outcome in the bare repo itself: main has the planner's README and not the denied line, and `feature/demo` has the builder's file.
  - The repo is a full Gitaly fork (40 MB checkout, about 30 `doc/graft` files including LIMITATIONS.md and AGENT-SECURITY.md). Read LIMITATIONS.md before any trial.
- **Extracted Repos / Tools**: https://github.com/feder-cr/git-ai · https://www.anthropic.com/engineering/redesigning-source-control (the design it follows)
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_143_145.py --entry gitai`. Looks up `$GITAI_DIR`, then `tmp/gitai`; HEAD pinned to `914e481e...` (`$GITAI_COMMIT`); exits 2 unless `_build/bin/{gitaly,gitaly-hooks,gitaly-ssh,graft,graft-cache}` were built there by hand and `gitaly --version` prints `Gitaly, version 0.3.1` (`$GITAI_VERSION`). Receipt: `pipelines/smoke/gitai/latest.json`.
- **Non-goals**: No build from the smoke, no service install, no pointing any real repo or agent at it, no LLM conflict resolver, no Slack superfans.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Heavy build | Go 1.26 and Git build deps don't fit nimo's toolchain | Build only under `tmp/gitai` with a local Go; if it needs system packages, stop and ask Mark |
| Young fork | v0.3.1 of a Gitaly fork; behaviour changes fast | Commit pin; trial on a scratch repo only |
| Landing semantics | An auto-landed change passes `verify.command` but is wrong | Keep Tester/Reviewer gating main; gitai only for worker branches |
| Untested smoke | The stub-tested checks miss a real quickstart detail | First nimo run is a hand run; fix the smoke then |

- **Status**: STAY I1 after the 2026-11-07 nimo probe. Pin v0.3.1 at `914e481ef057ca7b9dc9a5a7338d96bca16790e1` built as Gitaly 0.3.1. Eight disjoint lands all landed (117.9 ms, 1 attempt each) against plain git 1/8 on the first push and 36 pushes (436.0 ms). A same-line edit still conflicts. Not wired. See `eval/evq1107/gitai/REPORT.md`.
