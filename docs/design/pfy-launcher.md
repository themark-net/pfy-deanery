# Design: `pfy` launcher — pick a harness, pick a model, install the catalog into it

Status: **Proposed** (design only; no code in this PR) · 2026-10-12 · base `main` @ `a5c0362`
Owner: the operator · Related: [0012-simple-harness-agnostic-launch.md](../adr/0012-simple-harness-agnostic-launch.md) (simple `./pfy`; the number 0012 is also used by `0012-voice-half-duplex-local-first.md`, so cite this filename), ADR-0014 (inference spine), "ADR-0017" (toolset × harness; cited in `pfylib/` but **not yet in `docs/adr/`**), `data/harnesses.json`, `data/toolsets.json`, `pfylib/toolsets.py`, `scripts/pfy_launch_wizard_225.py` (#225).

> The operator: "an extremely good example of integrating skills and functionality to existing agents is [morluto/rea]. Figure out how to make pfy-mentat as easy as this to set up, or easier. The point of our repo is to add these types of tools such as rea but also additional ones. Think about how ollama lets you pick your harness."

## 1. Problem

Today a new user has to: clone the repo, run `./pfy setup`, then `./bootstrap/grok-cli/install.sh [--with-codebase-memory]`, then optional `make env-init` / `make env-check` profiles, then `./pfy toolset apply <id> --harness <h> --yes` one toolset at a time, and read AGENTS.md, ADR-0011, `docs/adr/0012-simple-harness-agnostic-launch.md` (not the voice file that reuses number 0012), and `bootstrap/opencode/README.md` to work out which surface is "primary". The skills live in three places (`.grok/skills/`, `bootstrap/grok-cli/skills/`, `bootstrap/project-process/skills/`). Only Grok really installs end to end. Claude Code, Codex, Hermes, OpenCode, Gemini, Exo, and Continue are all `partial` in `data/harnesses.json`. Gemini, Exo, and Continue are `stub` in the toolset matrix, and `./pfy start continue` is a separate STUB exit. Setup is really an operator lab. It is not a product install.

rea gets the same job (put tools + skills into whichever agent you already use) down to **one command plus a reviewed plan**. Ollama's `ollama launch` gets the "pick your harness, pick your model" job down to **one command plus one selector**. `pfy` should do both.

## 2. What rea does (findings from morluto/rea @ main, npm 6.4.0)

1. **Install is split from setup.** `curl …/install.sh | bash` only installs the CLI (npm global; Linux to `--prefix ~/.local`, so there is no sudo). It prints a plan (version, runtime, exact npm command, binary path), supports `--dry-run / --version / --no-setup`, and then runs `rea setup` only when a TTY exists. The script is wrapped in `{ … }` so a truncated `curl | bash` download is a syntax error and does nothing.
2. **One `setup` verb wires any harness.** `npx rea-agents setup` detects installed clients, lets you multi-select, shows the **exact paths and changes**, and writes only after approval. Scripts use `--client X` (repeatable), `--all-detected`, `--dry-run`, `--yes`, and `--json`. A bare `--yes` only refreshes existing rea-owned entries and never selects new clients.
3. **Per-client adapters are a data table plus a format writer.** `src/application/SupportedClients.ts` gives each client a name, a `configPath` resolver that honours env overrides, a `markerPath` for detection, a `skillPath`, and a `format`: json, toml, opencode, grok, vscode, copilot_cli, and others. It supports 18 clients: Claude Code/Desktop, Codex, Cursor, Gemini CLI, Windsurf, Devin, OpenCode, Antigravity, Copilot CLI, Command Code, Qwen, VS Code, Grok Build, OMP, Pi, Hermes, and DeepSeek Harness. Examples: Claude `~/.claude.json` (respects `CLAUDE_CONFIG_DIR`); Codex `$CODEX_HOME/config.toml`; Cursor `~/.cursor/mcp.json`; Grok Build `[mcp_servers.rea]` in `$GROK_HOME/config.toml` with `startup_timeout_sec = 30`; OpenCode V1 `mcp.rea` or V2 `mcp.servers` (respects `OPENCODE_CONFIG_DIR`).
4. **The integration has two parts: an MCP server plus a matching skill.** The MCP entry is pinned to the exact version that ran setup (`npx -y rea-agents@6.4.0 mcp`). The skill is copied to each client's personal skills dir: `~/.claude/skills` for Claude, and the shared `~/.agents/skills` for most others (Grok Build already reads it). Skill-only install also exists through `npx skills add morluto/rea`, and rea is published in the official MCP Registry (`server.json`).
5. **Writes are transactional and safe.** Malformed config blocks the whole transaction before anything is written. Writes preserve unrelated keys and comments. Backups use `.rea.backup`, and the first snapshot is never overwritten. Replacement is atomic and verified afterward.
6. **Ownership-scoped lifecycle.** `rea doctor` is strictly read-only and can be scoped (`--client`, `--skill`, `--provider`). `rea update` updates only the install that owns the running binary, then prints a scoped setup to refresh registrations. `rea uninstall` removes **only rea-owned** registrations and skill files. `--purge-data` removes `~/.rea` but never follows symlinks.
7. **Honest manual fallbacks.** For a harness it cannot write to, rea says so instead of faking it. For example, Grok Bot connectors live in the account, so `doctor --client grok_bot` reports a manual step. Each client also has a `verify-<client>-client.mjs` end-to-end check.

## 3. What `ollama launch` adds

`ollama launch` opens a selector of harnesses (Claude Code, Codex, OpenCode, Droid, OpenClaw, Hermes, …), then a model selector. It then **execs the harness with the model wired through env/flags** (Claude: `ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_AUTH_TOKEN=ollama`). `ollama launch claude --model X --yes -- <args>` is the non-interactive form: `--yes` skips selectors and requires `--model`, and everything after `--` goes to the harness. The model choice applies to the launched process only, so no global config is rewritten just to try a model.

## 4. Proposal in one paragraph

`pfy` becomes a **single user-level CLI** with three verbs that matter: `pfy setup` (rea-style: detect harnesses, pick catalog items, show plan, apply, verify), `pfy launch` (ollama-style: pick harness + model source, exec it with the chosen model wired into that one process), and `pfy doctor/update/uninstall`. A **catalog manifest** declares each installable item (skills, MCP servers, external CLIs such as rea) **once**. Per-harness **adapters** translate an item into that harness's native config. This generalises the existing `data/toolsets.json` × `data/harnesses.json` matrix and `pfylib/toolsets.py` file modes, so there is no parallel system. rea becomes one catalog item; pfy delegates to `rea setup --client <id> --yes` instead of re-implementing rea's writer.

## 5. User experience

```bash
# one line (no sudo, no clone needed):
curl -fsSL https://raw.githubusercontent.com/themark-net/pfy-mentat/v0.4.17/install.sh | bash
#  → installs pfy to ~/.local/share/pfy (pinned tag) + shim ~/.local/bin/pfy, then runs `pfy setup` if a TTY exists

pfy setup                         # interactive: harnesses → catalog items → plan → approve
pfy setup --harness grok --harness claude-code --item rea --item core-skills --dry-run --json
pfy launch                        # selector: harness, then model source
pfy launch claude-code --model ollama:qwen3.6:35b --yes -- -p "explain this repo"
pfy launch grok                   # Grok subscription (grok login), no model rewiring
pfy launch cursor                 # Cursor CLI with Cursor subscription
pfy doctor [--harness X] [--item Y] [--json]   # read-only
pfy update                        # update pfy itself, then print scoped `pfy setup` refresh
pfy uninstall [--harness X] [--item Y] [--purge-data]
```

Interactive `pfy setup` screen (plain TTY; works in the existing GUI later):

```
Detected harnesses:  [x] Grok Build (~/.grok)   [x] Claude Code (~/.claude)   [ ] Codex (not found)   [x] OpenCode
Catalog (recommended preset "core"):
  [x] core-skills    adr, docs, investigate, agent-loops, …  (skill)
  [x] rea            reverse engineering MCP + skill        (external: delegates to `rea setup`)
  [x] code-graph     codebase-memory MCP                    (mcp)
  [ ] jev            typed decision layer                   (skill+env)
Plan: 9 writes, 3 backups, 1 external command (npx -y rea-agents@6.4.0 setup --client grok_build --client claude_code --yes)
Apply? [y/N]
```

## 6. Model sources (the operator pays for Grok and Cursor only)

| Source id | Meaning | Harnesses | How it is wired |
|---|---|---|---|
| `grok` | Grok subscription (`grok login`) | Grok Build | native; no env |
| `cursor` | Cursor subscription | Cursor CLI (`cursor-agent`) | native; no env |
| `ollama:<tag>` | local Ollama (`:11434`) | Claude Code, Codex, OpenCode, Hermes, Droid… | **prefer delegating to `ollama launch <h> --model <tag>`** when Ollama ≥ the version with `launch`; else per-adapter env (Claude: `ANTHROPIC_BASE_URL/AUTH_TOKEN`; Codex/OpenCode: OpenAI-compatible base URL `http://localhost:11434/v1`) |
| `llamacpp:<alias>` | local llama-server / llama-swap (ADR-0014 spine) | same as above | OpenAI-compatible base URL from `./pfy models` detector; Claude via LiteLLM gateway (`config/litellm/local-only.yaml`) because Claude speaks Anthropic |

Rules: only `grok` and `cursor` are paid. Every other harness is offered **only with a local source**. Claude Code and Codex never get a paid vendor key from pfy, and pfy never prompts for one. A harness/source pair that does not work is shown greyed out with a reason (such as "Claude Code needs a local model ≥64k ctx; none pulled → `pfy models pull qwen3.6:35b`"). It is never silently skipped. `pfy launch` sets model env **for the child process only**. It never writes model/base-URL into harness config, so launching never breaks the user's normal `claude` or `codex`.

## 7. Catalog manifest (`catalog/items/<id>.json`, or an extension of `data/toolsets.json`)

Recommendation: **extend `data/toolsets.json` (v2) instead of adding a new tree**, so `pfy toolset matrix` and the Loop GUI keep working. Shape of one item:

```json
{
  "id": "rea",
  "title": "REA — reverse engineer anything",
  "kind": "external",                       
  "version": "6.4.0",
  "source": {"npm": "rea-agents", "pin": "6.4.0", "repo": "morluto/rea", "license": "MIT"},
  "catalog_ref": {"tools_json_id": "rea", "tier": "A"},
  "requires": [{"bin": "node", "min": "22.19"}, {"bin": "npx"}],
  "provides": {
    "mcp": [{"name": "rea", "command": "npx", "args": ["-y", "rea-agents@6.4.0", "mcp"], "env": {}, "startup_timeout_sec": 30}],
    "skills": [{"name": "reverse-engineer-anything", "from": "upstream"}]
  },
  "install": {
    "strategy": "delegate",
    "delegate": {"cmd": ["npx", "-y", "rea-agents@6.4.0", "setup", "--yes", "--json"], "client_flag": "--client",
                 "client_map": {"grok": "grok_build", "claude-code": "claude_code", "codex": "codex", "cursor": "cursor", "opencode": "opencode", "hermes": "hermes", "gemini": "gemini_cli"}},
    "uninstall": {"cmd": ["npx", "-y", "rea-agents@6.4.0", "uninstall"]},
    "doctor": {"cmd": ["npx", "-y", "rea-agents@6.4.0", "doctor", "--json"], "client_flag": "--client"}
  },
  "harnesses": {"grok": "implemented", "claude-code": "implemented", "codex": "implemented", "cursor": "implemented", "opencode": "implemented", "hermes": "partial"},
  "presets": ["core", "re"],
  "network": ["registry.npmjs.org"],
  "secrets": []
}
```

`kind` values: `skill` (a dir with `SKILL.md`, copied or symlinked), `mcp` (server entry pfy writes itself), `external` (tool with its own installer/setup; pfy delegates and records ownership), `env` (process env for `launch` only), and `bundle` (a preset of other ids, such as `core-skills`). `install.strategy` is either `native` (pfy adapters write it) or `delegate` (call the tool's own setup, which is what rea gets). `secrets` must be empty for any item in a preset. An item that needs a key is opt-in and reads it from env at runtime; pfy never stores it. Validation: `pfy catalog validate` (extends `make eval-structural`), with a JSON Schema in `data/schema/catalog-item.v2.json`.

Skill SoT is consolidated to **one** directory, `skills/` at the repo root (or `.grok/skills/` kept as SoT). `bootstrap/grok-cli/skills/` becomes generated or a symlink. This removes today's three copies.

## 8. Harness adapters (`pfylib/adapters/<id>.py`)

Each adapter implements a narrow interface, and none of them knows anything about catalog items:

```python
class Adapter:
    id: str                      # matches data/harnesses.json id
    def detect(env) -> Detection # bin on PATH/bin_fallbacks + marker dir; version
    def paths(env) -> Paths      # config file(s), skills dir; honours *_HOME overrides
    def plan_mcp(entry) -> [Write]
    def plan_skill(skill) -> [Write]
    def remove(owned) -> [Write]
    def launch(model_source, argv) -> (argv, env) | Unsupported(reason)
```

| Harness | Detect | MCP target | Skills dir | Local-model launch |
|---|---|---|---|---|
| Grok Build | `grok`, `$GROK_HOME`/`~/.grok` | `[mcp_servers.<n>]` in `config.toml` (+`startup_timeout_sec`) | `~/.grok/skills` (+ `[skills].paths`; also reads `~/.agents/skills`) | n/a (subscription) |
| Claude Code | `claude`, `~/.claude` | `mcpServers` in `~/.claude.json` (`CLAUDE_CONFIG_DIR`) | `~/.claude/skills` | `ollama launch claude` or Anthropic env → Ollama / LiteLLM |
| Codex | `codex`, `$CODEX_HOME`/`~/.codex` | `[mcp_servers.<n>]` in `config.toml` | `~/.agents/skills` | `ollama launch codex` or `--oss`/provider env |
| Cursor CLI | `cursor-agent`, `~/.cursor` | `mcpServers` in `~/.cursor/mcp.json` | `~/.cursor/skills` (fallback: rules file) | n/a (subscription) |
| OpenCode | `opencode`, `OPENCODE_CONFIG_DIR`/XDG | `mcp.<n>` (V1) or `mcp.servers` (V2) in `opencode.json[c]` | `~/.agents/skills` | provider block via env `OPENCODE_CONFIG_CONTENT` (process-only) or `ollama launch opencode` |
| Hermes | `hermes`, Hermes home | adapter TBD (copy rea's resolver) | `~/.agents/skills` | `ollama launch hermes` |
| Gemini / Droid / Pi / Qwen | later phases | from rea's table | `~/.agents/skills` | local only |

Adapters reuse rea's resolution rules as the reference (MIT) and cite them in a comment. Where pfy already has a working path (Grok: `bootstrap/grok-cli/install.sh` with `bootstrap/grok-cli/scripts/merge_config.py`; `pfy_attach_usable_2xx.py`), the adapter wraps it first and replaces it later, which follows T-0121's "no duplicated logic" rule.

## 9. Idempotency, ownership, uninstall

- **State ledger:** `~/.local/state/pfy/installed.json` (XDG_STATE_HOME). One record per write: `{harness, item, item_version, path, kind: mcp|skill|file|delegate, key, sha256_after, backup}`. A shared skill path such as `~/.agents/skills` is one row even when two harnesses read it. Uninstall removes only ledger-recorded objects whose current hash still matches. If the user edited one, pfy reports and leaves it. A matching file with an empty backup was created by pfy: remove it, or strip only the pfy entry when other content is in the file. A clean restore deletes the `.pfy.backup`.
- **Markers in place:** MCP entries are named `<item>` with a sibling `"_pfy": {"owner": "pfy", "item": "rea", "v": "…"}` where the format allows it (JSON). In TOML, pfy uses a `# managed-by: pfy item=<id>` comment line above the table. Skills get a `.pfy-owned` file in the skill dir. These are the same kind of thing as today's `<!-- pfy-toolset:<id> -->` markers.
- **Write discipline (copied from rea):** parse every target first, and if any file is malformed, abort the whole plan. Preserve unrelated keys and comments: `tomlkit`-style round-trip, or the existing `bootstrap/grok-cli/scripts/merge_config.py` until it is replaced. Take the first backup as `<file>.pfy.backup`, once. Write to a temp file and rename atomically, then re-read to verify.
- **Re-run = no-op:** a second `pfy setup` with the same selection must report `0 writes`. A changed pin produces an in-place update of the owned entry only.
- **Delegated items:** pfy records `{kind: delegate, item: rea, clients: [...]}` and calls the tool's own `uninstall`/`doctor`. pfy never edits rea-owned entries itself.

## 10. Safety

- **No sudo, ever.** The installer refuses to run as root unless `PFY_ALLOW_ROOT=1` is set (for containers). Every path is under `$HOME` (`~/.local/{bin,share,state}`, harness homes). No system packages and no services. Missing prerequisites such as node, ollama, or a harness binary print a next step with the vendor one-liner. pfy does not run it unless `--install-missing` is given and the item is explicitly allowed.
- **No secrets.** pfy never reads, writes, copies, or prints `auth.json`, API keys, or tokens. Login is the harness's own (`grok login`, `cursor-agent login`). Catalog items with `secrets != []` are excluded from presets. `scripts/check_no_encoded_payloads.py` plus a new `pfy catalog validate` rule reject manifests whose `args`/`env` contain anything that looks like a key.
- **Plan before write.** Every mutating verb has `--dry-run`. Non-TTY runs without `--yes` stop at `needs_confirmation` (exit 1). A bare `--yes` without `--harness` refreshes only already-owned entries, which is rea's rule.
- **Pinned supply chain.** Every external item pins an exact version (npm semver or git SHA, per ADR-0003). The installer resolves a tagged pfy release and verifies the downloaded tarball SHA256 against the release manifest. The script uses rea's `{ … }` truncation guard.
- **Scope:** user-level only. A project-level install (`.cursor/mcp.json`, `.claude/settings.json` in a repo) is a later opt-in `--scope project`.
- Catalog HOLD entries (70–75) are never in presets and never auto-installed.

## 11. Exit codes and output

The codes stay as they are in `pfylib/cli.py`: 0 READY, 1 FAIL, 2 usage, 3 STUB. `--json` output is a stable `{status: planned|applied|cancelled|needs_confirmation|failed, plan:[…], doctor:{…}}`. Prompts go to stderr and data to stdout, as in rea.

## 12. Rejected alternatives

- **Re-implement rea's writer for rea.** Rejected because rea already owns pinning, backups, and per-client quirks for 18 clients. Delegation keeps one owner per entry.
- **Make pfy depend on `npx skills` / skills.sh for everything.** Rejected because it handles skills only, with no MCP or model wiring, and adds a network dependency to every install. It stays a possible *source* of upstream skills.
- **Write the model/base URL into harness config permanently.** Rejected because it breaks the user's normal (possibly paid) harness use. Env stays per-process, as `ollama launch` does it.
- **Keep the GUI-first `./pfy` (board/Loop) as the install surface.** Rejected for setup. The GUI can call the same plan/apply API later, but install must work over SSH in a plain TTY.
- **System-wide install (/usr/local, apt, brew services).** Rejected because it violates no-sudo and user-level-only.

## 13. Phased plan (each phase = one PR, observable DoD)

### Phase 1: `pfy setup` for core skills + MCP on Grok Build, Claude Code, Codex, OpenCode, with rea as a delegated item
Scope:
- `install.sh` at repo root: `{…}` guard, `--dry-run/--version/--no-setup`, installs a tagged tarball (or `git clone --depth 1` of a tag) into `~/.local/share/pfy/<ver>`, shim `~/.local/bin/pfy`, then `pfy setup` if TTY. Refuses root.
- `pfylib/adapters/{grok,claude_code,codex,opencode}.py` with `detect/paths/plan_mcp/plan_skill/remove`. No `launch` yet.
- `data/toolsets.json` v2 fields (`kind`, `provides`, `install.strategy`, `presets`, `secrets`) plus a schema, and items `core-skills` (bundle from the one skill SoT), `code-graph` (MCP), and `rea` (delegate).
- `pfylib/setup.py`: detection → selection (TTY multi-select, or `--harness/--item/--preset`) → plan → apply (transactional, backups, atomic, verify) → ledger. Also `pfy doctor` (read-only) and `pfy uninstall` (ledger-scoped).
- Tests: Trophy-style, using a throwaway `HOME` per test and fake harness homes. No real harness or network; the rea delegate is stubbed with a fake `npx` on PATH that records argv.

DoD:
1. `HOME=$(mktemp -d) bash install.sh --dry-run` prints the plan and changes nothing (the tmp HOME stays empty). The same command with `PFY_ALLOW_ROOT` unset, run as root, exits 1.
2. On a fake HOME with `~/.grok`, `~/.claude`, `~/.codex`, and an OpenCode config: `pfy setup --preset core --yes --harness grok --harness claude-code --harness codex --harness opencode` writes skills plus a `code-graph` MCP entry into all four native files. It creates one `.pfy.backup` per pre-existing file and calls fake `npx -y rea-agents@<pin> setup --client grok_build --client claude_code --client codex --client opencode --yes --json` exactly once.
3. Running the same command again reports `0 writes` and makes no new backups.
4. Unrelated pre-existing MCP entries and TOML comments survive byte-for-byte.
5. With a malformed `~/.claude.json`, the whole plan aborts before **any** write (all four files are unchanged) and exits 1 with the path and a next step.
6. `pfy uninstall` removes only ledger-owned entries and skills, leaves a user-edited owned entry or skill dir in place with a warning, and calls rea's own uninstall. A file pfy created (no backup) is removed when its hash still matches, or only the pfy entry is removed when that file has other content. A clean byte-for-byte restore deletes the `.pfy.backup`. After it runs, the harness files equal the pre-setup files.
7. `pfy doctor --json` is read-only (file hashes unchanged) and reports per-harness/item `aligned|missing|drifted`.
8. `grep -R` finds no secret, auth, or token reads in the new code. `make eval-structural` stays green.

### Phase 2: `pfy launch` (harness × model source)
Adds `Adapter.launch()` for Grok (subscription), Cursor CLI (subscription), Claude Code / Codex / OpenCode with `ollama:<tag>` (delegating to `ollama launch` when available, else env) and `llamacpp:<alias>` (OpenAI-compatible, plus LiteLLM for Claude). Adds a TTY selector and `--model/--yes/--` passthrough, and reuses `./pfy models` detection (ADR-0014).
DoD: `pfy launch claude-code --model ollama:<tag> --yes --dry-run --json` prints the exact argv and env and leaves `~/.claude*` hash-unchanged. A paid source offered for Claude or Codex is refused with a reason. With Ollama down, it exits 1 with `ollama serve` as the next step. A live smoke (gated, with one model loaded and `ollama ps` empty first) gets a response from Claude Code through local Ollama.

### Phase 3: Cursor CLI adapter + more harnesses + more items
Adds Cursor (`~/.cursor/mcp.json`, skills/rules) and Hermes, then Gemini, Droid, and Pi from rea's resolver table. Moves `jev`, `orchestration`, `opencontext`, and `catalog-ask` to the v2 item shape. Adds `presets` (`core`, `re`, `memory`, `decision`).
DoD: `pfy toolset matrix` shows no `stub` for the 6 primary harnesses on `core`. Each adapter has one fake-HOME round-trip test (setup → doctor aligned → uninstall → original).

### Phase 4: update, release, GUI
Tagged releases with a SHA256 manifest. `pfy update` (self-update, then a printed scoped refresh). The Loop GUI "Launch session" calls the same plan/apply/launch API. An optional MCP Registry / skills.sh listing for pfy's own skills pack.
DoD: from tag N, `pfy update` moves to N+1 and verifies `pfy --version`. A tampered tarball is refused. The GUI apply produces the same ledger as the CLI apply.

## 14. Open questions (to file as OQs)

- OQ: Which skill dir is the single SoT: `.grok/skills/` or a new `skills/`? (Recommendation: `skills/`, with the others generated.)
- OQ: Write ADR-0017 properly (it is cited in `pfylib/` but missing from `docs/adr/`) and add ADR-0018 "pfy launcher: setup/launch/adapters/ledger", superseding parts of `docs/adr/0012-simple-harness-agnostic-launch.md` (number 0012 is also used by `0012-voice-half-duplex-local-first.md`).
- OQ: Cursor CLI skills location. Is it a native skills dir or rules only? Verify against current Cursor CLI docs before Phase 3.
- OQ: Is the minimum Ollama version with `launch` new enough on the operator's hosts to make delegation the default?
