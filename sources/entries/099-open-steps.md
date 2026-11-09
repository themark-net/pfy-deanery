### Entry 099: Open Steps — plain-language done-or-not skills plus a stop hook that demands a session report

- **URL**: https://github.com/kharmanskyi/open-steps (MIT, shell + Markdown skills, about 1.2k stars at this read, checked at commit `4fa744ba8ea0`)
- **Date**: 2026-10-07 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2107946314579218499
- **Summary / Key Claims** (upstream README): Eight `os-*` skills for Claude Code, Codex, Cursor and Gemini CLI: `os-done-or-not` (one-screen verdict: done or not, anything needed from you, new debt, safe to close), `os-check-work` (doesn't trust another session's report), `os-what-could-go-wrong` (fresh-agent pre-mortem), `os-whats-next`, `os-big-picture` (keeps a BIG-PICTURE.md), `os-step-by-step`, `os-ask-simple`, `os-say-simple`. Two plain bash hooks: `session-start.sh` records a git fingerprint of the repos in scope, and `stop-report.sh` blocks the agent's stop (exit 2) and asks for the `os-done-or-not` report when real work landed. Reports are written outside the repo, so a report can't retrigger the hook. Ships its own eval fixtures and a 290-check hook test suite.
- **Fit on nimo**: bash and git only. A clone under `~/DEVELOP/pfy-mentat/tmp/open-steps` is enough to test; wiring the hooks into a harness config is a separate step.
- **Verified on the Grok Bot box** (shallow clone in `/tmp`, HOME pointed at a temp dir): upstream `hooks/test.sh` reported 290 passed, 0 failed. Our own behavior check: start hook exit 0, clean stop exit 0, stop after a file change exit 2 with "use the os-done-or-not skill to produce the session report", repeat stop with no new change exit 0. The smoke below PASSed there.
- **Why it matters here**: Two standing rules map onto it directly: every work item ends with a handoff doc in the repo, and Tester and Reviewer don't take a session's word that it's done. The stop hook is a cheap, model-free way to make a long `./pfy build -p` run produce its own handoff before it exits, and `os-check-work` overlaps Tester's "diffs are not sufficient" stance. It's also a candidate for the operator's ask that Build runs go longer without babysitting: the hook keeps the session going until there's a report.
- **Extracted Repos / Tools**: https://github.com/kharmanskyi/open-steps · https://opensteps.ai/
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_098_100.py --entry opensteps`. Uses `$OPEN_STEPS_DIR`, then `~/DEVELOP/pfy-mentat/tmp/open-steps`. Exits 2 without a clone, bash or git. Otherwise runs both hooks in a throwaway repo with HOME in a temp dir and checks the four exit codes above. Receipt: `pipelines/smoke/opensteps/latest.json`.
- **Non-goals**: No copy into `~/.agents/skills`, `~/.claude`, `~/.codex` or `~/.cursor` from this entry; no routing block appended to any real AGENTS.md. Upstream's auto-merge behavior ("green checks and an approved review, the agent merges") must stay off: our merge path is Tester plus Reviewer double PASS.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Report nag | Stop hook fires on every tiny change during a long run | `OPEN_STEPS_COOLDOWN` and `OPEN_STEPS_MIN_FILES`; kill switch `OPEN_STEPS_DISABLE=1` |
| Wrong place for reports | Reports land under `~/.claude/open-steps/reports`, not the repo's `docs/` | Point the routing block at our handoff path, or copy the report into docs/ as part of the handoff skill |
| Merge bypass | Pack's own merge-when-green behavior skips our gates | Don't install the merging part; keep it to the reporting skills and hooks |
| Harness mismatch | Grok Build's hook model differs from Claude Code's exit-2 contract | Trial through `hooks/adapter.sh` or a pfy wrapper that checks the exit code itself |

- **Status**: STAY I0 after the 2026-11-07 nimo probe (`eval/evq1107/open-steps/`). Pin `4fa744ba8ea06ccf128a39853824c46ac391dd00`, pack 0.4.8, cache install `~/.cache/pfy/tools/open-steps/`. Second stop exits 0 with no report file in 4 of 4 work-landed cases. Not wired.
