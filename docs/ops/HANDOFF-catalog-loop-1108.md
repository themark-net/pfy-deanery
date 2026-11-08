# Handoff: catalog loop (2026-11-08)

Lane `loop` on `bot/loopbuild-loop-1108`. LIVE_HARD_OFF stays true. This lane did not install systemd units, did not enable a timer, did not run the real loop, and did not push.

## What landed

Commit `loop: add the catalog loop tick, eval lane, and hourly user units`:

- `scripts/catalog_loop.sh` runs one tick. It regenerates counts, the eval queue, the ceiling scan, and `eval/catalog-queue/needs-mark.tsv`. It applies landed verdicts, auto-raises ceilings, and launches lanes.
- `scripts/catalog_auto_raise.py`, `scripts/catalog_needs_mark.py`, and `scripts/catalog_card_guard.py`.
- `scripts/eval_lane.sh` ports the eval driver. The driver applies the verdict. The Build does not hand-edit the card.
- `ops/systemd/catalog-loop.service` and `catalog-loop.timer`. Hourly, `Persistent=true`, `RandomizedDelaySec=120`, `Type=oneshot`, `Nice=10`. The service bootstraps `scripts/loop_worktree.sh` from `origin/main`. It does not run from a checkout.
- `docs/eval/TOOLSET-RANKING.md` points trial verdicts at `data/stages/<slug>.json`, `VERDICT.json`, and `scripts/catalog_apply_verdict.py`. `data/tool_integration_stages.json` is retired.
- `docs/ops/INTEGRATE.md` names the loop as the trigger.
- `pipelines/catalog/loop.latest.json` is gitignored. The state-dir copy is the status source.

Commit `loop: add portable catalog pipeline skills`:

- `scripts/catalog_intake_dedupe.py`.
- Skills `catalog-intake-dedupe`, `catalog-eval-lane`, `catalog-integrate-lane`, `catalog-apply-and-ceiling`, and `catalog-loop-operator`. Source of truth is `bootstrap/grok-cli/skills/<name>/SKILL.md`. `.grok/skills/<name>/SKILL.md` is a full copy of the same bytes.
- `scripts/eval_lane.sh` and `scripts/integrate_lane.sh` tell the Build to read the skill, then the ticket. Each progress file gets `skill=<name> sha=<git hash-object of SKILL.md>`.
- `AGENTS.md` lists the five skills in the portable-skills line and in the catalog-first section.

Generated catalog commits inside a tick use author `catalog-loop <catalog-loop@localhost>`. Lane commits keep the existing git identity.

## Operator install

Copy the units, then enable the timer. The first tick can be manual.

```bash
cp ops/systemd/catalog-loop.service ops/systemd/catalog-loop.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now catalog-loop.timer
systemctl --user start catalog-loop.service
```

## Retire the counts timer

The loop regenerates counts and commits them with the rest of the tick. It does not call `scripts/catalog_counts_publish.sh`. The old unit files stay, because existing tests read them. Retire the timer with:

```bash
systemctl --user disable --now catalog-counts.timer
```

Do not delete `ops/systemd/catalog-counts.service` or `ops/systemd/catalog-counts.timer`. If both timers stay enabled they share `scripts/loop_worktree.sh`'s lock.

## State dir

Default state dir: `$PFY_LOOP_STATE`, or `$HOME/DEVELOP/pfy-mentat/tmp/loop` when unset.

```text
STATE/loop.lock
STATE/loop.latest.json
STATE/tails.json
STATE/STOP
STATE/QUOTA_STOP
STATE/QUOTA_STOP.auto
STATE/started-YYYYMMDD
STATE/eval/<slug>.dispatched
STATE/eval/<slug>.pid
STATE/eval/<slug>.parked
STATE/eval/<slug>.done
STATE/eval/LANDED_<slug>
STATE/eval/wt/<slug>
STATE/integrate/<slug>.dispatched
STATE/integrate/LANDED_<slug>
```

The loop worktree is `$PFY_LOOP_WT` (default `$HOME/DEVELOP/pfy-mentat/tmp/loop/wt`). `scripts/loop_worktree.sh` fetches and resets that worktree to `origin/main` on each tick.

