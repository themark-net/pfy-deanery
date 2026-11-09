### Entry 100: repository-harness — agent-ready repo protocol with a checksum-verified, three-way-merge updater

- **URL**: https://github.com/hoangnb24/repository-harness (MIT, Rust, about 1.2k stars at this read, release `harness-v0.1.10`)
- **Date**: 2026-10-07 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2107799092013187561
- **Summary / Key Claims** (upstream README): Installs a small "repository protocol" into a repo: a compact AGENTS.md entrypoint, a repo map in `docs/README.md`, optional product, decision and execution-plan locations, templates, and explicit-only skills (`onboard-repository`, `encode-invariant`, `audit-onboarding-proposal`, `improve-harness`) under `.agents/skills/`. The repo stays the system of record. The `harness` binary has `install`, `status`, `doctor` and `update`; updates keep the upstream base in `.harness-core/`, three-way merge, back up changed files, and stage overlapping edits instead of overwriting them. No database, no background process, no orchestration.
- **Fit on nimo**: Single static `harness-linux-x64` release binary with a published sha256; it can sit in `~/DEVELOP/pfy-mentat/tmp/repository-harness/` with nothing installed outside DEVELOP.
- **Verified on the Grok Bot box** (release binary, sha256 `68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397` matched): in a throwaway repo that already had its own AGENTS.md, `harness install --json` applied, reported AGENTS.md as `adopt` and left it byte-identical, created `.agents/skills/*`, `docs/README.md`, `docs/WORKFLOW.md` and plan/decision folders; `doctor --json` reported healthy; after a local edit, `status --json` flagged that file as modified. The smoke below PASSed there.
- **Why it matters here**: Org rules already require a thin AGENTS.md router in every active product repo and a handoff doc in `docs/` so the next model can take over from git alone. This is an open, maintained version of that scaffold, plus an updater that can push improvements to many repos without clobbering local edits, which is the part our `agents-md-in-every-product-repo` skill does by hand. Worth comparing against our own router before adopting anything.
- **Extracted Repos / Tools**: https://github.com/hoangnb24/repository-harness · https://github.com/hoangnb24/repository-harness/releases/tag/harness-v0.1.10
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_098_100.py --entry repoharness`. Uses `$HARNESS_BIN`, then `~/DEVELOP/pfy-mentat/tmp/repository-harness/harness`, then PATH. Exits 2 without the binary or git. Otherwise installs into a throwaway repo and checks: applied, our AGENTS.md untouched, doctor healthy, local edit flagged by status. Receipt: `pipelines/smoke/repoharness/latest.json`.
- **Non-goals**: Never run `install` against pfy-mentat or any product repo from this entry. No `curl | bash` bootstrap; no `--with-engineering-wisdom` payload.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Payload drift | A new release renames or drops `docs/README.md`, so the smoke FAILs | Pin `harness-v0.1.10` by sha256; read the install-files list before bumping |
| Overlap with our docs | Its `docs/` layout collides with pfy-mentat's existing docs tree | Only trial on a scratch copy; a merge decision about layout is a design call, not automatic |
| Generic binary name | Some other `harness` on PATH answers and the JSON checks fail | Set `$HARNESS_BIN` explicitly; the smoke records which binary it ran |

- **Status**: STAY I0. nimo probe in ops:eval/evq1107/repository-harness/REPORT.md. Pinned harness-v0.1.10 sha256 68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397. The new map named 0 of 6 authority paths. Not installed into this repo.
