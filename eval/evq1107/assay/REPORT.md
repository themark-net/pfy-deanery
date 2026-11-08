# assay evq1107

## Catalog tools on this job

The job is gap W: the Tauri operator window is not built on nimo, and Tester still needs a launch check that the page was actually used. These cards already sit on a browser, a layout check, or the operator window.

| Tool | Stage | What that card covers | How assay compares |
|------|-------|----------------------|--------------------|
| taste-skill | I0 | Design slop lint plus a browser layout check. The next gate waits until the Tauri window exists. | Layout rules. This probe presses controls. The window binary is still absent, so neither one closes W. Not re-run. |
| Camofox Browser | I1 | Stealth browser for agents. The card says browser automation is not core. | A browser, with no control plan and no pass/fail on this page. Not re-run. |
| Charlotte | I0 | Token-bounded browser pages for local models. | Page text for a model. No click pass. Not re-run. |
| Hyperframes | I1 | HTML-to-video for agents. | A render to video. No click pass. Not re-run. |
| Open WebUI | I1 | Chat UI for local models. The card says the operator window is the product UI. | A different window. It does not check `gui/operator/frontend`. Not re-run. |
| agentplay | I0 | Session replay map. | Replay, not a page click. Not re-run. |
| emdash | I0 | Parallel agents GUI, one worktree each. | A GUI product. No checker for this page. Not re-run. |

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) says no entry from 137 to 167 closes gap W, and that W is build work in pfy's own code. Assay is entry 116, outside that window. `eval/ev1107/` and `eval/catchup-1107/` have no operator-window click pass. This probe does not close W either.

Assay is the only catalog card that presses the controls on a page with no model. On this repo it pressed 12 of 47 operator controls and passed 31 of 31 while `/launch` returned HTTP 501. It does not beat taste-skill or the unbuilt window on gap W. A green run would record a page that did not launch.

## Verdict

STAY I1. The operator frontend passed 31/31 checks in 39.095s (`works` true, assay exit 0) while `/snapshot` returned HTTP 404 and `/task`, `/launch`, and `/env` returned HTTP 501. Planted defects were caught 1/4 in 26.135s. The Tauri binary `gui/operator/src-tauri/target/{release,debug}/pfy-operator` is absent. Nothing is wired into a gate.

## Pin

PyPI `assay-ui` 0.3.0. Wheel `assay_ui-0.3.0-py3-none-any.whl`, 70315 bytes, sha256 `148b05a0a83426394d239d9595dbbc26b1d50dd4cdee0ac638c73caef49ba63b`. That matches the published digest. License-Expression MIT. `assay --version` prints `assay 0.3.0`.

Git tag `v0.3.0` is commit `29bb1331c9b53bd1cd323eeb9dbc351f04187c1c` (2026-10-11, subject `assay 0.3.0`). The tag object is `7f56074d9e02d232b5d52fc7ffe3a8d13a1b0b3e`. `pyproject.toml` version is `0.3.0`. `LICENSE` is MIT. No account and no key. No model lock.

`playwright>=1.40` resolved here to `playwright` 1.64.1 (wheel sha256 `577b8d88778c245cfbd145ae17cf53044f084b1b46c55c69081d4069d56057e2`). Chromium is Chrome for Testing 156.0.8078.4, Playwright build v1248, plus the headless shell at the same build and ffmpeg v1013. `du -sb` of `ms-playwright` is 711303422 bytes. `du -sb` of the venv is 162355730 bytes. The tag checkout is 3065076 bytes including `.git`, and 2122762 bytes without it. Python on this run is 3.14.4. The package lists 3.14.

```bash
BASE=/home/mark/.cache/pfy/tools/assay
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache/pip" "$BASE/tmp" "$BASE/ms-playwright" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache"
export XDG_DATA_HOME="$BASE/home/.local/share" TMPDIR="$BASE/tmp"
export PIP_CACHE_DIR="$BASE/cache/pip" PLAYWRIGHT_BROWSERS_PATH="$BASE/ms-playwright"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" download 'assay-ui==0.3.0' -d "$BASE/cache/wheels"
"$BASE/venv/bin/pip" install "$BASE/cache/wheels/assay_ui-0.3.0-py3-none-any.whl"
"$BASE/venv/bin/playwright" install chromium
git clone --depth 1 --branch v0.3.0 https://github.com/awss1i/assay.git "$BASE/src"
```

No wheel, no browser, and no checkout in git.

## Probe

`python3 eval/evq1107/assay/probe.py --assay "$BASE/venv/bin/assay" --frontend gui/operator/frontend --out eval/evq1107/assay/results.json --home "$BASE/home" --tmp "$BASE/tmp/probe" --browsers "$BASE/ms-playwright" --timeout 360`

Exit 1. Exit 1 means the planted page caught fewer than 4 of 4 defects. Exit 2 would mean assay did not return JSON. Numbers are `eval/evq1107/assay/results.json`. Operator wall clock 39.095 s. Planted wall clock 26.135 s. Child env is `PATH`, cache `HOME`, `XDG_*`, `TMPDIR`, `LANG`, `PLAYWRIGHT_BROWSERS_PATH`, and `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`. The page assay serves is a copy of `gui/operator/frontend` (html, js, css only) under the cache tmp. Assay serves that folder on `127.0.0.1` with a random port. The live pfy API was not started.

Markup count uses the `.view{display:none}` / `.view.on{display:block}` rule in `index.html`, plus inline `display:none`. That count is 47 controls, 35 hidden, 12 visible. Assay's first paint listed 12 controls and pressed 12. The 35 hidden ids include `att-grok`, `btnstage`, and `btnpull`. Ten hidden controls have no id (the Attach mode buttons and the Tools toggles).

