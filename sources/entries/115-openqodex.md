### Entry 115: OpenQodex — pre-push code review: scanners on changed lines, then a reviewer that must answer every finding

- **URL**: https://github.com/openqodex/openqodex (Apache-2.0, TypeScript, 653 stars at this read; npm `openqodex` 0.12.0, repo created 2026-10-02)
- **Date**: 2026-10-13 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2110154613680902197
- **Summary / Key Claims** (upstream README and `docs/for-agents.md`): reviews "the commits you have not pushed plus everything uncommitted". First it runs the scanners that fit the changed files (22 built in, such as semgrep, gitleaks, ruff, bandit) and keeps only findings on changed lines. Then it starts a separate Claude Code or Codex process as the reviewer, which must raise or drop each scanner finding with a reason; scripts check that it answered every one. `init` also installs skills, rules, an MCP code-graph server and push-gate hooks for Claude Code, Codex, Cursor and Cline. No account or key of its own; Node 22+.
- **Why it matters here**: our Reviewer gate is a bot reading the diff. OpenQodex gives that pass a fixed shape: scanner candidates on changed lines, a brief, a findings JSON, and a `--finalize` step that checks the file without a model and refuses findings that cite a made-up source. `review --agent` hands the brief to whatever agent is running, so Grok Build or the Reviewer bot can be the reviewer even though Cursor and Grok are not supported reviewers upstream (Cursor is refused because cursor-agent "cannot be limited to reading"). **Eval-auto candidate**: run `review --agent` + `--finalize` as the Reviewer's first pass on pfy-mentat PRs and compare against today's hand review.
- **Fit on nimo**: Yes, as a package under `~/DEVELOP/pfy-mentat/tmp/openqodex` with Node 22 beside it and `HOME` under `tmp/`. Don't run `init` on nimo: it writes into `~/.claude`, `~/.cursor`, `~/.codex` and the repo (AGENTS.md and CLAUDE.md sections, a pre-push hook). Even a plain `review` creates `.openqodex/config.yaml` and `.openqodex/reviews/` in the repo it runs in, so only run it in a throwaway worktree.
- **Verified on the Grok Bot box** (`/tmp`, temp HOME, Node 22.23.3, no Claude Code or Codex): in a scratch repo with a planted `subprocess.call(cmd, shell=True)`, `review` reported "Full review unavailable", downloaded semgrep 1.94.0, gitleaks 8.21.2, ruff 0.8.4 and bandit 1.9.4 into HOME (about 360 MB, first run only), and listed semgrep and bandit candidates on that line. `review --agent` printed a brief with candidate ids and a findings path. `--finalize` accepted a valid findings file (exit 0) and rejected one citing a made-up source (exit 2). Not verified: code-graph MCP, push-gate hooks, custom scanners, false-positive rates on our code.
- **Finding**: the default block threshold is warn-only. A finalize with one major security finding printed "Passed with warnings" and exited 0, so a gate must set a threshold in `.openqodex/config.yaml` or read the receipt, not the exit code.
- **Extracted Repos / Tools**: https://github.com/openqodex/openqodex · https://github.com/openqodex/openqodex/blob/main/docs/for-agents.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_115_116.py --entry openqodex`. Uses `$OPENQODEX_DIR` or `~/DEVELOP/pfy-mentat/tmp/openqodex`, version pinned 0.12.0, Node >= 22, `HOME` from `$OPENQODEX_HOME` or `tmp/openqodex/home`. That HOME must resolve under `~/DEVELOP/pfy-mentat/tmp` or the system temp directory. Every subprocess, including `node --version`, goes through `run_isolated` (clean env, temp HOME, process-group kill on timeout). Exits 2 if `claude` or `codex` is on the tool PATH so no model can start. Receipt: `pipelines/smoke/openqodex/latest.json`.
- **Non-goals**: No `init`, no hooks, no skills or rules installed, no `.openqodex/` committed to pfy-mentat in this slice.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Warn-only default | A major finding still exits 0 | Set the block threshold in config, or gate on the receipt's finding counts |
| Repo writes | `.openqodex/` appears in the checkout | Throwaway worktree only; add to `.gitignore` if adopted |
| Scanner download | First run needs network and ~360 MB | HOME under `tmp/`, kept between runs; smoke exit 2 is honest offline |
| OPENQODEX_HOME outside the temp area | Scanners download into the real home or the repo | Smoke exits 2 and does not start a review |
| Young project | Released 2026-10-02, fast churn | Version pinned; bump deliberately |

- **Status**: STAY I1 on nimo 2026-11-07. Pin npm `openqodex@0.12.0` (tag `v0.12.0`, `9c4d516a15954ba3ed648fe1177038c92fb8f884`). Probe `eval/evq1107/openqodex/`: 2 of 3 planted changed lines hit, 0 candidates off the diff, default finalize exits 0 on major findings. Not wired into a gate. No Feature GO.
