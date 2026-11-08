# hyperframes evq1107

STAY I1 reference: HTML-to-MP4 does not build the operator window. Apache-2.0. Docs only. Gap W stays open.

## What it is

Hyperframes (heygen-com/hyperframes) turns HTML, CSS, and media into an MP4. An agent writes a composition. The CLI seeks each frame in headless Chrome and encodes with FFmpeg. Timing sits on `data-start` and `data-duration`. On one machine the same frame index seeks the same picture: no wall clock, no unseeded random, no fetch during the render. Across machines a local render can still shift by a pixel. README requirements are Node.js 22+ and FFmpeg. Docker can pin Chromium, fonts, and FFmpeg. The CLI also offers cloud, AWS Lambda, and GCP Cloud Run. Studio is a desktop app. Some skills call HeyGen. License is Apache-2.0 (root LICENSE, copyright 2026 HeyGen, Inc.; `@hyperframes/cli` license field).

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `ab785e9c5c59e9542593e49b93f9547cb2665b44` |
| Commit | 2026-11-08 04:46:46 +0000. `fix(studio): a menu row's highlight is rounder than its panel (#7395)` |
| Tag | `v0.9.22` is `26956ea1f4c855e80cfdd1677c1e02e15fbf088d` at 2026-11-08 01:18:54 +0000 (`chore: release v0.9.22`). This pin is 2026-11-08 04:46:46 +0000. CLI `package.json` still says `0.9.22`. |
| Time | `git fetch` 0.63 s. Checkout of the blobs was not timed. No upstream script ran. |
| Size | `du -sb --exclude=.git` 331781011 bytes. With `.git`, 405422695 after the pin checkout, 405839815 after the tag fetch. 9876 files. |
| Cache | `~/.cache/pfy/tools/hyperframes/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `npm_config_cache` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. Command: `git init`, remote `https://github.com/heygen-com/hyperframes.git`, `git fetch --depth 1 --filter=blob:none origin ab785e9c5c59e9542593e49b93f9547cb2665b44`, `git checkout --detach FETCH_HEAD`.

## Ideas, and the pfy file each would touch

1. Ask for one frame instead of recording live playback. A still of the operator page is already the BugPatrol pixel compare (`eval/evq1107/bugpatrol/REPORT.md`). The missing window is `docs/HANDOFF-headless-1105.md`. Do not add a video renderer.
2. Keep timing in HTML attributes, not a component tree the model must learn. Touch `docs/design/DESKTOP-SPEC.md`. The operator page is already HTML in `gui/operator/frontend`. A camera timeline is a different product.
3. A small core skill set, with the rest on demand. Touch `docs/build-dropins/skill-discovery.md`. That drop-in already forbids loading fetched skills. Do not run `npx skills add` or `npx hyperframes skills update`. The core skill tells the agent to run an events beacon once.
4. A design spec rewritten for a frame (`frame.md` in the README). Touch `docs/design/README.md` only if a later ticket asks for a promo film. The operator design pack is the product UI.

## Catalog comparison

Same job: HTML to video. The scheduler also queued this slug under gap W (operator window) in `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Entry 070 is older than that section. That section says nothing in 137 to 167 closes W. This lane builds no pipeline and no gate.

| Tool | Stage | What it covers | How Hyperframes compares |
| --- | --- | --- | --- |
| taste-skill | I2 | Design floor on `gui/operator/frontend/index.html`. | Reads the page. Does not encode video. |
| assay | I1 | Presses controls on the static operator page. | A click pass. No MP4. |
| BugPatrol | I1 | Pixel compare of that page. The window binary was absent. | Still the page, not a film. |
| Charlotte | I1 | Token-bounded read of the static operator page on origin/main. Tauri binaries stayed 0. | A page budget. Not a render. |
| Open WebUI | I1 | Chat UI. The operator window is the product UI. | Another UI. Not HTML-to-MP4. |
| Camofox Browser | I1 | Stealth browser. Not core. | A browser agent. Not a film. |
| Memvid | I1 | Video-backed memory. | Stores memory as video. Does not render HTML. |
| LiveKit, Pipecat | I0 | Voice-stack references. | Realtime audio. Not a composition. |

No other TOOLS.md row is HTML to MP4. Remotion is not cataloged. Hyperframes does not beat the operator-page probes, and it does not produce the pfy-operator binary named in `docs/HANDOFF-headless-1105.md`.

## Gates

Value (3 of 4 for I3): gap fill no (W is the Tauri window). Operator leverage no (Node 22, FFmpeg, Chrome, and an optional HeyGen account). Evidence no (docs only; render was not run). Blast radius yes (Apache-2.0, no weights, not the product runtime). Score 1 of 4.

Modularity (all 4 for a local copy): the README and concept docs were enough, the unit is a monorepo (16 packages, including studio, lambda, and cloud run), the cache copy is isolatable, and deleting it leaves the pin. 2 of 4. 331781011 bytes is over the 50 MB bar. Potential is low, so the I2 shelf does not apply. Uses and features name no pipeline role. No `self_pipeline`. TOOLS.md already has the row. This lane did not edit it. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Skills beacon | `npx hyperframes events` sends a skill name, and can attach an account | Do not install skills. This lane ran no CLI. |
| HeyGen or Gemini | Cloud render, TTS, or capture spends a key | No account. `.env.example` only names `GEMINI_API_KEY`. |
| Size | The monorepo lands in git | Cache only. 331781011 bytes. |
| Gap W false pass | An MP4 is counted as the operator window | The window stays `gui/operator`. Verdict stays I1. |

## Next gate

Stay I1 reference. Re-open only for one local MP4 in a temp project, with no skills install, no events beacon, no HeyGen account, and no cloud render. Not a Feature GO.

## Pipeline questions

This lane does not put Hyperframes on a pipeline. The scheduler started the read. It writes this directory, the card, and the entry Status line. No model and no account.

1. Trigger, if adopted later: a person runs `npx hyperframes render` in a video project. Not this scheduler.
2. It would read HTML and write an MP4, using local Chrome and FFmpeg, or HeyGen cloud. This lane only read the checkout.
3. Next: nothing in `./pfy`. The operator window is still unbuilt.
4. A human re-enters before any install, any cloud auth, or any I2 copy.
5. One worktree per slug (`bot/evq-hyperframes-1107`) keeps this card private.
