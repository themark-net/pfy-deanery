# BugPatrol evq1107

Verdict: STAY I1. Pinned npm `bugpatrol@0.3.0` ran under a redirected HOME. The no-model web gate caught a planted operator-window defect 1/1 (exit 1, 426 pixels, console error `tauri binary absent`) and a clean rerun matched at 0 pixels (exit 0). Two compares of the static `gui/operator/frontend` copy also matched at 0 pixels, with 0 tier-1 findings. The same 404 console line was present on all three frontend captures, so the gate treated it as the baseline. Tauri binaries on disk stayed 0. Under the model lock, `qwen2.5-coder:7b-instruct` executed 0 of 3 tool calls and raised 0 candidates. `qwen3.6:35b` raised 1 candidate for a planted CLI line (`tauri=absent`, exit 0). The installed tree is over the 50 MB I2 copy limit. Nothing was wired into a gate.

## Catalog comparison

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167. BugPatrol is entry 103, so it is not in that table. That section says gap W is the Tauri operator window, still not built on nimo, and that no entry in 137 to 167 closes it. This probe counted the same absence: 0 files at `gui/operator/src-tauri/target/{release,debug}/pfy-operator`.

A scan of `data/stages/*.json` uses, features, and tags for browser, window, UI, layout, playwright, screenshot, and console hit these cards. The job in this lane is a QA patrol of the operator window over a local model endpoint.

| Card | Stage | What it already covers | How BugPatrol compares |
| --- | --- | --- | --- |
| taste-skill | I0 | Design slop lint plus a browser layout check. Next gate waits until the Tauri window exists. | Same gap. This probe ran a browser gate on the static frontend and found 0 tier-1 findings. It did not build the window. |
| Open WebUI | I1 | Chat UI for local models. The card says the operator window is the product UI. | A product UI, not a patrol. This probe did not replace it. |
| Camofox Browser | I1 | Stealth browser for agents. Browser automation is not core. | A browser, not a regression gate. This probe did not use it. |
| Charlotte | I0 | Token-bounded browser pages for local models. Next gate is post-MVP. | Pages for a model, not a pixel or console gate. |
| kanbots | I1 | Kanban fan-out. The `#ui` tag is the board, not a window check. | Different job. |
| Sponsio | I2 | Pre-call order check. The word console in that card is a hosted console non-goal. | Different job. |
| agentplay | I0 | Session replay map. | A map of a past session, not a live gate. |

First-party, not a catalog card: the operator window path in `docs/ops/simple-launch.md` (Tauri if the binary exists, otherwise webkit, otherwise tk). This probe did not launch `./pfy`. The static frontend files are the page that path serves. The gate's 0 px compares are agreement with itself on that copy, while the API `/snapshot` 404 stayed in the baseline.

BugPatrol does not beat that set on gap W. The gate can see a planted pixel and console change. It left the missing Tauri binary at 0, and the 7b local route executed no tool call.

## Pins

| Item | Value |
| --- | --- |
| npm | `bugpatrol@0.3.0` |
| tarball | `https://registry.npmjs.org/bugpatrol/-/bugpatrol-0.3.0.tgz`, 239,476 bytes |
| sha256 | `2bb646a0f9a6c7402ebaddb7004f2461104a9760cf970d38310e57af2bc0fc0b` |
| npm integrity | sha512 matched the registry string for 0.3.0 |
| gitHead | `efd3a087321d58946f999ac53f7e20b68a89a83d` |
| license | Apache-2.0 |
| `bugpatrol --version` | `0.3.0` |
| Node | `/usr/bin/node` v22.23.0 (already on the box; no second Node install) |
| Playwright | chromium revision 1140 (130.0.6723.31) plus ffmpeg 1010, under `PLAYWRIGHT_BROWSERS_PATH` |
| Install | `~/.cache/pfy/tools/bugpatrol/`. Prefix `du -sh` 55M, `du -sb` 69,462,413. Browsers `du -sh` 255M, `du -sb` 581,231,432. npm cache `du -sb` 74,824,276. |
| Endpoint | `http://127.0.0.1:11434/v1/chat/completions` only. Both live tails listed 0 off-box URLs. |

