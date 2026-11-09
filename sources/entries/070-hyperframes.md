### Entry 070: Hyperframes — Write HTML, Render Video (Built for Agents)

- **URL**: https://x.com/i/status/2079882269007937996
- **Date**: 2026-07-22
- **Poster**: Harman (@itsharmanjot)
- **Summary / Key Claims**: HeyGen open-sourced Hyperframes. Agents write plain HTML (with data attributes); the framework returns a deterministic MP4. No component tree, no proprietary format, no build step the model has to learn. Ships agent skills (`npx skills add heygen-com/hyperframes`), CLI, catalog of blocks, Studio, and production use at HeyGen. Distinction between "built for developers" vs "built for agents" is the key claim.
- **Extracted Repos / Tools**: https://github.com/heygen-com/hyperframes (~34k stars). Also hyperframes-launches for example compositions.
- **TOOLS.md Link**: New row under **Agent Frameworks & Orchestration** or multimodal / skills. High value as a first-class video skill pack for Grok CLI agents. Complements existing skills ecosystem (ponytail, mattpocock, marketing-skills, Hermes).
- **Notes**: Stage 0 pass. Extremely high signal for agent tooling. HTML-native + non-interactive CLI + explicit skills is exactly the surface agents need. Recommend catalog + pattern extract (skill routing, composition contract, deterministic render) into first-party skill packs. Local render path exists (CLI + headless Chrome + FFmpeg); cloud option via HeyGen API is optional. Strong candidate for multimodal agent demos.
- **Status**: STAY I1 reference (read 2026-11-07). Pin `ab785e9c5c59e9542593e49b93f9547cb2665b44` is CLI 0.9.22, Apache-2.0 (tag `v0.9.22` is the earlier commit `26956ea1f4c855e80cfdd1677c1e02e15fbf088d`). No install, no render, no code copy. Gap W stays the operator window. Receipt: `ops:eval/evq1107/hyperframes/REPORT.md`. No Feature GO.
