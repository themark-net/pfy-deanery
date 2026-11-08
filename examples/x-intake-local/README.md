# X intake local smokes (Entries 095-100, 103-116)

Stdlib-only operate-or-FAIL checks for the X intake entries. Exit 0 PASS, 1 FAIL, 2 can't run here.
Each run writes `pipelines/smoke/<entry>/latest.json`. The smokes install nothing themselves; scratch files go to a tempfile dir that is removed.
Caveat: a first run can still download things the staged tool fetches on its own (e.g. the OpenQodex scanner pulls
its scanner on first use, and Moira's `docker compose up` pulls the digest-pinned image if it is not cached).

```sh
QWEN38_URL=http://127.0.0.1:8080/v1 python3 examples/x-intake-local/smoke.py --entry qwen38flash
python3 examples/x-intake-local/smoke.py --entry sandlock     # needs Linux 6.12+ and the release binary
python3 examples/x-intake-local/smoke.py --entry foremerge    # needs the release binary and git
python3 examples/x-intake-local/smoke_098_100.py --entry sponsio      # needs a venv with `pip install --pre sponsio`
python3 examples/x-intake-local/smoke_098_100.py --entry opensteps    # needs a clone of kharmanskyi/open-steps, bash, git
python3 examples/x-intake-local/smoke_098_100.py --entry repoharness  # repository-harness harness-v0.1.10 harness-linux-x64 sha256 68b6a51e40cd8e229f1f056c2aa5ea93de7934f746dcf8dd38e3b7d9dd4ee397, plus git
python3 examples/x-intake-local/smoke_103_105.py --entry bugpatrol    # npm --prefix bugpatrol@0.3.0, Node 22+, git; fake local OpenAI-compatible endpoint, no model or key
python3 examples/x-intake-local/smoke_103_105.py --entry graphjin     # graphjin v3.21.6 linux_amd64 binary sha256 e6f0fd88f99b07e8036ba7db76f24f0fceab697935559d154e823b5951f46805; throwaway SQLite
python3 examples/x-intake-local/smoke_103_105.py --entry antislop     # a clone of miqdadbadjuber/anti-slop; SKILL.md frontmatter check
python3 examples/x-intake-local/smoke_106_108.py --entry rulora       # npm --prefix @rulora/core@0.1.0-alpha.4, Node 20+; Core controls offline, no model
python3 examples/x-intake-local/smoke_106_108.py --entry har          # npm --prefix @osfactory/har@1.16.0, Node 20+, git; telemetry off, temp HOME, throwaway repo
python3 examples/x-intake-local/smoke_106_108.py --entry cassmemory   # cass-memory v0.5.0 linux-x64 binary sha256 06e1563881f8bb1225cf7036068252ef210f242704a27f8ce32518b822181bd7; no keys
python3 examples/x-intake-local/smoke_109_111.py --entry smolvm       # smolvm v1.26.1 linux-x86_64 tarball (smolvm-bin sha256 62ed0353d664c2d6d78bd87ecf3213c64464003f51cb58506b87b187b1a6494a), /dev/kvm read/write
python3 examples/x-intake-local/smoke_109_111.py --entry brigade      # venv with brigade-cli==0.27.0, git; BRIGADE_NO_UPDATE_CHECK=1, throwaway repo
python3 examples/x-intake-local/smoke_109_111.py --entry runx         # runx 0.9.1 musl binary sha256 e0c0627882c2ce7a4e8cfb20cf4896a4aa371db0e13c95c8b86fa31276388b60, clone at cli-v0.9.1, node
```

Prereqs are looked up via `$SANDLOCK_BIN` / `$FOREMERGE_BIN` / `$SPONSIO_PY` / `$OPEN_STEPS_DIR` / `$HARNESS_BIN`,
then `~/DEVELOP/pfy-mentat/tmp/{sandlock,foremerge,sponsio/.venv,open-steps,repository-harness}/`, then PATH where
it applies. Sponsio, opensteps, and repoharness tool subprocesses point HOME at a fresh temp dir (git keeps the
parent env) so they never touch real harness state. `PFY_XINTAKE_TIMEOUT` (float seconds, > 0) overrides those
timeouts; empty or invalid keeps 60s for opensteps hooks and 120s for sponsio and repoharness.

Entries 103-105 (`smoke_103_105.py`) look up `$BUGPATROL_BIN` + `$BUGPATROL_NODE` / `$GRAPHJIN_BIN` (pin override
`$GRAPHJIN_SHA256`) / `$ANTISLOP_DIR`, then `~/DEVELOP/pfy-mentat/tmp/{bugpatrol/node_modules/.bin/bugpatrol,
bugpatrol/node/bin/node,graphjin/graphjin,anti-slop}`, then PATH where it applies. Tool subprocesses get a fresh temp
HOME. The bugpatrol smoke strips paid provider keys from the env and serves its own stdlib fake model on 127.0.0.1,
so it never calls a real model; the graphjin smoke only binds 127.0.0.1 on a free port. `PFY_XINTAKE_TIMEOUT`
overrides 120s for bugpatrol explore and 60s for graphjin startup.

Entries 106-108 (`smoke_106_108.py`) look up `$RULORA_DIR` + `$RULORA_NODE` / `$HAR_BIN` + `$HAR_NODE` / `$CM_BIN`
(pin override `$CM_SHA256`), then `~/DEVELOP/pfy-mentat/tmp/{rulora,rulora/node/bin/node,har/node_modules/.bin/har,
har/node/bin/node,cass-memory/cm}`, then PATH where it applies. Tool subprocesses get a fresh temp HOME and an env
with paid provider keys (plus AWS credentials, `OLLAMA_BASE_URL`, `HAR_PORTAL_TOKEN`, `CASS_PATH`) stripped; none of
the three calls a model. The har smoke runs `har telemetry off` before anything else and FAILs if agent hook files
(`~/.cursor/hooks.json`, `~/.claude/settings.json`, `~/.codex/hooks.json`) appear in its temp HOME; its session
worktree lives under that temp HOME too. `PFY_XINTAKE_TIMEOUT` overrides the 120s per-command timeout.

Entries 109-111 (`smoke_109_111.py`) look up `$SMOLVM_BIN` (pin override `$SMOLVM_SHA256`) / `$BRIGADE_BIN`
(version override `$BRIGADE_VERSION`) / `$RUNX_BIN` (pin override `$RUNX_SHA256`) + `$RUNX_SRC` + `$RUNX_NODE`, then
`~/DEVELOP/pfy-mentat/tmp/{smolvm/smolvm,brigade/.venv/bin/brigade,runx/runx,runx/src,runx/node/bin/node}`, then PATH
where it applies. Tool subprocesses get a fresh temp HOME and an env with paid provider keys, `XDG_*` and inherited
`SMOLVM_*`/`BRIGADE_*`/`RUNX_*` stripped; none of the three calls a model. When `bwrap` works, the brigade and runx
commands run with a read-only root, only the temp HOME and scratch dir writable, and no network; otherwise the smoke
checks the tools' real-HOME state dirs did not change (receipt field `containment`). The smolvm smoke exits 2 without
read/write `/dev/kvm`, pulls `alpine` from Docker Hub on the host (`$SMOLVM_IMAGE` overrides), and adds
checkpoint/rewind only with `SMOLVM_CHECKPOINT=1`. `PFY_XINTAKE_TIMEOUT` overrides the 120s per-command timeout (300s
for smolvm machine commands).

Entries 112-114 (`smoke_112_114.py`) look up `$OVERTIME_DIR` + `$OVERTIME_NODE` (version override `$OVERTIME_VERSION`) /
`$FEST_BIN` with `camp` beside it (pin overrides `$FEST_SHA256`, `$CAMP_SHA256`) / `$SLOPTRIM_DIR` (commit override
`$SLOPTRIM_COMMIT`), then `~/DEVELOP/pfy-mentat/tmp/{overtime,overtime/node/bin/node,festival/fest,sloptrim}`, then PATH
where it applies. Every child, including the bwrap probe, `node --version`, sloptrim's `git rev-parse`, tool commands,
and overtime `daemon stop`, goes through `run_isolated` in `smoke.py`. That helper gives a fresh temp HOME and an env
limited to `PATH`, `HOME`, `TERM`, `LANG`, and `NO_COLOR`, plus the git identity variables Festival sets
(`GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`). None of the three calls a model.
Festival and Sloptrim pass `bwrap_writable`, so they run under `bwrap` with a read-only root, no network, and
`--unshare-pid` when that probe works. Overtime starts a detached daemon, so it passes no bwrap prefix. `daemon stop`
runs in a finally, and the smoke FAILs if a daemon is left or the real `~/overtime` changes, including when a command
times out. A timeout SIGKILLs the command's process group, so a forked grandchild dies too. Overtime needs Node >= 22.19
(exit 2 otherwise). `PFY_XINTAKE_TIMEOUT` overrides the 120s per-command timeout and, when it is smaller than 10s, the
`node --version` probe.

A recorded timeout reason is only `timeout_reason(step, seconds)` from `smoke.py`, the text `{step} timeout after {seconds}s` (for example `sponsio probe timeout after 0.2s`, `overtime timeout after 0.4s`, `openqodex timeout after 1s`). The overtime daemon-stop step uses the same helper (`overtime daemon stop timeout after 0.4s` when that step's limit is 0.4s). Smokes do not write a second timeout sentence.

New smokes must start every subprocess with `run_isolated` in `smoke.py` and with nothing else. Not `subprocess`,
not `os.system`, and not the older `run` helper (that one stays for Entries 095-097). `run_isolated` builds a clean
environment and does not copy the parent process's variables. It sets `HOME` to the temp directory the caller
passes. It starts the child in a new session and SIGKILLs the process group on timeout, so a grandchild the child
forked dies too. Pass `kill_on_exit=True` to SIGKILL that process group after a normal return as well.
Entries 157-164 do that, so a grandchild cannot outlive the smoke. Pass `bwrap_writable` (a list of directories
to bind writable) to add a bubblewrap prefix when `bwrap` works; the prefix includes `--unshare-pid` when that
flag works. Pass `None` to skip bubblewrap. `extra` is only for variables the smoke itself names. Do not pass
the parent environment as `extra`.

Entries 115-116 (`smoke_115_116.py`):

```sh
python3 examples/x-intake-local/smoke_115_116.py --entry openqodex   # Node >= 22, package pinned 0.12.0
python3 examples/x-intake-local/smoke_115_116.py --entry assay       # assay-ui pinned 0.3.0, local Chromium
```

OpenQodex looks up `$OPENQODEX_DIR` and `$OPENQODEX_NODE`, then `~/DEVELOP/pfy-mentat/tmp/openqodex`. Its HOME is
`$OPENQODEX_HOME` or `tmp/openqodex/home`, and that path must resolve under `~/DEVELOP/pfy-mentat/tmp` or the
system temp directory. Assay looks up `$ASSAY_BIN`, then `tmp/assay/venv/bin/assay`, and Chromium from
`$PLAYWRIGHT_BROWSERS_PATH` or `tmp/assay/ms-playwright`. Version probes use the same helper as the tool commands.
`PFY_XINTAKE_TIMEOUT` overrides the 600s per-command timeout.

Entries 117-118 (`smoke_117_118.py`):

```sh
python3 examples/x-intake-local/smoke_117_118.py --entry kander   # binary pinned 0.9.5 + sha256, temp HOME, no agent started
python3 examples/x-intake-local/smoke_117_118.py --entry moira    # needs docker compose and a digest-pinned image
```

Kander looks up `$KANDER_BIN`, then `~/DEVELOP/pfy-mentat/tmp/kander/kander`, then PATH (overrides `$KANDER_VERSION`,
`$KANDER_SHA256`). Moira looks up `$MOIRA_DIR` or `tmp/moira` (upstream compose file, Traefik config and an
operator-made `.env`) and `$DOCKER_BIN`, `tmp/docker/docker` or PATH, and refuses an image that is not pinned by
digest. Every child goes through `run_isolated`; Kander runs under bwrap when it works, Moira's compose calls do not
(they need the docker socket). The Traefik `image:` line in the staged compose file must be digest-pinned too
(upstream ships `traefik:v2.11.58`), or read `${TRAEFIK_IMAGE}` with a digest-pinned `$TRAEFIK_IMAGE`. The clean env
drops `DOCKER_HOST` and the temp HOME hides `~/.docker` contexts, so compose talks to `/var/run/docker.sock` only; on
nimo with a non-default socket (e.g. rootless Docker) set `MOIRA_DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock`.
`compose down -v` always runs, so named volumes do not survive. `PFY_XINTAKE_TIMEOUT` overrides the 600s per-command timeout.

Entries 119-121 (`smoke_119_121.py`):

```sh
python3 examples/x-intake-local/smoke_119_121.py --entry agentdescent  # pinned 0.5.1, offline demo only, no model call
python3 examples/x-intake-local/smoke_119_121.py --entry kenfold       # needs docker compose and a v0.1.1 checkout
python3 examples/x-intake-local/smoke_119_121.py --entry tsa           # pinned 2.2.0, temp fixture repo, no network
```

AgentDescent looks up `$AGENTDESCENT_BIN`, then `tmp/agentdescent/.venv/bin/agentdescent`, then PATH, and reads the
package version with the python next to it. Tree-sitter Analyzer looks up `$TSA_BIN`, then
`tmp/tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer`, then PATH, with `miswire-audit` beside it. Both run under
bwrap with no network when it works, with `--store` and the fixture repo inside the temp dir. Kenfold looks up
`$KENFOLD_DIR` or `tmp/kenfold` (a git checkout at the pinned tag) and `$DOCKER_BIN`, `tmp/docker/docker` or PATH;
its compose calls skip bwrap (they need the docker socket), bring up only postgres and kenfold with the update
check off, and always end with `compose down -v`. It exits 2 if `127.0.0.1:7077` is already in use. For a
non-default socket set `KENFOLD_DOCKER_HOST`. `PFY_XINTAKE_TIMEOUT` overrides the 600s per-command timeout.

Entries 122-124 (`smoke_122_124.py`):

```sh
python3 examples/x-intake-local/smoke_122_124.py --entry llmrouter      # pinned 15.4.0, offline classifier + demo, no model call
python3 examples/x-intake-local/smoke_122_124.py --entry harnessrouter  # needs docker; digest-pinned CE image on loopback
python3 examples/x-intake-local/smoke_122_124.py --entry squadra        # v3.10.1 checkout, temp git repo + registry
```

llm-router looks up `$LLMROUTER_BIN`, then `tmp/llm-router/.venv/bin/llm-router`, then PATH, and reads the package
version with the python next to it; it never runs `install`, so no host hook or config is written. Squadra looks up
`$SQUADRA_DIR` or `tmp/squadra` (a checkout at the pinned tag) and needs python3 >= 3.12; its registry and fixture repo
stay in the temp dir. Both run under bwrap with no network when it works and FAIL if their temp HOME is written.
HarnessRouter looks up `$DOCKER_BIN`, `tmp/docker/docker` or PATH; its docker calls skip bwrap (they need the docker
socket), bind only `127.0.0.1:$HR_SMOKE_PORT` (default 3917), add no provider key, and always remove the container
and its volume. For a non-default socket set `HR_DOCKER_HOST`. `PFY_XINTAKE_TIMEOUT` overrides the 600s per-command
timeout.

Entries 128-130 (`smoke_128_130.py`; 130 hal0 is catalog-only, no smoke):

```sh
python3 examples/x-intake-local/smoke_128_130.py --entry harnessscore  # pinned 1.8.2, two temp fixtures, offline scan
python3 examples/x-intake-local/smoke_128_130.py --entry openlore      # pinned 3.3.1, Node >= 22.19, temp TS repo
```

Both look up `$NODE_BIN`, then `tmp/node/bin/node`, then PATH. Harness Score reads `$HARNESS_SCORE_DIR` or
`tmp/harness-score/package` (the unpacked npm tarball, `dist/cli.js`); OpenLore reads `$OPENLORE_DIR` or
`tmp/openlore` (an npm prefix holding `node_modules/openlore`). Neither runs `install`, `connect`, `setup` or a plugin
install, so no host config is written. Both run under bwrap with no network when it works, FAIL if their temp HOME is
written, and fingerprint the real-HOME dirs the tool could write (`~/.harness-score`, `~/.config/harness-score`;
`~/.openlore`, `~/.pi/agent/extensions`) before the run and again in a finally: a created, deleted or changed entry
(content, size, permissions, mtime, symlink target) FAILs, even on timeout or without bwrap, and the receipt lists the
changed dirs in `real_home_changed`. Writes elsewhere in HOME are not watched.

Entries 131-133 (`smoke_131_133.py`):

```sh
python3 examples/x-intake-local/smoke_131_133.py --entry jah       # pinned 0.1.0, stub upstream + stub System-One, loopback
python3 examples/x-intake-local/smoke_131_133.py --entry aimemory  # pinned 3.1.1, loopback server on a temp data dir
python3 examples/x-intake-local/smoke_131_133.py --entry headson   # pinned 0.17.1, one temp JSON fixture
```

JevAgentHarness reads `$JAH_BIN`, then `tmp/jevagentharness/.venv/bin/jah`; ai-memory reads `$AI_MEMORY_BIN`, then
`tmp/ai-memory/ai-memory`; headson reads `$HSON_BIN`, then `tmp/headson/hson`; each falls back to PATH. The jah and
ai-memory smokes write a stdlib driver to a temp dir and run it on system `python3` as one isolated child, so the
proxy or server and its clients share the child's loopback (bwrap gives it no outside network). No real model, key,
`setup`, `install` or hook registration is used. All three FAIL if their temp HOME is written and fingerprint the
real-HOME dirs the tool could write (`~/.jah`; `~/.local/share/ai-memory`, `~/.config/ai-memory`;
`~/.local/state/headson`) before the run and again in a finally, as for 128-130.
OpenLore gets `TMPDIR` inside the temp dir and `OPENLORE_NO_UPDATE_NOTIFIER=1`. `PFY_XINTAKE_TIMEOUT` overrides the
600s per-command timeout.

Entries 135-136 (no smoke script; 134 is the Hermes entry, `sources/entries/134-hermes-agent.md`):

Monid (135) is catalog-only. Every useful path needs an account, a key or spend, and its open connector engine
still needs each vendor's own key, so there is nothing to smoke without Mark's OK. Harness² (136) has no script
here either: its own offline demo (`harness2-demo --k 2`, no model, no key) was run once on the Grok Bot box under
bwrap with no network and a temp HOME, and the result is in the entry. A pinned smoke can come with an eval-auto trial.

Entries 137-139 (`smoke_137_139.py`):

```sh
python3 examples/x-intake-local/smoke_137_139.py --entry neatroots     # pinned 0.2.9, `neatroots check` on temp trace files
python3 examples/x-intake-local/smoke_137_139.py --entry teammates     # pinned 1.1.0 @ de85f5d4793e, config + ledger only
python3 examples/x-intake-local/smoke_137_139.py --entry skillcreator  # pinned 0.3.6, V2 plugin with a fake OpenCode ctx
```

neatroots reads `$NEATROOTS_APP`, then `tmp/neatroots/app` (the unpacked release bundle), and Node 22+ from
`$NEATROOTS_NODE`, then `tmp/neatroots/node/bin/node`, then PATH. Hermes Teammates reads `$HERMES_TEAMMATES_DIR`, then
`tmp/hermes-teammates` (a git clone; HEAD is pinned with `$HT_COMMIT`). The skill creator reads `$OSC_DIR`, then
`tmp/opencode-skill-creator` (an `npm install --prefix ... --ignore-scripts` tree), and Node 18+ from `$OSC_NODE`, then
`tmp/opencode-skill-creator/node/bin/node`, then PATH. Only offline paths run: `neatroots check` (rules, no server,
no model, `TMPDIR` inside the temp dir), a stdlib driver that imports `teammates_config.py` and `teammates_store.py`
(no Hermes, `PYTHONDONTWRITEBYTECODE=1`), and a node driver that loads the skill creator's plugin entry with
`XDG_CONFIG_HOME`/`XDG_CACHE_HOME` in the temp dir and `OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0`. No installer,
`neatroots connect`, `hermes plugins install`, `opencode run` or model call. All three FAIL if their temp HOME is
written and fingerprint the real-HOME paths the tool could write (`~/.neatroots`;
`~/.hermes/plugin-data/hermes-teammates`; `~/.config/opencode/skills/opencode-skill-creator`,
`~/.config/opencode/opencode-skill-creator-update-check.json`, `~/.cache/opencode/packages/opencode-skill-creator@latest`)
before the run and again in a finally, as for 128-130.

Entries 140-142 (`smoke_140_142.py`):

```sh
python3 examples/x-intake-local/smoke_140_142.py --entry chiasmus   # pinned 0.1.40, MCP over stdio: Z3, Prolog, call graph
python3 examples/x-intake-local/smoke_140_142.py --entry tracekit   # pinned 1.4.1, dev signer in the temp dir + offline verify
python3 examples/x-intake-local/smoke_140_142.py --entry charlotte  # pinned 0.8.0, core profile on a file:// fixture form
```

Chiasmus reads `$CHIASMUS_DIR`, then `tmp/chiasmus` (an `npm install --prefix ... --ignore-scripts --omit=optional`
tree), and Node 22+ from `$CHIASMUS_NODE`, then `tmp/chiasmus/node/bin/node`, then PATH. Tracekit reads `$TRACEKIT_VENV`,
then `tmp/tracekit/venv` (a venv with `tracekit-ai==1.4.1`; `tracekit` on PyPI is another project). Charlotte reads
`$CHARLOTTE_DIR`, then `tmp/charlotte` (an `npm install --prefix` tree made with `PUPPETEER_SKIP_DOWNLOAD=1`), Node 20+
from `$CHARLOTTE_NODE`, then `tmp/charlotte/node/bin/node`, then PATH, and a browser from `$CHARLOTTE_CHROME`, then
`tmp/charlotte/chrome/chrome`, then `chromium`/`google-chrome` on the system PATH. The two MCP servers are driven over
stdio by a stdlib driver the smoke starts (Chiasmus with `CHIASMUS_HOME`/`CHIASMUS_CACHE_DIR` in the temp dir;
Charlotte with `TMPDIR` and `XDG_*` there, `--no-sandbox` inside bwrap, stopped by closing stdin and then SIGTERM).
Tracekit's driver runs in the venv and starts a same-user dev signer on a Unix socket in the temp dir; the smoke then
runs `tracekit verify` on the export and on tampered copies it makes itself. No `npm install -g`, client config edit,
`tracekit init`/`up`, HTTP mode, live site or model call. All three FAIL if their temp HOME is written and fingerprint
the real-HOME paths the tool could write (`~/.chiasmus`, `~/.cache/chiasmus`; `~/.tracekit-client`, `~/.tracekit-signer`,
`~/.local/share/tracekit`; `~/.cache/puppeteer`) before the run and again in a finally, as for 128-130. An explicit
`$CHIASMUS_NODE`, `$CHARLOTTE_NODE` or `$CHARLOTTE_CHROME` that is not an executable file exits 2 instead of falling
back. `PFY_XINTAKE_TIMEOUT` overrides the 600s per-command timeout; a value that is not a number > 0 exits 2.

Entries 143-145 (`smoke_143_145.py`):

```sh
python3 examples/x-intake-local/smoke_143_145.py --entry taste-skill  # pinned commit 6010f91, lint + seeded draw + headless Chrome inspect
python3 examples/x-intake-local/smoke_143_145.py --entry gitai        # pinned v0.3.1, repo quickstart on prebuilt binaries (exit 2 unbuilt)
python3 examples/x-intake-local/smoke_143_145.py --entry muxin        # pinned 0.6.0 binary sha, demo fleet + MCP over stdio
```

taste-skill reads `$TASTE_SKILL_DIR`, then `tmp/taste-skill` (a git clone, HEAD pinned), Node 22+ from `$TASTE_NODE`,
then `tmp/taste-skill/node/bin/node`, then PATH, and a browser from `$TASTE_CHROME`, then `chromium`/`google-chrome` on
the system PATH (handed over as `CHROME_PATH`), with `TASTE_SKILL_HISTORY`, `TASTE_SKILL_TMP`, `TMPDIR` and `XDG_*` in
the temp dir. gitai reads `$GITAI_DIR`, then `tmp/gitai` (a clone of v0.3.1 where `make build` was run by hand) and runs
the repo's `examples/graft/quickstart.sh` in a temp work dir with a `make` shim that accepts only `-C <repo> build` and
does nothing; it exits 2 until the five `_build/bin` binaries exist and `gitaly --version` prints `Gitaly, version 0.3.1`
(`$GITAI_VERSION`). Muxin reads `$MUXIN_BIN`, then
`tmp/muxin/Muxin/muxin`, then PATH (the release tarball unpacked, never `install.sh`), checks the binary sha256 and
version, sets `MUXIN_HOME`, `XDG_STATE_HOME` and `XDG_CONFIG_HOME` to temp dirs (`$MUXIN_LIB_DIR` becomes
`LD_LIBRARY_PATH` when set; a `--version` that can't run exits 2) and drives `muxin mcp --demo` over stdio with the stdlib driver from 140-142; only demo data
is used. No skill install, build, installer, real host, account or model call. All three fingerprint the real-HOME
paths the tool could write (`~/.taste-skill`; `~/.config/graft`, `~/.cache/graft`; `~/.config/muxin`,
`~/.local/state/gh`) before the run and again in a finally, as for 128-130. Bad overrides and `PFY_XINTAKE_TIMEOUT`
behave as for 140-142.

Entries 146-147 (`smoke_146_147.py`):

```sh
python3 examples/x-intake-local/smoke_146_147.py --entry skill-up  # pinned v0.14.0 binary sha, custom local-command engine eval (1 PASS, 1 FAIL by design)
python3 examples/x-intake-local/smoke_146_147.py --entry hiroute   # pinned v0.3.1 archive/manifest/installer shas, temp-HOME install, daemon + loopback gateway fails closed
```

skill-up reads `$SKILLUP_BIN`, then `tmp/skill-up/skill-up`, then PATH, and grades a fixture skill whose engine is a python
stub run as `engine.custom` (no model, docker or OpenSandbox), with TMPDIR and XDG_CONFIG_HOME in the temp dir. hiroute
reads `$HIROUTE_DIR`, then `tmp/hiroute` (release archive, its `.json` manifest and `standalone.py`), needs bwrap, runs the
installer only into a throwaway temp HOME (it would otherwise write `~/.local`, a systemd user unit and skills into
`~/.agents/skills` and `~/.claude/skills`) and checks the daemon, the 127.0.0.1 gateway (503/401 with nothing configured)
and the routing/decision commands. Both fingerprint the real-HOME paths the tool could write (`~/.skill-up`,
`~/.config/skill-up`; the eight HiRoute install paths) before the run and again in a finally. `HIROUTE_TERM_WAIT`
(default 45 s) bounds the wait after SIGTERM. `PFY_XINTAKE_TIMEOUT` and bad overrides behave as for 140-142.

Not wired into CI or Make.

Entries 154-156 keep the self-contained runners in `smoke_154.py`, `smoke_155.py`, and `smoke_156.py` (renumbered from 150-152, then from 153-155). Entries 157-164 use `run_isolated` / `find_bin` / `pinned` / `timeout_reason` and pass `kill_on_exit=True`:

```sh
python3 examples/x-intake-local/smoke_154.py   # dsh-superagent: staged clone typecheck, vitest, build; else exit 2
python3 examples/x-intake-local/smoke_155.py   # RoBrain: staged offline VetoBench; else exit 2
python3 examples/x-intake-local/smoke_156.py   # Kanzo: staged binary init + MCP; else exit 2
python3 examples/x-intake-local/smoke_157.py   # SysKnife: pinned clone build or --help/--dry-run; else exit 2
python3 examples/x-intake-local/smoke_158.py   # Emdash: pinned Linux release metadata, then exit 2 (GUI not launched)
python3 examples/x-intake-local/smoke_159.py   # skills-manager-cli help + list; HOME and npm cache under tmp/
python3 examples/x-intake-local/smoke_160.py   # agentplay: pinned venv, --help/--version, import one synthetic map; else exit 2
python3 examples/x-intake-local/smoke_161.py   # agentgg: pinned npm --help/--version; local scan only if Ollama is already up; else exit 2
python3 examples/x-intake-local/smoke_162.py   # Strata: pinned Linux AppImage metadata, then exit 2 (not launched)
python3 examples/x-intake-local/smoke_163.py   # magpie: pinned CLI release metadata, then exit 2 (not run)
python3 examples/x-intake-local/smoke_164.py   # Reasonix: pinned CLI tar metadata, then exit 2 (not run)
```

SysKnife reads `$SYSKNIFE_BIN`, else `tmp/sysknife/sysknife`, else PATH. With no binary it builds only when `$CARGO_BIN` or `cargo` exists and `$SYSKNIFE_DIR` (else `tmp/sysknife`) is the pinned commit. The build's `CARGO_HOME` and target dir stay under this worktree's `tmp/`. `--dry-run` is the planner preview (`check disk usage`); the smoke never passes `--yes` or `--dangerously-skip-approval`. No bubblewrap means no dry-run (the planner would not be network-isolated). Emdash reads the pinned GitHub release JSON through `$EMDASH_FETCH_BIN` or a stdlib fetch. It does not download the AppImage. Skills Manager reads `$SKILLS_MANAGER_BIN` or installs `skills-manager-cli` at the pinned version with `npm` into a scratch prefix under `tmp/`, with `HOME` and the npm cache in that same tree. `list` may refuse with no skill home; the smoke does not bootstrap. `PFY_XINTAKE_TIMEOUT` overrides the per-command limit. A bad value exits 2.

agentplay (160) installs pinned `agentplay==0.2.6` into a venv under this worktree's `tmp/xintake-160/`. Every child gets `AGENTPLAY_NO_NETWORK=1`, `DO_NOT_TRACK=1`, and a temp `HOME`. It runs `--help` and `--version`, then `import` of one synthetic `agentplay/v1` map and `list`. It never runs `view` (that opens a browser). It does not read `~/.grok`. Pip or network missing exits 2. agentgg (161) installs pinned `agentgg@0.1.29` with `HOME` and the npm cache under `tmp/xintake-161/`, then runs `--help` and `--version`. A scan runs only when Ollama is already answering on `127.0.0.1:11434` with a local model already installed. The smoke picks the smallest of those and skips `:cloud` and `remote_host` models. It does not pull one. If only an OpenAI-compatible server on `127.0.0.1:8080` answers, the smoke exits 2 and does not invent an API key. The scan is time-boxed, uses one local agent file, and does not pass `--live-validate`, a key, or the hosted app. No local endpoint exits 2 after help and version.

Entries 162-164 (`smoke_162.py`, `smoke_163.py`, `smoke_164.py`) are release-metadata receipts in the Emdash (158) shape. Each reads the pinned GitHub release JSON through `$STRATA_FETCH_BIN` / `$MAGPIE_FETCH_BIN` / `$REASONIX_FETCH_BIN` or a stdlib fetch, checks name/size/digest/(commit when present), and exits 2 without downloading or running the asset. `PFY_XINTAKE_TIMEOUT` overrides the metadata timeout. A bad value exits 2.

Entries 165-167 (`smoke_165.py`, `smoke_166.py`, `smoke_167.py`) are commit-metadata receipts. Each reads the pinned
GitHub commit JSON through `$EGM_FETCH_BIN` / `$ODAI_FETCH_BIN` / `$TEAQL_FETCH_BIN` or a stdlib fetch, checks the SHA,
and exits 2 without cloning or installing plugins/skills into agent homes. `PFY_XINTAKE_TIMEOUT` overrides the metadata
timeout. A bad value exits 2.

Entries 168-170 (`smoke_168.py`, `smoke_169.py`, `smoke_170.py`) are commit-metadata receipts for cedr, IM.codes and
Pi-Harness. Each reads the pinned GitHub commit JSON through `$CEDR_FETCH_BIN` / `$IMCODES_FETCH_BIN` / `$PIHARNESS_FETCH_BIN`
or a stdlib fetch, checks the SHA, and exits 2 without installing anything. `PFY_XINTAKE_TIMEOUT` overrides the timeout.
