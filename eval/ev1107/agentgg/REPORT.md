# agentgg ev1107 (2026-11-07)

Verdict: STAY I0. The scan caught the planted `shell=True` diff and missed the planted Python secret-in-log diff. Every finding on the six historical diffs was a false positive. Each scan finished in under 10 minutes. I3 is out of scope.

## Pins

Install root: `~/.cache/pfy/tools/agentgg/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` were directories under that root. No global install. Real `~/.agentgg` was not created.

- Node v22.23.0, npm 11.12.1.
- npm package `agentgg@0.1.29`. Registry `gitHead` `20cca9c1896ef4fee26c93a8730c0f46e4ca44d6`. Tarball `https://registry.npmjs.org/agentgg/-/agentgg-0.1.29.tgz`. `agentgg --version` printed `0.1.29`. Package directory about 115 MB.
- Official agents: `agentgg agents update --force` installed 266 agents, `v0.1.41`, under the cache `HOME` at `.agentgg/agentgg-agents`.
- semgrep-core 1.173.0 from the pinned linux-x64 wheel (`sha256` `cb21aa06246bdd79d3e9e7f9118ec7baecb1be39cf89c46e07af13b4128d7b79`), extracted the way the CLI installer does, into `.agentgg/semgrep/1.173.0/`. The scan log says it used that cache.
- Model: `qwen2.5-coder:7b-instruct` (Ollama size 4.7 GB), already on the host. No pull. Base URL `http://127.0.0.1:11434`. No API key. No `--live-validate`, no `--view`, no `--serve`.

## Commands

Install, agents, and the semgrep extract ran without the model lock. The eight scans ran as one `scripts/model_lock.sh` step.

```bash
export HOME=/home/mark/.cache/pfy/tools/agentgg/home
export XDG_CONFIG_HOME=$HOME/.config
export XDG_CACHE_HOME=$HOME/.cache
export npm_config_cache=/home/mark/.cache/pfy/tools/agentgg/npm-cache
export TMPDIR=/home/mark/.cache/pfy/tools/agentgg/tmp
npm install --ignore-scripts --no-fund --no-audit --no-package-lock \
  --prefix /home/mark/.cache/pfy/tools/agentgg/prefix agentgg@0.1.29
/home/mark/.cache/pfy/tools/agentgg/prefix/node_modules/.bin/agentgg agents update --force
```

At lock start, `ollama ps` was empty and MemAvailable was 62096452 KiB (about 59 GiB). The bar was model size plus 25 GiB (30 GiB). The warmup request sent `keep_alive: "2m"` because the model was not loaded. Nothing was unloaded.

Each scan:

```bash
agentgg scan <fixture> --diff HEAD -o <out> \
  --provider ollama --base-url http://127.0.0.1:11434 \
  --model qwen2.5-coder:7b-instruct \
  --concurrency 1 --max-turns 6 --no-fix --no-score --no-auto-exclude --verbose
```

Wall clock cap was 600 seconds. None hit it. Raw logs stay under `tmp/agentgg-bench/` and are not committed.

## Diffs

`git log` on `*trading*`, `*kalshi*`, and `*polymarket*` is empty, so there is no trading diff in this repo. The six historical diffs are deploy, release, and secrets paths. Each fixture is a two-commit git repo under `tmp/` whose `HEAD` diff is that file only (parent blob, or an add when the file was new). `agentgg scan --diff HEAD` reviewed that diff. These times are for that one-file repo, not a scan of the whole worktree.

| Id | Source | Path | Area |
|----|--------|------|------|
| h1-deploy-script | `889855bccf70005776689d8d10699104c799efe2` | `scripts/eval-deploy-ready.sh` | deploy |
| h2-deploy-runbook | `2ad493609ade568155eea28a788aa4dfef1d95cb` | `docs/ops/DEPLOY.md` | deploy |
| h3-deploy-profiles | `c18493b44aee49bdefb36fa10cad7f7ff47a7248` | `docs/ops/deployment-profiles.md` | deploy |
| h4-deploy-pins | `9c51e1ff1113c94d7db12b0468799b3421c1caff` | `examples/litellm-ollama/pins.env` | deploy |
| h5-secret-redact | `e558bd5001c65f2d76c6615288efa11608ca0d99` | `scripts/pfy_build_cloud.py` | secrets |
| h6-payload-gate | `df9a9cdabd46b744d433a479b96264dcb505babb` | `scripts/check_no_encoded_payloads.py` | secrets |
| p1-secret-log | planted | `handlers/session.py` | secrets |
| p2-shell-true | planted | `handlers/runner.py` | injection |

p1 adds a log line that prints a session token parameter. p2 passes that function's command argument to `subprocess.check_output` with `shell=True`.

## Results

Model column is `qwen2.5-coder:7b-instruct` for every row. `calls` is `state/usage.json`.

