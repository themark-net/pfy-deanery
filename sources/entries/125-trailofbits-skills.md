### Entry 125: Trail of Bits skills — security-audit skill pack for coding agents (property tests, Semgrep rule writing, variant analysis, sharp edges)

- **URL**: https://github.com/trailofbits/skills (**CC-BY-SA-4.0**, Markdown skills plus helper scripts; 44 plugins / 85 `SKILL.md` files; about 7,618 stars at this read; checked at commit `5c99c03fb8a9`, 2026-10-15)
- **Date**: 2026-10-17 (dev-skills investigation: stop "rookie" systems and security mistakes in Build and bot output)
- **Source / Poster**: the operator's dev-skills ask after leasegrid-c PRs #73 and #74; seen on X via @ai4cybersec, https://x.com/ai4cybersec/status/2110790103392210956, and a reviewer's use on LND PRs, https://x.com/iamflops/status/2047433185948995598
- **Summary / Key Claims** (upstream README and skill frontmatter): Trail of Bits' audit playbook as Claude Code / Codex plugins. Covers smart-contract scanners, C/C++ and Rust review, supply-chain audit, YARA, zeroize audit, an Actions auditor for agent risks, and general skills: `property-based-testing` (Hypothesis, fast-check, proptest), `mutation-testing` (mewt/muton campaigns and surviving-mutant triage), `semgrep-rule-creator`, `variant-analysis` (find other instances of one root cause), `sharp-edges` (footgun APIs and configs), `differential-review` (security review of a diff with blast radius), `fp-check` (true/false-positive verdict with evidence), and `testing-handbook-skills` (atheris, AFL++, cargo-fuzz, sanitizers).
- **Worth porting** (as a Grok `[skills].paths` pack, unmodified files plus attribution):

| Skill | Use here |
|-------|----------|
| `property-based-testing` | Build writes Hypothesis properties for parsers, restored state and redaction (leasegrid B3/B5-class bugs) |
| `semgrep-rule-creator` | Turn each Tester/Reviewer blocker into a project Semgrep rule |
| `variant-analysis` | After a blocker, hunt its siblings before the next gate round |
| `sharp-edges` | Reviewer lens for footgun APIs (QLockFile stale handling, QLocalServer defaults, killpg) |
| `differential-review` | Reviewer pass on a PR diff with blast radius |
| `fp-check` | Triage scanner findings before they become gate noise |
| `testing-handbook-skills/atheris` | Optional nightly Python fuzzing on nimo |

  Skip: blockchain, YARA, Burp, DWARF, Lean, zeroize, C/C++/Rust review, culture/game plugins.
- **License note**: CC-BY-SA-4.0. A snapshot **committed** to pfy-mentat counts as redistribution, even unmodified. It must ship with: the license text or its URI (https://creativecommons.org/licenses/by-sa/4.0/), credit to Trail of Bits, the upstream URL and pinned SHA (`5c99c03fb8a9`), and any copyright, license or disclaimer notices upstream includes. **Any edit** to a ToB file makes it adapted material: it must stay CC-BY-SA-4.0 and the change must be marked in that file. So keep the snapshot byte-identical, and put pfy-specific guidance (for example Task → `/agent-loops`) in a separate pfy-authored `PORT.md` beside it, never inside a ToB file. Never fold ToB text into pfy-owned first-party skills.
- **Fit on nimo**: Plain files; no GPU, no model, no service. A pinned snapshot under `~/DEVELOP/pfy-mentat/bootstrap/grok-cli/skills-external/trailofbits/` (only the skills above) registered in `[skills].paths`, the same way as `mattpocock/`. Some skills assume Claude Code tools (Task, plugins); Grok reads them as guidance.
- **Verified on the Grok Bot box** (shallow clone in `/workspace`): 44 plugins in `.claude-plugin/marketplace.json`; all 7 port candidates have frontmatter whose `name` equals the folder, descriptions 179–845 chars, bodies 3.9–11.8 KB. ToB does cover TOCTOU races in general (`plugins/rust-review/prompts/general/toctou-finder.md`, and a TOCTOU section in `plugins/sharp-edges/skills/sharp-edges/references/lang-c.md`), but a grep found nothing on PID locks, temp-file IPC or PID reuse, so the leasegrid lock/IPC class still needs a pfy-owned skill.
- **Extracted Repos / Tools**: https://github.com/trailofbits/skills · https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing · https://github.com/trailofbits/skills/tree/main/plugins/semgrep-rule-creator · https://github.com/trailofbits/skills/tree/main/plugins/variant-analysis
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: None in this slice (docs-only entry). Next step is a `make smoke-grok-skills` style frontmatter check over the ported snapshot.
- **Non-goals**: No `claude plugin marketplace add`, no plugin installs, no copying skill text into first-party skills, no mewt/muton install.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Share-alike leak or missing notices | Edited ToB text lands in a pfy-owned skill, or the snapshot ships without LICENSE/credit/SHA | Snapshot stays byte-identical under `skills-external/trailofbits/` with LICENSE (or URI), ToB credit, upstream URL, pinned SHA and upstream notices; any edited file is marked as adapted BY-SA; Reviewer checks |
| Context bloat | Big skills crowd a local model's context | Port only the 7 listed; load per task, not always-on |
| Claude-only assumptions | Skill tells the agent to use Task or a plugin command | A separate pfy-authored PORT.md maps Task to `/agent-loops` (no edits inside ToB files) |
| Upstream churn | Skills renamed or reshaped | Pin the commit; refresh deliberately |

- **Status**: STAY I0 after the 2026-11-07 evq probe on nimo. Pin `5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0` is in the cache only. The install check on the 7 port candidates exited 1 (3 SAFE, 3 CAUTION, 1 DO_NOT_INSTALL). differential-review on commit a81ffba found 0 new defects. Not copied into skills.paths. Report: `ops:eval/evq1107/trailofbits-skills/REPORT.md`.
