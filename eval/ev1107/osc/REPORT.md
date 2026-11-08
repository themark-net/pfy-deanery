# OpenCode Skill Creator eval (2026-11-07)

Verdict: STAY I0. `skill_validate` from `opencode-skill-creator@0.3.6` is a six-key frontmatter allowlist. On this repo it fails 33 of 68 `SKILL.md` directories. 30 of those fails are keys we keep on purpose (`argument-hint` 26, `disable-model-invocation` 4). It marks the incident-responder `shell=True` / `drop_caches` example valid. That example is the useful SkillSpector finding. This is not an install check beside SkillSpector. No wrapper script. Trigger evals were not run.

## Pins

| Item | Value |
| --- | --- |
| Package | `opencode-skill-creator@0.3.6` |
| Tarball sha256 | `eef1b5e9f9b9a77d744c39eade57a11a8233062ab50e812824c094fb8f627deb` (matches entry 139) |
| Tarball size | 79477 bytes. Unpacked package is about 303 kB. |
| Install | `~/.cache/pfy/tools/osc/prefix`, `--ignore-scripts --omit=dev` |
| Packages | 29, 56149420 bytes on disk |
| Direct dependency | `jsonc-parser@3.3.1` |
| Peer that npm installed | `@opencode-ai/plugin@1.19.5` (also `@opencode-ai/sdk@1.19.5`, `zod@4.1.8`, `effect@4.0.0-beta.83`) |
| Node | v22.23.0 (package engines: `>=18`) |
| npm | 11.12.1 |
| Auto-update | `OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0` |
| Sandbox | `bwrap --unshare-net --unshare-pid` |

The peer tree is why the install is 56 MB. The lightweight-copy limit in `docs/ops/integration-stages.md` is 50 MB. The package stays in the cache. It is not copied into the repo.

## Commands

Install, isolated home, empty npm user and global config so the real `~/.npmrc` is not the one npm reads:

```bash
BASE="$HOME/.cache/pfy/tools/osc"
mkdir -p "$BASE"/{home,xdg,cache,npm-cache,tmp,prefix,pack}
: > "$BASE/npmrc-empty"; : > "$BASE/npmrc-global"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg" XDG_CACHE_HOME="$BASE/cache"
export npm_config_cache="$BASE/npm-cache" npm_config_userconfig="$BASE/npmrc-empty"
export npm_config_globalconfig="$BASE/npmrc-global" TMPDIR="$BASE/tmp"
export OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0
npm pack opencode-skill-creator@0.3.6 --pack-destination "$BASE/pack"
npm install --prefix "$BASE/prefix" --ignore-scripts --omit=dev --no-fund --no-audit \
  "$BASE/pack/opencode-skill-creator-0.3.6.tgz"
```

`npm install` added 29 packages in 8.28s. `npm pack` sha256 matched the entry before install.

Validate. The harness is `eval/ev1107/osc/validate.mjs`. It loads `dist/skill-creator.js` with the same fake OpenCode ctx the entry smoke uses, then calls only `skill_validate`. It does not call `install`, `skill_eval`, or `skill_optimize_loop`.

```bash
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-net --die-with-parent --unshare-pid \
  --bind "$BASE/home" "$BASE/home" --bind "$BASE/xdg" "$BASE/xdg" \
  --bind "$BASE/cache" "$BASE/cache" --bind "$BASE/tmp" "$BASE/tmp" \
  --chdir "$WORK" \
  env -i HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg" XDG_CACHE_HOME="$BASE/cache" \
    TMPDIR="$BASE/tmp" OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0 PATH=/usr/bin:/bin LANG=C.UTF-8 \
  /usr/bin/node eval/ev1107/osc/validate.mjs "$BASE/tmp/spec.json"
```

Writable binds are only the cache home, XDG, cache, and tmp. The repo and `node_modules` stay on the read-only root. A first run from a cache copy of the harness and this run from the committed file agreed on every path, pass bit, and failing key.

## Numbers

Wall clock for the committed harness, including bwrap: 0.085s. stderr empty. 14 tools registered. One tool executed.

