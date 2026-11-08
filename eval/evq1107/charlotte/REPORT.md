# Charlotte evq1107

Verdict: STAY I1. Pinned npm `@ticktockbent/charlotte@0.8.0` ran under a redirected HOME with Chrome's sandbox on. The core profile returned the 7 tools. On a scratch copy of `gui/operator/frontend`, the summary named 12 of 12 visible buttons and leaked 0 hidden buttons. That summary is 2346 bytes. A raw accessibility tree of the same copy is 91975 bytes. Tauri binaries on disk stayed 0. The prefix is 68106118 bytes (`du -sb`) and 60M (`du -sh`), over the 50 MB I2 copy limit. Nothing was wired into a gate. No local model was called.

## Catalog comparison

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167. Charlotte is entry 142, in the hold-or-comparison list with 143 (taste-skill, "after the window exists"). That section says gap W is the Tauri operator window, still not built on nimo, and that no entry in 137 to 167 closes it. This probe counted the same absence: 0 files at `gui/operator/src-tauri/target/{release,debug}/pfy-operator`.

A scan of `data/stages/*.json` uses, features, and tags for browser, window, puppeteer, playwright, screenshot, and accessibility hit these cards. The job in this lane is a token-bounded read of the operator window.

| Card | Stage | What it already covers | How Charlotte compares |
| --- | --- | --- | --- |
| assay | I1 | Presses the controls visible on the first paint. The 2026-11-07 probe pressed 12 of 47 operator controls and passed 31 of 31 while `/launch` returned HTTP 501. | Same page, stronger action. Charlotte named the 12 visible buttons and clicked none of them. It did not see the HTTP 501, because this probe used `file://` and started no server. |
| BugPatrol | I1 | Pixel and console patrol. Planted defect caught 1/1 (426 px). Static frontend matched at 0 px on 2/2. Tauri binaries 0. | Charlotte returns text, not pixels. It does not beat that catch. |
| taste-skill | I2 | Offline design lint and a seeded app draw. App mode: 0 FAIL on `gui/operator/frontend/index.html`, 4 FAIL on a planted page. Inspect: 2 FAIL on the live page. Tauri binaries 0. | A lint of the same page, already at I2. Charlotte does not beat it, and it does not build the window either. |
| Camofox Browser | I1 | Stealth browser for agents. Browser automation is not core. | A different browser. This probe did not use it. |
| Open WebUI | I1 | Chat UI for local models. The operator window is the product UI. | A product UI, not a page bound for a local model. |
| Hyperframes | I1 | HTML-to-video for agents. | Not a page bound. |
| agentplay | I0 | Session replay map. | A map of a past session, not a live page read. |
| Emdash | I0 | Parallel agents GUI, one worktree each. | A different GUI. |
| kanbots | I1 | Kanban fan-out. The board is the UI. | Different job. |

First-party, not a catalog card: the operator window path in `docs/ops/simple-launch.md` (Tauri if the binary exists, otherwise webkit, otherwise tk). This probe did not launch `./pfy`.

Charlotte does not beat Assay, BugPatrol, or taste-skill on gap W. A smaller page dump does not build the Tauri window. The 12 visible labels agree with Assay's first paint of 12. The accessibility pass counted 45 buttons in the DOM. Assay counted 47 controls. Those counters are not the same list.

## Pins

| Item | Value |
| --- | --- |
| npm | `@ticktockbent/charlotte@0.8.0` |
| tarball | `https://registry.npmjs.org/@ticktockbent/charlotte/-/charlotte-0.8.0.tgz`, 266627 bytes |
| sha256 | `b6a94defc8ea1d42cf5e89110cf32d77c22cd5fa7fb992db23621e04ec333eec` (rechecked on the file and by the probe) |
| sha1 | `0e91783ac0496ca9ebac60eb2e573189c1af349d` (rechecked) |
| integrity | `sha512-CMaiX5UsZWIpJSLt8evU9i0EzwlRa4UyXLqrB3JSabRzpkfXFtudx+NBsqFN2ohlcIhPH7OVxxM5Dgph1z8Xbw==` (rechecked) |
| gitHead | `208f6727467993d857ff1e527a470b6877b3ff97` (registry metadata for 0.8.0). Tag `v0.8.0` is `932e95aa6095aaa1089d9b71ae49750690b9765e`. This lane pinned the published tarball, not git `main`. |
| license | MIT |
| package version | `0.8.0`, bin `dist/index.js` |
| Node | `/usr/bin/node` v22.23.0 (already on the box) |
| npm | 11.12.1 |
| Chrome | `/usr/bin/google-chrome`, Google Chrome 157.0.8103.38. Sandbox stayed on. Chrome for Testing 148.0.7778.97 was not downloaded. |
| puppeteer | 24.43.1 installed. Declared range `^24.0.0`. `PUPPETEER_SKIP_DOWNLOAD=1`. |
| Install | `~/.cache/pfy/tools/charlotte/`. Prefix `du -sb` 68106118, `du -sh` 60M. npm cache `du -sb` 101893845, `du -sh` 57M. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `TMPDIR`, and `npm_config_cache` pointed under that cache for the install. The probe child got a fresh env with those homes, `PUPPETEER_EXECUTABLE_PATH`, `PUPPETEER_CACHE_DIR`, and `PUPPETEER_SKIP_DOWNLOAD=1`. The parent env was not copied. No account and no paid key.