| Id | Seconds | Calls | Findings | Judgment |
|----|--------:|------:|---------:|----------|
| p1-secret-log | 16.4 | 5 | 0 | Miss |
| p2-shell-true | 28.7 | 7 | 1 | True positive, validator `uncertain` |
| h1-deploy-script | 37.4 | 9 | 2 | Both false positives |
| h2-deploy-runbook | 10.2 | 5 | 0 | None |
| h3-deploy-profiles | 9.9 | 5 | 0 | None |
| h4-deploy-pins | 9.2 | 5 | 0 | None |
| h6-payload-gate | 68.0 | 13 | 1 | False positive, validator `false-positive` |
| h5-secret-redact | 133.7 | 13 | 2 | Both false positives, validator `uncertain` |

p2: agent `python-command-injection` names `handlers/runner.py` and the `shell=True` call. That is the planted bug. The validator stayed `uncertain` because the proof of concept invented an HTTP route this file does not have. The finding also cites CWE-89.

p1: agent `secret-in-log` queued because a `.py` file exists, then semgrep produced 0 anchors. The rule file `exposure/secret-in-log` is `languages: [typescript, javascript]`. The log says `secret-in-log: no candidate files`. The two agents with no file scope ran (up to 6 turns) and reported nothing. Output tokens on that scan were 210 across 5 calls. The planted log line was never a finding.

h1: `bash-code-injection` flagged two hardcoded commands in the deploy-ready script (a `python3` invocation, and a fixed smoke-script path). Neither takes external input. The validator marked the first `false-positive` and the second `uncertain`. Both are false positives.

h6: `sandbox-runtime-script` flagged an `exec(compile(...))` string inside the gate's own negative fixture. That string is data the checker looks for. It is not executed. The validator marked `false-positive`.

h5: `redos` and `sandbox-runtime-script` flagged the static redaction regexes. Those patterns are compiled constants, not a pattern built from a request. The character classes are not nested quantifiers. Both verdicts are `uncertain`. Both are false positives.

Historical findings: 5 of 5 false positives. The validator rejected 2 and left 3 uncertain. That is a low count and a bad rate.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. The missing pass is a local SAST read of a risky diff. The shell plant shows the shape. The secret plant, which is the secrets half of that gap, was not caught, and the official rule behind that agent does not target Python.
2. Operator leverage: no. A person still has to throw out the historical findings, and a clean Python log of a token produces silence.
3. Evidence: yes. The commands above ran on this host.
4. Blast radius: yes. Apache-2.0 CLI in the cache, loopback Ollama, no key, no Docker, no in-repo copy. Deleting the cache leaves the pin and this report.

Modularity, all four, for a cache probe only:

1. Local code was required. The docs do not say the secret-in-log prefilter is JavaScript and TypeScript only.
2. The CLI entrypoint is bounded. The pack is 266 agents, selected by prefilters.
3. It sat under `~/.cache/pfy/tools/agentgg/` and did not become the product runtime.
4. Deleting that directory does not remove the catalog pin or this report.

The unpacked tree is over the 50 MB in-repo copy limit, so nothing was copied into the repo. The promote rule for this lane was both planted bugs, a manageable false-positive rate, and under 10 minutes per diff. The clock passed (slowest 133.7 seconds). The catch and the false-positive rate did not. Stage stays I0.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Python secret logging is invisible | The prefilter never seeds the agent, so the model is not asked | Treat a zero-finding Python secrets diff as "not scanned for logs", and keep the human review |
| Validator leaves a false positive as `uncertain` | An operator treats `uncertain` as a real bug | Read the line. On this probe the uncertain historical rows were hardcoded commands and static regexes |
| One-file fixture times are not whole-repo times | A scan of this worktree would also run agents that walk the tree | Do not budget a monorepo scan from these numbers |
| semgrep-core is a cached binary | A machine without the extract degrades prefilters and changes which agents run | Keep the 1.173.0 pin and the wheel digest with the install |
| Model lock | A second live lane waits, or MemAvailable drops below model size plus 25 GiB | This run held one lock for all eight scans. Below the bar, wait up to 30 minutes, then record HOST-BUSY and skip the live part |

## Next gate

Stay I0. A later probe can argue I2 if a Python secret written to a log is reported and the false injection findings on the deploy script and the redaction diff are gone. Wiring a gate still needs Tester and Reviewer. This lane does not wire one.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A diff that touches a deploy, release, or secrets path, after the diff exists and before anyone treats the change as cleared. Trading paths would be included if this repo ever has one. Nothing triggers it today.
2. What does it do, and which services does it read and write? It reads the git diff and a loopback Ollama model. It writes a scan directory (findings and `state/`). It does not call a hosted model and it does not write a gate result.
3. What does it trigger next? A person reads the findings. It does not start pregate, CI, or a merge.
4. Where does a human re-enter? On every finding. This probe's validator did not confirm a single true positive, and it missed a planted secret log. Mark GO is required before any gate uses it.
5. What stops two runs doing the same work? One output directory per diff, and the host model lock around the Ollama calls. This lane did not add a second runner.

Numbers: `eval/ev1107/agentgg/results.json`.
