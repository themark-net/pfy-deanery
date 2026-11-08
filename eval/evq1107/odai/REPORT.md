# odai evq1107

STAY I0 reference: MIT governance skill restates checks pfy already holds and does not move the pfy build timeout

## What it is

odai (orziz/odai) is a task-governance skill, an optional orchestration skill, a provider-neutral CLI (`odai-cli`), and two DeepSeek Harness packages. The kernel asks five questions: the result the user wants, what is true, the smallest sufficient path, what counts as done, and where to stop. A clear low-risk task skips the extra files. Done requires evidence tied to the object. A model claim, a diff, a log, and a command result stay separate. Host routing and DSH are optional. The tree also contains care and crisis-safety references. This lane does not port them.

License is MIT. `LICENSE` and `cli/LICENSE` are the MIT grant. `cli/package.json`, `dsh/plugin/package.json`, and `dsh/agent/package.json` each set `"license": "MIT"`.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `ce7a999843ca42ecd84778561cb0ac7642c5648e` |
| Commit | 2026-10-29 20:45:33 +0800, `chore: advance DSH candidate to 0.3.3 after 0.3.2 release` |
| Versions | skill `0.7.1` (runtimeContract 9, schemaVersion 5); orchestration `0.2.3`; `odai-cli` `0.0.2`; DSH plugin and agent `0.3.3` |
| Fetch | 2 s. `git init`, `git fetch --depth 1 origin ce7a999843ca42ecd84778561cb0ac7642c5648e`, checkout. No upstream script. |
| Bytes | worktree 28312838 (assets 18830123, pets 5026958). `.git` 25122228. |
| Cache | `~/.cache/pfy/tools/odai/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `npm_config_cache` sat under `~/.cache/pfy/tools/odai`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

## Ideas, and the pfy file each would touch

1. Ask only when the missing answer changes the goal, scope, authorization, acceptance, risk, or the stop line. Touch `docs/ops/human-decision-inventory.md` and `bootstrap/grok-cli/skills/one-shot/SKILL.md`.
2. Done is the lightest evidence that can falsify the result. Touch `bootstrap/grok-cli/skills/prefer-behavior-and-fail-recover-tests/SKILL.md` and `docs/ops/loop-engineering.md`.
3. Load a playbook only for the current gap. Touch `bootstrap/grok-cli/skills/agent-loops/SKILL.md`.
4. Keep one resume record, and only when a later turn must continue. Touch `docs/ops/loop-engineering.md`. This lane's record is `eval/evq1107/odai/VERDICT`.
5. Name the object, the stop, and the rollback before a hard-to-undo action. Touch `docs/ops/PREGATE.md`.
6. A fetched skill cannot override authorization or completion. Touch `docs/build-dropins/skill-discovery.md`.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the 3 hour `./pfy build` timeout and two parked pregate FAILs. That section holds entry 166 for comparison. No entry from 137 to 167 closes B. This lane builds no pipeline step.

Same job, already covered: Finn Loop / eval-loop / 8-exits patterns I1 (exit cards), mattpocock/skills I1 (plan and review skills, tag `#review`), Hermes Agent (feedback loops) I1, karpathy-guidelines I1, gstack I1 (role recipes in docs), eval-harness (pfy) I1. project-process bootstrap is I3. Write mediation is write-guard-mcp I3. Isolation is agent-cage (PNNL) I3. Shell deny is destructive_command_guard I2. Skill import scan is SkillSpector I3.

Same job, still outside the product path: dsh-superagent I0 (entry 154 authorization docs; odai's DSH packages are 0.3.3 and this lane installs neither), Festival I1 (plan files; the probe left the timeout open), Squadra I1 (ack and a close check), Kander I1 (two-role done gate; N/A roles still reached done), Rulora I1 (loop counters; the host still stops Build), Open Steps I0 (stop nag on a git fingerprint), Sponsio I2 (call order), TeaQL Agent Kit I0, imcodes I0, Elephant-Goldfish I1 (fresh-eyes spec read; indirect on B), Foremerge I1 (pre-edit ledger). Odai is prompt doctrine on top of that set. It adds no mechanical check those cards lack, and the 3 hour build timeout stays put.

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no, evidence no (entry 166 smoke is commit metadata and exits 2; this lane ran no upstream script). Blast radius yes: MIT, no weights, worktree 28312838 bytes, skill install does not rewrite host settings until someone asks for routing, hooks, or DSH. Score 1 of 4.

Modularity (all 4 for a local copy): docs were enough, so local code was not required. The unit is a skill plus a CLI plus DSH packages plus pets, so the surface is not one package. The cache copy is isolatable and deleting it leaves the pin. 2 of 4. 28312838 bytes is under the 50 MB I2 cap. Potential is low, so I2 does not open.

`uses` and `features` do not name a CI, test, or review role token. No `self_pipeline` field. No gate wiring. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Second doctrine | A skill install stacks on the 8 exits and one-shot | Stay I0. Do not copy the skill into a home. |
| DSH or hook write | `dsh plugin add` or the routing installer edits a profile | The entry already forbids that install. This lane did not run it. |
| Care content | Crisis playbooks get treated as a pfy procedure | Leave `care.md` and `human-safety.md` upstream. Do not port them. |
| Gap B false pass | Prompt rules get counted as a fix for the 3 hour timeout | B stays pfy build and pregate. This verdict stays I0. |
| Pin drift | `main` moves past skill 0.7.1 | Pin the SHA. The intake smoke checks this SHA and exits 2. |

## Next gate

Stay I0 reference. Re-open only if a later ticket names one check in `bootstrap/grok-cli/skills/` that this text adds, and that check changes a real Build lane. No install, no code copy, no gate. Not a Feature GO.

## Pipeline questions

This lane does not put odai on a pipeline. The scheduler started it. It writes this directory, the card, and the entry Status line.

1. Trigger, if adopted later: a person names the skill on a task. Not this scheduler.
2. It would read the task and project files and write only what that task authorized. This lane called no model and used no account.
3. Next: nothing in pfy. Completion stays the lane's own evidence.
4. A human re-enters before any skill copy, any DSH install, any hook install, or any I1 trial.
5. One worktree per slug keeps this card private. Do not start a second read that installs into the same agent home.