Real `~/.cache/puppeteer` mtime stayed 2026-04-09. Real `~/.config/google-chrome` stayed 2026-04-26. Real `~/.cache/fontconfig` stayed 2026-11-05. Chrome wrote under `~/.cache/pfy/tools/charlotte/home/config/google-chrome` and `home/cache/fontconfig`.

## Commands

Install from the saved tarball, then one probe. No `--no-sandbox`. No `--skip-ax`.

```bash
CACHE="$HOME/.cache/pfy/tools/charlotte"
export HOME="$CACHE/home" \
  XDG_CONFIG_HOME="$CACHE/home/config" \
  XDG_CACHE_HOME="$CACHE/home/cache" \
  XDG_DATA_HOME="$CACHE/home/data" \
  XDG_STATE_HOME="$CACHE/home/state" \
  TMPDIR="$CACHE/tmp" \
  npm_config_cache="$CACHE/npm-cache" \
  PUPPETEER_SKIP_DOWNLOAD=1
npm install --prefix "$CACHE/prefix" "$CACHE/dl/charlotte-0.8.0.tgz" \
  --no-fund --no-audit --ignore-scripts
python3 eval/evq1107/charlotte/probe.py \
  --prefix "$CACHE/prefix" \
  --page gui/operator/frontend/index.html \
  --page-dir gui/operator/frontend \
  --repo . \
  --out eval/evq1107/charlotte/results.json \
  --home "$CACHE/home" \
  --tmp "$CACHE/tmp/probe2" \
  --node /usr/bin/node \
  --chrome /usr/bin/google-chrome \
  --tarball "$CACHE/dl/charlotte-0.8.0.tgz"
```

Numbers below are from `eval/evq1107/charlotte/results.json`. Scratch for that run: `/home/mark/.cache/pfy/tools/charlotte/tmp/probe2`. The probe copies `gui/operator/frontend` to `tmp/probe2/site` and opens only that copy. It does not write the frontend in this worktree.

`python3 -m unittest tests.test_charlotte_probe` drives the same script with a stub executable. Those runs pass `--skip-ax` and do not start Chrome.

## Numbers

Tauri binaries present: 0 of 2 paths. Page file: 17272 bytes. Frontend copy: 76470 bytes. `page_url_in_scratch` true. `ok` true, exit 0, server version 0.8.0.

Session field `seconds` is 1.466. That clock starts at launch and stops before the accessibility pass. The accessibility pass is 0.38 seconds. Sandbox `on`, attempts 1. Stop reason `term`: 0.8.0 does not exit on stdin EOF, so the probe closes stdin, waits 2 seconds, then SIGTERM the process group.

Core tools, exact list: `charlotte_click`, `charlotte_find`, `charlotte_navigate`, `charlotte_observe`, `charlotte_submit`, `charlotte_tools`, `charlotte_type`. Tool-list payload 7970 bytes.

| Call | Bytes | Seconds | Notes |
| --- | ---: | ---: | --- |
| navigate (minimal) | 1026 | 0.197 | no element ids, interactive total 12, console 0, network 0 |
| observe summary | 2346 | 0.008 | 12 labels, 12 ids |
| observe summary again | 2346 | 0.006 | same ids |
| observe minimal | 1026 | 0.008 | no ids |
| observe full | 4380 | 0.008 | full text 1928 chars |
| observe tree | 509 | 0.006 | no launch label |
| observe tree-labeled | 832 | 0.004 | launch label present |
| find Launch session | 151 | 0.007 | id `btn-6d84f8` |
| click unknown id | 210 | 1.008 | `ELEMENT_NOT_FOUND` |
| find again | 151 | 0.012 | same id `btn-6d84f8` |

`ids_stable` true. `find_matches_summary` true. `server_survived_bad_id` true. The unknown-id click is most of the 1.466 seconds. The probe did not click the real Launch session button.

Static agreement 1.0: 12 found of 12 expected, 0 hidden leaks, 0 extra labels. The static parse treats `display:none`, a `hidden` attribute, a hidden ancestor, and a `.view` without `.on` as hidden. The browser pass uses computed style on the same copy: agreement 1.0, 12 of 12, 0 hidden leaks, 0 extra labels.

Accessibility tree: status ok, 91975 bytes, 252 nodes, outer HTML 18027 bytes, 45 buttons. The summary is 2346/91975 of that tree (about 39 times smaller). Tree-labeled is 832/1026 of the minimal page on this file (about 19 percent smaller). Full is 4380 bytes.

