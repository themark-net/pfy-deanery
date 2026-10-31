# Autonomous decisions: mvp-cloud-1031

- 2026-10-31: Skills write-loop-exits-first and repo-handoff-doc-required are not files in this worktree or ~/.grok/skills. Bound the loop to the drop-in exit list, the agent-loops exit card in the run log, and docs/ops/HANDOFF-mvp-cloud-1031.md. Alternative was to stop and ask. The drop-in already states the exits and the handoff path.
- 2026-10-31: origin/main has no scripts/pfy_build_cloud.py and no pfylib/build_preflight.py. Implement the runner here. Inline classify_cloud_failure with the preflight phrases (rate limit, usage limit, quota exceeded, too many requests, 429, then unauthenticated, not logged in, please log in, auth.json; rc 0 is other). Do not import pfylib.build_preflight.
- 2026-10-31: Ordered items share scripts/pfy_build_cloud.py, the test module, and scripts/pfy. Run them in order in this lead session. Do not spawn parallel implementers. The project-map agent may write only gitignored .project-map/.
- 2026-10-31: The word help is a task. Only -h and --help print help. Alternative was to treat help as --help and steal a task named help.
- 2026-10-31: `pfy build -p --help` is rewritten to `pfy_build_p.py --help` in cmd_build. Dogfood argparse treats the next token as the -p value, so --help never opened the help. The dogfood script stays unedited.
