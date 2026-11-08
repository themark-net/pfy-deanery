# Handoff: three ceilings and the integrate2 lanes (2026-11-08)

Mark approval 2026-11-08 10:03am PT. No pull request. `integration_stage` on the three cards was written by `scripts/catalog_apply_verdict.py`. It was not typed in by hand.

## Part 1

`tier_ceiling` is I3 on only these cards. Each `rationale` and `provenance` cites that approval. Catalog tier A still computes I1. `catalog_stage_eval.py` keeps a higher existing ceiling. No other ceiling changed. No card was demoted.

| slug | stage | receipt | main_sha |
| --- | --- | --- | --- |
| destructive-command-guard | I3 | `eval/integrate/destructive-command-guard/receipt.json` | `c883782dfcc86bd7b070e6bd62e0e3cdc3fe7233` |
| sandlock | I3 | `eval/integrate/sandlock/receipt.json` | `679d4ffd32005e67dc1d0dde75aaddca9ac50970` |
| llama-cpp-ngram-mod | I3 | `eval/integrate/llama-cpp-ngram-mod/receipt.json` | `14b79a0a81d71e63c02007137010d8f0a17021a4` |

The dcg and sandlock receipts are the files already produced under `tmp/integrate/receipts/` after those lanes landed. The llama receipt was already on main. Each `main_sha` is an ancestor of `origin/main`. Evidence on each card is `receipt:eval/integrate/<slug>/receipt.json`. A second apply printed `STAY I3`.

`scripts/catalog_counts.py` rewrote `pipelines/catalog/counts.latest.json` and `pipelines/catalog/dashboard.latest.md`. Stage counts: I0 47, I1 60, I2 13, I3 9. Coverage stays `129 tools registered`.

`next_gate` text on these cards is unchanged. Sandlock and destructive-command-guard still mention the old I1 ceiling in that prose. The ceiling field is I3.

## Part 2 (running outside this commit)

Scheduler and lane drivers live under `/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/`. They are not in git. Live pids are in `STATUS.json` in that folder.

Thirteen lanes, at most 4 at once: atomic-task-graph-atg, bumblebee, codebase-memory-mcp, headson, hiroute, litellm, neatroots, ollama, opencode-mem, repowise, sponsio, strata, taste-skill. Each worktree is `tmp/integrate2/wt/<slug>`, cut from `origin/main`.

Intake runs first (`scripts/integrate_intake.py`). A ceiling below I3 does not get raised. The lane records proposed I3 and leaves the card stage unchanged when apply refuses. Bumblebee is not demoted. No other card is demoted. Ollama is not restarted or reconfigured. Local-model commands go through `scripts/model_lock.sh`. Main pushes take one flock. Light tests do not.

Markers in that folder: `LANDED_<slug>`, `<slug>.done`, `<slug>.parked`, `STOP`, `QUOTA_STOP`, `ALL_DONE`, `progress.md`.

## Human re-entry

Remove `<slug>.dispatched` only after reading `<slug>.parked`, when a retry is wanted. `STOP` parks new work. `QUOTA_STOP` stops new launches. Do not force-push. Do not edit the owner checkout `/home/mark/DEVELOP/pfy-mentat`.
