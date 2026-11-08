# Handoff: sandlock integrate lane (2026-11-08)

Lane `bot/integrate-sandlock-1108`. Not pushed. No pull request. `data/stages/sandlock.json` is unchanged. `integration_stage` stays I2. `tier_ceiling` stays I1. This lane does not reach I3. Apply refused, and that refusal is the expected stop.

## What landed

- `scripts/integrations/sandlock/wrap.py`: one install or one run. `PFY_SANDLOCK` defaults to `auto`.
- `scripts/integrations/sandlock/confine.py`: turns the passthrough argv into `sandlock run` for the real binary.
- `eval/integrate/sandlock/run-on-main.sh`: one fixture install and one fixture run, then the receipt JSON. Exits 1 when HEAD is not an ancestor of `origin/main`.
- `eval/integrate/sandlock/fixtures/hello.sh`: the harmless local tool. It writes `ok` to the path in `$1`.
- `eval/integrate/sandlock/VERDICT.json`: proposes I3 and names `receipt:eval/integrate/sandlock/receipt.json`.
- `eval/integrate/sandlock/notes.md`: receipt `log_path`. The receipt file itself is not in this branch.
- `docs/ops/integrate/sandlock.md`: the filled ticket.
- No edit to `scripts/integrate_lane.sh`. The destructive-command-guard lane already runs `eval/integrate/<slug>/run-on-main.sh` after land and then calls `catalog_apply_verdict.py`. A missing script keeps today's land. A script failure and an apply refusal are logged. The land still completes. The driver does not commit the receipt.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, and the `uses`, `features`, and `tags` on the stage cards before writing code.

- TOOLSET-RANKING names SkillSpector as the offline scan in front of a skill import. It does not name a sandbox for a fetched-tool install, and it does not write `eval/integrate/<slug>/receipt.json`.
- `integration-stages.md` defines I3 as onboard. It says not to flip `integration_stage` just because a ceiling allows it. The receipt rule lives in `docs/ops/INTEGRATE.md`.
- Sandlock (`uses`: rootless confinement of one fetched-skill install) is I2 with `tier_ceiling` I1. Its non-goals already say it does not replace SkillSpector, agent-cage, or write-guard.
- SkillSpector is I3. It statically scans a skill directory before copy. It does not confine the install process.
- write-guard-mcp is I3. It mediates writes. It does not run the fetched command.
- agent-cage (PNNL) is I3. It is the lab container. This lane does not start it.
- destructive-command-guard is I2 with `tier_ceiling` I1. It classifies shell text. It does not install a tool.
- smolvm is I1. Its card says Sandlock already confines an install faster and lighter. This lane does not start a microVM.
- runx is I0. A fetched skill runs when its directory is named. That is not an installer sandbox.
- Bumblebee is I2 with `tier_ceiling` I1. It checks lockfiles and MCP configs.
- `scripts/catalog_eval_queue.py` writes a queue file. It does not install a tool.
- No card's uses are "sandbox the eval-lane fetched-tool install and one tool run." This lane adds that wrapper. It does not add a stage card and it does not edit `docs/eval/TOOLSET-RANKING.md`.

## Five questions

1. What triggers it? A person, or `scripts/integrate_lane.sh` after land, runs `eval/integrate/sandlock/run-on-main.sh`. An eval lane opts in by calling `wrap.py` with `PFY_SANDLOCK` (default `auto`).
2. What does it do, and which services does it read and write? It reads `SANDLOCK_BIN` or the cache unpack binary through `confine.py`, the caller cache, and the fixture or command. It writes the stage directory, a per-cache success receipt, and stderr `sandlock: unsandboxed` when it falls open. On main, after land, the driver writes `eval/integrate/sandlock/receipt.json`. No hosted service, no account, no sudo, no model lock.
3. What does it trigger next? The driver, using the hook already on main, calls `scripts/catalog_apply_verdict.py`. Apply refuses I3 under ceiling I1 and leaves the card bytes unchanged. The receipt JSON stays in the worktree. The driver does not commit it.
4. Where does a human re-enter? Mark, to raise `tier_ceiling` above I1. A person, if a command that already started fails because the profile is too tight: widen the grants in `confine.py`, or set `PFY_SANDLOCK=off`. `tmp/STOP` parks the driver. This lane does not copy a stage directory into `.grok/skills` or `bootstrap/grok-cli/skills`.
5. What stops two runs doing the same work? The driver marker `tmp/integrate/sandlock.dispatched` (a second start exits 2). Inside one call, an advisory lock on `<cache>/lock` and a success receipt keyed by action, the exact command, and `SANDLOCK_BIN`. A second successful wrap with the same binary exits 0 and does not run the command. Different caches do not share the lock. There is no global lock.

## Failure mode