Console count 0 and network count 0 because the page was `file://`. That is not a launch check. Assay's HTTP 501 on `/launch` remains the launch check.

One Chrome temp dir remained under the redirected TMPDIR: `com.google.Chrome.aKnEa3`, `du -sb` 19. The screenshot dir was created and held 0 files. No `puppeteer_dev_chrome_profile` was left.

Gap W closed: 0.

## Gates

Value gate (3 of 4 needed for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. Tauri binaries stayed 0. Assay already presses the 12 visible controls. taste-skill already lints this page. BugPatrol already compares pixels. A smaller dump does not build the window. |
| Operator leverage | No. The probe did not open the operator window, did not press Launch session, and did not call a model. |
| Evidence | Yes. `probe.py` and `results.json` reproduce the counts above. The stub unittest covers a bad tarball, a wrong version, a page outside the page dir, a hidden leak, a bad id, EOF, and one sandbox retry. |
| Blast radius | Yes, while it stays a cache install. MIT, no paid key, no hosted model. It does not become the product runtime. `file://` can read local files, so it stays off the product path. |

Score: 2 of 4. Not I3.

Modularity gate (all 4 needed to keep a local copy as I2):

| Check | Result |
| --- | --- |
| Local code needed | Yes. The docs do not say this page's summary is 2346 bytes, or that system Chrome 157 answers with the sandbox on. |
| Bounded surface | Yes for this slice. One npm package. Server argv is `node dist/index.js --profile core`. |
| Isolatable | Yes. Cache dir under `~/.cache/pfy/tools/charlotte/`. Scratch only. |
| Reversible | Yes. Delete the cache dir. The pin and the entry remain. |

Modularity passes. The lightweight I2 limit is a working tree under 50 MB and no large binaries. The prefix is 60M allocated and 68106118 bytes apparent. Potential is low, not ambiguous. The ticket promotes to I2 only when the probe measurably helps. It does not. Stay I1.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| EOF leaves Chrome up | 0.8.0 ignores stdin EOF. A kill that skips the process group leaves a browser and a temp profile. | Close stdin, wait 2 seconds, SIGTERM the process group. This run stopped with `term`. One 19-byte Chrome temp dir remained under the redirected TMPDIR. Delete that scratch. |
| Local file read | `file://` loads, and the SSRF guard runs only in HTTP mode. | This probe copied the frontend into scratch and opened only that copy. Do not point it at a real home. Keep HTTP mode off. |
| Chrome ahead of the pin | Puppeteer 24.43.1 pins Chrome for Testing 148. This box used Google Chrome 157. | This run finished with the sandbox on. If CDP breaks, install Chrome for Testing 148 under the tool cache. Do not download it into `~/.cache/puppeteer`. |
| Byte counts move | A repeat of the same page can change a response by a byte. | Cite `results.json` from this run. Do not treat a 1-byte move as a new finding. |
| Hidden view missed by the static parse | A button hidden only by a stylesheet the parser does not know can look visible. | The browser score uses computed style. Both scores were 12/12 and 0 leaks here. If they diverge, trust the browser score and fix the parse. |
| `file://` hides server errors | Console and network stayed 0. A dead `/launch` does not show up. | Keep Assay's HTTP 501 result as the launch check. Do not read a zero console count as a healthy server. |
| Install over 50 MB | Copying the prefix into the repo fails the I2 size gate and commits `node_modules`. | Leave it under `~/.cache/pfy/tools/charlotte/`. Pin the tarball sha256. |
| Sandbox retry | A sandbox error retries once with `--no-sandbox`. | This run did not retry. Do not pass `--no-sandbox` for a real site. |

## Next gate

Stay I1. Do not wire a gate. The prefix is 68106118 bytes, over the 50 MB I2 copy limit. Reopen only if the operator binary exists and a local-model browse task needs this page shape. No Feature GO.

## How this tool would run in our pipeline

1. What triggers it? Nothing in this repo calls Charlotte. A person would start `node dist/index.js --profile core` and send newline-delimited JSON-RPC on stdin. This lane adds no caller.
2. What does it do, and which services does it read and write? It reads one page URL. This probe read a `file://` copy of `gui/operator/frontend` under the scratch dir and system Chrome at `/usr/bin/google-chrome`. It writes a Chrome profile under the redirected HOME and an empty screenshot dir under TMPDIR. It does not write this repo. No account, no hosted model, no model lock.
3. What does it trigger next? A tool result comes back on stdout. A bad element id returns `ELEMENT_NOT_FOUND` and the server stays up. Nothing in CI listens for that result. This lane wires no next step.
4. Where does a human re-enter? A person chooses the page and whether `file://` is allowed. Promoting past I1, or any gate wiring, needs Mark's GO. This lane does not ask for that.
5. What stops two runs doing the same work? One cache dir under `~/.cache/pfy/tools/charlotte/` and one scratch TMPDIR per run. Two servers would each launch Chrome. There is no model lock because the probe is offline. This lane ran one live session.
