### Entry 098: Sponsio — deterministic tool-call contracts for agents (LTL monitors, no LLM in the hot path)

- **URL**: https://github.com/SponsioLabs/Sponsio (Apache-2.0, Python + TypeScript, about 440 stars at this read, PyPI `sponsio` 0.2.0a17 alpha)
- **Date**: 2026-10-07 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2107957626403189037
- **Summary / Key Claims** (upstream README and docs): Policies written in YAML or plain English compile to Linear Temporal Logic formulas and finite-state monitors that are checked at every tool call (`guard_before(name, args)` / `guard_after(name, result)`), in microseconds and with zero LLM calls at runtime. Violations can block, escalate to a human, or redirect to a safe tool; observe mode logs without blocking. Ships 22 contract bundles (for example `sponsio:capability/shell`, `/filesystem`, `/destructive`, `/credentials`, `/self-modify`, `/subagent`) built from 48 patterns. Enforcement is local and needs no account; the hosted console (`sponsio push`) is optional.
- **Fit on nimo**: Pure Python, CPU only, no GPU or model needed. A venv under `~/DEVELOP/pfy-mentat/tmp/sponsio/.venv` keeps it inside DEVELOP.
- **Verified on the Grok Bot box** (fresh `/tmp` venv, `pip install --pre sponsio`, 0.2.0a17): with only `sponsio:capability/shell` included and `mode="enforce"`, 9 contracts armed; `guard_before("exec", {"command": "ls -la"})` returned `allowed=True`, while `rm -rf ~/` and `curl ... | bash` returned `allowed=False` with "BLOCKED: det constraint violated". The smoke below PASSed there.
- **Why it matters here**: pfy-mentat's guard ideas so far are pattern lists (destructive_command_guard in the toolset drop-in) or sandboxes (Sandlock, Entry 096). Sponsio adds ordering rules over a whole run, which is what our gates actually say: "tests must pass before merge", "no push to main", "no writes outside ~/DEVELOP", "never lock nimo". Those could be enforced on the CUA lane or `./pfy build` tool loop without spending a model call per decision, which also fits the cheap-decision goal behind `./pfy decision`.
- **Extracted Repos / Tools**: https://github.com/SponsioLabs/Sponsio · https://sponsio.dev/ · https://pypi.org/project/sponsio/
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_098_100.py --entry sponsio`. Uses `$SPONSIO_PY`, then `~/DEVELOP/pfy-mentat/tmp/sponsio/.venv/bin/python`. Exits 2 when there's no Python with `sponsio`. Otherwise arms the shell bundle in a temp dir and expects `ls -la` allowed and both dangerous commands blocked (FAIL on a false positive or a leak). Receipt: `pipelines/smoke/sponsio/latest.json`.
- **Non-goals**: No `sponsio init` inside a product repo yet, no `sponsio push` or hosted console, no stochastic (LLM-judge) atoms.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Alpha churn | 0.2.0a-series API or bundle names change and the probe breaks | Smoke FAILs with "API shape changed?"; pin the version in the venv and re-read the release notes |
| Wrong tool name | Our loop calls the shell tool something other than `exec`, so rules never fire | Bundles say to rename the tool; a trial must include a known-bad call that has to be blocked |
| Over-blocking | Contracts block legitimate Build or ROCm commands (for example `sudo`-style patterns escalate) | Start in observe mode, read the violations, then flip to enforce per contract |
| False confidence | Regex-level shell rules miss an obfuscated command | Treat as one layer next to Sandlock confinement, not a replacement for it |

- **Status**: I2 probe on nimo (2026-11-07). Pinned PyPI sponsio 0.2.0a17, git 957cb5264f156b98208e48c17700addf3aa7c64e, under ~/.cache/pfy/tools/sponsio/. See ops:eval/evq1107/sponsio/REPORT.md. Not a gate.
