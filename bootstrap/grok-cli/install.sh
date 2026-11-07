#!/usr/bin/env bash
# install.sh — Replay Grok CLI customizations from pfy-mentat.
#
# Idempotent. Safe to re-run. Does not touch auth tokens.
#
# Usage:
#   ./bootstrap/grok-cli/install.sh
#   ./bootstrap/grok-cli/install.sh --dry-run
#   ./bootstrap/grok-cli/install.sh --skills-only
#   ./bootstrap/grok-cli/install.sh --with-codebase-memory
#   ./bootstrap/grok-cli/install.sh --no-ponytail
#   ./bootstrap/grok-cli/install.sh --no-mattpocock
#   ./bootstrap/grok-cli/install.sh --no-permission-mode
#
# Env:
#   GROK_HOME          default: ~/.grok
#   GROK_SKILLS_DIR    default: $GROK_HOME/skills
#   SKIP_CODEBASE_MEMORY=1
#   SKIP_PONYTAIL=1
#   SKIP_MATTPOCOCK=1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
PONYTAIL_SRC="$SCRIPT_DIR/skills-external/ponytail"
MATTPOCOCK_SRC="$SCRIPT_DIR/skills-external/mattpocock"
CLAUDE_UA_SRC="$SCRIPT_DIR/skills-external/claude-unified-agents"
PROJECT_PROCESS_SKILL="$SCRIPT_DIR/../project-process/skills/project-process"
MERGE_PY="$SCRIPT_DIR/scripts/merge_config.py"

GROK_HOME="${GROK_HOME:-$HOME/.grok}"
GROK_SKILLS_DIR="${GROK_SKILLS_DIR:-$GROK_HOME/skills}"
CONFIG_TOML="$GROK_HOME/config.toml"

DRY_RUN=0
SKILLS_ONLY=0
CONFIG_ONLY=0
MCP_ONLY=0
WITH_CODEBASE_MEMORY=0
NO_PONYTAIL=0
NO_MATTPOCOCK=0
NO_CLAUDE_UA=0
NO_PERMISSION_MODE=0
FORCE=0
VERIFY=0

log()  { printf '==> %s\n' "$*"; }
warn() { printf 'warn: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \?//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skills-only) SKILLS_ONLY=1; shift ;;
    --config-only) CONFIG_ONLY=1; shift ;;
    --mcp-only) MCP_ONLY=1; shift ;;
    --with-codebase-memory) WITH_CODEBASE_MEMORY=1; shift ;;
    --no-ponytail) NO_PONYTAIL=1; shift ;;
    --no-mattpocock) NO_MATTPOCOCK=1; shift ;;
    --no-claude-ua) NO_CLAUDE_UA=1; shift ;;
    --no-permission-mode) NO_PERMISSION_MODE=1; shift ;;
    --force) FORCE=1; shift ;;
    --verify) VERIFY=1; shift ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

[[ -d "$SKILLS_SRC" ]] || die "skills source missing: $SKILLS_SRC"
[[ -f "$MERGE_PY" ]] || die "merge script missing: $MERGE_PY"

# Honour env skips
if [[ "${SKIP_PONYTAIL:-0}" == "1" ]]; then NO_PONYTAIL=1; fi
if [[ "${SKIP_MATTPOCOCK:-0}" == "1" ]]; then NO_MATTPOCOCK=1; fi
if [[ "${SKIP_CODEBASE_MEMORY:-0}" == "1" ]]; then WITH_CODEBASE_MEMORY=0; fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'dry-run:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

