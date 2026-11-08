# Handoff: destructive-command-guard integrate lane (2026-11-08)

Branch `bot/integrate-destructive-command-guard-1108`. Not pushed. No pull request. The card `integration_stage` is still I2. `tier_ceiling` is still I1. No `receipt.json` is committed. A worktree run is not an I3 receipt.

## What landed

- `scripts/integrations/dcg/guard.sh` classifies argv and does not execute it. Exit 0 allows. Exit 126 denies. `PFY_DCG_DISABLE=1` is the only opt-out.
- `scripts/integrations/dcg/config.toml` turns off update checks, hook self-heal, and history. Same switches as the evq1107 probe.
- `scripts/integrate_lane.sh` calls the guard before every git and grok command (`run_checked`). A deny does not run the command. After a fast-forward land, a worktree that contains `eval/integrate/<slug>/run-on-main.sh` runs that script and then `catalog_apply_verdict.py`. A missing script keeps today's behavior. Apply refusal is logged and does not rewrite a card.
- `eval/integrate/destructive-command-guard/run-on-main.sh` writes the receipt only when `HEAD` is an ancestor of `origin/main`.
- `eval/integrate/destructive-command-guard/VERDICT.json` proposes I3.
- `docs/ops/integrate/destructive-command-guard.md` is the filled ticket.
- `docs/ops/INTEGRATE.md` documents `PFY_DCG_DISABLE=1`.

The pinned binary is `~/.cache/pfy/tools/destructive-command-guard/unpack/dcg` (v0.16.0, commit `665fcd8fc62cb5941e0484ddab012419f146523d`). Override with `PFY_DCG_BIN`. It is not vendored. The probe is `eval/evq1107/destructive-command-guard/probe.py` (12 of 12 destructive denied, 8 of 8 ordinary allowed).

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, and the `uses`, `features`, and `tags` on `data/stages/*.json` before writing code.

- TOOLSET-RANKING row 4 names destructive_command_guard as a catalog row for unattended workers, next to write-guard. It does not name a driver and it does not write `eval/integrate/<slug>/receipt.json`.
- write-guard-mcp (`uses`: write mediation above the cage mount) does not see the shell command. The evq1107 probe counted 0 shell ops and 0 shell tools.
- Sandlock (`uses`: rootless confinement of one fetched-skill install command) stops a process by effect. It does not classify command text. It is a sibling lane on this same driver.
- Sponsio (`uses`: pre-call ordering of one agent tool call) is a different check. It is not the lane shell path.
- llama-cpp-ngram-mod (`uses`: n-gram draft speed) is not this job. It is the other sibling on this driver. The driver comment names both siblings.
- SysKnife and claude-codex-settings are reference rows. There is no in-repo Grok hook config. This lane does not write `~/.grok`.
- `examples/eval-harness/` and `data/eval-lanes.json` run fixed make and python commands. They do not take an agent shell argv. `scripts/pfy_build_cloud.py` `run_command` starts the test gate and the grok process. Wrapping that call would not classify one shell command. The path that runs git and grok for this pipeline is `scripts/integrate_lane.sh`.

## Five questions

1. What triggers it? `scripts/integrate_lane.sh` is about to run git or grok. After a fast-forward land, the same driver runs `run-on-main.sh` when that file is in the worktree. A person can run `guard.sh` on argv.
2. What does it do, and which services does it read and write? It reads the argv and, when the binary is present, `scripts/integrations/dcg/config.toml`. It writes a one-line decision on stderr. It does not execute the command. The dcg child gets a clean environment (`PATH`, `LANG`, `NO_COLOR`, `DCG_CONFIG`, cache `HOME`). It does not write `~/.grok`. The receipt script writes only the path the caller passes.
3. What does it trigger next? Exit 0: the driver runs the command. Exit 126: the driver parks and does not run it. After land, `catalog_apply_verdict.py` runs when the verdict and the card are in the worktree.
4. Where does a human re-enter? Mark, to raise `tier_ceiling`. An operator, by setting `PFY_DCG_DISABLE=1` for one run, or by running a denied command by hand. A person, to delete `tmp/integrate/<slug>.dispatched` after reading `<slug>.parked`.
5. What stops two runs doing the same work? The guard is stateless and writes no lock file. Two checks both run. The driver marker `tmp/integrate/<slug>.dispatched` still stops a second lane (exit 2). `run-on-main.sh` writes no receipt when `HEAD` is not an ancestor of `origin/main`. `catalog_apply_verdict.py` is the only writer of `integration_stage`.

## Apply refusal

```text
python3 scripts/catalog_apply_verdict.py \
  --card data/stages/destructive-command-guard.json \
  --verdict eval/integrate/destructive-command-guard/VERDICT.json
```

Exit 1. Stderr:

```text
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I2: entry, pin, record, report, VERDICT, probe artifact; tier_ceiling I1 caps the evidence)
```

The card bytes did not change. `tier_ceiling` I1 is why I3 is refused. That is pending Mark. This lane does not edit the card.

## Fail safe

Timeout is 2 seconds (`timeout` sends the signal; uutils coreutils returns 124). Missing binary, bad JSON, a dcg error, or that timeout prints `dcg-fallback`. Ordinary commands exit 0. The built-in list still exits 126 for `rm -rf /`, `rm -rf ../`, `git push --force` / `-f` / `--force-with-lease`, `git reset --hard`, `git clean` with both `f` and `d` in a short option, `dd` with `of=/dev/...`, and `mkfs` / `mkfs.*`. `git push origin main` stays allowed.

Grok's own tool shell is inside the grok process. This lane does not install a hook under `~/.grok`, so that inner shell is not classified. The driver classifies the git and grok argv it starts.

## Tests

`python3 -m unittest` on `tests.test_dcg_fail_safe`, `tests.test_dcg_opt_out`, `tests.test_dcg_modular_ci`, `tests.test_dcg_no_double_work`, `tests.test_dcg_timeout`, `tests.test_dcg_receipt_fixture`, `tests.test_dcg_lane_hook`, `tests.test_integrate_lane_dispatched`, `tests.test_integrate_lane_land`. Pass. `python3 scripts/catalog_check.py` PASS. `python3 scripts/check_no_encoded_payloads.py` PASS.

`run-on-main.sh` was run on a fixture repo. Diverged `HEAD` exits nonzero and writes no file. `HEAD` equal to `origin/main` writes a receipt and does not execute `rm`.

## Self-review

Reviewed the diff against `origin/main`. The first VERDICT metric said the wired guard denied 12 commands. The evq1107 probe did that. This lane did not re-run those 12. The metric now names the probe and the wiring. The threshold stays 12 because that is the probe count.

Left as documented limits. A missing `guard.sh` fails open with a loud line. A missing binary still denies the built-in list. Argv is joined with spaces for the dcg posix parser. The receipt is written after the push and is not committed, so it is not in the landed SHA. Grok's inner tool shell is not classified. `catalog_apply_verdict.py` still refuses I3 because `tier_ceiling` is I1. The card bytes stay the same.
