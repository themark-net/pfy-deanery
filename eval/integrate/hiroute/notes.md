# hiroute integrate notes

`routing list` is the local-control command. Its schema says `network: local_control_only`, `effect: none`, and `model_call: never`. The runner uses the trial home under `~/.cache/pfy/tools/hiroute/` and does not bind a port.

`routing_agreement_of_20` is the verdict metric. It needs the decision model. This runner does not call that model. A list receipt is not that score. Do not treat the list as an I3 measurement.

The card stays as it is unless `scripts/catalog_apply_verdict.py` changes it. This lane does not hand-edit `integration_stage` or `tier_ceiling`.

The 2026-11-08 run on `d6088a477cf79b27c681c358ff0812d91e93c87f` wrote `eval/integrate/hiroute/receipt.json`. `routing list` returned 1 plan, alias `hiroute-eval-difficulty-route`. `model_call` was never. The version command's first line was 258 characters and contained a slash, so `tool_version` stayed `hiroute`.

Apply after that receipt refused:

```
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I1: entry, report; tier_ceiling I3 does not raise it)
```

Stage stays I2. The loop had already set `tier_ceiling` to I3. This run did not change it. `routing_agreement_of_20` was not re-run.
