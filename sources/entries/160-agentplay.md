### Entry 160: agentplay: replay a coding-agent session as a map and a timeline

- **URL**: https://github.com/Entelligence-AI/agentplay (Apache-2.0, Python). GitHub API description: "Replay your coding agent sessions as a map and a timeline." Pinned to tag `v0.2.6`, commit `ff5f83e37063a38ec55ab7dd2b0fcdc435f4a72c` (committer 2026-10-26T20:00:59Z). PyPI package `agentplay` version `0.2.6` (Python >= 3.11, no runtime dependencies). Published wheel sha256 for `agentplay-0.2.6-py3-none-any.whl` is `b595890785649cb9fa8d83957fadcfbb1cfc47117bb1d60e21ebfdb0938ba4ee`. The smoke records that digest and checks the `--version` string. It does not re-hash the wheel file. `main` at check time was `b5fcffe889933cbcf28515d2ccc9d3567b22274b` (2026-11-04, Goose parser). That commit is not the pin.
- **Date**: 2026-11-04 (X intake)
- **Source / Poster**: https://x.com/DanKornas/status/2117926316578079141
- **Summary / Key Claims** (upstream description; their claims except where marked verified): a local, no-key replay of coding-agent sessions as a map and a timeline (files read or edited, retries, failed calls, context fill). The CLI reads Claude Code, Codex, Cursor, and OpenCode transcripts. A bare `agentplay` with no subcommand is `view`, which opens a browser. `import` accepts an `agentplay/v1` map file into a local store. `list` prints sessions.
- **Why it matters here**: Grok Build now writes the change, runs the tests, reviews its own work, and fast-forwards `main` on green. agentplay is one way to audit what a coding-agent session actually did. It does not read Grok Build sessions under `~/.grok`. That gap is the limit of this receipt. A Build session on this machine is not visible to it until a reader for that transcript exists.
- **Fit on nimo**: AMD Strix Halo, Radeon 8060S, no NVIDIA. The tool is a Python CLI and does not need a GPU. This machine has Python 3.14.4. The smoke installs the pin into a venv under this worktree's `tmp/xintake-160/`.
- **Verified on nimo** (2026-11-04, this worktree, no sudo): `python3 examples/x-intake-local/smoke_160.py` exited 0. Receipt verdict `PASS`. The pass path does not set a reason string. Checks: `help` is `ok`, `parse` is `imported`, `browser` is `not_opened` because the smoke never invoked `view`. `--version` contained `0.2.6`. `import` of one synthetic `agentplay/v1` map and `list --json` showed session `local:claude-code:pfy-smoke-160`. Every child had `AGENTPLAY_NO_NETWORK=1`, `DO_NOT_TRACK=1`, and a temp `HOME`. The venv and the pip cache were under `tmp/xintake-160/`. The scratch directory was removed when the smoke exited. Real-HOME paths the smoke watches were unchanged (a change would have forced exit 1).
- **Findings**:
  - The synthetic map proves `import` and `list` accept an `agentplay/v1` document. It does not prove the tool can parse a real Claude Code, Codex, Cursor, or OpenCode transcript, and it does not read `~/.grok`.
  - `view` is on the CLI and opens a browser. The smoke never runs it.
  - The published wheel sha256 is recorded as `checks.wheel_sha256_pin`. pip installs `agentplay==0.2.6` with `--no-deps`. The pin check is the version string.
- **Extracted Repos / Tools**: https://github.com/Entelligence-AI/agentplay · PyPI `agentplay==0.2.6` · compare with Grok Build session logs under `~/.grok` (not read by this tool)
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_160.py`. Uses `run_isolated`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads `$AGENTPLAY_BIN` or installs the pin with `$AGENTPLAY_PYTHON` or `python3` into a venv under `tmp/xintake-160/`. A set override that is not executable exits 2 and does not fall through. Python older than 3.11 exits 2. Then `--version`, `--help`, `import` of one synthetic map, and `list --json`. No `view`. Receipt: `pipelines/smoke/agentplay/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_160` (8 stub tests: missing python, hang killed, no surviving grandchild, import does not open the viewer, venv scratch stays in the worktree, real-HOME write, bad timeout, gitignored receipt).
- **Non-goals**: No browser, no read of `~/.grok`, no network after the install (`AGENTPLAY_NO_NETWORK=1`), no re-hash of the wheel, no pin to `main`, no TOOLS.md row. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| `view` opens a browser | A no-arg CLI run starts the viewer | The smoke calls only `--version`, `--help`, `import`, and `list` |
| Install writes the real home | pip uses `~/.cache/pip` or the tool writes `~/.agentplay` | `HOME`, `PIP_CACHE_DIR`, `TMPDIR`, and `AGENTPLAY_HOME` are under the worktree `tmp/`. The finally compares one-level names of the watched homes and fails the run if they change |
| Network or an old Python | pip cannot fetch the wheel, or Python is below 3.11 | Exit 2 with that reason. Do not fall through to another interpreter |
| The map is not a real session | `import` accepts a hand-built document | Treat the pass as a CLI check. A transcript reader for `~/.grok` is still missing |
| Timeout | The install or a command exceeds the bound | Exit 2. `kill_on_exit` SIGKILLs the process group |

- **Status**: Cataloged I0. Smoke PASS on nimo for version, help, and import of one synthetic map. Not a reader for Grok Build sessions. No Feature GO.
