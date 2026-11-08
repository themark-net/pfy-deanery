# Adopt or build: does an existing project already do the suite?

**Date of research:** 2026-11-08
**Worktree:** `/tmp/pfy-adopt-or-build-20261108` on `research/adopt-or-build-20261108`. First write sat on `210cd443` (`catalog: regenerate counts`) and was committed as `6980ff8f`. This continuation edits only this file.
**Scope of this change:** this report only. Catalog, code, and config were not edited. Nothing was installed, published, or pushed.
**Continuation provenance:** a parent session supplied member-page notes from Read Multiplex (Brian Roemmele). Those notes are labeled **parent-read** below. This pass did not read the member bodies. A public GET of each URL on 2026-11-08 returned HTTP 200 and the page title, and the HTML contained a "members only" marker. Public checks in this pass were the GitHub and Hugging Face records for Laya, and the GitHub record for x402.

## Bottom line

Mark should not stop building pfy-mentat to adopt someone else's whole suite.

No public project found on 2026-11-08 does all five parts together, with working evidence: track outside sources for coding-agent and dev tools, catalog and dedupe them, evaluate claims against improvement vectors, integrate the survivors into that project's own pipeline, and promote only what that evidence supports. The closest projects each miss at least two parts, or they are dormant, hosted, or a different product (a coding agent, a skill pack, a skill registry, or a "does it run" bench).

Star counts, a place in a backlog, and a short eval wall do not show that a tool made output better. This brief keeps a **17.5-day backlog wait** separate from an **evaluation that finishes in under an hour**. Neither number was re-measured here, and neither is a quality result. The quality results already on disk are the ones that say gain or no gain: harness2 held-out gain 0, skill-up delta 0, Hermes bake-off NO-WIN.

The parent-read member notes do not name a project that does the five parts. Laya is a real Apache-2.0 decision model, already trialed in this repo on 2026-10-06. That trial did not establish a speed or quality win, so Laya is not added to the adopt list. The order below is the same as in `6980ff8f`. The `1e546d96` watchlist still has no `replace_us` row, and it does not mention Laya.

### Adopt a piece, in this order

