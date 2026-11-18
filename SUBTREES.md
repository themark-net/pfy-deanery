# Subtree & Submodule Policy for Individual Tool Repos

This document defines the selective policy for embedding or tracking external repositories as always-available copies inside this catalog. The goal is reproducibility and pipeline independence without repo bloat.

**Core Principle**: Embed or pin only what delivers clear integration value to the Grok CLI + agents + MCP code memory + DSPy/LiteLLM + continuous pipeline stack. Most tools stay as documented + pinned-SHA references.

**Lifecycle first:** See [docs/ops/integration-stages.md](docs/ops/integration-stages.md) (I0-I4). Embed (this file) is **I4 only**, after staged evaluation (I1), optional lightweight probe (I2, <50 MB), and onboard (I3). **No symbolic first subtree** (OQ-0003: wait).

## When to Use Subtree (Rare)

Use `git subtree` only when **all** of the following are true:
- Tool is already **I3 onboard** (skill/smoke/eval path), not merely catalogued.
- The repo is small (< ~50 MB full history).
- It is S-tier or high A-tier per the staged rubric in CATEGORIZATION.md.
- You actively customize, vendor, or deeply integrate its code (not just consume via API).
- Having the exact source versioned inside this repo improves pipeline reproducibility or offline work more than a shallow clone + pinned commit.

**Examples of likely candidates**: Tiny custom MCP memory backends, small DSPy module extensions, or a minimal agent harness you fork and modify heavily.

**Explicit exclusions**:
- Large inference engines (Ollama, llama.cpp, vLLM, MLX full history).
- Full IDE agents or UIs (Continue.dev, Aider, Open WebUI).
- Any repo whose primary output is models, weights, or large binaries.
- Tools still at I1 staged evaluation or I2 ad-hoc probe only.

Subtree duplicates the entire child history under the prefix. This is powerful for the rare qualifying case but scales poorly.

## When to Use Submodules (Preferred for Most Embedded Cases)

Use git submodules when you want a lightweight pointer to a pinned commit but do not need to edit the child code inside this repo. Size impact is minimal. Still **I4** - prefer only after I3.

- Good for small-to-medium tools you want versioned but not heavily customized here.
- Also suitable for high-value *aggregate/list* repos (see sources/aggregates.md).

**I2 probe (not embed):** For ambiguous potential + <50 MB, a throwaway or `tools/_probe/<name>/` copy may be used for ad-hoc eval without claiming submodule integration - see integration-stages.md.

Add with:
```bash
git submodule add https://github.com/user/repo.git tools/<short-name>
git commit -m "submodule: add <name> at <commit>"
```

Update later:
```bash
git submodule update --remote tools/<short-name>
# or pin specific commit
git -C tools/<short-name> checkout <sha>
git add tools/<short-name>
git commit -m "submodule: pin <name> to <sha>"
```

Track in `.gitmodules` (auto-managed) and document in this file or data/tools.json.

## Default Approach for Most Tools (Recommended)

For the large majority of individual tools (**I1**):
1. Score with the full staged rubric (CATEGORIZATION.md).
2. Record in TOOLS.md table + data/tools.json with these fields:
   - `github`
   - `pinned_commit` (exact SHA or tag for reproducibility)
   - `notes` (integration notes for Grok CLI, MCP, pipeline use)
   - optional: `integration_stage` (`I1` default)
3. In pipelines / examples / CI: perform shallow clone at the pinned commit.
   Example:
   ```bash
   git clone --depth 1 https://github.com/user/repo.git tools/<name>
   cd tools/<name> && git fetch origin <sha> && git checkout <sha>
   ```
4. No embedding. This keeps the tracking repo lean while guaranteeing exact versions on demand.

## Workflow for Adding a Subtree (When Criteria Met)

```bash
# 1. Add at specific commit (recommended over branch for pinning)
git subtree add --prefix=tools/<short-name> https://github.com/user/repo.git <commit-sha-or-tag> --squash \
  -m "subtree: add <name> at <commit>"

# 2. Record immediately
# - Add entry to SUBTREES.md (below)
# - Update data/tools.json with "subtree_path": "tools/<short-name>", "pinned_commit": "<sha>"
# - Add row or update in TOOLS.md with integration notes

# 3. Future selective update (only when upstream has valuable changes you want)
git subtree pull --prefix=tools/<short-name> https://github.com/user/repo.git <branch> --squash
```

**Never** run broad `git subtree pull` on a schedule. Only pull when you have reviewed changes and decided they improve your pipeline.

## Tracking Requirements

Every subtreed or submoduled repo must have an entry in this file (or linked section) containing:
- Short name and prefix/path
- Full upstream URL
- Pinned commit SHA or tag at addition time
- Rationale (why subtree/submodule vs default pinned-SHA approach)
- Last update date and reason
- Link to corresponding TOOLS.md row and data/tools.json entry
- Any custom patches or vendored modifications made inside the prefix

## Current Subtrees / Submodules

*(None yet - OQ-0003: wait for first real I3→I4 candidate; do not force a symbolic embed.)*

## Integration with Existing Rubric & Pipeline Vision

Subtree/submodule decisions are **downstream** of:
1. Stage 0-4 scoring in CATEGORIZATION.md (catalog quality).
2. Integration stages I0-I4 in [docs/ops/integration-stages.md](docs/ops/integration-stages.md) (how deep we pull it in).

Only tools that clear value + modularity gates, reach I3, and then meet this file’s embed criteria qualify for I4. The default pinned-SHA + shallow-clone path satisfies "always available" for the rest without compromising repo health.

This policy will be reviewed after the first 2-3 real embeddings or when repo size growth becomes measurable.
