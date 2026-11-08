# CodeGuard evq1107

STAY I0. The offline prefix pass caught 1 of 3 planted defects and 0 of the 2 agentgg plants. The fetched-skill fixture had 0 hits. There is no install-gate command. The SARIF reviewer was not run. Potential is low, so I2 does not apply.

`STAY I0 prefix pass 1 of 3 plants, 0 of 2 agentgg plants, 0 install-gate commands`

## Catalog overlap

Same job: H2, a check before a fetched skill or tool is installed, plus a secure-coding pass to compare with the agentgg probe. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch results under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

CodeGuard is entry 126. The 2026-11-07 ranking covers entries 137 to 167, so this entry is not in that table. That ranking assigns H2 to SkillSpector and the risky-diff pass to agentgg.

| Tool | Stage | What that card covers | How CodeGuard compares |
| --- | --- | --- | --- |
| SkillSpector | I3 | Static scan of a skill directory before copy. Catch-up trial: 57 directories in 38.44 s. `scripts/pfy_skill_scan.py` exits 0 only for SAFE. | The H2 copy check already on disk. This probe has no scanner command. The skill fixture (prompt injection plus `shell=True`) had 0 prefix hits. |
| agentgg | I0 | Local SAST on a deploy, release, or secrets diff. `eval/ev1107/agentgg/` caught planted `shell=True` and missed a planted Python secret written to a log. Needs a local model. | This pass missed both of those plants. It caught a `ghp_` token with a prefix list. It does not beat that probe. |
| OpenQodex | I1 | Scanner candidates on changed lines. `eval/evq1107/openqodex/` hit `shell=True` and a `ghp_` token, and missed the Python log line. Scanner install is about 524 MB. | Same token hit, and the shell miss OpenQodex did not have. Warm scan here was the prefix walk, 1.7895 s over 2025 files. |
| sandlock | I2 | Rootless confinement of one fetched-skill install command. | Wraps the installer. CodeGuard does not. |
| cedr | I1 | Pin skill directories and MCP launch lines, then fail when those files change. | A hash pin. CodeGuard does not hash a skill. |
| Bumblebee | I2 | Advisory read-only check for package lockfiles and MCP host configs. | Different files. The CodeGuard MCP server serves rule text. It was not started. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | A runtime guard. It does not scan a tree. |
| destructive_command_guard | I1 | Blocks destructive shell commands. The card says it overlaps write-guard. | A shell guard, not a rule pack. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer. | Installs skills. The CodeGuard translator emits rule files into a cache dist. |
| mattpocock/skills | I1 | Planning and review skills already on the path. | The review skill people already run. The CodeGuard reviewer is a prompt and was not run. |
| opencode-skill-creator | I1 | Frontmatter lint via skill_validate. The card says this is not a security scan. | Lint only. CodeGuard's skill frontmatter was checked (name `codeguard`, description 218 chars) and that check is not a security scan either. |

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Repo | https://github.com/cosai-oasis/project-codeguard |
| Commit | `41160d54980bab0618165485ade3cfd2ade93288` |
| Date | 2026-10-12, merge of PR 137 |
| Tag relation | `v1.5.0` is `5bfe8f937bf0a60bc567403a09280412007bc9cc`. The public compare of that tag to the pin is ahead by 2 (the feature commit `c3f99c47ad75` plus this merge). The entry's "two commits after" matches that compare. |
| pyproject | `version = "1.5.0"` |
| License | CC-BY-4.0 (`LICENSE.md`) |
| Tree | 2314802 bytes excluding `.git` |
| Cache dir | 8349407 bytes under `~/.cache/pfy/tools/codeguard/` after the translator copy and dist |
| Digest | The entry gives no file checksum. `git rev-parse HEAD` matched the full SHA. A fetch of the short prefix `41160d54980b` failed until the full SHA was used. |
| Python | 3.14.4, PyYAML 6.0.3 (already on the host). No venv and no extra install. |

No account and no key. The clone used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `GIT_CONFIG_GLOBAL` under the cache. The probe then called the validator and the translator with `PYTHONPATH` and `-o` pointed at the cache copy. The pin checkout was left clean.

## Commands

