# X intake 2026-11-05: handoff (Entries 162-164)

Window: `2026-11-05T01:30:00Z` .. `2026-11-06T01:37Z` (PT calendar day 2026-11-05). Highest existing entry on `origin/main` before this slice was **161** (`161-agentgg.md`); next numbers are **162-164**. Catalog HOLD 70-75 was not touched. No Feature GO.

Prior slice 154-161 is already on `origin/main` (`b9ed0c2` intake tip; main later moved with headless-1105 slice work). This run does not renumber.

nimo headless driver pid 594813 was still alive on `tmp/headless-1105` during this intake, so keepers were filed from the Grok Bot box via GitHub push (no nimo worktree, no GPU fight, Mark's main checkout untouched).

## New entries

All three are I0. No TOOLS.md row, no `data/tools.json` row, no stage card. Smokes are release-metadata checks that exit 2 on a matching pin (asset not downloaded, tool not run), same shape as Entry 158 (Emdash).

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 162 | [Strata](https://github.com/Niko1221/Strata) (MIT, `v0.2.11` AppImage) | Local inference host with OpenAI/Anthropic localhost APIs; upstream docs name Strix Halo and ship HIP DeepSeek packs. Candidate next to Ollama for large local packs. | Metadata only here. Live trial needs large disk and HIP/ROCm check on Radeon 8060S. |
| 163 | [magpie](https://github.com/yetone/magpie) (MIT, CLI `v0.1.3081`) | One local gateway so every coding agent shares providers and fail-over. Routing layer vs per-harness base URLs. | Metadata only. Installer can rewrite agent configs; not run. |
| 164 | [Reasonix](https://github.com/esengine/DeepSeek-Reasonix) (MIT, `studio-v2.57.0` CLI tar) | DeepSeek-native coding agent for long sessions. Comparison with Hermes / Build / dsh-superagent. | Metadata only. Running wants a model provider and an isolated worktree. |

Source posts: [Strata](https://x.com/yume_arasaki/status/2118381673230520569), [magpie](https://x.com/DanKornas/status/2118266061862604931), [Reasonix](https://x.com/DanKornas/status/2118515218531704876).

Pins:

- Strata AppImage sha256 `9cac9be7f81ce92ca7fb0b839180bec73d454b8ae4b2bc0a724c0678c2e2119e`, size `305052152`, commit `c3b3f5035506f3e966f1b4b7b188aeaabae92f1d`
- magpie-cli-linux-amd64 sha256 `6aaf6d22a43fcb01f3aee865ce721aa99fcc509ce9f4938bcff77fc134996adb`, size `71479458`, source commit `4e7661adcee3ff019a729edcbae987b536ef4b53`
- reasonix-linux-amd64.tar.gz sha256 `c227bbc08c65af27dbcc49aae84e115a912123a3e2b7902a6668acda75fb948f`, size `40362566`, commit `737a181c49367a7a153c71889c168638fcfc0ba3`

Files: `sources/entries/162-strata.md`, `163-magpie.md`, `164-reasonix.md`, `examples/x-intake-local/smoke_162.py`, `smoke_163.py`, `smoke_164.py`, `tests/test_x_intake_smoke_162.py`, `163`, `164` (7 stub tests each), `.gitignore` receipt dirs, README note for 162-164.

## Left open / not keepers this run

- SeaGOAT, Rome, Trekker, Rta-Smriti Brain, CiteProof, JobCtrl, AGI-Alpha-Agent-v0, IncarnaMind, Browser Use Benchmark: logged LATER/REFERENCE/SKIP in candidates; not opened (max 3 keepers).
- Weekly @tom_doerr Grok automation: only non-tool tax chatter in window; no duplicate intake.
- Live smokes against GitHub and nimo pregate/CI: left for green CI on this PR / owner merge per catalog-only self-review rule. Headless-1105 still owns nimo.

## Eval-auto note

No strong drop-in replacement trial this window. Magpie is the closest routing-layer candidate vs ad-hoc base URL edits; Strata is the closest local-host candidate vs Ollama for very large packs. Neither is wired.