`loop.latest.json` fields: `tick_started`, `tick_finished` (each `{"utc","pt"}`), `origin_main`, `status` (`ok`, `stopped`, `busy`, `quota`, `error`), `stop_files`, `running` (`slug`, `kind`, `unit`, `pid`, `source`, plus `pid_age_s` and `hang_same_tail` when set), `started_today`, `cap` (`{"running":4,"daily":20}`), `slots`, `launched`, `skipped_taken`, `needs_mark_count`, `needs_mark_changed`, `applied`, `auto_raised`, `refused`, `parked`, `errors`.

`status` is `quota` when the daily cap blocks launches. It is `ok` when the running cap is the only reason `slots` is 0. A busy lock exits 0 with `busy` and launches nothing.

## Markers

A slug is taken when any of these exist for it: `.dispatched`, a live `.pid` (the pid's `/proc` entry exists), `LANDED_<slug>`, `.done`, `.parked`.

Dirs checked:

- `$PFY_LOOP_STATE/eval` and `$PFY_LOOP_STATE/integrate`
- `$PFY_INTEGRATE_ROOT` (default `$HOME/DEVELOP/pfy-mentat/tmp/integrate`)
- `$PFY_INTEGRATE2_ROOT` for integrate kind (default `$HOME/DEVELOP/pfy-mentat/tmp/integrate2`)
- `$PFY_EVQ_ROOT` for eval kind (default `$HOME/DEVELOP/pfy-mentat/tmp/evq`)

The loop writes `$PFY_LOOP_STATE/<kind>/<slug>.dispatched` with noclobber before `systemd-run`. That file is not the integrate lane's `tmp/integrate/<slug>.dispatched`. Eval continues when `PFY_LANE_FROM_LOOP=1` and the marker already exists. A second eval start without that variable exits 2.

Retry: read `<dir>/<slug>.parked`, then remove `.dispatched`. A leftover `.parked` still counts as taken, so remove it in the same step only after the reason is read and a retry is intended. Do not remove `LANDED_` or `.done` after a land. A tick that fails inside `systemd-run` leaves `.dispatched` and no `.parked`. Read `errors` in `loop.latest.json`, then remove that `.dispatched` to retry.

`STOP` or human `QUOTA_STOP` in the state dir stops the tick with status `stopped`. Do not clear a human `QUOTA_STOP`. Reaching 20 starts in one America/Los_Angeles day writes `QUOTA_STOP.auto`. A later tick on a new day removes only that auto file when the new day's counter is under 20.

## integrate2

`tmp/integrate2` is a live batch. This loop reads its marker files and counts pid files whose `/proc` entry exists. Those live pids count toward the cap of 4. The loop does not edit that directory and does not signal its processes.

## needs-mark.tsv

Path: `eval/catalog-queue/needs-mark.tsv`. Header: `slug`, `kind`, `reason`, `evidence`, `since`. Bytes are deterministic. The file is replaced only when the bytes change.

`kind` is one of: `ceiling`, `gpu`, `pull-over-25gb`, `excluded`, `demotion-flag`, `parked`, `risky-class`.

Sources: `scripts/integrate_intake.py` flags, `eval/catalog-queue/exclusions.tsv` rows whose reason says Mark, GPU, or 25 GB, demotion rows in `eval/catalog-verdicts/CEILING-MISMATCHES.md`, auto-raise refusals by class, and parked lane files. Evidence paths are repo-relative. `since` is an ISO date from the parked file's first line, otherwise `-`.

The loop does not launch a slug that appears in this file.

`needs-mark.tsv` is written after auto-raise in the same tick. A ceiling that this tick raised to I3 is not listed as below I3, so the slug can still launch. Auto-raise refusals are still rows, because those cards are unchanged.

## Auto-raise rule and word lists

`scripts/catalog_auto_raise.py` raises `tier_ceiling` to I3 only when `value_gate` and `modularity_gate` pass on the latest `VERDICT.json` and the risk class is `none`. It appends `ceiling_history` with `from`, `to`, `by` = `catalog_loop`, `date`, `reason`, and `evidence`. It never demotes, never lowers a ceiling, and never touches a card above I3.

`risk_class` on the card wins when it is `security`, `live-money`, `runtime-takeover`, or `none`. Anything else in that field is `unknown`. With no field, the keyword classifier runs. No tokens, or two classes at once, is `unknown`. Unknown goes to needs-mark and is not raised. `risk_class: none` wins over keyword classes. It does not override GPU, size, or release.

Tokenizer: `[a-z0-9]+(?:-[a-z0-9]+)*` on the lowercased text of `uses`, `features`, `tags`, `catalog_tags`, and `next_gate`. These tokens must match the script.

- security (whole token): security, secret, secrets, credential, credentials, password, pentest, penetration, exploit, vulnerability, sast, keyring
- live-money (whole token): trading, broker, payment, payments, wallet, invoice, bank, funds, stripe, live-money
- runtime-takeover (whole token): runtime-takeover, takeover, privilege, sudo, rootkit, host-control
- GPU: `weights` matches only as a whole token. `gpu`, `vulkan`, `rocm`, `hip`, and `cuda` also match as a hyphen part, so `cpu-gpu` matches and `open-weights` does not.
- release (whole token or hyphen part): release, deploy, deployment
- size: a number strictly greater than 25 followed by `gb` or `gib`. An exclusion reason that says `25 gb` or `25gb` is `pull-over-25gb`.

GPU runs and model pulls over 25 GB always need Mark. Trading, release, deploy, and secrets work is never launched.

## Card guard

`scripts/catalog_card_guard.py` runs against current `origin/main` after the rebase. The diff is `git diff origin/main...HEAD`. It may revert only this lane's own disallowed edits to `tier_ceiling`, `integration_stage`, and `ceiling_history`. It does not rewrite a card the lane did not change. It does not restore from the lane's base snapshot. A test covers another lane landing a card on main mid-run: after rebase, that card stays as main left it.

## Five questions

1. What triggers it? The hourly user timer `catalog-loop.timer`, one manual `systemctl --user start catalog-loop.service`, or one `scripts/catalog_loop.sh` tick. The service fetches `origin/main` and runs through `scripts/loop_worktree.sh`.
2. What does it do, and which services does it read and write? It reads `origin/main`, `data/stages/<slug>.json`, verdicts, receipts, `eval/catalog-queue/exclusions.tsv`, intake flags, and lane markers including integrate2 pid files. It writes the counts files, `eval/catalog-queue/queue.tsv`, `needs-mark.tsv`, `eval/catalog-verdicts/CEILING-MISMATCHES.md`, ceiling and stage fields through the apply and raise scripts, and `STATE/loop.latest.json`. When bytes change and push is allowed, it commits as `catalog-loop` and fast-forwards `main`. It then starts at most `slots` user units through `systemd-run` (`PFY_SYSTEMD_RUN` in tests).
3. What does it trigger next? `scripts/integrate_lane.sh --slug <slug>` for an I2 card whose ceiling is already I3 or I4 and which has no receipt. Every other launchable card goes to `scripts/eval_lane.sh --slug <slug>`. The next tick applies a landed verdict or receipt.
4. Where does a human re-enter? `needs-mark.tsv`, a human `STOP` or `QUOTA_STOP`, and a parked lane after the `.parked` reason is read. GPU, pulls over 25 GB, security, live-money, runtime-takeover, unknown, release, and deploy stay with Mark. The operator installs the timer.
5. What stops two runs doing the same work? `flock -n` on `STATE/loop.lock`, the noclobber `.dispatched` marker, and the taken markers listed above. There is no global CI lock and no second scheduler.

## Catalog-first

Checked `docs/eval/TOOLSET-RANKING.md`, stage `uses` / `features` / `tags`, `docs/ops/INTEGRATE.md`, `docs/ops/integration-stages.md`, and the 1107 and 1108 handoffs before writing code.

- ATG: not used. It is not a catalog scheduler. Blocking on it would not tick the queue.
- neatroots: not vendored and not called. The tick keeps a neatroots-style hang signal: the last log line is stored in `STATE/tails.json`, and a repeated identical tail sets `hang_same_tail` next to `pid_age_s`.
- headson: not used. It previews logs. It does not claim a lane or raise a ceiling.
- Sponsio: not used. It is not this pregate. Skill install scan stays on `python3 bootstrap/grok-cli/scripts/verify_skills.py`.
- Brigade: the exclusive-claim idea is the flock plus the noclobber marker. Brigade itself is not vendored.
- SkillSpector, skill-up, and asm (agent-skill-manager): not used as the skill index. First-party skills already have `SKILL.md` frontmatter plus `bootstrap/grok-cli/manifest.json`. The offline check is `verify_skills.py` (`make smoke-grok-skills` without `INSTALLED=1`). SkillSpector's card says not to vendor it and not to make it a pregate. skill-up grades a with/without harness gap. asm is an I1 reference card, not this repo's installer.

`PFY_LOOP_NO_PUSH=1` and `--dry-run` push nothing. `--dry-run` does not launch. `PFY_LOOP_NO_PUSH=1` still launches.