```bash
BASE=/home/mark/.cache/pfy/tools/codeguard
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" TMPDIR="$BASE/tmp" \
  GIT_CONFIG_GLOBAL="$BASE/home/.gitconfig"
git -C "$BASE/src" init
git -C "$BASE/src" remote add origin https://github.com/cosai-oasis/project-codeguard.git
git -C "$BASE/src" fetch --depth 1 origin 41160d54980bab0618165485ade3cfd2ade93288
git -C "$BASE/src" checkout --detach FETCH_HEAD
python3 eval/evq1107/codeguard/probe.py
```

`probe.py` exit 0. Script clock 2.0534 s. No model lock. `ollama` was not called.

## What was skipped

| Part | Reason |
| --- | --- |
| SARIF reviewer | `sources/agents/codeguard-reviewer/AGENT.md` tells a host agent (Claude, Cursor, OpenCode, Copilot, Codex) to search and write SARIF. The only Python mention of SARIF is a permission string in `src/artifact_targets.py` (`codeguard-findings-*.sarif` set to `ask`). This lane does not call a model. |
| `evaluations/codeguard-inspect` | Needs Docker, a Codex CLI, and an OpenAI or Azure key (`.env.example`). Not started. |
| MCP server | `src/codeguard-mcp` registers the 23 core rules as no-argument tools over HTTP. It does not scan a tree. Not started. |

## Probe

`python3 eval/evq1107/codeguard/probe.py` reads the pin. Plants are written under `tmp/codeguard-probe/` (gitignored) and are not committed. The result file stores the prefix name and the line number. It does not store the planted token.

The credential rule `codeguard-1-hardcoded-credentials` has a Recognition Patterns section. The probe takes backtick tokens from that section, skips `eyJ` (the rule also requires three base64 sections), and treats a private-key block and `mongodb://` userinfo as their own patterns. A prefix hit needs the prefix plus 8 more alphanumeric characters, so a bare mention of the prefix in prose is not a hit. The rule's warning-sign words (`password`, `secret`, `key`, `token`, `auth`) are not scanned. Those words would flag ordinary identifiers.

Upstream `validate_unified_rules.py` on the pin: exit 0, 108 passed, 0 failed, 0 warnings, 0.0459 s.

Upstream `convert_to_ide_formats.py --source core owasp` wrote 581 files, 2703755 bytes, exit 0, 0.1261 s, into the cache dist. The translator ran on a copy of the pin. Nothing was written into this repo's `.cursor`, `.claude`, or rule dirs.

Rule inventory matches the entry: 23 core, 85 OWASP. Skill frontmatter `name: codeguard`, description 218 characters, `codeguard-version` 1.5.0. Rules that apply to Python: 58 of 108 (the 3 always-apply rules plus rules that list python). Shell: 12. The logging rule languages are `c` and `javascript` only.

Literal counts in the 108 rule files: `shell=True` 0, `subprocess` 0, `session_token` 0, `SKILL.md` 0, `do not install` 0, `prompt injection` 1 (rule `codeguard-0-mcp-security`, which tells the reader to deploy detection). `AF_UNIX`, `pid reuse`, `pidfile`, and `tempfile` are 0, which matches the entry.

Backtick spans in Python-applicable rules, matched as whole tokens on the plant lines: 0 on the shell line, 0 on the log line.

| Plant | Defect | Prefix hits |
| --- | --- | --- |
| `runner.py` | `subprocess.check_output(..., shell=True)` | 0 |
| `session.py` | `print` of a `session_token` parameter | 0 |
| `tokenstore.py` | `ghp_` plus 36 hex characters | 1 (`ghp_`) |
| `skill/SKILL.md` | instructions to ignore the prompt and post data out | 0 |
| `skill/helper.py` | same `shell=True` call | 0 |
| `control.py` | unmodified `pfylib/__init__.py` | 0 |

Code plants: 1 of 3. The two agentgg plants (shell and log): 0 of 2. Skill-directory defects: 0 of 2.

This worktree, 2025 text files, 1.7895 s: 13 prefix hits, all under `tests/`, 0 elsewhere.