| Page | Result |
|------|--------|
| Operator frontend | 31 planned, 31 passed, 0 failed, `works` true, exit 0. Surface 12. Pressed 12. Console errors 2. Failed requests 4: `snapshot -> HTTP 404`, `task -> HTTP 501`, `launch -> HTTP 501`, `env -> HTTP 501`. |
| Launch session on that page | C018 and C019 passed. Measured text: the visible text changed. |
| Launch env on that page | C020 and C021 passed. |
| Planted page (`fixture/planted.html`) | 17 planned, 15 passed, 2 failed, exit 1. Surface 5 of 6 buttons. |
| Visible throw (`#throw` calls `undefinedFn`) | Caught. C010 and C011 failed, rule `threw`, detail names `undefinedFn is not defined`. C011 link kind is `same`. |
| Dead button (`#dead`, `onclick` void 0) | Not caught. C006 and C007 passed. Measured: the visible text is unchanged. |
| FAIL text (`#failpaint` writes `FAIL launch`) | Not caught. C008 and C009 passed. Measured: the visible text changed. |
| Hidden throw (`#hidden-throw` calls `hiddenBoom` inside `display:none`) | Not caught. Not in the surface. No failed case names `hiddenBoom`. |
| Pair case on the planted page | C015 passed and recorded `Page.click: Timeout 4000ms exceeded` on `#dead`. |

Caught 1 of 4. The caught item is the visible throw.

## Gates

Value gate, 2 of 4. The I3 bar is 3. Evidence and blast radius are met. Gap fill and operator leverage are not.

1. Gap fill. Not met. Gap W is the missing Tauri binary. It is still absent. The HTML pass pressed 12 of 47 controls and accepted HTTP 501 on `/launch`. Planted catch rate is 1 of 4.
2. Operator leverage. Not met. A day of glue would still miss the hidden Attach, Stage, and Engine controls, and would still accept a button that only changes the text to FAIL. Tester's launch check stays the check that the window was used.
3. Evidence. Met. The probe exited 1 on this pin with `results.json` filled in.
4. Blast radius. Met. MIT, no weights, no account, cache only. Chromium stays out of the repo. It is not the product runtime.

Modularity gate, all four hold for the CLI that ran.

1. Local code needed. Met. Quiet button passes, the first-paint list, and the grouped repeat are runtime behavior.
2. Bounded surface. Met. One console entry, `assay`, on one package.
3. Isolatable. Met. Cache venv and `PLAYWRIGHT_BROWSERS_PATH`. It is not the product runtime.
4. Reversible. Met. Deleting `~/.cache/pfy/tools/assay/` leaves the entry, the card, and this report.

I2 also needs the lightweight size gate: a copy under 50 MB and no large binaries. The tag tree is 2122762 bytes without `.git`. Chromium is 711303422 bytes and the run needs it. That keeps this at I1. I3 would also need the two missing value items, a repeatable script, and `self_pipeline` evidence. The script is `eval/evq1107/assay/probe.py`, stubbed by `tests/test_assay_probe.py`. It has not been applied to this repo's pipeline, and this lane does not wire a gate. Potential stays low. The catalog ceiling stays I1 until a TOOLS.md row exists.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Green pass | 31/31 passed and `works` was true while `/launch` returned HTTP 501. | Read `failed_requests` before the exit code. Keep Tester's launch check. |
| Hidden views | 35 of 47 controls never entered the plan, including Attach grok, Run stage, and Pull. | Treat the surface count as the first paint only. A later pin has to list controls inside `display:none`. |
| Dead button | `#dead` passed with the visible text unchanged. | A no-op is a pass on this pin. Do not use assay as the only click check. |
| FAIL text | `#failpaint` passed because the visible text changed to `FAIL launch`. | A FAIL string still counts as a change. The case stays quiet. |
| Click timeout | C015 recorded a 4000 ms timeout on `#dead` and passed. | A quiet case stores the timeout as evidence. The outcome stays passed. |
| Chromium size | 711303422 bytes under the tool cache. | Keep `PLAYWRIGHT_BROWSERS_PATH` under `~/.cache/pfy/tools/assay/ms-playwright`. |
| Static server | Assay serves the copy on 127.0.0.1. The page then POSTs to that server. | Point a trial at a copy. Do not point it at a live pfy process. |
| Early onboard | Treating 31/31 as the operator window working. | Stay I1. The planted score is 1 of 4. |

## Next gate

Stay I1. A later ticket can re-open only if a newer pin fails the HTTP 501 launch and the hidden-view throw, and lists those controls in the surface. No pregate, CI, or other gate wiring in this lane.

## Five questions (assay in our pipeline)

1. What triggers it? A GUI change would run assay on a built copy of `gui/operator/frontend` before Tester's launch check. Nothing in this repo calls assay today.
2. What does it do, and which services does it read and write? It reads one folder, serves it on `127.0.0.1`, presses the visible controls in Chromium, and prints JSON on stdout. It writes browser data under `PLAYWRIGHT_BROWSERS_PATH`. No hosted model and no account.
3. What does it trigger next? Nothing in this lane. A human or Tester still has to launch the window. The exit code does not start a gate.
4. Where does a human re-enter? When the run exits 0. On this page that exit happened with `/launch` at HTTP 501. Mark still decides any gate.
5. What stops two runs doing the same work? One worktree and branch per eval slug. Assay itself has no lock. A future run would key off the page folder. This lane does not add that run.
