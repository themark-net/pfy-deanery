# Camofox Browser evq1107

STAY I1 reference: stealth browser does not build the Tauri operator window, and browser-use stays off the product core. This lane installed nothing, ran no upstream script, and copied no code.

## What it is

Camofox Browser (https://github.com/jo-inc/camofox-browser) is a Node REST server that launches Camoufox, a Firefox fork with C++ fingerprint spoofing, for agents. `@askjo/camofox-browser` at this pin is 1.18.1. `@askjo/camofox-browser-mcp` is the same version and lists 11 tools. The MCP process proxies to the REST server and does not ship the browser. Default port is 9377. A tab is `userId` plus `sessionKey`. A snapshot is an accessibility tree with refs such as `e1`. Refs reset on navigation. `lib/snapshot.js` windows a tree at 80000 characters and keeps a 5000 character tail. Session inactivity defaults to 600000 ms in `lib/config.js` and the env table. The architecture paragraph still says 30 minutes. The browser process stops after 300000 ms with no sessions. Profiles default to `~/.camofox/profiles/`. Cookie import stays closed unless `CAMOFOX_API_KEY` is set. Crash telemetry defaults on, to `camofox-telemetry.askjo.workers.dev`. The README says the first `npm install` downloads about 300MB of Camoufox. Node is `>=22`. The entry's 47-tool MCP is the redf0x1 fork. This pin is not that fork. The GitHub API at this read reported 12199 stars. The entry's "~6k" is older.

## License and pin

MIT. Root `LICENSE`, copyright 2025 Jo, Inc. Both package files say MIT and version 1.18.1. `camofox.config.json` still says `"version": "1.6.0"`. Camoufox is a separate Firefox fork. This lane did not fetch it.

| Item | Value |
| --- | --- |
| Pin | `39c82094013480b373df6600d44c7f036f58356e` |
| Tag | `v1.18.1` peels to that commit. Tag object `2dc5f4a8153d2099cacaf3337c39155e0d46b580`. |
| Commit | 2026-10-04 19:30:55 -0700. Subject: Merge pull request #12634: release v1.18.1 patch. |
| Fetch | `git clone --filter=blob:none --no-checkout`, then `git fetch --depth 1 origin <pin>`, detach. No script ran. Wall clock not recorded. |
| Bytes | `du -sb` src 6036917, `.git` 2603986, `--exclude=.git` 3432931. 240 files. Under the 50 MB I2 source cap. |
| Cache | `~/.cache/pfy/tools/camofox-browser/src`. Not committed. |

## Ideas, and the pfy file each would touch

1. Window a large accessibility tree and keep the nav tail. Would touch a reader of `gui/operator/frontend/index.html`. Charlotte already cut that page from 91975 bytes to 2346. Do not add this server to do it.
2. One user id, one cookie jar, and a delete that drops the session. Would touch `docs/adr/0016-jev-decision-layer.md`, which already keeps browser-use out of the decision layer.
3. A thin MCP client that does not download the browser. Would touch `bootstrap/grok-cli/README.md` if we registered it. We do not.
4. Loopback unless an access key is set. This pin leaves the bind open when `CAMOFOX_BIND_HOST` is unset. The safer default would matter only if a later server grows a port. `docs/ops/simple-launch.md` stays Tauri, then webkit, then tk.

## Catalog comparison

Same job: an agent browser, and gap W (the Tauri operator window). Searched `data/stages/*.json` uses, features, and tags. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) says no entry from 137 to 167 closes gap W. Entry 071 is older and sits in catalog HOLD 70-75. This lane builds no pipeline, CI, or gate. This worktree has 0 `pfy-operator` binaries under `gui/operator/src-tauri/target/{release,debug}`. TOOLS.md still calls this a default stealth candidate. This lane does not edit that shared row.