`HOME`, `XDG_*`, `TMPDIR`, `npm_config_cache`, and `PLAYWRIGHT_BROWSERS_PATH` pointed under that cache. The real `~/.cache/ms-playwright` was not the browser path. No account and no paid key. `BUGPATROL_MODEL_API_KEY` was a local dummy. Provider key names were not copied into the child env.

## Commands

Install, then the offline gate, then the live explore under the model lock:

```bash
CACHE="$HOME/.cache/pfy/tools/bugpatrol"
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg-config" \
  XDG_CACHE_HOME="$CACHE/xdg-cache" XDG_DATA_HOME="$CACHE/home/.local/share" \
  XDG_STATE_HOME="$CACHE/home/.local/state" TMPDIR="$CACHE/tmp" \
  npm_config_cache="$CACHE/npm-cache" \
  PLAYWRIGHT_BROWSERS_PATH="$CACHE/browsers" PLAYWRIGHT_SKIP_BROWSER_GC=1
npm install --prefix "$CACHE/prefix" bugpatrol@0.3.0 --no-fund --no-audit
node "$CACHE/prefix/node_modules/playwright-core/cli.js" install chromium
python3 eval/evq1107/bugpatrol/probe.py gate
scripts/model_lock.sh python3 eval/evq1107/bugpatrol/probe.py live
```

Numbers are in `results.json`. Gate scratch: `/home/mark/.cache/pfy/tools/bugpatrol/tmp/probe-20261108T035539Z`. The probe copies `gui/operator/frontend` into that scratch and serves it there. It does not write `.bugpatrol/` into this worktree.

## Numbers

Tauri binaries present: 0 of 2 paths. Frontend files copied: 7 (`index.html`, four `app-core-*.js`, `app-ui.js`, `space-invaders.js`).

Fixture page (clean text `window: not built`, then the same page with `window: ready` and `console.error("tauri binary absent")`). One desktop viewport, `bugpatrol run --no-models --screens /`.

| Phase | Exit | Seconds | Blocking | Changed pixels | Console |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 0 | 0.724 | 0 | (baseline created) | none |
| clean rerun | 0 | 0.746 | 0 | 0 | none |
| planted | 1 | 0.851 | 2 | 426 | `tauri binary absent` |

Clean agreement: 1/1. Planted catch: 1/1. Blocking rules: `visual/pixel-diff`, `runtime/console-errors`. The pixel summary was 426 pixels, 1 region, 0.033% of the compared area.

Static operator frontend, same command. The third capture used the same files as the first two. It is a second compare, not a plant.

| Phase | Exit | Seconds | Blocking | Changed pixels | Console |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 0 | 0.824 | 0 | (baseline created) | 404 File not found |
| compare | 0 | 0.857 | 0 | 0 | same 404 |
| compare again | 0 | 0.893 | 0 | 0 | same 404 |

Compare agreement: 2/2 at 0 pixels and 0 tier-1 findings. The 404 is the static server answering `/snapshot`. It was in the baseline, so the change-aware console rule did not raise it.

Live explore, one hold of `scripts/model_lock.sh`, CLI platform, `maxSteps` 4, fixer off, GitHub off, `patrol.pull: false`. `ollama ps` was empty, so each model got `keep_alive: "2m"` on a one-token warmup. The probe did not call `ollama stop`. MemAvailable was above model size + 25 GiB for both (7b need 29.38 GiB, 35b need 45.49 GiB).

| Model | Warmup | Explore | Executed tool calls | `run_command` | `report_bug` | Candidates | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen2.5-coder:7b-instruct | 2.205s | 4.165s | 0 | 0 | 0 | 0 | 0 |
| qwen3.6:35b | 19.061s | 24.599s | 3 | 1 | 1 | 1 | 0 |

The 7b replies were text that contained a JSON tool shape. BugPatrol logged `Model replied without a tool call` three times and ran no command. Tokens: 6.6k in, 56 out. The 35b run called `run_command` on `python3 window_status.py`, then `report_bug`, then `finish`. The candidate text quoted `tauri=absent` and exit code 0. Tokens: 8.5k in, 571 out. Wall for the locked command: 50.14s. Judge, fixer, and `bugpatrol review` were not run.

