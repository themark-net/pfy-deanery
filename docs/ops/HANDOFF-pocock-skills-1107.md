# Handoff: pocock skills pin and pipeline retro (2026-11-07)

Branch `bot/pocock-skills-1107` in worktree `tmp/pk-1`. Not pushed. Driver pushes.

## Vendored

Upstream https://github.com/mattpocock/skills at pin `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. Previous pin `391a2701dd94`. Path moves: none. `tdd`, `code-review`, and `to-spec` are still `skills/engineering/<name>/`.

Copied verbatim into `bootstrap/grok-cli/skills-external/mattpocock/`:

| Skill | Upstream path |
| --- | --- |
| tdd, code-review, to-spec, implement, retro | `skills/engineering/<name>/` |
| grilling, grill-me | `skills/productivity/<name>/` |
| software-factory | `skills/in-progress/software-factory/` |

`software-factory` is `SKILL.md`, `EXAMPLE-TASKS.md`, and `RUNNERS.md` only. MIT `LICENSE` is in that directory. `agents/openai.yaml` is not copied. Attribution, the pin, and the refresh loop are in `PORT.md`. `bootstrap/grok-cli/manifest.json` `external_skills.mattpocock` lists the eight skills at this pin.

`pipeline-retro` is first-party at `.grok/skills/pipeline-retro/SKILL.md`. It is not in the mattpocock snapshot and not in `bootstrap/grok-cli/skills/`.

## Visibility

`~/.grok/config.toml` was not edited. `install.sh` was not run.

`.grok/skills/grilling`, `tdd`, `code-review`, and `to-spec` are relative symlinks into the vendored directory. `implement`, `retro`, `grill-me`, and `software-factory` are thin pointer `SKILL.md` files. Upstream sets `disable-model-invocation` on those four (and on `to-spec`). A symlink of that file stays out of the Grok Build skill list. Each pointer tells the model to follow the vendored file.

Headless check, second run, exit 0:

```
grok -p "list the skills you can load whose names are implement, retro, grilling, grill-me, software-factory, pipeline-retro" --max-turns 2 --cwd /home/mark/DEVELOP/pfy-mentat/tmp/pk-1
```

The model listed all six as loadable, with paths under `.grok/skills/`. The session's injected skill list contained `implement`, `retro`, `grilling`, `grill-me`, `software-factory`, `pipeline-retro`, `tdd`, and `code-review`. It did not contain `to-spec`.

The first run, while those four were still symlinks, exited 1 with `Max turns reached`. That session's injected list had `grilling` and `pipeline-retro` only, out of the six names. The pointers are the form the loader accepted.

## How to run the retro

```bash
python3 scripts/pipeline_retro.py
python3 scripts/pipeline_retro.py --json
python3 scripts/pipeline_retro.py --offline
python3 scripts/pipeline_retro.py --since 2026-11-01
```

Default is the last 10 first-parent commits on `origin/main`. Cache is `~/.cache/pfy/retro` (fallback `$TMPDIR/pfy-retro-cache`). `--offline` reads that cache and does not open the network. The client is cache-first and stops before the unauthenticated 60/hour floor.

Run the skill on every 10th first-parent landing (`git rev-list --first-parent --count origin/main` divisible by 10) or on demand. Write `docs/ops/PIPELINE-RETRO-<MMDD>.md`.

## Numbers (this run)

Saved as `docs/ops/PIPELINE-RETRO-1107.md`. Cache-only replay. GitHub ok. Network not contacted.

Baseline comparison line: about 6 full-suite runs and about 127 runner-minutes (39 min pregate + 44 min branch CI + 44 min main CI). These 10 landing SHAs did not retain a full pregate, so the 39 min figure is not a measurement of this window.

| sha | full | total min | schedule min | dup | over |
| --- | --- | --- | --- | --- | --- |
| 341877173d | 4 | 162.3 | 0.0 | yes | yes |
| 4f69919edf | 4 | 154.9 | 0.9 | yes | yes |
| 7ec63eed04 | 2 | 77.5 | 108.2 | yes | no |
| b38db3765e | 4 | 157.4 | 0.0 | yes | yes |

The other six SHAs are intermediate commits in a push. Actions ran on the tip only, so they are all zeros.

Full jobs are `G0 (ubuntu-24.04)` and `G0 (self-hosted nimo)`. One pair is about 77 to 80 min. The three over-baseline tips ran that pair twice (branch or `workflow_dispatch`, then push to main). `7ec63eed04` ran it once on main and stays under 127. It is still duplicated because the two G0 jobs discover the same tests.

`341877173d` also has 10 lint-only pregates, 1.1 min, at this snapshot. Wall time is -834s because those lint runs started after main CI finished. A cancelled `workflow_dispatch` on main (19s and 25s) is inside the minutes and is not a full-suite run. Schedule minutes (`nightly-models` 0.9, `local-lab` 108.2 failed) are outside the landing total.

Nothing in the data stops two runs from doing the same work. The cut list is in the retro doc. No CI or pregate step was added.

## Catalog

`docs/eval/TOOLSET-RANKING.md` already lists mattpocock skills under "Already integrated" on `skills.paths`. `data/tool_integration_stages.json` is still one file on this branch. No catalog tool joins local pregate logs with Actions runner-minutes. This cut used the public Actions API plus local pregate summaries and lane progress files. It did not add a gate, and it did not edit the catalog files. Lane `bot/stages-split-1107` owns the stages split.

## Tests

`python3 -m unittest tests.test_pipeline_retro` (7 tests). They parse fixtures and count. One flags a duplicated full-suite run on the same SHA. No network. A full `unittest discover -s tests` was not run: this change does not touch `scripts/run_tests.py`, pregate, or catalog check, and that discover is the repeated call the retro says to cut.

Follow-up on the sanity check: current G0 steps call `scripts/ci_selected_tests.sh`. The ubuntu job also runs two named unittest modules. The classifier marks both G0 jobs selected. `Full suite backstop` runs `python3 scripts/run_tests.py` with no module arguments and is full. A job that still contains `unittest discover -s tests` stays full. The table above counted earlier G0 runs as full because those SHAs still ran discover. Replaying the script on this tree labels the same job names from the current workflow files, so those historical names count as selected.

## Left alone on purpose

`install.sh` still logs the old three skill names. README and `AGENTS.md` were not edited. `AGENTS.md` is in the fastpipe lane.

## Risks

- Until Mark pulls main, `skills.paths` still points at `~/DEVELOP/pfy-mentat`, which has the old pin. This worktree's headless session listed one `tdd` and one `code-review`, both from `.grok/skills` at the new pin. A session whose cwd is the main checkout still loads the old pin.
- `to-spec` at this pin sets `disable-model-invocation`. The symlink is on disk and the loader did not list it.
- The first live Actions fetch burned the unauthenticated budget down to about 7 remaining. Do not call the API again until the hour resets. The cache under `~/.cache/pfy/retro` already covers these 10 SHAs. `--offline` is the safe replay.
- Diag logs under `~/actions-runner/_diag` are consulted only for a SHA whose Actions query did not return, and only when the log's job context sha matches. This run added zero diag fills. Do not paste those logs. They can contain tokens.
- Lint-only pregate counts move while other lanes are landing. The report's "10" is this snapshot.
- Cancelled jobs count in minutes and do not count as suite runs. Schedule jobs are reported and excluded from the baseline total.
- A negative wall time is kept. It means the retained pregate started after main CI completed.
- The upstream clone used for the copy sits in this worktree's `tmp/` and is gitignored. Do not commit it.