`PFY_SANDLOCK=auto` sandboxes `install` only, and only after `SANDLOCK_BIN` passes a `true` self-test. `all` also sandboxes `run`. `off` never sandboxes. wrap.py does not search `PATH`. A missing or non-executable `SANDLOCK_BIN` logs `sandlock: unsandboxed` and runs the command once.

Self-test timeout is 30 seconds. Command timeout is 120 seconds. A timeout or error before the starter marker logs `sandlock: unsandboxed` and runs the command once. A command that already started keeps its exit code, including 124. There is no second unsandboxed attempt after a start. A profile denial after start is that exit code. This is not a deny-guard.

The success key includes `SANDLOCK_BIN`. The flag test's missing-binary install reuses the install cache and the same command. A key of only action plus command would skip that call. An empty `SANDLOCK_BIN` is a different key, so the unsandboxed call still runs. The same binary still skips.

`run-on-main.sh` points `SANDLOCK_BIN` at `confine.py` and `SANDLOCK_REAL` at `~/.cache/pfy/tools/sandlock/unpack/sandlock` when `SANDLOCK_BIN` is unset and that file is executable. confine.py uses read grants on `/usr`, `/lib`, `/lib64`, `/bin`, and `/etc`, write on the stage and the marker directory, `--clean-env`, and `--timeout 120`. It does not call `sandlock ps` or `kill`.

Lane cache: `PFY_SANDLOCK_CACHE`, or `~/.cache/pfy/tools/integrate-sandlock/lane`. Delete that directory to force the fixture to run again.

## Apply refusal

Command:

```bash
python3 scripts/catalog_apply_verdict.py --card data/stages/sandlock.json --verdict eval/integrate/sandlock/VERDICT.json
```

Exit 1. Stderr:

```text
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I2: entry, pin, report, VERDICT, probe artifact; tier_ceiling I1 caps the evidence)
```

`git diff -- data/stages/sandlock.json` was empty after that command. The card did not gain a `receipt:` line. `self_pipeline` was not added. Sandlock's uses do not match the catalog_check CI, testing, or review words.

`eval/integrate/sandlock/receipt.json` is not committed here. A branch SHA is not an I3 receipt. After land, the driver runs `run-on-main.sh` in the worktree. That write is not pushed. The destructive-command-guard handoff records the same limit.

## Real binary check

On this host the unpack binary is sandlock 0.8.9. A temp checkout whose HEAD was an ancestor of its own `origin/main` ran `run-on-main.sh` with `SANDLOCK_BIN` unset, so the script selected `confine.py` and that binary. Stderr was empty. The stage file was `ok`. The temp receipt `did` was "Sandboxed one local fixture install and one fixture tool run. Both commands exited 0." `tool_version` was `sandlock 0.8.9`. That file was deleted. It is not the main receipt.

The unit tests use a passthrough double. They do not need the real binary.

## Tests

Grill tests are in `tests/test_integrate_sandlock_idempotency.py`, `tests/test_integrate_sandlock_modular_ci.py`, `tests/test_integrate_sandlock_flag.py`, and `tests/test_integrate_sandlock_fallback.py`. The flag test's third call reuses `cache-install-default`. `Path.mkdir` raises if that directory exists, so the test uses `mkdir(exist_ok=True)`. The assertions are the grill assertions. The ticket text was not edited.

Also: `tests/test_integrate_sandlock_run_on_main.py` (fixture repo: ancestor writes the receipt and sandboxes both steps; a later commit exits nonzero and writes nothing), `tests/test_integrate_sandlock_confine.py`, `tests/test_integrate_sandlock_lane_hook.py` (the landed driver runs the script, logs apply refusal, and does not push the receipt). Existing lane and dcg tests still pass.

`python3 scripts/catalog_check.py` passed. `python3 scripts/check_no_encoded_payloads.py` passed. No model call. `git fetch origin` showed this branch first at `14b79a0a`, then behind the destructive-command-guard commits. The branch was fast-forwarded to `c883782d` before this commit.

## Self-review

`origin/main` gained the destructive-command-guard lane while this worktree was open (`3af18e46`, `c883782d`). This branch fast-forwards onto those commits. The driver hook in that lane already runs `run-on-main.sh` and apply. This lane does not edit `scripts/integrate_lane.sh` again.

Checked the diff against that `origin/main` for correctness, scope, secrets, file ownership, tests that fail without the new behavior, and the stage rules. No card edit. No forbidden shared file (`Makefile`, `.github/`, `scripts/pregate.sh`, `scripts/test_select.py`, `scripts/run_tests.py`, `scripts/test_cache.py`, `docs/eval/TOOLSET-RANKING.md`, `AGENTS.md`, trading code, `data/stages/_registry.json`). `wrap.py` does not mention `model_lock` or those runners. No secret, no binary, no cache, no receipt JSON in the commit.