Gap W closed: 0.

## Gates

Value gate (3 of 4 needed for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. Tauri binaries stayed 0. The static frontend already exists, and two compares found 0 tier-1 findings. taste-skill already names the layout check for after that window exists. |
| Operator leverage | No. The gate did not open the operator window, and the 7b route executed 0 tool calls. The 35b candidate quotes a script the probe wrote. |
| Evidence | Yes. `probe.py gate` and `probe.py live` reproduce the counts above. |
| Blast radius | Yes, while it stays a cache install. Apache-2.0, no paid key, no hosted model. Prefix allocated size is 55M, browsers 255M. It does not become the product runtime. |

Score: 2 of 4. Not I3.

Modularity gate (all 4 needed to keep a local copy as I2):

| Check | Result |
| --- | --- |
| Local code needed | Yes. The docs do not say that 7b will emit tool JSON as plain text, or that a stable 404 becomes the baseline. Those needed a run. |
| Bounded surface | Yes for this slice. One npm CLI. Commands used: `--version`, `run --no-models --screens /`, `explore --steps 4`. |
| Isolatable | Yes. Cache dir under `~/.cache/pfy/tools/bugpatrol/`. Throwaway git dirs only. |
| Reversible | Yes. Delete the cache dir. The pin and the entry remain. |

Modularity passes. The lightweight I2 limit is a working tree under 50 MB and no large binaries. The prefix is 55M allocated and Chromium is 255M allocated. Potential is low, not ambiguous. The ticket promotes to I2 only when the probe measurably helps. It does not. Stay I1.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Text-only tool reply | The 7b model wrote a tool JSON blob and BugPatrol counted 0 calls, 0 candidates | Use `qwen3.6:35b` for the custom route. This probe did that on the second attempt. Keep the 7b result as a fail count. |
| Baseline swallows a stable error | The frontend 404 was in every capture, so compare stayed exit 0 | A regression gate needs a known-good baseline. Do not treat the first capture of a broken page as a pass. |
| Checkout edits | Patrol can pull `origin/main` and the fixer writes a worktree | This lane set `patrol.pull: false`, left the fixer off, and ran only in cache scratch. Do not point it at Mark's checkout. |
| Paid route | A provider key in the env can select a hosted `via` | Pin `via: custom` and an endpoint on 127.0.0.1. Give the child a whitelist env. |
| Browser cache outside the tool dir | Playwright's default is `~/.cache/ms-playwright` | Set `PLAYWRIGHT_BROWSERS_PATH` under the tool cache before install. |
| Early 0.x churn | Config or the candidate line changes | Pin `bugpatrol@0.3.0` and the tarball sha256. |
| Vision | The web explorer wants screenshots. These local models were not benched for vision | The live step used the CLI platform. The web number is the no-model gate. |

## Next gate

Stay I1. Do not wire a gate. Reopen only if a later ticket runs this gate against the built operator window and shows a defect the webkit or tk path misses. That ticket grills wiring first.

## How this tool would run in our pipeline

1. What triggers it? Nothing in this repo calls BugPatrol. A person would run `bugpatrol run --no-models` on a throwaway copy of a web app, or `bugpatrol explore` when a local model endpoint is up.
2. What does it do, and which services does it read and write? It reads the app URL or a CLI in the repo it is pointed at. It writes `.bugpatrol/runs/` there (screenshots, `run.json`). The custom route reads Ollama on 127.0.0.1:11434. Fixer and GitHub stay off, so it writes no pull request and no issue. This probe did not start those.
3. What does it trigger next? A clean gate exits 0. A tier-1 diff exits 1. Nothing in CI listens for that exit. `explore` leaves candidates for a later `judge`, which this lane did not run.
4. Where does a human re-enter? The first baseline is a human choice: a stable 404 was accepted by the second run. Dismissing a candidate is `bugpatrol issue dismiss`. This lane did not file an issue.
5. What stops two runs doing the same work? One cache dir and one scratch per probe. The model lock serializes the live explore. The gate itself has no cross-run lock. Two gates on one `.bugpatrol/` would share baselines. This lane ran the gate once, then the live step once, in separate scratch repos.
