# cedr evq1107

PROMOTE I1. Guard pins 43 skills offline and catches a one-line edit. The value gate is 2 of 4. Sync init exits 2 on this tree. This is not an H2 install gate.

`PROMOTE I1 Guard pins 43 skills offline and catches a one-line edit; value gate is 2 of 4 and Sync does not init this tree`

## Catalog overlap

Same job: pin skills and MCP servers, sync rules into each agent's files, and gate a skill before it is installed (gap H2). Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Cards that only mention the word skill are skill packs (mattpocock, ponytail, karpathy, marketing-council, gstack). They are the trees under test, not scanners.

| Tool | Stage | Why it covers this job | How cedr compares |
| --- | --- | --- | --- |
| SkillSpector | I3 | Static scan of a skill directory before copy. Features: static analysis, JSON receipt, no-llm. Tags include `#security` and `#skills`. | This lane scanned 43 directories in 116.51s: 20 real `.grok/skills` directories, 15 bootstrap, 8 mattpocock. SAFE 9, CAUTION 34, DO_NOT_INSTALL 0, llm false. 10 rows have findings (MP3, EA2, EA3, RP1). cedr lint on the same commit reported CG009 0 times. The lock's 43 is a different split (it keeps the 4 `.grok` symlinks and drops their mattpocock targets). SkillSpector does not write a hash lock and does not sync rules. |
| `scripts/pfy_skill_scan.py` | wrapper, I3 via SkillSpector | Advisory install check. Exit 0 is SAFE only. CAUTION exits 1. | The wrapper exit was 1. That is the H2 copy rule already. cedr does not replace it. |
| Bumblebee and `scripts/pfy_mcp_scan.py` | I2 | Advisory read of package lockfiles and MCP host configs. | On the throwaway root: CLEAN, 0 findings, 0.09s. cedr lock: 0 MCP servers. This repo has no MCP config in the tree. Neither tool was pointed at a real agent home. |
| `scripts/catalog_check.py` | first-party | Stage cards, TOOLS.md rows, entry numbers, and the self-pipeline rule. | It does not read SKILL.md or an MCP config. It checks the card this lane added. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer. Feature: skill audit. | Not run. It installs skills. It does not write a content lock. |
| OpenCode Skill Creator | I0 | Frontmatter schema check. | Overlaps the CG004 frontmatter errors only. That card already stayed I0. |
| Skills Manager | I0 | Skill distribution CLI. | A distributor. Not a pin. |
| Grok CLI bootstrap | I3 | Installs the skill tree we already keep. | The installer. The drift check is the missing piece, and this trial did not make cedr that check. |

H2 in the 2026-11-07 ranking is SkillSpector's job, and that trial already landed an advisory scan. cedr's extra, measured here, is the hash pin and the link/frontmatter lint.

Beats what we have for the install gate: no. The hash pin itself works.

## Pin

Host is linux x86_64. glibc 2.43 (the archive needs 2.34 or newer). Install path: `~/.cache/pfy/tools/cedr/`. No sudo, no copy into `~/.local/bin`.

```bash
mkdir -p ~/.cache/pfy/tools/cedr/dl ~/.cache/pfy/tools/cedr/bin
cd ~/.cache/pfy/tools/cedr/dl
curl -fsSL -o SHA256SUMS https://github.com/Sheernox/cedr/releases/download/v0.10.0/SHA256SUMS
curl -fsSL -o cedr-linux-x86_64.tar.gz https://github.com/Sheernox/cedr/releases/download/v0.10.0/cedr-linux-x86_64.tar.gz
sha256sum -c SHA256SUMS --ignore-missing
tar -xzf cedr-linux-x86_64.tar.gz
install -m 755 cedr-linux-x86_64/cedr ~/.cache/pfy/tools/cedr/bin/cedr
```

`sha256sum -c` printed `cedr-linux-x86_64.tar.gz: OK`.

| Piece | Value |
| --- | --- |
| Release | `v0.10.0` (published 2026-11-06) |
| Tag commit | `9cf2683e54a60e2f36f6f11fe715a7906e711597` (matches the entry; GitHub tag object type is commit) |
| Archive sha256 | `2bd8d14ef4456c36f2ded6e481953ea013b9c200fc093d39aed92bda44a2e634` |
| Binary sha256 | `d49387a3379f18bb886a87cd122b338dcac01e91604be7c9b2c01fdf4bde7c50` |
| Binary size | 31658632 bytes, ELF x86-64, dynamically linked |
| `cedr --version` | `cedr 0.10.0` |

