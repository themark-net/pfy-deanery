# SkillSpector catch-up (2026-11-07)

Verdict: PROMOTE I3. Static mode ran offline on nimo over every in-repo skill directory in 38.44 seconds. Triage found one useful true positive and a few explainable false positives. No `DO_NOT_INSTALL` recommendation.

## What ran

Install, worktree only, no global package:

- `uv` 0.9.26 created `tmp/skillspector/.venv` with CPython 3.12.12 (system `python3` is 3.14).
- `uv pip install "skillspector @ git+https://github.com/NVIDIA/SkillSpector.git@e7172462caf367736645f66c1aa154ca5f9c64dc"`
- `skillspector --version` printed `SkillSpector v2.12.0`. The venv is gitignored.

Scan: `skillspector scan <dir> --no-llm --format json` inside `bwrap --unshare-net`, `HOME` and caches under `tmp/skillspector/`. Four workers. `metadata.llm_requested` was false on every report. Wall clock 38.44s for 57 directories. Every scan exited 0.

Trees scanned:

| Tree | Skill dirs |
|------|------------|
| `bootstrap/grok-cli/skills` | 15 |
| `bootstrap/grok-cli/skills-external` | 25 |
| `bootstrap/project-process/skills` | 1 |
| `.grok/skills` | 15 |
| `examples/agentdescent-trial/skill` | 1 |
| `.opencode/skills` | absent |

`make skill-scan` covers the first four trees, plus `.opencode/skills` when that directory exists. It does not include the agentdescent fixture. An offline `make skill-scan` with `PFY_SKILLSPECTOR_BIN` set to the venv (receipt under `tmp/`, not `~/.pfy-mentat`) scanned 56 directories in about 137 seconds and exited 1 (`CAUTION` 36, `SAFE` 20, `llm` false). GNU make then reports status 2 for that failed recipe. That nonzero result is the advisory list, not a product failure.

Counts: `SAFE` 20, `CAUTION` 37, `DO_NOT_INSTALL` 0. Of the 37 `CAUTION` rows, 28 are score 0 with no findings. Those scans are `partial` because a path-like reference in the skill does not match a bundled file (the adr skill is the example: score 0, no issues, recommendation `CAUTION`). Nine `CAUTION` rows have findings. One `SAFE` row still has a finding (orchestrator). Machine summary: `eval/catchup-1107/skillspector/scan-summary.json`. Per-skill JSON stays under `tmp/skillspector/scans/` and is not committed.

## Triage

High findings only. No skill was `DO_NOT_INSTALL`.

| Skill | Finding | Class | Reason |
|-------|---------|-------|--------|
| `.grok/skills/open-questions` and `bootstrap/grok-cli/skills/open-questions` `SKILL.md:39` | HIGH `MP3` Memory Poisoning, "delete history" | False positive | The line says "do not delete history." The rule matched the negated phrase. |
| `bootstrap/grok-cli/skills-external/claude-unified-agents/orchestrator` `SKILL.md:157` | HIGH `MP3` Memory Poisoning, "clear context" | False positive | The line is "Provide clear context to each agent." Score stayed 20 and the recommendation stayed `SAFE`. |
| `bootstrap/grok-cli/skills-external/claude-unified-agents/incident-responder` `SKILL.md:370` and `:401` | HIGH `TM1` Tool Misuse, `shell=True` and `drop_caches` | True positive | The playbook includes an automation example that runs `subprocess.run` with `shell=True` on a journalctl pipeline and invokes `drop_caches` with `shell=True`. An agent that copies the example can run it. Recommendation `CAUTION`, score 30, so the wrapper exits 1. |

Follow-up, not edited in this lane: review the incident-responder automation example before that skill is copied into a live skills directory.

Other findings are in the summary (excessive-agency and example-URL hits). They are not high and not `DO_NOT_INSTALL`. `.grok/skills/prefer-behavior-and-fail-recover-tests` was `SAFE` at score 0 while the bootstrap copy was `CAUTION` at score 0 with no findings. Same partial-reference label, not a security finding.

## Wrapper

`scripts/pfy_skill_scan.py` runs static mode only (`--no-llm`) and drops provider env vars from the child. Lookup is `PFY_SKILLSPECTOR_BIN`, then `PATH`. A set but missing `PFY_SKILLSPECTOR_BIN` does not fall through. Receipt default is `$PFY_STATE_DIR/skill-scan.json` (`~/.pfy-mentat` when unset). Exit 0 is `SAFE` only. `CAUTION` exits 1 unless `--allow-caution`. Exit 2 is a missing binary or unreadable JSON, with a next step. Operator doc: `docs/ops/skill-scan.md`.

H2 rule in that doc: a fetched skill may be copied into a skills dir only after `scripts/pfy_skill_scan.py` exits 0 on it. The check is advisory. It is not in pregate, CI, or any existing gate. A blocking security gate needs Tester and Reviewer. That is a separate step.

## Tests

`python3 -m unittest tests.test_pfy_skill_scan` (stub binaries only): missing binary, flagged JSON, garbage, nonzero exit with no JSON, `CAUTION`, default receipt path, and a receipt path that cannot be written. Each failure path has a recovery run. Raw scanner JSON is removed before return, including when the receipt write fails.

`RED: treat CAUTION as safe (drop the allow_caution check in is_safe) -> tests.test_pfy_skill_scan.SkillScanTests.test_caution_is_not_safe_until_allow_caution`

The mutant was restored. The test passes again. The mutant is not committed.

## Catalog

Entry 148 status is I3. The stage card and the `TOOLS.md` row are `SkillSpector`. Scores are the weighted rubric truncated, same way harness2 recorded 59.5 as 59: `0.35*86 + 0.25*92 + 0.25*84 + 0.15*82 = 86.4`, recorded 86, tier A. `integration_stage` is I3 because this trial's promote rule was met. `tier_ceiling` stays `I3`. The 2026-11-07 re-rank on main set that ceiling for this trial, and `catalog_stage_eval.py` does not lower an existing ceiling. The A-tier formula alone would say `I1`. `--apply` does not rewrite `integration_stage`. The card also keeps the re-rank `entry` path and the `feature_go` and `catalog_hold_70_75` non-goals. Other tools' cards are unchanged. Coverage stays `85 tools registered`.

## Risks

- Score 0 plus `CAUTION` and no findings is a partial scan, not malware. The H2 copy rule still refuses it until the command exits 0. `--allow-caution` is a person override, not the copy rule.
- A `SAFE` recommendation can carry a HIGH finding when the score stays low. This trial's case was a false positive. A real high finding with a low score would pass the wrapper.
- Static rules are a filter, not proof. The trial cut the network so the OSV lookup could not run. The wrapper does not unshare the network itself.
- The installed tree is a gitignored venv. A later host needs the same pin or `PFY_SKILLSPECTOR_BIN`.

## Next gate

Tester and Reviewer before anyone wires this into pregate, CI, or a product gate. A baseline file can accept the known false positives if we want `make skill-scan` to exit 0 on our own trees. Do not treat this I3 as that gate.
