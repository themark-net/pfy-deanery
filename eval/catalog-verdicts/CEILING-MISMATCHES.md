# Ceiling mismatches

This scan does not change integration_stage. A flagged card stays where it is. Mark decides any demotion.

Allowed stage is the lower of the evidence ceiling and tier_ceiling when the card has one. tier_ceiling is a cap from the catalog tier and posture. It does not raise a card whose evidence is weaker.

Evidence ceiling, from the evidence list only:

- I4 when an item starts with `submodule:` or `subtree:` and a valid main-run receipt is an ancestor of `origin/main`.
- I3 when the card has a valid main-run receipt: an evidence item `receipt:eval/integrate/<slug>/receipt.json` whose file parses, whose `run_kind` is `pipeline` or `gate`, and whose `main_sha` is an ancestor of `origin/main`.
- `make:` and `path:` are operator paths. They support I2. They do not support I3 or I4.
- I2 when an item is a measured probe: `results.json`, `check-results.json`, a name ending in `-results.json` or `-bench.json`, `receipt.json`, a `receipt:` item, `tools/_probe/`, or `probe:`.
- I1 when the list has any other artifact (notes, pin, entry, report, scan summary, VERDICT, summary, script).
- I0 when the evidence list is empty.

A card already at I3 or I4 without a valid receipt is flagged with `missing-main-receipt`, `receipt-malformed`, `receipt-sha-not-on-main`, or `git-unavailable`. The scan does not demote it. Cards below I3 do not get those codes.

Apply adds two write caps the scan does not need. A failing modularity gate caps the write at I1. A failing value gate caps the write at I2. Both gates must pass before a write of I3 or I4.

A tool whose uses, features, or tags cover CI, testing, or review cannot sit above I2 unless self_pipeline passes the same check as scripts/catalog_check.py (applied with evidence, not_applicable with a reason, or pending with grace). That check does not promote a card. Notes, a scan summary, and a report stay I1 even when tier_ceiling is I3.

Scanned 129 cards. Mismatches 11.

| Tool | Stage | Evidence ceiling | Tier ceiling | Allowed | Why |
| --- | --- | --- | --- | --- | --- |
| Antigravity-Manager | I1 | I1 | I0 | I0 | evidence I1: notes; tier_ceiling I0 caps the evidence |
| Bumblebee | I2 | I1 | I1 | I1 | evidence I1: notes, pin, report, VERDICT, script; tier_ceiling I1 agrees |
| Grok CLI bootstrap | I3 | I2 | I3 | I2 | evidence I2: make target, repo path; tier_ceiling I3 does not raise it; missing-main-receipt |
| HiRoute | I2 | I1 | I3 | I1 | evidence I1: entry, report; tier_ceiling I3 does not raise it |
| MLX + MLX-LM | I1 | I0 | I1 | I0 | evidence I0: no evidence listed; tier_ceiling I1 does not raise it |
| SkillSpector | I3 | I1 | I3 | I1 | evidence I1: entry, notes, pin, scan summary, report; tier_ceiling I3 does not raise it; missing-main-receipt |
| agent-cage (PNNL) | I3 | I2 | I3 | I2 | evidence I2: make target, repo path; tier_ceiling I3 does not raise it; missing-main-receipt |
| llama.cpp (server mode) | I1 | I0 | I1 | I0 | evidence I0: no evidence listed; tier_ceiling I1 does not raise it |
| project-process bootstrap | I3 | I2 | I3 | I2 | evidence I2: repo path; tier_ceiling I3 does not raise it; missing-main-receipt |
| skill-up | I3 | I1 | I3 | I1 | evidence I1: summary, report, entry; tier_ceiling I3 does not raise it; a self_pipeline record does not raise this evidence; missing-main-receipt |
| write-guard-mcp | I3 | I2 | I3 | I2 | evidence I2: make target, repo path; tier_ceiling I3 does not raise it; missing-main-receipt |

## Intent values outside the enum

Existing card intent strings are left in place. New verdict writes must use the enum or an alias.
Enum: `awareness`, `catalog_default`, `staged_evaluation`, `ad_hoc_probe`, `onboard`, `embedded`.
Aliases: `staged_eval` -> `staged_evaluation`, `adhoc_probe` -> `ad_hoc_probe`, `ad-hoc-probe` -> `ad_hoc_probe`, `ad-hoc_probe` -> `ad_hoc_probe`.

| Tool | Intent |
| --- | --- |
| AgenC | `demoted_adr0010` |
| Antigravity-Manager | `skip_install` |
| Atomic Task Graph (ATG) | `submodule_later` |
| Chroma (or LanceDB) | `watch` |
| DeepSeek-V4.1-Flash-1017 GGUF | `awareness_fit_gate_failed` |
| Exo (exoharness) | `pattern_extract_self_mod` |
| GraphJin | `watch` |
| Graphify | `watch` |
| Grok CLI bootstrap | `first_party` |
| Hermes Teammates | `blocked_on_hermes_wiring` |
| Kolibri-1 | `local_smoke_patched_llamacpp_gguf` |
| Laguna S 2.1 | `eval_under_250gb_pool` |
| LiteLLM | `smoke_path` |
| LiveKit | `ref_only` |
| MUE-X | `pattern_only` |
| Multica | `reference` |
| Ollama | `host_runtime` |
| Pipecat | `ref_only` |
| SkillSpector | `advisory_skill_scan` |
| SmythOS Studio | `reference` |
| Strata | `local_probe_stayed_i2` |
| adr-tools | `optional_pin` |
| agent-cage (PNNL) | `primary_harness` |
| agentplay | `design_reference` |
| asm (agent-skill-manager) | `evq1107_probe` |
| claude-code-unified-agents | `curated_paths_pack` |
| claude-codex-settings | `pattern_only` |
| codebase-memory-mcp | `smoke_path` |
| colibri | `local_probe_stayed_i1` |
| dsh-superagent | `design_reference` |
| freeapp | `ref_only` |
| llama.cpp ngram-mod | `speed_probe` |
| multi-agent-generator | `design_reference` |
| odai | `design_reference` |
| project-process bootstrap | `first_party` |
| repowise | `smoke_path` |
| skill-up | `trial_1107` |
| write-guard-mcp | `first_party` |