The archive and the source tarball stay under `~/.cache/pfy/tools/cedr/`. Nothing from upstream is committed.

## Self-update off

Upstream `docs/update.md` at this tag: a normal command starts `cedr update --background` once a day unless `auto_update = false` in `$XDG_CONFIG_HOME/cedr/cli.toml`, or `CEDR_NO_AUTO_UPDATE` is set to anything other than empty, `0`, `false`, or `off`. `cedr update --auto off` writes the config key and does not look up a release.

First command, before any other run, with `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` under `~/.cache/pfy/tools/cedr/`:

```bash
CEDR_NO_AUTO_UPDATE=1 CEDR_TELEMETRY=0 DO_NOT_TRACK=1 cedr update --auto off
```

Printed `automatic updates: off` in 0.00s. `cli.toml` is one line: `auto_update = false`. The real `~/.config/cedr` was not created.

Network-off check uses `bwrap --unshare-net` and `strace -f -e trace=network` around a real command (`cedr guard lint` on an empty directory). `cedr --version` and `cedr guard lint --help` exit inside clap before `auto_start`, so they do not prove the flag.

| Case | Wall | AF_INET | State file | Binary hash |
| --- | --- | --- | --- | --- |
| `CEDR_NO_AUTO_UPDATE=1` and `auto_update = false` | 0.03s | 0 | none | unchanged |
| Flag unset, no `cli.toml` (control) | 18.02s | 4 connects to `127.0.0.53:53` | `update-check` plus `update.json` | unchanged |

The control's `update.json` error is a DNS failure while looking up the release. The binary was not replaced. Every later trial command used the flag, the config key, telemetry off, and `bwrap --unshare-net`. After those commands the state dir was still empty and the binary hash was still `d49387a3379f18bb886a87cd122b338dcac01e91604be7c9b2c01fdf4bde7c50`.

## What ran

Throwaway: `git worktree add --detach tmp/cedr-trial origin/main` inside this lane. Detached at `db42453`. Removed with `git worktree remove --force` at the end. cedr's cwd was that directory only. `HOME` and the XDG dirs stayed in the cache. No read of `~/.grok`, `~/.claude`, `~/.codex`, or `~/.config/opencode`.

Extra skill roots in the throwaway `.cedr/guard.toml` (relative, inside the copy):

```toml
version = 1
skills = [
  "bootstrap/grok-cli/skills",
  "bootstrap/grok-cli/skills-external/mattpocock",
]
```

`.grok/skills` is a built-in Grok root, so it was not listed again. On disk: 24 `.grok/skills` entries, 15 under `bootstrap/grok-cli/skills`, 8 under mattpocock. Four `.grok/skills` entries are symlinks into mattpocock: `code-review`, `grilling`, `tdd`, `to-spec`.

| Command | Exit | Wall | Result |
| --- | --- | --- | --- |
| `cedr guard lint` text | 1 | 0.06s | 9 findings |
| `cedr guard lint --format json` | 1 | 0.05s | same 9 |
| `cedr guard lock --offline` | 0 | 0.02s | `wrote ./.cedr/guard.lock: 43 skills, 0 MCP servers` |
| `cedr guard verify --format json` | 0 | 0.02s | `findings` empty |
| one extra line in `bootstrap/grok-cli/skills/adr/SKILL.md`, then verify | 1 | 0.02s | CV001, skill `adr` content changed. The line was restored. |
| `cedr sync init` on the unmodified tree | 2 | 0.01s | symlink refused |
| `cedr doctor --format json` | 0 | 0.02s | 33 checks, 2 warnings |

Route, Council, Bench, `guard outdated`, `guard push`, and `guard lock --introspect` were not run. Council wants one reviewer per vendor. Route wants `routes.toml` and plan readings. Doctor, with no org configured, skipped the API key (`key.present` skip: none needed). `route.config` and `sync.config` were warnings. Monitor reported every harness, including grok, as not on this machine, because the isolated home has no agent install. That is the isolation working. `guard.lock` in doctor said `0 Guard findings` after the clean verify. Lint itself had already exited 1.