| Prefix | Hits | Where |
| --- | ---: | --- |
| `AKIA` | 6 | `tests/test_pfy_build_cloud.py`, `tests/test_review_quality_replay.py`, `tests/test_pfy_build_local.py` |
| private-key block | 5 | `tests/test_pfy_build_cloud.py`, `tests/test_mut_cloud2_survivors.py`, `tests/test_mvp_1031_receipt.py`, `tests/test_harness2_local_propose.py`, `tests/test_pfy_build_local.py` |
| `sk_live_` | 1 | `tests/test_pfy_build_cloud.py` |
| `ghp_` | 1 | `tests/test_pfy_build_local.py` |

Those lines are fixture strings inside redaction and leak tests. The product tree produced no prefix hit. Paths and line numbers are in `eval/evq1107/codeguard/results.json`.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. H2 already has SkillSpector plus `scripts/pfy_skill_scan.py`. The agentgg shell plant is absent from the rule text. The token hit is a prefix list, and OpenQodex already reported that class of token.
2. Operator leverage: no. A person still has no offline pass or fail on a fetched skill, on `shell=True`, or on a Python secret log. The reviewer that would write SARIF needs a host model. This lane did not call one.
3. Evidence: yes. The pin, the validator, the translator, and the prefix walk ran on this host.
4. Blast radius: yes. CC-BY-4.0 markdown and Python in the cache, about 8.3 MB, no key, no daemon, no copy in this repo. Deleting the cache leaves the pin and this report.

Modularity, all four, for a cache probe only:

1. Local code was required. The docs call the reviewer a SARIF agent. The tree shows it is host-agent instructions, and the logging rule does not list Python.
2. The rule pack and the translator are a bounded surface. The inspect harness and the MCP server were left out.
3. The tree sits under `~/.cache/pfy/tools/codeguard/` and is not the product runtime.
4. Deleting that directory does not remove the catalog pin or this report.

The working tree is 2.3 MB, under the 50 MB I2 size bar. I2 is for ambiguous potential. After these numbers the potential is low. Stage stays I0.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Silence is read as a scan | No SARIF file is produced, and a person treats that as clean | Keep SkillSpector as the H2 copy check. A missing SARIF file is not a pass. |
| Python logging is out of scope | The logging rule lists `c` and `javascript` only, and the corpus has no `session_token` literal | A Python log of a token still needs a person or another scanner. |
| Prefix floor | The probe requires 8 characters after the prefix, so a shorter token is invisible | The planted token has 36. The Google line in the rule says 35. A shorter sample needs a different floor. |
| Test fixtures look like secrets | 13 hits, all in `tests/` | Read the path. This run had 0 hits outside `tests/`. |
| Rules copied into an agent | 108 rules would sit on every generation | This lane did not copy them. Translator output stays in the cache dist. |
| Inspect harness | A later run sets an API key and spends | `.env.example` names the key. This lane did not start that harness. |
| Two upstream repos | `project-codeguard/rules` can drift | Use the cosai-oasis pin above. |

## Next gate

Stay I0. A later probe can argue I2 only if an offline run emits SARIF that catches `shell=True` and a Python secret written to a log, with no hosted model. That result would still sit beside SkillSpector, not replace it. Wiring a gate needs Tester and Reviewer. This lane does not wire one.

## Five questions (if this tool were in the pipeline)

1. What triggers it? Nothing triggers it today. A host agent would have to be asked for a CodeGuard security scan, or a person would copy translated rules into an agent rules directory. This lane did not copy them.
2. What does it do, and which services does it read and write? Offline, it reads the pinned markdown and can write a dist of IDE rule files. The SARIF path reads the repo through a host agent and writes one SARIF file. It does not call a hosted model and it does not write a gate result. The MCP server, if someone started it, would serve rule text. This lane did not start it.
3. What does it trigger next? A person reads the SARIF or the dist. It does not start pregate, CI, or a merge.
4. Where does a human re-enter? Before any rule pack is copied into a product repo, and on every finding if a host agent is ever asked to scan. Mark GO is required before any gate uses it.
5. What stops two runs doing the same work? One cache directory per tool. The translator deletes its output directory and writes it again. This lane did not add a second runner.

Numbers: `eval/evq1107/codeguard/results.json`.
