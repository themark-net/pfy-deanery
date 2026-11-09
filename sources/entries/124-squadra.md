### Entry 124: Squadra — local registry that coordinates several agent windows with acknowledgements, proofs and independent review

- **URL**: https://github.com/dagoSte/squadra (MIT, Python standard library, 238 stars at this read; release v3.10.1, 2026-10-16)
- **Date**: 2026-10-16 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2111117212794703954
- **Summary / Key Claims** (upstream README at v3.10.1): one durable local record shared by Codex, Claude, Cursor and human seats on one project. A coordinator records tasks with a file scope; workers must acknowledge assignments; closing needs source-bound proofs and an independent review, and a task marked `--defect-fix` needs proof that the regression test fails without the change and passes with it. Also records decisions, questions, lessons and checkpoints, reads local token usage, offers read-only load and forecast advice, and has a local dashboard. 50 subcommands, no account, no network service.
- **Why it matters here**: our Project Manager → DevBot → Tester → Reviewer flow keeps its record in GitHub comments and repo handoff docs. Squadra's rules (acknowledge before work, proof before close, independent review, fail-without-fix proof for defects) line up with the org's test doctrine (`prefer-behavior-and-fail-recover-tests`) and the handoff rule. Worth a look as a local ledger for multi-agent Build sessions on nimo, or as a source of rules to borrow.
- **Fit on nimo**: Yes: stdlib Python 3.12+ and git, checkout under `~/DEVELOP/pfy-mentat/tmp/squadra`, run as `python3 -B scripts/squadra.py` without installing. Node.js is needed only for `selftest` and the dashboard's JavaScript checks. Clients are codex, claude, cursor or manual; Grok Build and the Grok bots would be `manual` seats.
- **Verified on the Grok Bot box**: smoke PASS in `/tmp` with a temp HOME, under bubblewrap: `init --temporary`, a coordinator and a builder seat, one task; `doctor` reported integrity "passed" with the assignment pending acknowledgement, `status` showed the task, the project repo stayed clean and HOME stayed empty. Negative paths: not staged gives exit 2; a wrong `$SQUADRA_VERSION` gives 2; a tiny `PFY_XINTAKE_TIMEOUT` gives 1.
- **Finding**: the default registry lives under `~/.local/state/squadra/` (outside DEVELOP on nimo), so always pass `--root` under `tmp/`. `--lang` defaults to Italian, and some `status` lines stay Italian even with `--lang en`. On the box, hand-editing `events.jsonl` did not change `doctor`'s verdict, so treat that file as a readable mirror and the SQLite registry as the record. The installer copies skills into host config dirs; use the no-install path.
- **Extracted Repos / Tools**: https://github.com/dagoSte/squadra · https://github.com/dagoSte/squadra/blob/v3.10.1/references/start.md
- **TOOLS.md Link**: None. No TOOLS.md row and no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_122_124.py --entry squadra`. Needs `$SQUADRA_DIR` or `tmp/squadra` at v3.10.1 and python3 >= 3.12. Temp git repo and registry only; no agent CLI started. Receipt: `pipelines/smoke/squadra/latest.json`.
- **Non-goals**: No skills installed into any host, no real project registry, no change to the GitHub-based gate flow.
- **Status**: STAY I1 after the 2026-11-07 nimo probe. Pin v3.10.1, tag object `acd9e6d6099903e5fd128eb0906f061a4e72e88e`, commit `5081a06ae054bc80072d8109ee2ef088b52513c3`. Ack refused 1/1. An always-passing challenge matched 0/1 (both runs passed). The real test failed by assertion on the base and passed on the candidate, 1/1, and close exited 0 only after a non-author review. Wall 2.8925s. Gap B (the 3 hour `./pfy build` timeout and the two pregate FAILs) was not changed. Not a gate. No Feature GO. Report `ops:eval/evq1107/squadra/REPORT.md`.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Registry lands in the real HOME | `~/.local/state/squadra` appears on nimo | Always pass `--root` under `tmp/`; the smoke snapshots the real `~/.local/state/squadra` and `~/.cache/squadra` and FAILs if they change (also after a timeout and without bwrap), and FAILs if its temp HOME is written |
| Two records of truth (GitHub and Squadra) | Gate state drifts | Trial only on one Build session; GitHub stays the gate of record |
| Python older than 3.12 on the runner | Smoke exits 2 | Use a newer python from a venv under `tmp/` |
| Upstream moves fast (3.x releases weekly) | Pin goes stale | Bump the pin deliberately after re-running the smoke |