## What Guard pins

The lock has 43 `[[skill]]` entries and 0 `[[mcp]]` entries. Split: 24 `.grok/skills`, 15 bootstrap skills, 4 mattpocock skills. The other 4 mattpocock skills are the symlink targets. Discovery keeps one entry per canonical directory (`a skill reached twice is one skill` in `discovery.rs`). The lock path is the first root, `.grok/skills/<name>`, and the hash walks the canonical directory. Docs say two roots make two entries. This binary keeps one.

Replacing those four symlinks with real copies, in the throwaway only, made verify report CV002 for `code-review`, `grilling`, `tdd`, and `to-spec` (added, not in the lock). The pin follows canonical identity. Turning a symlink into its own directory looks like a new skill.

Lint findings, all of them:

| Rule | Severity | Count | Where |
| --- | --- | --- | --- |
| CG002 | warning | 7 | Broken relative links |
| CG004 | error | 2 | `software-factory` frontmatter, both the `.grok` pointer and the mattpocock file |
| CG009 | error or warning | 0 | Ported SkillSpector patterns. None fired. |

CG004 is an unquoted colon in the description (`software factory: the tasks`). YAML then splits the line. The same bytes are valid enough for our skill loader and invalid for cedr.

CG002 on `.grok/skills/agent-loops`, `investigate`, and `worker-monitor` points at `../../../../docs/...`. From `bootstrap/grok-cli/skills/<name>/` that prefix is the repo root. From `.grok/skills/<name>/` it leaves the repo. `investigate` is byte-identical in the two trees, and only the `.grok` path was flagged. Guard saw a real depth bug. It does not compare the two trees to each other.

Of the 15 skill names in both trees, 9 trees are byte-identical and 6 differ (`agent-loops`, `best-effort-and-bot-budget-build-max`, `one-shot`, `prefer-behavior-and-fail-recover-tests`, `ui-is-the-app-design-in-loop`, `worker-monitor`). `.grok/skills/pipeline-retro` has no bootstrap twin. Guard's lock stores each path on its own, so those six pairs are not a finding until one side changes after the pin.

There is no MCP server in the tree (no `.grok/config.toml`, no `mcp.json`). The lock's MCP count is 0 because the repo has nothing to pin. The real Grok MCP config lives under `~/.grok`, which this lane does not read.

## What Sync would rewrite

On the unmodified throwaway, `cedr sync init` exits 2:

`sync: symlink refused: .grok/skills/to-spec; Sync never reads or writes through a link`

`cedr sync --dry-run` then exits 2 because `.cedr/sync.toml` was never written. There is no diff.

After the four symlinks were replaced with copies (throwaway only), init still exited 2: `skills: invalid front matter`. The message does not name the file. A YAML parse of every `SKILL.md` found two failures, both `software-factory` (the colon above). `examples/agentdescent-trial/skill/SKILL.md` has no front matter and is outside Sync's skill roots.

After that one description was quoted in the throwaway `.grok` copy, init exited 0 (0.03s) and wrote `.cedr/sync.toml` with targets `agents` and `grok`. `.cedr/rules/10-agents.md` matched `AGENTS.md` byte for byte (12930 bytes). The generated comment is added only when Sync emits `AGENTS.md`. Dry-run (`cedr sync --dry-run`, no `--force`) was 189831 bytes, 56 files, 0.01s:

| Path | What the diff does |
| --- | --- |
| `AGENTS.md` | Adds 1 line, deletes 0. The line is the generated-by-cedr comment. |
| `.agents/skills/**` | 55 new files, the `.grok/skills` tree copied out. `sync check` reports them as CS003 (generated file is missing) plus CS001 on `AGENTS.md`. |

`.grok/skills` itself was not in the diff (already the source). `bootstrap/grok-cli/skills` was not a Sync root. Applying that dry-run would put a third skill tree at `.agents/skills` and stamp `AGENTS.md`. This lane did not apply it.

A note on the dry-run says Grok holds the generated folder back until the folder is trusted. We did not run `grok --trust`.

## Gates

Value gate (3 of 4 required for I3):