| Tree | Result |
| --- | --- |
| `bootstrap/grok-cli/skills` | 3 pass, 12 fail |
| `bootstrap/grok-cli/skills-external` | 24 pass, 6 fail |
| `bootstrap/project-process/skills` | 0 pass, 1 fail |
| `.grok/skills` | 7 pass, 13 fail |
| `.opencode/skills` | absent |
| `examples/agentdescent-trial/skill` | 0 pass, 1 fail (no frontmatter) |
| `eval/catchup-1107/skill-up/cases` | 1 pass (skill-up fixture, not in the SkillSpector 57) |

Totals: 68 directories, 35 pass, 33 fail. Per-skill rows: `eval/ev1107/osc/results.json`.

Fail reasons:

| Count | What failed |
| --- | --- |
| 26 | Unexpected key `argument-hint`. 25 are first-party (12 under `.grok/skills`, 12 under `bootstrap/grok-cli/skills`, plus `project-process`). One is vendored ponytail. The adr skill is the pattern: a `>` description is accepted, then `argument-hint` fails the allowlist. |
| 4 | Unexpected key `disable-model-invocation` on vendored mattpocock skills (`grill-me`, `implement`, `retro`, `to-spec`). |
| 2 | Unquoted `description` contains `: ` (colon space). Both software-factory copies, line 3. The message says the runtime will drop the skill. This lane did not start OpenCode, so that drop was not observed. |
| 1 | `examples/agentdescent-trial/skill` has no YAML frontmatter. It is a prompt excerpt, not a skill package. |

The only first-party fail that is not `argument-hint` is `.grok/skills/software-factory`. The vendored software-factory also sets `disable-model-invocation: true`. `skill_validate` returns on the unquoted colon first, so that key is not in `failing_keys` for that file. The 4 above are the files where the allowlist error is the one the tool returned.

Side effects of plugin load, both runs: the bundled skill was copied to `$XDG_CONFIG_HOME/opencode/skills/opencode-skill-creator/` (8 files). With auto-update off there was no update-check file and no file under `XDG_CACHE_HOME`. The cache `HOME` stayed empty. `~/.config/opencode` directory mtime did not change across pack, install, or either validate run.

## Comparison with SkillSpector

Source: `eval/catchup-1107/skillspector/scan-summary.json` (57 directories, static `--no-llm`). Ten skill dirs exist now that that scan did not cover. Five are under `.grok/skills`: grill-me, implement, pipeline-retro, retro, software-factory. Five are under mattpocock: grill-me, grilling, implement, retro, software-factory. `pipeline-retro` is only in `.grok/skills`. `grilling` is only in the vendored tree. On the shared 57: osc fails 28 and passes 29. SkillSpector has findings on 12 directories. Those split 6 / 6 against osc pass/fail, and the overlap is not the same issue.

What `skill_validate` catches that SkillSpector does not:

- The six-key allowlist. SkillSpector does not flag `argument-hint` or `disable-model-invocation`.
- The unquoted colon in the two software-factory descriptions.
- Missing frontmatter on the agentdescent fixture. SkillSpector recorded that directory as `CAUTION` with no findings.

What SkillSpector catches that `skill_validate` does not:

- `incident-responder`: HIGH `TM1` `shell=True` and `drop_caches`. osc says `Skill is valid!`.
- `monitoring-specialist`: MEDIUM `E1` example URLs and `requests.post`. osc pass.
- `performance-engineer`: MEDIUM `E1` example URL. osc pass.
- `orchestrator`: HIGH `MP3` "clear context" (the SkillSpector report calls this a false positive, recommendation stayed `SAFE`). osc pass.
- `marketing-council` (both copies): LOW `EA3` "beyond documented". osc pass.
- On the six directories where both fail, osc fails only on `argument-hint`. SkillSpector findings there are `EA3`, `MP3` "delete history", and `EA2`. Different checks.

SkillSpector also has 28 `CAUTION` rows with no findings (partial path references). osc passes 9 of those and fails 19, and those 19 fails are the allowlist, not the partial scan.

## Why there is no `scripts/pfy_skill_lint.py`

