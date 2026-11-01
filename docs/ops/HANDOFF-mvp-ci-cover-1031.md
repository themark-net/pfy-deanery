# Handoff mvp-ci-cover-1031

Branch `bot/mvp-ci-cover-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`. No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. No local model. No `--local`. Pregate not run: host busy (`Runner.Worker` was running). This lane's drop-in also says the operator runs pregate.

Exit: lane empty. The ubuntu-24.04 G0 job and the nimo G0 job already collect every `tests/test_*.py` with `python3 -m unittest discover -s tests -t .`. A structural test now fails if a new file would sit outside either job. No workflow edit. Wall cap was 2026-11-01T06:41:36Z.

## Done

| Item | Commit | Result |
|------|--------|--------|
| Exit card before the coverage test | `40c532c` | Pushed |
| Structural discovery test | `68936a5` | `tests.test_ci_discover_cover`: 6 OK in 0.014s |
| Skip audit of today's test modules | `68936a5` | No owned file needed a change |

Reviewer check, bwrap hidden, on the worktree that became `68936a5`: `tests.test_pfy_build_local_review_ci` OK in 31.944s. The review module ran 17 tests, skipped 0.

Image pin helper, workflow tree unchanged: `python3 scripts/check_workflow_image_pin.py .github/workflows` printed `PASS workflow image pin: 5 file(s)`.

## What CI runs

Suite jobs, and only these, must collect the modules:

- `.github/workflows/eval-structural.yml` job `structural-github`, name `G0 (ubuntu-24.04)`, `runs-on: ubuntu-24.04`
- same file, job `structural-local`, name `G0 (self-hosted nimo)`, self-hosted labels

Both run `python3 -m unittest discover -s tests -t .`. The filemode job `G0 launcher 100755` is a mode check, not a suite job. The test ignores it.

`git diff --name-only origin/main...HEAD -- tests/` at the coverage commit includes 24 `tests/test_*.py` modules (added or modified since `origin/main`) plus fixtures and `tests/support_tmpclean_leaker.py`. All 24 import. Discover collects every `tests/test_*.py` on the tree (75 files, including this lane's new module), and that set includes `tests/test_pfy_build_local_review.py` and `tests/test_pfy_build_local_review_ci.py`.

## Skips on ubuntu (recorded, not changed)

| Module | Why it skips | Gap? |
|--------|----------------|------|
| `tests.test_hermes_bakeoff` one live test | `HERMES_BAKEOFF_LIVE=1` is unset | No. Opt-in live test |
| `tests.test_mvp_1031_sixtask_report` one test | Skips only if `eval/mvp-1031/sixtask/REPORT.md` is missing. The file is in the tree | No |
| `tests.test_workflow_image_pin` parse cases | Skip only when PyYAML cannot be imported. The ubuntu job pip-installs PyYAML before discover | No. The new test locks that order |
| `tests.test_pfy_build_local` confinement tests | bwrap missing or unusable | No. `docs/ops/PREGATE.md` says those tests skip on the pinned image |
| `tests.test_pfy_build_local` opencode flag test | real `opencode` binary missing | No. A fake would not prove the real flags |
| `tests.test_x_intake_smoke_149` sandbox cases | bwrap unusable. The no-bwrap exit 2 case still runs | No. Same contract as entry 148 |
| `tests.test_pfy_build_local` help test | whole test skips when `grok` is not on PATH | Real for ubuntu, not fixed here. Cross-lane |

`tests/support_tmpclean_leaker.py` is outside discover on purpose (the name does not match `test*.py`). `eval/mvp2/gates/test_mvp2_*.py` stay outside `tests/` because the mvp2 handoff says they are red on base by design.

## How it fails and how we recover

- Explicit list or a narrow `-p`: `tests.test_ci_discover_cover` builds a fixture workflow. An ubuntu step `python3 -m unittest tests.test_kept` reports `tests/test_new.py` as outside that job. A pattern `test_old*.py` on both jobs reports `tests/test_new_gap.py`. Recovery: put `python3 -m unittest discover -s tests -t .` back, or add the missing module to the list. The same fixture passes after discover is restored.
- Discover start directory moved to `tests/fixtures`: a top-level `tests/test_new.py` is outside both jobs. Recovery: `-s tests`.
- PyYAML install removed or placed after discover on the ubuntu job: `ubuntu_yaml_gap` fails, which is how `tests.test_workflow_image_pin` would skip its parse cases on ubuntu. Recovery: `python3 -m pip install pyyaml` in an earlier step. Do not apt-install onto a different interpreter.
- Image pin: this lane did not change `runs-on`. A move to `ubuntu-latest` fails `scripts/check_workflow_image_pin.py` and also fails this test, because the suite job is recognized only as `ubuntu-24.04`. Recovery: pin `ubuntu-24.04` again.
- Review tests: `tests.test_pfy_build_local_review_ci` hides bwrap and fails if the review module skips or errors. Recovery: keep review tests on the stub opencode and the stub HTTP reviewer.

## Cross-lane requests

- `tests/test_pfy_build_local.py` `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` skips when `shutil.which("grok")` is None, so the ubuntu G0 job never checks bare `./pfy build --help` against `./pfy build -p --help`. A fake grok on PATH for those two assertions would let the test run. This lane does not own the file.
- Do not unskip the bwrap confinement tests, and do not install bwrap or opencode on the ubuntu job from this request.

## Gate

Test and docs only. No product runtime change. No workflow change. Gate: pregate plus Reviewer. The operator pregates the tip. Do not treat this handoff as a Feature GO.

## Next

Lane empty for this worktree. Operator pregates `origin/bot/mvp-ci-cover-1031` at the handoff tip. The open help-test skip is the cross-lane request above.

## Finish

state: lane empty | tests: tests.test_ci_discover_cover 6 OK; review module ran 17 skipped 0 | files: 1 test module plus this lane's docs | err: none
