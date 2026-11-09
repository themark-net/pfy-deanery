---
name: hermes-feedback
description: >
  Run Hermes-style self-improvement feedback loops on Grok: (1) auto-memory —
  capture durable learnings after work; (2) auto-skill — after complex tasks,
  draft a reusable SKILL.md; (3) curator — prune, pin, and consolidate agent-
  created skills. Use when the user runs /hermes-feedback, /hermes-loops,
  "feedback loops", "auto-memory", "auto-skill", "curator", "compound learnings",
  "session retro", end-of-session reflect, or wants the agent to get smarter
  across sessions without installing Hermes Agent.
argument-hint: "[memory | skill | curator | all] [optional focus]"
---

# /hermes-feedback — Three self-improvement loops (pfy-mentat)

**Pattern, not runtime.** Inspired by [Hermes Agent](https://github.com/NousResearch/hermes-agent)
three loops (X Entry 048 / catalog **Hermes Agent (feedback loops)**). This skill is
**first-party** for Grok Build + this process stack — no Hermes install, no
awesome-hermes-skills bulk import, no AgenC.

| Loop | Hermes idea | What you do here |
|------|-------------|------------------|
| **1 · Auto-memory** | Save learnings after responses | Persist facts prefs mistakes tools into Grok memory + project process artifacts |
| **2 · Auto-skill** | After complex tasks → SKILL.md | Propose/create a focused skill when a procedure is reusable |
| **3 · Curator** | Periodic prune / pin / consolidate | Audit agent-created skills; archive dead weight; pin critical ones |

**Iron habit:** After non-trivial work, run at least **Loop 1**. After complex
work (see threshold), run **Loop 1 + 2**. Run **Loop 3** on demand or when
skills feel bloated (weekly-ish for long-running operators).

## When to run

- User: `/hermes-feedback`, `/hermes-loops`, "capture learnings", "make a skill
  from this", "curate skills", "session retro", "compound what we learned"
- End of a multi-step task, successful `/one-shot`, or major milestone
- Before context compaction / handoff to another session
- Reflect stage of the role router (Think → … → Ship → **Reflect**)

**Do not** run auto-skill for trivial one-liners, or dump secrets into memory/skills.

## Modes

| Argument | Behavior |
|----------|----------|
| *(none)* or `all` | Run loops in order 1 → 2 (if complex) → optional 3 if user asked or skill dir is messy |
| `memory` | Loop 1 only |
| `skill` | Loop 2 only (still scan for memory gaps; offer Loop 1) |
| `curator` | Loop 3 only |

---

## Loop 1 — Auto-memory

Capture what future agents need without re-deriving it.

### What to save

| Kind | Examples | Prefer store |
|------|----------|--------------|
| **Preferences** | deploy path, Grok-first, no AgenC, cage-first smokes | Grok user/project memory |
| **Stack facts** | make targets, policy files, session volume paths | Memory + short note in module docs if durable for the repo |
| **Mistakes** | wrong session cwd encoding, POLICY missing grok.com, rsync chown on bind-mount | Memory ("gotcha") + TODO/OQ if still open |
| **Tools that worked** | `make cage-grok-net-smoke`, import-host-sessions script | Memory; skill if multi-step |
| **Decisions** | ADR-0010 reject AgenC primary | Point to `docs/adr/` — do not restate entire ADR in memory |
| **Open threads** | blocked OQs, next TODO | `docs/TODO.md` / `docs/OPEN_QUESTIONS.md` — not only chat |

### Steps

1. **Scan the session** — what was learned that is still true and reusable?
2. **Dedup** — `memory_search` (or project memory files) for existing notes; update don't duplicate.
3. **Write short bullets** — each fact: *what*, *where*, *why it matters*. No novels.
4. **Project process** — if it blocks others or is P0–P2 product/tech: update **TODO** or **OQ** (do not leave only in chat).
5. **Session worksheet** (optional, multi-session work) — short trace under a committed path if the repo already uses agent worksheets; otherwise memory + TODO is enough.
6. **Report** what was written (paths / memory titles), not the full secret-laden transcript.

### Do not put in memory

- API keys, `auth.json`, tokens, passwords  
- Full customer data, private hostnames if sensitive  
- One-off chat filler with no reuse value  

---

## Loop 2 — Auto-skill creation

After a **complex** task, turn the procedure into a reusable skill so the next
run does not re-derive tools, order, and pitfalls.

### Complexity threshold (any is enough)

- **≥ 5 tool calls** toward one procedure, or  
- Multi-file / multi-service dance (cage + policy + MCP + make), or  
- User said "we will do this again", or  
- You had to rediscover non-obvious steps more than once this session  

### Steps

1. **Name** — `a-z0-9-`, 2–64 chars (e.g. `cage-session-import`).
2. **Scope** — Prefer **project** skill under `<repo>/.grok/skills/<name>/` for
   repo-specific ops; **user** `~/.grok/skills/<name>/` only if portable across
   all projects. First-party catalog ports that belong in the bootstrap live under
   `bootstrap/grok-cli/skills/` and are installed via `install.sh` (follow
   `/create-skill` + this repo's skill layout).
3. **Draft description** — what + **trigger phrases** so Grok auto-invokes.
4. **Body** — procedure steps, commands, pitfalls, handoffs. Not a blog post.
5. **Attribution** — if adapted from Hermes/upstream, note "pattern only" in
   a short `PORT.md` when shipping into bootstrap.
6. **Wire** — if first-party bootstrap skill: update `bootstrap/grok-cli/manifest.json`,
   README skills table, and re-run `./bootstrap/grok-cli/install.sh --skills-only`
   when installing for the operator. Project-only skills: write under `.grok/skills/`.
7. **Offer commit** — do not force-push; ask before push.

### Skill quality bar

- Actionable in one read  
- Explicit **Do not**  
- Links to existing ADRs/Make targets instead of copying policy  
- No secrets  

If the procedure is really "update TODO and stop", **skip** skill creation —
memory + TODO is enough.

### Handoff to create-skill

If the user wants a guided interactive scaffold, invoke **`/create-skill`**.
This loop is the **when/why/what** discipline; create-skill is the scaffold UX.

---

## Loop 3 — Curator

Keep skill surface area honest. Hermes archives unused agent-created skills
(~90 days) and supports pin + optional consolidation. On Grok we do this
**explicitly** (no background daemon required).

### Steps

1. **Inventory**
   - Project: `.grok/skills/*/`
   - User: `~/.grok/skills/*/`
   - Bootstrap source of truth (this repo): `bootstrap/grok-cli/skills/*/`
   - External packs: `skills-external/*` (do **not** delete upstream snapshots
     casually — update pin or PORT notes instead)
2. **Classify each agent-created or experimental skill**

| Class | Action |
|-------|--------|
| **Pinned / first-party process** (`adr`, `docs`, `investigate`, `hermes-feedback`, …) | Keep; edit in bootstrap only |
| **Used recently / referenced in AGENTS or smokes** | Keep |
| **Duplicate of another skill** | Merge into one; delete or archive the weaker |
| **Unused, unclear, or superseded** | Archive (see below) or delete with user OK |
| **Broken / empty** | Fix or remove |

3. **Archive** (prefer over silent delete for agent-created skills):
   - Move to `bootstrap/grok-cli/skills/_archive/<name>-YYYYMMDD/` **or**
     `.grok/skills/_archive/` for project-only, **or**
   - Set frontmatter / PORT: `status: archived` and remove from active install list
4. **Pin list** — optional short `PINNED.md` or note in `manifest.json` purpose
   field; critical skills must not be auto-archived.
5. **Consolidate** — if two skills share 80% steps, keep one entrypoint with modes.
6. **Report** table: kept / archived / merged / needs human.

### Cadence

- On `/hermes-feedback curator`  
- When install skill count grows without clear triggers  
- After a large skill-port session (e.g. T-0011-style waves)  

---

## End-of-session checklist (quick)

```text
HERMES FEEDBACK
════════════════════════════════════════
Loop 1 memory:   [bullets written | skipped — reason]
Loop 2 skill:    [path created/updated | skipped — not complex]
Loop 3 curator:  [ran: summary | skipped]
TODO/OQ:         [ids touched or —]
Secrets check:   OK (nothing sensitive persisted)
Status:          DONE | PARTIAL | SKIPPED
════════════════════════════════════════
```

## Map to this stack

| Need | Use |
|------|-----|
| Durable architecture | `/adr` |
| Parked decisions | `/open-questions` |
| Module operator docs | `/docs` / `/catalog-docs` |
| RCA before fix | `/investigate` |
| Unattended build | `/one-shot` |
| Reflect / compound | **`/hermes-feedback`** |
| Scaffold any skill | `/create-skill` |
| Catalog tool row for Hermes upstream | `TOOLS.md` + Entry 048 — do not embed Hermes repo |

## Credential hygiene (Entry 055 pattern)

Scoped keys / no raw secret sharing to sub-agents. When documenting tools or
writing skills:

- Reference env registry (`bootstrap/env/REGISTRY.md`) and profiles  
- Never paste live keys into SKILL.md, memory, or worksheets  
- Cage policy and host secrets stay outside git  

## Do not

- Install or require [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) as runtime  
- Bulk-vendor [awesome-hermes-skills](https://github.com/ZeroPointRepo/awesome-hermes-skills)  
- Create skills that duplicate `investigate` / `one-shot` / `adr` without a clear delta  
- Treat memory write as a substitute for ADR/TODO when the item is a real project decision  
- Commit `auth.json` or secrets "for the next agent"  

## Attribution

Process adapted from public descriptions of Hermes Agent feedback loops
(Entry 048 in `sources/x-posts.md`). Skill text owned first-party under
pfy-mentat (T-0048). See [PORT.md](PORT.md).