| Tool | Stage | What it covers | How Camofox compares |
| --- | --- | --- | --- |
| Charlotte | I1 | Token-bounded pages and stable element ids. Operator summary 2346 bytes against a 91975 byte tree. Tauri binaries 0. | Same snapshot idea. Charlotte already measured our page. Camofox adds an unrun fingerprint claim and a browser download. |
| assay | I1 | Presses the controls on the first paint of the operator page. | Camofox does not press that page. |
| BugPatrol | I1 | Patrol of a web or CLI app. Its probe did not build the operator window. | Camofox is not that patrol. |
| taste-skill | I2 | Design lint of `gui/operator/frontend/index.html`. Tauri binaries 0. | Camofox does not lint that file. |
| Hyperframes | I1 | HTML-to-video. | Not a browser and not the window. |

First-party: `docs/ops/simple-launch.md` and `docs/modules/pfy.md` open the operator window. `docs/design/DESKTOP-SPEC.md` and ADR-0016 keep browser-use off the core. Charlotte, assay, BugPatrol, and taste-skill already cover that page. Camofox does not build the window.

## Gates

Value (3 of 4 for I3): gap fill no (gap W is the missing Tauri binary). Operator leverage no (browser-use is a non-goal, and catalog 70-75 stays HOLD). Evidence no (docs only; no server and no smoke). Blast radius no (about 300MB on first install, default listen is all interfaces, telemetry defaults on, cookies under `~/.camofox`, page JavaScript execution). Score 0 of 4. The MIT license would allow an external binary later.

Modularity (all 4 for I2): the README was enough to stay. The surface is the REST server, youtube and persistence on, vnc present and off, an OpenClaw plugin, an MCP package, and a telemetry worker. The cache clone is isolatable and reversible. 2 of 4. Potential is low, not ambiguous, so the I2 shelf does not apply. No `self_pipeline`. Uses and features name no CI, test, or review role. The existing TOOLS.md row stays. There is still no `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Browser download | `npm install` fetches about 300MB. Postinstall can ignore a skip flag. | Do not install. The cache is source only. |
| Open listen | Unset `CAMOFOX_BIND_HOST` listens on all interfaces. The access key is optional. | Stay I1. A later trial would set `127.0.0.1` and an access key. |
| Telemetry | Crash reports default on to a Cloudflare worker. | Leave the server unstarted. A trial would set `CAMOFOX_CRASH_REPORT_ENABLED=false`. |
| Cookie store | Persistence writes `~/.camofox/profiles/`. | Do not start it. A trial would set `CAMOFOX_PROFILE_DIR` under the cache and leave cookie import unset. |
| Gap W misread | A stealth browser is treated as the operator window. | The verdict stays I1. Tauri binaries stayed 0. |
| HOLD lift | Entry 071 moves onto the product path. | Do not edit TOOLS.md. The ask queue still HOLDs 70-75 by entry number. |
| Handoff apply | `catalog_stage_eval.py --apply` copies uses and next_gate from `data/catalog_stage_handoff.json`, which still says Stay I1. | This lane leaves that shared file alone. Put this card's text back if an apply lands first. |

## Next gate

Stay I1 reference. Re-open only as an external binary at pin `39c82094013480b373df6600d44c7f036f58356e`, bind `127.0.0.1`, telemetry off, no cookie import, no VNC, profile dir under the cache, and a grill before any run. Not a Feature GO.

## Pipeline questions

This lane does not put Camofox on a pipeline. The scheduler started the read. It writes this directory, the card, and the entry Status line. No model and no account.

1. Trigger, if adopted later: a person starts the REST server. Not this scheduler.
2. It would read and write tabs, cookies, and profiles, and call the sites an agent names. This lane only read the checkout.
3. Next: nothing in `./pfy`. The driver sanity check lands this read.
4. A human re-enters before any install, any key, any MCP registration, or any gate ticket. `tmp/STOP` in this worktree stops the lane.
5. One worktree per slug (`bot/evq-camofox-browser-1107`) keeps other lanes off this card.