An advisory wrapper with exit 1 on any `skill_validate` fail would exit 1 on this repo because of keys we ship. People would ignore it. A wrapper that allowlists `argument-hint` and `disable-model-invocation` would hide the signal the tool is built to emit and would leave one colon warning plus a fixture. That is a different checker, and it still would not see the `shell=True` example. SkillSpector already covers the install-check job. skill-up already covers trigger evals. This lane does not add a script, so it adds no tests.

## Value gate (need 3 of 4 for I3)

1. Gap fill: no. It does not close a hole SkillSpector or skill-up leave open. The unique hits are an allowlist mismatch, one colon warning, and a fixture with no frontmatter.
2. Operator leverage: no. A day of glue still produces a command that fails a clean tree for keys we want.
3. Evidence: yes. The validate path ran offline on this repo's own skills. Receipt is `results.json`.
4. Blast radius: yes, if isolated. Apache-2.0, no weights, no model. The cost is a 56 MB peer tree in the cache and a bundled-skill write on every plugin load. Isolation held on this run.

Score: 2 of 4. Not I3.

## Modularity gate (all 4, required for I2)

1. Local code needed: yes. The allowlist and the colon rule are visible only by running the checker.
2. Bounded surface: yes. One npm package, one tool call.
3. Isolatable: yes, under `~/.cache/pfy/tools/osc`, as long as `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and auto-update are set. It is not the product runtime.
4. Reversible: yes. Deleting the cache leaves the pin and this entry.

I2 still does not fit. I2 is for ambiguous potential plus a lightweight copy under 50 MB. Potential is low after this run, not ambiguous. The installed tree is 56 MB. Stay I0. `tier_ceiling` stays `I1`. The ceiling is a cap, not a promotion.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Plugin load writes OpenCode config | Every `setup` copies the bundled skill into `$XDG_CONFIG_HOME/opencode/skills/` or `~/.config/opencode/skills/` | Point `HOME` and `XDG_CONFIG_HOME` at `~/.cache/pfy/tools/osc`. This run did. The real `~/.config/opencode` mtime did not change. |
| Auto-update | A daily registry fetch can delete a cached package | `OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0` and `bwrap --unshare-net`. No update-check file was written. |
| Allowlist vs our skills | 30 of 33 fails are keys we keep. A gate would block our own tree. | Do not wire it. STAY I0. |
| Colon warning over-read | The message says OpenCode will drop software-factory. This lane did not run OpenCode, so that drop was not observed. | Quote the description if an OpenCode session actually drops it. Do not adopt the plugin for that one line. |
| Security false pass | incident-responder passes `skill_validate` and fails the SkillSpector static scan. | Keep SkillSpector in front of skill imports. |
| Peer tree size | 56 MB, over the 50 MB copy limit, because of `@opencode-ai/plugin`. | Leave it in the cache. Do not commit `node_modules`. |

## Next gate

Stay I0. Reconsider only if upstream allowlists `argument-hint` and `disable-model-invocation`, or this repo drops those keys, and a later run still finds defects SkillSpector does not. Trigger evals (`skill_eval`, `skill_optimize_loop`) stay with skill-up and need a model lane. They were out of scope here. Do not wire this into pregate, CI, or any gate.

## Five questions, if this tool were in the pipeline

1. What triggers it? A person about to copy a fetched skill into a skills directory, beside `scripts/pfy_skill_scan.py`. Not a CI trigger. This lane does not wire it.
2. What does it do, and which services does it read and write? It reads one skill directory and checks frontmatter against six keys. Plugin load writes the bundled skill under `XDG_CONFIG_HOME`. It does not write the repo. With auto-update off it does not call the network.
3. What does it trigger next? Nothing. A person reads the failing keys.
4. Where does a human re-enter? On every fail, because a fail is usually an allowed extra key, and whenever the XDG write must go to a scratch directory instead of `~/.config/opencode`.
5. What stops two runs doing the same work? The repo read is safe to repeat. Two runs that share one `XDG_CONFIG_HOME` can race the bundled-skill copy. Give each run its own XDG directory under the cache. No model lock, because this path does not call a model.