| Test | Met | Why |
| --- | --- | --- |
| Gap fill | no | SkillSpector plus `pfy_skill_scan.py` already scan a skill before copy. Bumblebee plus `pfy_mcp_scan.py` already read MCP configs. cedr's pattern port added 0 hits on this tree. The hash pin is new and is not the H2 content check. |
| Operator leverage | no | Sync does not init this tree. A dry-run after two throwaway edits would stamp `AGENTS.md` and create `.agents/skills`. That fights the bootstrap skill tree as the source. Route and Council need accounts and other vendors. |
| Evidence | yes | Offline lock, clean verify, and CV001 on a one-line edit. Commands and timings are above. |
| Blast radius | yes | Apache-2.0, one 30 MB binary, no GPU, no account. Self-update is off and the network-off run proved it. Deleting `~/.cache/pfy/tools/cedr` leaves the catalog pin. |

Score 2 of 4.

Modularity gate (all 4, required for I2 local code and for I3):

| Test | Met | Why |
| --- | --- | --- |
| Local code needed | yes | Symlink dedupe, the frontmatter rejection, and the dry-run file list are CLI behavior, not something the README settles. |
| Bounded surface | yes | One binary. This trial used `guard` and `sync` only. |
| Isolatable | yes | Cache dir plus a throwaway worktree. It was not the product runtime. |
| Reversible | yes | The worktree is removed. The catalog row is the pin and this report. |

Score 4 of 4. I2 is for ambiguous potential plus a small local copy. Potential is medium: the pin works, the rules compiler does not fit this repo. That is I1, not I2 and not I3. I3 would also need a self-pipeline record if the card is later worded as a CI or review tool. This lane wires nothing.

## How this tool would run in the pipeline

1. What triggers it? A person asks for an advisory pin, or a dry-run, before copying a skill or editing shared rules. Nothing in the scheduler, pregate, or CI starts it.
2. What does it do, and which services does it read and write? It reads the repo skill trees and `AGENTS.md`. It can write `.cedr/guard.lock` and, if someone applies Sync, `.agents/skills` and a header on `AGENTS.md`. It does not call a model. It does not read a cedr.dev account when no org is configured.
3. What does it trigger next? Nothing. A failed `guard verify` is a report. It does not start a build, a test lane, or a landing.
4. Where does a human re-enter? On CV001 or CV002, on a Sync exit 2 (symlink or front matter), and before anyone applies a dry-run. Mark decides whether a later ticket wraps the pin. This lane does not.
5. What stops two runs doing the same work? They are not scheduled. Two writers of one `.cedr/guard.lock` would race. We do not run it on shared CI, so that race is not live. Eval lanes already keep separate stage cards.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Daily self-update | A writable install with the flag unset looks up GitHub and can replace the binary. The control did the lookup and stopped on DNS. | Keep `CEDR_NO_AUTO_UPDATE=1` and `auto_update = false`. Trials stay on `bwrap --unshare-net`. |
| Sync apply | `--force`, or a plain `cedr sync` after init, writes agent files. The dry-run would stamp `AGENTS.md` and add 55 files. | Do not pass `--force`. Dry-run only. This lane did not apply it. |
| Symlink pin | The lock names `.grok/skills/<name>` and skips the vendored path. Making the symlink a real directory looks like a new skill (CV002). | Read the lock path. Content edits of the canonical directory still fail verify. |
| Clean lint treated as a security pass | CG009 was 0 while SkillSpector flagged 10 rows, including the known MP3 "delete history" false positive on open-questions. | Keep `pfy_skill_scan.py` as the H2 check. A cedr lint exit of 0 would still not be that check. |
| Doctor on the wrong home | Monitor and MCP checks look at the isolated home, so they miss the real Grok install. | Do not point cedr at `~/.grok` to "fix" that. |

## Checks

`python3 scripts/catalog_check.py` exited 0. The new card is stage-only (no TOOLS.md row). `i1_cards_open` was 0. `python3 scripts/check_no_encoded_payloads.py` exited 0. No new script, so this lane adds no test file.

## Next gate

Stay I1. A later advisory pin can wrap `cedr guard verify` beside `pfy_skill_scan.py` on a fixture that has an MCP config and no skill-dir symlink. Tester and Reviewer come before any gate. No Feature GO. Catalog HOLD 70-75 was not touched.
