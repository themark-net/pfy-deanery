# Verifying first-party Grok skills

**Purpose:** Prove that new skills are **on disk, listed, installable, and usable** — not only mentioned in chat.  
**Related:** `bootstrap/grok-cli/`, `/agent-loops`, `/hermes-feedback`, `/one-shot`

Skills are prompt packs. There is no full unit-test of LLM behavior without an API call. We split verification into:

| Layer | What it proves | Cost |
|-------|----------------|------|
| **0 — Structural smoke** | Files exist, frontmatter matches, manifest lists every skill, optional install dir | Free, CI-able |
| **1 — Install** | `install.sh` copies skills to `~/.grok/skills` | Free |
| **2 — Operator acceptance** | Grok loads skill; slash command / auto-invoke works | One Grok session |
| **3 — Behavioral DoD** | Agent follows the skill’s iron law / checklist on a real task | Cloud tokens |

---

## Layer 0 — Structural (required every skill PR)

From repo root:

```bash
make smoke-grok-skills
# same as:
python3 bootstrap/grok-cli/scripts/verify_skills.py
```

After install on this machine:

```bash
make smoke-grok-skills INSTALLED=1
# or:
python3 bootstrap/grok-cli/scripts/verify_skills.py --installed
```

**Pass criteria:** exit 0. Failures include: missing `SKILL.md`, `name:` ≠ directory, empty description, skill dir not in `manifest.json`, manifest entry without dir.

**When adding a skill, checklist:**

1. `bootstrap/grok-cli/skills/<name>/SKILL.md` (+ optional `PORT.md`)
2. Row in `bootstrap/grok-cli/manifest.json` → `first_party_skills.skills`
3. Mention in `bootstrap/grok-cli/README.md` skills table
4. AGENTS.md router line if it is a process skill
5. `PORT.md` states the org skill is a pointer when the pack is a doctrine port (a private ops note)
6. `make smoke-grok-skills` green
7. `./bootstrap/grok-cli/install.sh --skills-only` then `make smoke-grok-skills INSTALLED=1`

---

## Layer 1 — Install

**Host:**

```bash
./bootstrap/grok-cli/install.sh --skills-only
./bootstrap/grok-cli/install.sh --verify
ls ~/.grok/skills/agent-loops/SKILL.md
ls ~/.grok/skills/hermes-feedback/SKILL.md
```

**Cage (also part of `make cage-grok`):**

```bash
make cage-grok-skills-install
# or: docker exec … install.sh --skills-only under /workspace/pfy-mentat
```

Project mirror: `make cage-workspace-sync` copies `bootstrap/grok-cli/skills/*` → `.grok/skills/` for cwd discovery.

---

## Layer 2 — Operator acceptance (new Grok session)

Start **host** `grok` or cage `make cage-grok` / `cage-grok-run`.

| Check | How |
|-------|-----|
| Skill appears | In TUI: `/skills` or slash menu — look for `agent-loops`, `hermes-feedback` |
| Explicit invoke | `/agent-loops exits` → should print/fill eight-exit card |
| Explicit invoke | `/hermes-feedback memory` → should run Loop 1 discipline (not invent Hermes install) |
| Auto-invoke | Plain: “write the eight exits for this build loop” — agent should load agent-loops patterns |
| No runtime deps | Skill must **not** require cloning hermes-agent or extra binaries |

If slash menu stale: restart Grok session (skills reload from disk; extreme cases re-run install).

### Cage note

Cage image must have skills installed **inside** the container profile, or load from synced workspace `.grok/skills`. After skill commits:

```bash
make cage-workspace-sync   # if using workspace bind/rsync path
# re-install skills in whatever env the cage Grok uses, if separate from host ~/.grok
```

---

## Layer 3 — Behavioral DoD (per feature)

Use these as **Definition of Done** in `/one-shot` or `/agent-loops run` when changing skill text.

### `/agent-loops` DoD

1. On `/agent-loops plan <task>`, output includes a filled **LOOP EXIT CARD** with exits 1–7 non-empty.  
2. On a forced thrash (same failing check 3×), agent **stops** citing exit 5 or 7 (not infinite retry).  
3. On `audit` of `docs/ops/one-shot-workflow.md`, report which exits one-shot already covers vs gaps.  
4. Does **not** claim Hermes/AgenC must be installed.

### `/hermes-feedback` DoD

1. After a multi-step task, `/hermes-feedback` proposes memory bullets and (if complex) skill draft decision.  
2. Curator mode inventories skill dirs without deleting first-party process skills.  
3. Never writes secrets into memory/SKILL.md.

### Founder standings (T-0126)

Structural proof is still `make smoke-grok-skills` (manifest + `SKILL.md` + frontmatter `name:` = directory). These packs are prompt text; do not add unit tests that only assert the file exists.

| Skill | Behavioral check |
|-------|------------------|
| `prefer-behavior-and-fail-recover-tests` | A test review names a failure mode and recovery. Tautological or implementation-detail units are a FAIL. |
| `ui-is-the-app-design-in-loop` | Product UI cites a `docs/design/` pack. A docs/skills PR that adds no product chrome passes without a new design pack. |
| `best-effort-and-bot-budget-build-max` | Reversible docs/skills land on a named branch. The PR does not touch an open founder checkout and does not claim Feature GO. |

### Regression template (paste into PR)

```markdown
## Skill verification
- [ ] `make smoke-grok-skills` exit 0
- [ ] `make smoke-grok-skills INSTALLED=1` exit 0 (after install)
- [ ] Manual: `/agent-loops exits` in Grok
- [ ] Manual: `/hermes-feedback` or N/A if not in scope
- [ ] Behavioral DoD for this PR: …
```

---

## Iteration discipline (features stay real)

For **any** new feature (skill, make target, cage path):

1. **Name it** in TODO (`T-NNNN`) before or with the PR.  
2. **Structural proof** — script or `make smoke-*` that fails if the feature is deleted.  
3. **Operator proof** — one command or slash invocation documented under `docs/ops/` or module docs.  
4. **Behavioral DoD** — 2–5 pass/fail checks (prefer commands over vibes).  
5. **Re-run in the next session** — new iteration starts with `make smoke-grok-skills` (and relevant smokes) before claiming green.

Skills cannot be fully regression-tested offline; **layer 0 + install + one manual slash** is the minimum bar for “implemented.”

---

## Related make targets

| Target | Role |
|--------|------|
| `make smoke-grok-skills` | Layer 0 skill structure |
| `make catalog-json` | tools.json parse |
| `make smoke-write-guard` / `smoke-litellm-ollama` / … | Integration lab |
| `make eval-v02` | Scored model tasks (not skill packs) |