1. **OpenCode, already in use, record the canonical repo.** `sst/opencode` and `anomalyco/opencode` are the same GitHub repository (id `975734319`). The live name is [anomalyco/opencode](https://github.com/anomalyco/opencode). It is the worker harness (ADR-0011), status `partial` in `data/harnesses.json`, and that record's `github` field is null. It is not a catalog. Do not make it the product.
2. **Sandcastle's native sandbox, as a later read-only probe, not a new runtime.** [mattpocock/sandcastle](https://github.com/mattpocock/sandcastle) is Matt Pocock's MIT library. The current README is `sandcastle.run()` plus Bubblewrap, Seatbelt, Docker, Podman, and cloud providers. A local fork, sandcastle-grok, already cuts lanes (see `docs/ops/GRILL-STEP.md`). There is no stage card. The 1 November 2026 "every skill becomes an Agent()" pitch is not what the README ships.
3. **Keep the pieces already on the path.** `mattpocock/skills` is stage **I1**. skill-up is stage **I3** and is the skill-eval piece. Hermes feedback is a pattern port at **I1**, not the Hermes runtime. Do not add a second skill registry or a second skill grader because a new README also says "evals".
4. **Official MCP Registry as an intake feed only.** [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry) catalogs MCP servers. Upstream says the codebase is not designed for self-hosting. It does not score improvement and it does not integrate tools into a product pipeline.
5. **OpenEvolve only if a later ticket needs evolutionary search over a program with an automatic score.** It is maintained. It is not a tool catalog. SICA, the Darwin Gödel Machine, and ACE are research prototypes or research code, not a suite to switch to.

**Not inserted.** Laya stays off this list. The 7 Nov 2026 parent-read post proposes it as a cheaper local clerk in front of a Grok bot. Public records confirm the weights and the Apache-2.0 code repo. Entry 086 already ran that clerk on the decision lane and did not promote it. A use as cheap intake classification was not measured. See "Laya, checked this pass" under Brian Roemmele.

### Uncertainties

- GitHub star counts below are `stargazers_count` from `api.github.com` on 2026-11-08. They move the same day.
- AgenC's "84.5% on Terminal-Bench 2.1 for $27" is an upstream README claim. This research did not re-run it.
- Aggregator counts for MCP servers (roughly 25k, 60k, and 170k on different sites the same day) disagree. They are not facts about tool quality.
- Smithery's proxy shutdown on 31 October 2026 is from a secondary write-up, not from a Smithery status page opened here.
- `grokbot.rocks` redirects to a Read Multiplex URL. The first commit did not open the member site. This continuation still did not read member bodies. Public episode notes claim a directory of more than 8,300 Grok bots in 32 categories. The parent-read 31 Oct 2026 note gives a different count, about 9,628 templates, 32 categories, updated daily. Neither count was checked inside the directory. Both stay claims.
- A parallel deep-research workflow was still in its verify phase when `6980ff8f` was committed. Its output was not folded in then, and this continuation does not start a new sweep. New material is the parent-read notes plus the Laya and x402 public checks.
- The parent-read comparison of bot platforms (8 Nov 2026) names a seven-part frame and ten products. It does not, in the note supplied here, score them on track, catalog, evaluate, integrate, and promote. This pass did not re-check those ten products.
- Zero-Human Company notes supplied by the parent (24 Jan, 27 Feb, 10 Jul, and the 5 Oct "How To Hire A Grok Bot" post) name no repository. They were not verified on GitHub because there was nothing to open. They stay idea-level.
- Author numbers on the Laya model card (0.766 accuracy, 32.8 ms on a T4, the Jev comparison) are upstream claims. The card itself says the Jev figures were not measured in that run. This pass did not re-benchmark Laya.
- This worktree does not contain `origin/main` commit `1e546d96` ("supersede watch", 2026-11-08). That commit was read with `git show` and not merged. It reaches the same stop/no-stop answer. One of its Flux details is not in the README fetched today (see Flux). After that commit, `origin/main` kept moving with F5 receipt commits. Those were not reviewed for this question and were not merged. The watch files themselves were not changed after `1e546d96`.

## What "the suite" means here

From `docs/DESIGN.md`, the catalog mission is track, categorize, rank, and integrate local-first LLM development tools. The product surface is `./pfy` (onboard, stage, ship). The catalog is how pieces are chosen.

| Part | Working evidence in this repo | What does not count |
|------|-------------------------------|---------------------|
| Track | `sources/x-posts.md`, `sources/entries/`, aggregates | A README that says "always up to date" |
| Catalog | `TOOLS.md`, slim `data/tools.json` (ADR-0015), one card per tool in `data/stages/` | An awesome-list or a star sort |
| Evaluate | Stage 0 plus rubric; integration stages I0–I4; `self_pipeline` before I3 when the tool touches CI, test, or review | A benchmark number in a launch post |
| Integrate | Skill, smoke, eval task, or cage path, and a run on this repo's own pipeline | Listing the tool, or vendoring it |
| Promote | A stage move plus a receipt. I3 is onboard. I4 is a rare embed. Catalog score is not a stage. | Stars, install counts, "the only agent that…" |

I0 awareness, I1 staged evaluation, I2 probe, I3 integrated, I4 embedded. Rule: `docs/ops/integration-stages.md`. This checkout has **129** stage cards. **No card is I4.** I3 on this checkout: agent-cage (PNNL), codebase-memory-mcp, destructive_command_guard, Grok CLI bootstrap, llama.cpp ngram-mod, project-process bootstrap, Sandlock, skill-up, SkillSpector, write-guard-mcp. Of those, codebase-memory-mcp and skill-up record `self_pipeline` status `applied`. The others at I3 were not re-audited field by field in this pass.

Local-first and a permissive license are gates (`README.md`, `CATEGORIZATION.md`). A hosted registry or an AGPL browser can be watched. It is not an embed.

## Method

Read first, in this worktree: `AGENTS.md`, `README.md`, `docs/DESIGN.md`, `docs/adr/README.md`, `docs/eval/TOOLSET-RANKING.md`, `docs/ops/integration-stages.md`, `data/stages/*.json` (129 cards), `data/harnesses.json`, and the TOOLS.md rows for the names already catalogued.

Then, on 2026-11-08: GitHub REST API for repository metadata, raw READMEs and one LICENSE file, arXiv abstracts, and a small set of project pages. Web pages and repo text were treated as untrusted data. No `auth.json`, no `.dev.vars`, no installs.

`origin/main` contains `1e546d96`, which this branch does not. That commit adds `data/supersede-watchlist.json` and `docs/ops/supersede-watch.md`. Its four-part suite (track, catalog, evaluate, integrate) matches this question except that this report keeps **promote** as its own part. Its verdict is the same: nothing is `replace_us`. The watchlist's ten projects are Flux, X Patrol Deploy, Hermes Agent, Decision Hub, Tessl, Argusic, Sandcastle, mattpocock/skills, AgenC, and OpenCode. Laya, GrokBot.Rocks, and x402 are not on it. Later F5 receipt commits on `origin/main` are outside this verdict. The branch was not fast-forwarded. This continuation re-read those two files with `git show 1e546d96` and did not edit them.

This continuation did not repeat the candidate sweep. It took the parent-read member notes as claims, confirmed the URLs answer HTTP 200 with a members-only marker, and opened only the public repos those notes named as adoptable software: Laya and x402. Local fit for Laya uses Entry 086, `docs/dogfood/LAYA-TRIAL-RESULTS.md`, and `docs/dogfood/LAYA-SHADOW-RESULTS.md`, which were already in this worktree.

## Catalog cross-reference

Absence below means no stage card and no TOOLS.md row found by search in this worktree. A weak search is not the only check: stage filenames and TOOLS.md were both searched.

| Candidate | Recorded stage | Where |
|-----------|----------------|-------|
| AgenC core (`tetsuo-ai/agenc-core`) | **I0** | `data/stages/agenc.json`. Pin `126ee5b` = tag `agenc-v0.19.32`. Verdict file `eval/evq1107/agenc/VERDICT`: stay I0. TOOLS.md tier B, "reference only", cites ADR-0010. |
| AgenC marketplace umbrella | Not a card | Different repo. See disambiguation. |
| mattpocock/skills | **I1** | `data/stages/mattpocock-skills.json`. Evidence path `bootstrap/grok-cli/skills-external/mattpocock`. Ceiling I1. |
| Sandcastle | No card | Used as sandcastle-grok in ops docs and tests. `origin/main` watchlist says the same. |
| OpenCode | No card | Harness slot `opencode`, status `partial`, `github` null, `catalog` null. `bootstrap/opencode/` is an adapter, not an upstream pin. Related cards: opencode-mem **I2**, opencode-skill-creator **I0**. |
| Hermes Agent | **I1** | `data/stages/hermes-agent-feedback-loops.json`, posture `pattern_only`. Harness slot `hermes` is `partial`. Bake-off NO-WIN, `docs/PENDING-HANDOFF.md` 2026-10-19. |
| SICA, DGM, ACE, OpenEvolve, ShinkaEvolve, CodeForge | No card | Not in TOOLS.md under those names. |
| BrowserOS | No card, no TOOLS.md row | `sources/x-posts.md` Entry 040 says "Processed and cataloged". The stage registry and TOOLS.md do not contain it. That is drift. |
| skill-up | **I3** | `data/stages/skill-up.json`. nimo: both arms 5/5, delta 0. Not a Feature GO. |
| harness2 | **I1** | `data/stages/harness2.json`. Held-out 15/16 both ways, gain 0. |
| MCP registries, skills.sh, Smithery, Glama, Decision Hub, Tessl, Argusic, Flux, X Patrol | No card | Except skills.sh appears as a link inside Entry 105 (anti-slop), which is not a card for skills.sh itself. |
| Laya (`NandhaKishorM/laya`, weights `convaiinnovations/laya`) | No card | Entry 086. Trial-ran 2026-10-06. Catalog HOLD 70–75. No TOOLS.md row. Shadow flag `PFY_JEV_LAYA_SHADOW` default off. |
| x402 (`x402-foundation/x402`) | No card | Payments protocol. Named only as a non-goal on Monid and Runx intake. |

ADR-0010 (2026-07-12) rejected AgenC as the primary runtime after a TUI trial. ADR-0013 (2026-07-27) supersedes the absolute "catalog-only" posture: the AgenC surface may be scored, the default stays Grok plus agent-cage, and preference is measured only after real use. The 2026-11-07 card still says stay I0 and do not install. ADR-0013 did not promote it.

## Candidates

Overlap is split on purpose. "Partial" means the README or the code shows that slice. It does not mean the slice is good.

### AgenC (three different things)

**Coding agent, the one this catalog means.** [tetsuo-ai/agenc-core](https://github.com/tetsuo-ai/agenc-core). MIT. 114 stars. Default-branch tip `92d519f6e2` at 2026-11-08 18:39 UTC, author login `signerless`, message starts "eval(harbor): run AgenC the way the published TB2.1 runs did". Release `agenc-v0.19.32` is commit `126ee5b` (7 Nov 2026), the same pin as the I0 card. npm `@tetsuo-ai/agenc` 0.19.32. Maintained harness: daemon, TUI, headless `agenc -p`, many providers including Ollama. README goal text is "multiply model capability per dollar of inference" and the Terminal-Bench sentence above. That bench line is their claim.

Overlap: track none, catalog none, evaluate partial (they run their own Harbor/Terminal-Bench and an internal Hermes comparison dated 2026-09-04 in `docs/eval/real-agent-comparison-2026-09-04.md`), integrate partial (it is a runtime you could sit inside, not a tool pipeline), promote none. Local fit: yes, if you accept Node 26.x or their installer. Conflict: ADR-0002 and ADR-0011 defaults, the July 2026 TUI and auth trial, and the November 2026 card. **Verdict: ignore as a suite. Keep the I0 watch. Do not reinstall for this question.**

**Marketplace umbrella.** [tetsuo-ai/AgenC](https://github.com/tetsuo-ai/AgenC). GPL-3.0. 195 stars. Pushed 2026-11-04. Solana escrow marketplace where agents are hired and paid. Its own docs still call `agenc-core` a private daemon; the core repo is public. Live money. **Verdict: ignore.** Not a tool catalog. Do not wire it.

**Lookalikes.** `tetsuo-ai/agenc-c` is a small MIT C library set (1 star), not a harness. `agency-agents` and forks are persona packs. They are not AgenC. **Verdict: ignore.**

### Matt Pocock

**Skills.** [mattpocock/skills](https://github.com/mattpocock/skills). MIT. 318,387 stars. Default-branch tip `4ae2317` at 2026-10-31 14:23 UTC, author `mattpocock`, "software-factory: glossary skill for designing a factory (#1316)". `pushed_at` is 2026-11-05, so other branches may be newer than `main`. This repo's `AGENTS.md` already points at that software-factory skill as an external glossary, not a vendored copy. The pack is user-invoked engineering skills (grill, spec, TDD, review). It does not watch the world for tools.

Overlap: all five parts none, as a pipeline. The skills are content. **Verdict: adopt a piece, already done (I1). Do not replace process docs or the catalog with the pack.**

**Sandcastle is his.** [mattpocock/sandcastle](https://github.com/mattpocock/sandcastle). MIT. 8,930 stars. Tip `ed8e716` at 2026-11-05 11:49 UTC, author `mattpocock`. `pushed_at` 2026-11-06. Release `v0.14.0` was cut 2 Nov 2026 (GitHub releases page). README fetched raw on 2026-11-08: orchestrate coding agents in sandboxes and merge branches back. Native sandboxes use the OS (Bubblewrap on Linux). Cloud providers are optional. His 1 Nov 2026 post (`@mattpocockuk`, status `2116805878187794740`) pitches a larger v1: six harnesses, durable factories, and every skill as `Agent()`. That pitch is not the README.

Overlap: track none, catalog none, evaluate none, integrate partial (a lane runner; sandcastle-grok already runs some of this repo's lanes), promote none. Local fit: the Bubblewrap provider matches a local-first lab; Daytona, E2B, Modal, and Vercel do not have to be used. Conflict: a second isolator next to agent-cage (I3), and a factory vocabulary next to `./pfy build` and `/agent-loops`. **Verdict: adopt a piece only after a read-only probe. Do not adopt the factory pitch as the product.**

**software-factory skill.** Glossary and five design questions inside `mattpocock/skills` at `4ae2317`. Not a running factory. **Verdict: borrow the questions, already cited. Ignore as software.**

### OpenCode

Canonical repository: [anomalyco/opencode](https://github.com/anomalyco/opencode), "The open source coding agent." MIT. 225,484 stars. Tip `ff4a652` at 2026-11-08 19:05 UTC, author login `rekram1-node`. `api.github.com/repos/sst/opencode` returns the same id and the same `full_name` (`anomalyco/opencode`). The rename of in-repo links is PR 6687, merged 2 Jan 2026 by `thdxr`. Maintained harness (terminal and desktop, any provider, MIT). Secondary pages also describe an OpenCode 2 line (v2.2.x in late October 2026). Those version strings were not re-checked against the releases API.

Overlap: track none, catalog none (models.dev is a sibling model list, not verified in this pass), evaluate none for outside tools, integrate partial (it is the worker), promote none. Local fit: yes, pointed at `LOCAL_OPENAI_BASE_URL` (ADR-0014). Conflict: making it the primary harness would drop ADR-0002. **Verdict: adopt a piece, already the secondary surface. Record the canonical URL on the harness record later. Do not vendor it.**

### Self-improving harnesses

These rewrite an agent, a prompt, or a program. They do not watch X for tools and promote the ones that win a rubric.

**Hermes Agent.** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). MIT. 261,703 stars. Tip `acdc8f1` at 2026-11-08 10:27 UTC, author login `kshitijk4poor`. Org: Nous Research. README, fetched raw: "The self-improving AI agent" and "the only agent with a built-in learning loop". Working surface in that README: skills, memory, FTS5 session search, cron, messaging gateway, subagents, several terminal backends including local and Docker. The "only" sentence is marketing. Companion repo [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution): 5,674 stars, `pushed_at` 2026-06-17, GitHub license API returned 404 (no detected license). Its README describes DSPy+GEPA for skill files as implemented, and later phases (tool descriptions, system prompt, tool code, continuous loop) as planned. That is a research add-on, not the shipping harness.

This repo already ported the feedback pattern (`/hermes-feedback`) and kept the runtime off the card (`non_goals`: Hermes as primary runtime). The October 2026 bake-off did not clear the win bar. Overlap: track none, catalog partial (Skills Hub / agentskills.io, their skills, not our tool universe), evaluate partial (a curator over its own sessions, not a rubric over outside tools), integrate partial (harness slot), promote none for outside tools. Local fit: possible, with `HERMES_HOME` isolation, as in the bake-off notes. **Verdict: adopt a piece, already done as a pattern. Do not switch the operator to Hermes. Do not adopt the self-evolution repo.**

**SICA.** [MaximeRobeyns/self_improving_coding_agent](https://github.com/MaximeRobeyns/self_improving_coding_agent). MIT. 415 stars. `pushed_at` 2025-04-23. Workshop paper, ICLR 2025 SSI-FM, arXiv:2504.15228. The paper's claim is 17% to 53% on a random subset of SWE-bench Verified. Research prototype. No 2026 commits. **Verdict: ignore the code. The loop shape (benchmark archive, then edit yourself) is a paper, not a product.**

**Darwin Gödel Machine.** Paper: Zhang, Hu, Lu, Lange, Clune, arXiv:2505.22954, published as an ICLR 2026 conference paper. Code: [jennyzzt/dgm](https://github.com/jennyzzt/dgm). Apache-2.0. 2,494 stars. `pushed_at` 2025-08-13. Sakana's write-up (30 May 2025) states SWE-bench 20.0% to 50.0% and Polyglot 14.2% to 30.7%. Those are paper results. The repo is not moving. Unofficial reimplementations exist (`lemoz/darwin-godel-machine` and others). They are not the paper's repo. **Verdict: ignore as a harness to adopt. A self-modifying agent that keeps an archive is a research bet with a high bill and a real risk of training on the judge.**

**ACE (Agentic Context Engineering).** Paper: Qizheng Zhang and others, arXiv:2510.04618, ICLR 2026. Code the authors pointed at: [ace-agent/ace](https://github.com/ace-agent/ace). Apache-2.0. 1,439 stars. Tip `82709de` at 2026-08-24, author login `momoway`. The paper's claim is about +10.6% on agent tasks and +8.6% on finance by evolving a context playbook, not by editing weights. Research code, quieter since August 2026. Overlap with `/hermes-feedback` and skill text is the idea of a curated playbook. **Verdict: borrow the idea if a later memory or skill ticket needs incremental context updates. Do not adopt the repo as a runtime.**

**OpenEvolve.** [algorithmicsuperintelligence/openevolve](https://github.com/algorithmicsuperintelligence/openevolve). Apache-2.0. 7,737 stars. Tip `c1f4c31` at 2026-11-07, author login `Qile-J`. README: open implementation of AlphaEvolve, LLM mutations, MAP-Elites, any problem you can score. Maintained research tool. It evolves programs. It does not catalog dev tools. **Verdict: ignore for this mission. Adopt a piece only when a ticket has an automatic score and a reason to search programs.**

**Nearby, same class.** [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve), Apache-2.0, 1,502 stars, pushed 2026-10-05. Sample-efficient program evolution. Same verdict as OpenEvolve, and not a second tool to probe in parallel. [skyvanguard/CodeForge](https://github.com/skyvanguard/CodeForge), MIT, 0 stars, pushed 2026-03-24. A blog calls it a local Hyperagents port. The repo metadata does not support "maintained". **Verdict: ignore.** Survey list [iSEngLab/Awesome-Self-Evolving-Coding-Agents](https://github.com/iSEngLab/Awesome-Self-Evolving-Coding-Agents), 152 stars, no license detected, pushed 2026-10-04. A bibliography. **Verdict: ignore as software. Useful only as a map of papers.**

### Brian Roemmele

**Public items opened in the first pass, or already in the repo.** Paid pages were not used for these:

- X post 14 July 2026, `@BrianRoemmele`, status `2077011759114973616`, promoting BrowserOS. The same post is Entry 040 in `sources/x-posts.md`.
- Public Substack post the same day naming [browseros-ai/BrowserOS](https://github.com/browseros-ai/BrowserOS) and `browseros.com`.
- [browseros-ai/BrowserOS](https://github.com/browseros-ai/BrowserOS). AGPL-3.0. 14,283 stars. Pushed 2026-11-08. Org `browseros-ai`. Active browser product. Nothing in the API result shows Roemmele as the owner. He documented it. He is not, on this evidence, the maintainer.
- Public podcast and Apple Podcasts listing (early November 2026) for a directory he calls GrokBot.Rocks: "every public Grok bot", with counts in the episode notes (more than 8,300, 32 categories). Those counts are episode-note claims. `grokbot.rocks` redirects to `readmultiplex.com`.

BrowserOS overlap: track none, catalog none, evaluate none, integrate none for our tool loop, promote none. It is a local-ish agent browser with an MCP server. AGPL conflicts with the permissive-embed gate. The Entry 040 receipt says cataloged. The stage registry does not have a card. **Verdict: ignore as a suite. Reconcile the catalog drift later. Do not embed AGPL code.**

**Parent-read member notes, not read by this pass.** The parent supplied these from Read Multiplex. This pass confirmed each URL returns HTTP 200 and that the HTML includes a members-only marker. The article text was not used. Maturity of anything that lives only inside those pages is unknown here.

- 8 Nov 2026, [I tested every bot platform](https://readmultiplex.com/2026/11/08/i-tested-every-bot-platform-so-you-did-not-have-to-here-is-what-i-found/). Parent says the piece compares Dots, Muse, ChatGPT Work, Claude, Gemini, Copilot, Manus, Perplexity, OpenClaw, and Grok Bot on a frame of brain, computer, hands-tools, memory, clock, leash-safety, and recipe. That frame is a bot-platform checklist. It is not the five-part suite in this report. The supplied note does not crown a replacement catalog. OpenClaw is the same host already ignored under X Patrol Deploy. **Verdict: ignore as a suite. The frame is a borrow-idea for how someone else describes a bot, not a score we adopt.**
- 31 Oct 2026, [Why I built GrokBot.Rocks](https://readmultiplex.com/2026/10/31/why-i-built-grokbot-rocks-the-compressive-directory-of-all-known-public-grok-bots/). Parent observation, paywalled: a searchable index of about 9,628 public Grok templates across 32 categories, updated daily. This pass did not count the index. The public episode notes say more than 8,300 and the same 32 categories. Discovery only. Overlap with our suite: a directory can feed track, and it does not catalog dev tools, score improvement vectors, integrate a tool, or promote on a receipt. **Verdict: ignore. Do not treat either count as a catalog fact.**
- Member starter kit at [readmultiplex.com/grokbot-rocks](https://readmultiplex.com/grokbot-rocks/). Public title on the HTTP 200 shell: "Every Grok Bot: The Complete Directory". Parent says the member kit contains a memory template, a routine prompt, safety rules, a token-budget checklist, multi-bot coordination, and a launch checklist. No repo was named. **Verdict: borrow-idea for operator checklists if a later ops ticket wants them. Not a suite. Not software to pin.**
- Zero-Human Company, parent dates 24 Jan, 27 Feb, and 10 Jul. Parent summary: LM Studio and LM Link nodes, a Mirafish sim, and markdown memory swarms. 5 Oct, "How To Hire A Grok Bot": parent calls it idea-level orchestration and self-refining scripts. No repository was supplied, so none was verified. **Verdict: ignore as adoptable code. Unknown maturity. Leave it as a note.**

### Laya, checked this pass

The 7 Nov 2026 parent-read post, [A simple way to make Grok Bot run faster and cost less](https://readmultiplex.com/2026/11/07/a-simple-way-to-make-grok-bot-run-faster-and-cost-less/), names Laya as a local 421M-parameter Apache-2.0 model for bounded routing and classification, and cites `convaiinnovations/laya`. The parent likens it to a TypeSafe Jev clerk. The post's performance claim was not read here and is not treated as measured.

Public records on 2026-11-08:

| Check | Result |
|-------|--------|
| `github.com/convaiinnovations/laya` | HTTP 404 from `api.github.com`. That path is not a GitHub repository. |
| Code repo | [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya). Apache-2.0 on the GitHub license API. 35,221 stars. Default-branch tip `2e50c4e` at 2026-11-08 18:09 UTC, author `NandhaKishorM`. Description: non-autoregressive System 1 decision engine, typed choice, score, and yes/no, with a router that picks the checkpoint. Homepage points at the Hugging Face repo. |
| Weights | [huggingface.co/convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya). Not gated. Card metadata `license: apache-2.0`, `pipeline_tag: text-classification`. Hub sha `7b928d828b7b0e022f929d9bd2e44165aa270148`, `lastModified` 2026-10-03. API `safetensors.total` is 421,293,830, one 421M checkpoint, not the sum of the three folders. Same revision string as the 6 Oct trial. The GitHub tip is newer than that sha. Its message says a v0.4.30 release gate failed before publish. That is a runtime-repo fact. The weights the trial loaded have not moved. |
| What the card says the model is | English root: ModernBERT-large, 421M, 512-token context. `laya-multilingual`: mmBERT-base, 322M, 1,024 tokens, up to 8,192 with `max_len`. `laya-typed-decisions`: ModernBERT-large, 421M, 1,024 tokens, fine-tuned on that benchmark. `Router` sends English to the English checkpoint and other languages to multilingual. `laya-serve` speaks `POST /v1/systemone`, the TypeSafe Jev wire. It does not generate text. |
| Card's own limit on the headline number | Fine-tuned checkpoint 0.766 on 2,000 typed decisions. Base English checkpoint 0.362 on the same set. The card's baselines on that set are 0.318 random and 0.461 majority-class, so 0.362 sits above random and below majority. The 0.766 figure is the checkpoint trained on that benchmark's training split. Jev 1.13.0 numbers on the card are marked third-party, not measured in that run. T4 latency figures (about 33–40 ms) are the card's GPU claim. |

Local fit, from files already in this worktree, not from the member post:

- Entry 086 (2026-10-05) and the eval-auto trial (2026-10-06, nimo, CPU) already asked whether Laya can fill the TypeSafe slot with no key. ADR-0016 keeps CUA-S1-FORMS as `PRIMARY_LOCAL`. TypeSafe stays optional cloud.
- On 48 labeled Choice cases, gate 0.85: `laya:english` raw accuracy 30/48 (62.5%) and **0/48 held**. Confidence max 0.6553. `laya:typed-decisions` 27/48 and 0/48 held. Warm p50 about 0.20 s. Process high-water about 4.57 GB with both checkpoints loaded. CUA-S1-FORMS was 27/48 accurate, 11/48 escalate, about 26 MB. The written recommendation is to keep CUA. Catalog HOLD 70–75. No stage card. Not a Feature GO.
- Shadow (`PFY_JEV_LAYA_SHADOW`, default off): english caught 9 of 16 CUA wrong-but-confident cases and false-escalated 4 of 21 held-correct cases. English-only high-water about 2.9 GB. The write-up says keep the flag off unless an operator is already running `laya-serve`.
- A Grok Bot box CPU smoke (8 vCPU, no GPU, package `laya` 0.3.28) returned the README billing example as `billing` at confidence 0.9865 in 16.9 s including the first download. That shows the CPU path runs. It is one example, not a speed win.
- The license passes the permissive gate. The weights fit a CPU host that already has a few gigabytes free. The English 512-token budget is a tight fit for a long intake post. The built-in router chooses a language checkpoint. It does not classify a tool into this catalog.

Overlap with the five parts: track none, catalog none, evaluate none for outside tools, integrate none for the catalog pipeline, promote none. The decision-layer trial already pointed `laya-serve` at the Jev wire and left the default on CUA. That experiment is not suite integration. The parent's "faster and cheaper Grok bot" claim is not established by the October receipt: on that set Laya was slower and much larger than CUA, and it never auto-acted. Using it as a cheap intake classifier for new sources is a different task, and this repo has no measurement of that task. Unknown until that set exists: whether a short intake label fits the 512-token English budget, and whether confidence on that set clears 0.85.

**Verdict: do not add it to the adopt list. Do not reinstall it from the 7 Nov post. Keep the October disposition (shadow off, CUA primary). Reopen only with a new labeled intake-classification set, and only as a bounded classifier, after the October confidence result is treated as the prior.** The `1e546d96` watchlist does not need a Laya row for the supersede question: Laya does not cover two of track, catalog, evaluate, and integrate.

### x402, one public check

[x402-foundation/x402](https://github.com/x402-foundation/x402). Apache-2.0. 6,793 stars. Pushed 2026-11-08. API description: "A payments protocol for the internet. Built on HTTP." The parent asked for a brief mention and called agent payments likely out of scope. This repo already names x402 only as something intake must not wire (Monid, Runx). **Verdict: ignore. Out of scope for the suite.**

### Discovery, catalog, and eval projects that are not the suite

**Flux.** [Nairon-AI/flux](https://github.com/Nairon-AI/flux). MIT. 7 stars. Pushed 2026-05-12. README fetched 2026-11-08: a Codex-first SDLC harness. `/flux:improve` matches session friction to a recommendation cache and can offer installs. `Nairon-AI/flux-recommendations` returns HTTP 404. The current README text that was fetched does not mention an X radar. The `origin/main` watchlist says Flux Radar read curated X accounts. That sentence is **not confirmed** by the README read today. Even if an older radar existed, the repo has not been pushed since May 2026, the recommendations repo is gone, and the scoring described is friction-to-tool, not I0–I4 on improvement vectors. **Verdict: watch only if it ships again. Do not adopt. Closest idea, not a working suite.**

**X Patrol Deploy.** [00OO666/x-patrol-deploy](https://github.com/00OO666/x-patrol-deploy). 0 stars. No license detected. Pushed 2026-02-28. About text: an OpenClaw skill that patrols an X feed and deploys tools. **Verdict: ignore.** Stale, unscored, wrong host agent.

**Decision Hub.** [pymc-labs/decision-hub](https://github.com/pymc-labs/decision-hub). MIT. 113 stars. Pushed 2026-10-23. README: self-hostable skill registry (CLI, server, UI). Every publish can run sandboxed eval cases with an LLM judge and an A–F security grade. Skills only. Author-submitted. Data-science slant. Public hub is `hub.decision.ai`. Overlap: track partial (GitHub republish of skills you point at), catalog full for skills, evaluate partial (publish-time cases, not our vectors, and the judge is an LLM), integrate none into a coding product's pipeline, promote partial (a public report is not I3). Local fit: `make deploy-local` is real in the README and needs Docker. Conflict: skill-up is already the grader, and an LLM judge is a different contract than script checks. **Verdict: adopt a piece later, the eval-case file shape only, if a ticket asks for publish-time skill tests. Do not replace the catalog.**

**Tessl registry.** [tessl.io](https://tessl.io/blog/skills-are-software-and-they-need-a-lifecycle-introducing-skills-on-tessl/) blog, 29 Jan 2026, by Guy Podjarny. Hosted skill registry. The post says review evals exist for over 2,000 skills and that task evals compare with and without the skill. Commercial and hosted. **Verdict: watch the uplift-per-skill idea. Do not adopt the service.**

**Argusic.** [argusic.com](https://argusic.com/), fetched 2026-11-08. Public pages say an agent clones a pinned project on a clean machine and records whether it runs. Homepage figures that day: 3,719 subjects, 5,520 runs. A subjects page the same day said 3,706 tested. Methodology page: the thing measured is "does it run", and the agent-versus-agent leaderboard's first cycle was still "in progress" on the copy that search returned (page stamp in the snippet: 8 Oct 2026). Many homepage rows show the same score, 92. I did not open a log. **Verdict: adopt a piece as prior "does it run" evidence for an I2 probe, after one log is actually opened. It does not answer "does it improve the work". Do not treat the score as a rubric.**

**Official MCP Registry.** [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry). 7,454 stars. Pushed 2026-11-08. License file: new contributions Apache-2.0, docs CC-BY-4.0, older contributions still MIT until relicensed. Live API at `registry.modelcontextprotocol.io`. Docs say it is metadata for public MCP servers, host apps should not consume it directly, and the implementation is not meant to be self-hosted. **Verdict: adopt a piece as a tracked feed. Do not fork it.**

**Smithery, Glama, PulseMCP, mcp.so, Docker MCP catalog, awesome-mcp-servers.** Directories and rankings. [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) is MIT, 97,485 stars, pushed 2026-11-06: a list. MCP Toplist (8 Nov 2026) says it ranks by versions, stars, and age across those directories, and it printed 172,960 servers. A different public page the same day said the official registry had about 60,194. Another said about 25,445 after filters. **Verdict: ignore as a suite.** A star rank is not an improvement vector. Smithery as a proxy is a bad dependency: a 3 Nov 2026 secondary article says the proxy and API shut down on 31 Oct 2026 and the site remains a directory under Arcade. Unverified against Smithery's own status page.

**skills.sh.** Not fully fetched (cross-host redirect). Secondary descriptions (Skillburst, 27 Feb 2026; SkillReg comparison, 16 Oct 2026) call it Vercel's public skill directory and installer. **Verdict: borrow as a place to look up a skill URL. Not an evaluator. Not verified by opening the site in this pass.**

**skill-up and harness2, already measured here.** skill-up ([alibaba/skill-up](https://github.com/alibaba/skill-up), Apache-2.0, 1,439 stars, pushed 2026-11-06) is I3. The nimo run graded with and without a skill and found no difference. harness2 ([google-research/harness2](https://github.com/google-research/harness2), Apache-2.0, 23,125 stars, pushed 2026-11-02) is I1 with gain 0. Both are evidence that a famous eval harness can land in this repo and still not show a quality gain. **Verdict: keep skill-up. Leave harness2 at I1. Do not adopt either as the suite.**

## What would have counted as "stop"

A single maintained, local-first, permissively licensed project whose own docs and repo show all of the following, not a slide:

1. It ingests outside sources on a schedule, including something like X or GitHub, and writes a deduped record per tool.
2. It scores claims on more than one improvement vector, and it keeps the failed evidence.
3. A tool is not "in" until that project uses it on its own pipeline and can show the run.
4. Promotion is a recorded decision, and a high star count cannot skip the decision.

Flux is the only project whose README even sketches (1) and a thin (3), and it is dormant, Codex-specific, and missing (2) and (4). Decision Hub and Tessl sketch a skill-only (2). Argusic sketches a different question. Hermes sketches self-improvement of itself. None of them is the suite.

## Integration and conflict risks

- Replacing Grok or the catalog with OpenCode, Hermes, or AgenC collides with ADR-0002, ADR-0011, and the AgenC card. ADR-0013 allows scoring AgenC. It does not make it the default.
- Sandcastle next to agent-cage is two isolators. Use the Bubblewrap provider only if a probe shows a job cage does not do (branch strategy and merge-back). Leave cloud providers off.
- A second skill registry (Decision Hub, Tessl, Smithery skills, skills.sh) next to skill-up and the first-party skill tree splits the source of truth. `bootstrap/opencode/README.md` already says the skill source of truth is `bootstrap/grok-cli/skills/`.
- Self-modifying loops (SICA, DGM, Hermes self-evolution, OpenEvolve pointed at this repo) fight write-guard, cage policy, and "receipts over vibes". They can also fit the judge.
- AGPL (BrowserOS, and the AgenC umbrella's GPL-3.0) is not an embed.
- The MCP Registry's own docs say not to self-host it and not to point host apps at it directly.
- Entry 040 says BrowserOS was cataloged. The machine catalog has no card. Fixing that is a catalog change, out of scope here.
- `origin/main` already wrote a watchlist with this same stop rule. Merging this report and that commit needs a human pass so the two do not fork into two decision logs. This report does not edit `docs/adr/` or the watchlist.
- Promoting Laya from the 7 Nov member post would ignore the 6 Oct receipt and ADR-0016. The shadow flag stays off. A member speed claim is not a new checkpoint: the Hub sha still matches the trial revision `7b928d82`.
- GrokBot.Rocks templates and the member starter kit are prompts and a directory. Copying them into `bootstrap/grok-cli/skills/` would add a second skill source of truth. The kit was not copied.

## Next probes

Each probe is a read or a one-hour eval. None of them is a reason to believe a tool is better before the eval exists. Do not install from this report.

1. When catalog edits are allowed, set the OpenCode harness `github` to `https://github.com/anomalyco/opencode` and note that `sst/opencode` is the same repo id. No version bump.
2. Read Sandcastle `docs/guide/sandbox-providers.md` beside `harness/agent-cage/` and write down one job only Sandcastle does. If there is no such job, stop. Do not npm-install it in the product repo.
3. Leave AgenC at I0. The 8 Nov 2026 commit is a Harbor eval tweak, not the UX gates in ADR-0010 (clear approvals, Grok-subscription auth, parity with Grok, Claude Code, and OpenCode).
4. Reconcile Entry 040 with the missing BrowserOS card. Expected outcome is a watch row or an explicit "receipt was wrong", not an integrate.
5. If skill publish-time tests become a ticket, diff Decision Hub's eval YAML against skill-up's case format. skill-up stays the runner until a harder set shows a non-zero delta.
6. Before citing an Argusic score, open one published log and see if the commands match the verdict. Until then the number is a claim.
7. Do not schedule SICA, DGM, ACE, or OpenEvolve. Reopen OpenEvolve only with a scorer and a held-out set.
8. Optional intake: one read-only pull of the official MCP Registry API, deduped against `data/stages/`, stored as a note. Not a self-hosted registry.
9. After this branch can see `1e546d96`, fold this report's corrections (Flux radar not in the current README, OpenCode repo id, AgenC's two licenses, BrowserOS drift) into the watchlist. Do not keep two stop-rules. Do not add Laya, GrokBot.Rocks, or x402 to that list unless a later read shows one of them covering two suite parts.
10. Do not reopen Laya from the 7 Nov member post. The October trial is the prior. A new ticket needs a labeled intake-classification set and has to beat "always escalate at 0.85" before any flag default changes. No install from this report.

## Handoff

- Question answered: do not stop. No whole-suite adoption. The parent-read member notes do not change that. Laya is not a new adopt piece.
- File: `docs/research/2026-11-08-adopt-or-build.md` on `research/adopt-or-build-20261108`. First commit `6980ff8f`. This continuation is a second local commit on the same file.
- Not done, on purpose: no catalog triple-write, no stage-card edits, no Sandcastle card, no OpenCode URL edit, no Laya flag change, no merge of `1e546d96` or later `origin/main` F5 commits, no PR, no install, no push.
- The owner of the next catalog pass should treat the ten probes as the queue. Probe 2 and probe 4 are the only ones that change what we might adopt. The rest are bookkeeping or explicit non-adoptions.
- If a later web pass finds a project with all five parts full, the decision goes to Mark in writing. It does not land as a silent swap.
- Adopt pieces, unchanged order: record the OpenCode canonical repo; Sandcastle only after a read-only probe; keep mattpocock/skills, skill-up, and the Hermes pattern; MCP Registry as an intake feed; OpenEvolve only with an automatic score. Laya, GrokBot.Rocks, the member starter kit, the Zero-Human notes, and x402 are not on that list.

## Sources

Primary, opened or returned by the GitHub API on 2026-11-08 unless noted:

- https://github.com/tetsuo-ai/agenc-core and raw README via the API and search snapshots of `README.md`, releases, and `docs/eval/real-agent-comparison-2026-09-04.md`
- https://github.com/tetsuo-ai/AgenC including `docs/CODEBASE_MAP.md` and `docs/GETTING_STARTED.md`
- https://github.com/mattpocock/skills commit `4ae2317`
- https://github.com/mattpocock/sandcastle raw README; releases page for `v0.14.0`
- https://github.com/anomalyco/opencode and the `sst/opencode` API redirect to the same id; PR https://github.com/anomalyco/opencode/pull/6687
- https://github.com/NousResearch/hermes-agent raw README
- https://github.com/NousResearch/hermes-agent-self-evolution
- https://github.com/MaximeRobeyns/self_improving_coding_agent and https://arxiv.org/abs/2504.15228
- https://github.com/jennyzzt/dgm and https://arxiv.org/abs/2505.22954 and https://sakana.ai/dgm/
- https://github.com/ace-agent/ace and https://arxiv.org/abs/2510.04618 and https://ace-agent.github.io/
- https://github.com/algorithmicsuperintelligence/openevolve
- https://github.com/SakanaAI/ShinkaEvolve
- https://github.com/browseros-ai/BrowserOS
- https://github.com/modelcontextprotocol/registry and its `LICENSE`, plus https://modelcontextprotocol.io/registry/about
- https://github.com/Nairon-AI/flux raw README; API 404 for `Nairon-AI/flux-recommendations`
- https://github.com/00OO666/x-patrol-deploy API about text
- https://github.com/pymc-labs/decision-hub raw README
- https://argusic.com/ and https://argusic.com/methodology and https://argusic.com/subjects
- https://tessl.io/blog/skills-are-software-and-they-need-a-lifecycle-introducing-skills-on-tessl/
- https://x.com/BrianRoemmele/status/2077011759114973616
- https://x.com/mattpocockuk/status/2116805878187794740
- Local: `docs/DESIGN.md`, `docs/adr/0010-reject-agenc-as-primary-runtime.md`, `docs/adr/0011-hybrid-operator-surfaces-grok-opencode-ollama.md`, `docs/adr/0013-optional-operator-tuis-empirical-preference.md`, `docs/ops/integration-stages.md`, `docs/eval/TOOLSET-RANKING.md`, `data/stages/`, `data/harnesses.json`, `TOOLS.md`, `sources/x-posts.md` Entry 040, `eval/evq1107/agenc/VERDICT`, `docs/PENDING-HANDOFF.md`
- Read-only from `origin/main` at `1e546d96`: `docs/ops/supersede-watch.md`, `docs/ops/HANDOFF-supersede-watch-1108.md`, `data/supersede-watchlist.json`. Re-read in this continuation with `git show`. Not merged.
- This continuation, public only: `api.github.com` 404 for `convaiinnovations/laya`; `api.github.com` for `NandhaKishorM/laya` (license Apache-2.0, tip `2e50c4e`); Hugging Face model API and raw README for `convaiinnovations/laya` (sha `7b928d82`, card license apache-2.0); `api.github.com` for `x402-foundation/x402`. HTTP 200 title-and-marker check only for the four Read Multiplex URLs listed below. Member bodies were not read.
- Local Laya prior, already in the tree: `sources/entries/086-laya.md`, `docs/dogfood/LAYA-TRIAL-RESULTS.md`, `docs/dogfood/LAYA-SHADOW-RESULTS.md`, ADR-0016.

Secondary, labeled as such in the text: MCP Toplist, Skillful.sh, the 3 Nov 2026 Smithery shutdown article, Skillburst on skills.sh, releasealert.dev for Hermes canaries, and the CodeForge blog. Those were not used as the maturity numbers in the tables above.

Parent-read, paywalled, not independently accessed in this pass. Findings in the Brian Roemmele section are the parent's notes, not a reading of the articles:

- https://readmultiplex.com/2026/11/08/i-tested-every-bot-platform-so-you-did-not-have-to-here-is-what-i-found/
- https://readmultiplex.com/2026/11/07/a-simple-way-to-make-grok-bot-run-faster-and-cost-less/
- https://readmultiplex.com/2026/10/31/why-i-built-grokbot-rocks-the-compressive-directory-of-all-known-public-grok-bots/
- https://readmultiplex.com/grokbot-rocks/
- Zero-Human Company posts dated by the parent 24 Jan, 27 Feb, 10 Jul, and 5 Oct 2026 ("How To Hire A Grok Bot"). No URLs were supplied for those four, and none were fetched.