install_first_party_skills() {
  log "Installing first-party skills → $GROK_SKILLS_DIR"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    find "$SKILLS_SRC" -mindepth 1 -maxdepth 1 -type d -printf 'dry-run: would install skill %f\n'
    return 0
  fi
  mkdir -p "$GROK_SKILLS_DIR"
  local skill
  for skill in "$SKILLS_SRC"/*/; do
    [[ -d "$skill" ]] || continue
    local name
    name="$(basename "$skill")"
    local dest="$GROK_SKILLS_DIR/$name"
    if [[ -e "$dest" && "$FORCE" -ne 1 ]]; then
      # Overwrite skill content (idempotent refresh of managed skills)
      :
    fi
    mkdir -p "$dest"
    # Prefer rsync if available
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "$skill" "$dest/"
    else
      rm -rf "$dest"
      mkdir -p "$dest"
      cp -a "$skill"/. "$dest/"
    fi
    log "  skill: $name"
  done
  # project-process skill (scaffold DESIGN/ADR/TODO/OQ into any repo)
  if [[ -d "$PROJECT_PROCESS_SKILL" ]]; then
    local dest="$GROK_SKILLS_DIR/project-process"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "dry-run: would install skill project-process"
    else
      mkdir -p "$dest"
      if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete "$PROJECT_PROCESS_SKILL/" "$dest/"
      else
        rm -rf "$dest"; mkdir -p "$dest"; cp -a "$PROJECT_PROCESS_SKILL"/. "$dest/"
      fi
      log "  skill: project-process"
    fi
  else
    warn "project-process skill missing at $PROJECT_PROCESS_SKILL"
  fi
}

# Collect absolute dirs for [skills].paths (external packs; not copied into ~/.grok/skills)
SKILLS_PATH_ABS=()

install_ponytail_path() {
  if [[ "$NO_PONYTAIL" -eq 1 ]]; then
    log "Skipping ponytail skills path (--no-ponytail)"
    return 0
  fi
  [[ -d "$PONYTAIL_SRC" ]] || die "ponytail snapshot missing: $PONYTAIL_SRC"
  local abs
  abs="$(cd "$PONYTAIL_SRC" && pwd)"
  SKILLS_PATH_ABS+=("$abs")
  log "Ponytail skills path: $abs"
}


install_claude_ua_path() {
  if [[ "${NO_CLAUDE_UA:-0}" -eq 1 ]]; then
    log "Skipping claude-unified-agents skills path (--no-claude-ua)"
    return 0
  fi
  if [[ ! -d "$CLAUDE_UA_SRC" ]] || [[ ! -f "$CLAUDE_UA_SRC/security-auditor/SKILL.md" ]]; then
    warn "claude-unified-agents snapshot missing: $CLAUDE_UA_SRC"
    return 0
  fi
  local abs
  abs="$(cd "$CLAUDE_UA_SRC" && pwd)"
  SKILLS_PATH_ABS+=("$abs")
  log "claude-unified-agents skills path: $abs (curated subset; PORT.md)"
}

install_mattpocock_path() {
  if [[ "$NO_MATTPOCOCK" -eq 1 ]]; then
    log "Skipping mattpocock skills path (--no-mattpocock)"
    return 0
  fi
  if [[ ! -d "$MATTPOCOCK_SRC/tdd" ]]; then
    warn "mattpocock snapshot missing or incomplete: $MATTPOCOCK_SRC"
    return 0
  fi
  local abs
  abs="$(cd "$MATTPOCOCK_SRC" && pwd)"
  SKILLS_PATH_ABS+=("$abs")
  log "mattpocock skills path: $abs (tdd, code-review, to-spec)"
}

install_codebase_memory() {
  if [[ "$WITH_CODEBASE_MEMORY" -ne 1 ]]; then
    log "Skipping codebase-memory binary install (pass --with-codebase-memory to fetch)"
    cache_cm="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin/codebase-memory-mcp"
    if command -v codebase-memory-mcp >/dev/null 2>&1; then
      log "Found existing: $(command -v codebase-memory-mcp)"
    elif [[ -x "$cache_cm" ]]; then
      log "Found existing: $cache_cm"
    else
      warn "codebase-memory-mcp not on PATH or in ~/.cache/pfy/bin; MCP entry will be configured but inactive until installed"
    fi
    return 0
  fi
  log "Installing codebase-memory-mcp (official installer, --skip-config)"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "dry-run: curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config"
    return 0
  fi
  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh \
    | bash -s -- --skip-config
  cache_cm="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin/codebase-memory-mcp"
  if ! command -v codebase-memory-mcp >/dev/null 2>&1 && [[ ! -x "$cache_cm" ]]; then
    warn "install finished but codebase-memory-mcp not on PATH or in ~/.cache/pfy/bin (check ~/.local/bin)"
  fi
}

merge_config() {
  log "Merging Grok config → $CONFIG_TOML"
  local args=(python3 "$MERGE_PY" --config "$CONFIG_TOML")
  local p
  for p in "${SKILLS_PATH_ABS[@]:-}"; do
    [[ -n "$p" ]] || continue
    args+=(--skills-path "$p")
  done
  if [[ "$NO_PERMISSION_MODE" -eq 1 ]]; then
    args+=(--permission-mode "")
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    args+=(--dry-run)
  fi
  "${args[@]}"
}

verify() {
  log "Verifying install"
  local ok=1
  local name
  # Prefer dynamic list from manifest; fall back to known core set
  local names=()
  if command -v python3 >/dev/null 2>&1 && [[ -f "$SCRIPT_DIR/manifest.json" ]]; then
    mapfile -t names < <(python3 -c '
import json,sys
m=json.load(open(sys.argv[1]))
for s in m.get("first_party_skills",{}).get("skills",[]):
    print(s["name"])
' "$SCRIPT_DIR/manifest.json" 2>/dev/null || true)
  fi
  if [[ ${#names[@]} -eq 0 ]]; then
    names=(adr docs open-questions karpathy-guidelines project-process catalog-docs one-shot marketing-council investigate agent-loops hermes-feedback)
  fi
  for name in "${names[@]}"; do
    if [[ -f "$GROK_SKILLS_DIR/$name/SKILL.md" ]]; then
      echo "  OK skill $name"
    else
      echo "  MISSING skill $name"
      ok=0
    fi
  done
  if [[ "$NO_PONYTAIL" -ne 1 ]]; then
    if [[ -f "$PONYTAIL_SRC/ponytail/SKILL.md" ]]; then
      echo "  OK ponytail snapshot"
    else
      echo "  MISSING ponytail snapshot"
      ok=0
    fi
  fi
  if [[ "$NO_MATTPOCOCK" -ne 1 ]]; then
    if [[ -f "$MATTPOCOCK_SRC/tdd/SKILL.md" && -f "$MATTPOCOCK_SRC/code-review/SKILL.md" && -f "$MATTPOCOCK_SRC/to-spec/SKILL.md" ]]; then
      echo "  OK mattpocock snapshot (tdd, code-review, to-spec)"
    else
      echo "  MISSING mattpocock snapshot subset"
      ok=0
    fi
  fi
  if [[ -f "$CONFIG_TOML" ]]; then
    if grep -q 'mcp_servers.codebase-memory' "$CONFIG_TOML"; then
      echo "  OK config MCP codebase-memory"
    else
      echo "  MISSING config MCP codebase-memory"
      ok=0
    fi
    if grep -q '\[memory\]' "$CONFIG_TOML" && grep -q 'enabled = true' "$CONFIG_TOML"; then
      echo "  OK memory enabled (section present)"
    fi
    if [[ "$NO_MATTPOCOCK" -ne 1 ]] && grep -q 'skills-external/mattpocock' "$CONFIG_TOML"; then
      echo "  OK config paths include mattpocock"
    fi
  else
    echo "  MISSING $CONFIG_TOML"
    ok=0
  fi
  if command -v grok >/dev/null 2>&1; then
    echo "  OK grok binary: $(grok --version 2>/dev/null || echo present)"
  else
    warn "grok not on PATH — install from https://x.ai/cli/install.sh"
  fi
  cache_cm="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin/codebase-memory-mcp"
  if command -v codebase-memory-mcp >/dev/null 2>&1; then
    echo "  OK codebase-memory-mcp on PATH"
  elif [[ -x "$cache_cm" ]]; then
    echo "  OK codebase-memory-mcp at $cache_cm"
  else
    echo "  note: codebase-memory-mcp not on PATH or in ~/.cache/pfy/bin (use --with-codebase-memory)"
  fi
  [[ "$ok" -eq 1 ]] || die "verification failed"
  log "Verification passed"
}

# --- main -------------------------------------------------------------------

log "pfy-mentat Grok CLI bootstrap"
log "repo: $REPO_ROOT"
log "GROK_HOME: $GROK_HOME"

SKILLS_PATH_ABS=()

if [[ "$MCP_ONLY" -eq 1 ]]; then
  WITH_CODEBASE_MEMORY=1
  install_codebase_memory
  install_ponytail_path
  install_mattpocock_path
  install_claude_ua_path
  merge_config
  [[ "$VERIFY" -eq 1 ]] && verify
  log "Done (mcp-only)."
  exit 0
fi

if [[ "$CONFIG_ONLY" -eq 1 ]]; then
  install_ponytail_path
  install_mattpocock_path
  install_claude_ua_path
  merge_config
  [[ "$VERIFY" -eq 1 ]] && verify
  log "Done (config-only)."
  exit 0
fi

if [[ "$SKILLS_ONLY" -eq 1 ]]; then
  install_first_party_skills
  install_ponytail_path
  install_mattpocock_path
  install_claude_ua_path
  # still wire paths so external packs are discoverable
  merge_config
  [[ "$VERIFY" -eq 1 ]] && verify
  log "Done (skills-only)."
  exit 0
fi

# Full install
install_first_party_skills
install_ponytail_path
install_mattpocock_path
install_claude_ua_path
install_codebase_memory
merge_config
verify

cat <<EOF

Bootstrap complete.

Next steps:
  1. Ensure Grok is installed:  curl -fsSL https://x.ai/cli/install.sh | bash
  2. Authenticate if needed:    grok login   (or export XAI_API_KEY=...)
  3. Restart any running Grok sessions so skills/MCP reload.
  4. Optional binary fetch:     $0 --with-codebase-memory
  5. In a project: "Index this project" (codebase-memory) once MCP is live.

Managed skills: adr, docs, open-questions, karpathy-guidelines, project-process, catalog-docs, one-shot
Extra skills path: ${PONYTAIL_ABS:-"(disabled)"}
Config: $CONFIG_TOML
Manifest: $SCRIPT_DIR/manifest.json

New project process scaffold:
  $REPO_ROOT/bootstrap/project-process/init.sh /path/to/repo --name <name>
EOF
