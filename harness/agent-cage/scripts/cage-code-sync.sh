#!/usr/bin/env bash
# cage-code-sync.sh — host-privileged sync between catalog clone and cage workspace
#
# Isolation stays: cage runs in a separate tree/container. This script is the
# *automated bridge* so agent commits and host edits do not permanently diverge.
#
# Default locations (override with env):
#   CATALOG_ROOT   host git clone (PFY_ROOT or local-llm-dev-tools)
#   AGENTCAGE_DIR  ~/.agentcage
#   CAGE_WS        $AGENTCAGE_DIR/workspace/pfy-mentat
#
# Usage (on HOST, not inside agent container):
#   ./harness/agent-cage/scripts/cage-code-sync.sh status
#   ./harness/agent-cage/scripts/cage-code-sync.sh from-cage   # import agent commits → host
#   ./harness/agent-cage/scripts/cage-code-sync.sh to-cage     # rsync host → cage (+ align git)
#   ./harness/agent-cage/scripts/cage-code-sync.sh sync       # from-cage then to-cage
#   ./harness/agent-cage/scripts/cage-code-sync.sh sync --push  # also git push origin
#
# Safe order for sync: always import cage history BEFORE rsync (rsync does not
# copy .git; git align uses fetch/reset so cage tip matches host).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# harness/agent-cage/scripts → catalog root
CATALOG_ROOT="${CATALOG_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
AGENTCAGE_DIR="${AGENTCAGE_DIR:-${HOME}/.agentcage}"
WORKSPACE_REPO_NAME="${WORKSPACE_REPO_NAME:-pfy-mentat}"
CAGE_WS="${CAGE_WS:-${AGENTCAGE_DIR}/workspace/${WORKSPACE_REPO_NAME}}"
BRANCH="${SYNC_BRANCH:-main}"
REMOTE_NAME="${CAGE_GIT_REMOTE:-cage-ws}"

DO_PUSH=0
FORCE=0
DRY=0

die() { echo "error: $*" >&2; exit 1; }
log() { printf '==> %s\n' "$*"; }
warn() { printf 'warn: %s\n' "$*" >&2; }

need_host() {
  if [[ -f /.dockerenv ]] || [[ -n "${AGENT_CAGE:-}" ]]; then
    # Allow override for advanced use
    if [[ "${CAGE_SYNC_ALLOW_IN_CONTAINER:-0}" != "1" ]]; then
      die "run on the host (privileged side), not inside agent-cage (set CAGE_SYNC_ALLOW_IN_CONTAINER=1 to override)"
    fi
  fi
}

parse_args() {
  CMD="${1:-status}"
  shift || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --push) DO_PUSH=1 ;;
      --force) FORCE=1 ;;
      --dry-run) DRY=1 ;;
      -h|--help) sed -n '2,30p' "$0" | sed 's/^# \?//'; exit 0 ;;
      *) die "unknown arg: $1" ;;
    esac
    shift
  done
}

git_short() {
  git -C "$1" rev-parse --short HEAD 2>/dev/null || echo "(none)"
}

git_branch() {
  git -C "$1" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(none)"
}

ensure_repos() {
  [[ -d "$CATALOG_ROOT/.git" ]] || die "CATALOG_ROOT is not a git repo: $CATALOG_ROOT"
  [[ -d "$CAGE_WS" ]] || die "cage workspace missing: $CAGE_WS (make cage-init / cage-workspace-sync once)"
  if [[ ! -d "$CAGE_WS/.git" ]]; then
    warn "cage workspace has no .git — will only rsync content (to-cage); from-cage is no-op"
  fi
}

# Paths that must not block sync (lab receipts, local MCP preset, editor noise).
is_sync_noise_path() {
  local p="$1"
  case "$p" in
    pipelines/*/results.latest.md|pipelines/*/*/results.latest.md) return 0 ;;
    pipelines/eval/structural.latest.md|pipelines/eval/results.latest.md) return 0 ;;
    .grok/config.toml|.grok/sessions/*) return 0 ;;
    *.pyc|__pycache__/*|*/__pycache__/*) return 0 ;;
  esac
  [[ "$p" == *results.latest.md ]] && return 0
  [[ "$p" == *structural.latest.md ]] && return 0
  return 1
}

# Returns 0 if repo has *meaningful* uncommitted changes (not just receipts).
repo_meaningfully_dirty() {
  local repo="$1" line path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    # porcelain v1: XY PATH or XY ORIG -> PATH
    path="${line:3}"
    path="${path#* -> }"
    if ! is_sync_noise_path "$path"; then
      return 0
    fi
  done < <(git -C "$repo" status --porcelain 2>/dev/null || true)
  return 1
}

list_noise_dirty() {
  local repo="$1" line path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    path="${line:3}"
    path="${path#* -> }"
    if is_sync_noise_path "$path"; then
      echo "  noise: $line"
    fi
  done < <(git -C "$repo" status --porcelain 2>/dev/null || true)
}

cmd_status() {
  ensure_repos
  log "catalog (host): $CATALOG_ROOT"
  echo "  branch=$(git_branch "$CATALOG_ROOT") HEAD=$(git_short "$CATALOG_ROOT")"
  git -C "$CATALOG_ROOT" status -sb | head -5 | sed 's/^/  /'
  log "cage workspace: $CAGE_WS"
  if [[ -d "$CAGE_WS/.git" ]]; then
    echo "  branch=$(git_branch "$CAGE_WS") HEAD=$(git_short "$CAGE_WS")"
    git -C "$CAGE_WS" status -sb | head -5 | sed 's/^/  /'
    # divergence
    if git -C "$CATALOG_ROOT" rev-parse --verify HEAD >/dev/null 2>&1 \
      && git -C "$CAGE_WS" rev-parse --verify HEAD >/dev/null 2>&1; then
      host_h=$(git -C "$CATALOG_ROOT" rev-parse HEAD)
      cage_h=$(git -C "$CAGE_WS" rev-parse HEAD)
      if [[ "$host_h" == "$cage_h" ]]; then
        echo "  tips: IDENTICAL"
      else
        ahead_c=$(git -C "$CATALOG_ROOT" rev-list --count "$host_h..$cage_h" 2>/dev/null || echo "?")
        ahead_h=$(git -C "$CATALOG_ROOT" rev-list --count "$cage_h..$host_h" 2>/dev/null || echo "?")
        # need objects: fetch temporarily into catalog
        git -C "$CATALOG_ROOT" fetch -q "$CAGE_WS" "+refs/heads/*:refs/remotes/${REMOTE_NAME}/*" 2>/dev/null || true
        cage_ref="refs/remotes/${REMOTE_NAME}/${BRANCH}"
        if git -C "$CATALOG_ROOT" rev-parse --verify "$cage_ref" >/dev/null 2>&1; then
          ahead_c=$(git -C "$CATALOG_ROOT" rev-list --count "HEAD..$cage_ref" 2>/dev/null || echo "?")
          ahead_h=$(git -C "$CATALOG_ROOT" rev-list --count "$cage_ref..HEAD" 2>/dev/null || echo "?")
          echo "  tips: DIVERGED  cage-ahead≈${ahead_c}  host-ahead≈${ahead_h}"
          echo "  cage tip: $(git -C "$CATALOG_ROOT" log -1 --oneline "$cage_ref" 2>/dev/null || true)"
          echo "  host tip: $(git -C "$CATALOG_ROOT" log -1 --oneline HEAD)"
        else
          echo "  tips: DIFFER (host=$host_h cage=$cage_h)"
        fi
      fi
    fi
  else
    echo "  (no git)"
  fi
  if git -C "$CATALOG_ROOT" rev-parse --verify origin/main >/dev/null 2>&1; then
    o=$(git -C "$CATALOG_ROOT" rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
    b=$(git -C "$CATALOG_ROOT" rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
    echo "  origin/main: host ahead $o / behind $b"
  fi
}

cmd_from_cage() {
  ensure_repos
  [[ -d "$CAGE_WS/.git" ]] || { warn "no cage .git — nothing to import"; return 0; }

  # Uncommitted cage work: ignore smoke/eval receipts; block on real edits
  if repo_meaningfully_dirty "$CAGE_WS"; then
    if [[ "$FORCE" -eq 1 ]]; then
      warn "cage has meaningful uncommitted changes — continuing (--force); those files not imported"
      git -C "$CAGE_WS" status --porcelain | sed 's/^/  /' | head -20
    else
      echo "error: cage workspace has uncommitted changes (not just lab receipts):" >&2
      git -C "$CAGE_WS" status --porcelain | sed 's/^/  /' | head -30
      echo "  Commit/stash in cage, or: make cage-code-sync FORCE=1" >&2
      echo "  (receipts like pipelines/**/results.latest.md are ignored automatically)" >&2
      exit 1
    fi
  else
    list_noise_dirty "$CAGE_WS" | head -10 || true
  fi

  log "fetch cage workspace → host remotes/${REMOTE_NAME}/*"
  if [[ "$DRY" -eq 1 ]]; then
    echo "dry-run: git -C $CATALOG_ROOT fetch $CAGE_WS +refs/heads/*:refs/remotes/${REMOTE_NAME}/*"
    return 0
  fi
  git -C "$CATALOG_ROOT" fetch "$CAGE_WS" "+refs/heads/*:refs/remotes/${REMOTE_NAME}/*"
  cage_ref="refs/remotes/${REMOTE_NAME}/${BRANCH}"
  git -C "$CATALOG_ROOT" rev-parse --verify "$cage_ref" >/dev/null 2>&1 \
    || die "no ${REMOTE_NAME}/${BRANCH} after fetch (cage branch name? SYNC_BRANCH=$BRANCH)"

  if git -C "$CATALOG_ROOT" merge-base --is-ancestor "$cage_ref" HEAD 2>/dev/null; then
    log "host already contains cage ${BRANCH} ($(git -C "$CATALOG_ROOT" rev-parse --short "$cage_ref"))"
  elif git -C "$CATALOG_ROOT" merge-base --is-ancestor HEAD "$cage_ref" 2>/dev/null; then
    log "fast-forward host ${BRANCH} to cage"
    git -C "$CATALOG_ROOT" merge --ff-only "$cage_ref"
  else
    log "merge cage ${BRANCH} into host (non-ff)"
    git -C "$CATALOG_ROOT" merge --no-edit -m "merge ${REMOTE_NAME}/${BRANCH}: import cage agent commits" "$cage_ref"
  fi
  log "from-cage OK host HEAD=$(git_short "$CATALOG_ROOT")"
}

# Content-only rsync: never -a (chown/chgrp fail on agent-owned bind mounts).
# Matches workspace-sync policy: transfer data, tolerate attr errors.
RSYNC_CONTENT=(
  -r --delete
  --no-owner --no-group --no-perms --omit-dir-times
  --exclude '.git/'
  --exclude '.venv/' --exclude '**/.venv/'
  --exclude 'node_modules/' --exclude '**/node_modules/'
  --exclude '.agentcage/' --exclude '__pycache__/'
  --exclude '.grok/sessions/' --exclude '.grok/config.toml'
  --exclude '.env' --exclude '.env.*'
  --exclude 'pipelines/**/results.latest.md'
  --exclude 'pipelines/eval/structural.latest.md'
  --exclude 'pipelines/catalog-item/'
  --exclude 'pipelines/smoke/agenc/'
)

prepare_cage_writable() {
  # Prefer docker root when available (host privileged)
  if command -v docker >/dev/null 2>&1 \
    && docker inspect agent-cage-agent --format '{{.State.Status}}' 2>/dev/null | grep -q running; then
    docker exec -u root agent-cage-agent bash -lc \
      'chmod -R a+rwX /workspace/pfy-mentat 2>/dev/null; true' 2>/dev/null || true
  fi
  chmod -R a+rwX "$CAGE_WS" 2>/dev/null || true
}

rsync_to_cage() {
  ensure_repos
  mkdir -p "$CAGE_WS"
  prepare_cage_writable
  log "rsync host → cage (content only; no owner/group)"
  local flags=("${RSYNC_CONTENT[@]}")
  [[ "$DRY" -eq 1 ]] && flags+=(--dry-run -v)
  set +e
  rsync "${flags[@]}" "$CATALOG_ROOT/" "$CAGE_WS/" 2> >(grep -v 'chgrp\|chown\|preserving times' >&2 || true)
  local rc=$?
  set -e
  # 0 ok; 23/24 partial (attrs / vanished) — content usually landed
  if [[ $rc -ne 0 && $rc -ne 23 && $rc -ne 24 ]]; then
    die "rsync failed rc=$rc"
  fi
  if [[ $rc -ne 0 ]]; then
    warn "rsync rc=$rc (partial attrs OK on cage bind-mount)"
  fi
}

align_cage_git() {
  [[ -d "$CAGE_WS/.git" ]] || return 0
  log "align cage git tip to host ${BRANCH}"
  if [[ "$DRY" -eq 1 ]]; then
    echo "dry-run: git -C cage fetch host + reset --hard"
    return 0
  fi
  if repo_meaningfully_dirty "$CAGE_WS" && [[ "$FORCE" -ne 1 ]]; then
    die "cage has meaningful uncommitted changes before git align — commit, from-cage, or --force"
  fi
  # Drop noise-only dirt so reset --hard is clean for receipts
  git -C "$CAGE_WS" checkout -- pipelines 2>/dev/null || true
  git -C "$CAGE_WS" clean -fd pipelines 2>/dev/null || true
  git -C "$CAGE_WS" fetch "$CATALOG_ROOT" "+refs/heads/${BRANCH}:refs/remotes/host/${BRANCH}" 2>/dev/null \
    || git -C "$CAGE_WS" fetch "$CATALOG_ROOT" "+HEAD:refs/remotes/host/${BRANCH}"
  if git -C "$CAGE_WS" rev-parse --verify "refs/remotes/host/${BRANCH}" >/dev/null 2>&1; then
    if [[ "$FORCE" -eq 1 ]] || ! repo_meaningfully_dirty "$CAGE_WS"; then
      git -C "$CAGE_WS" reset --hard "refs/remotes/host/${BRANCH}" 2>/dev/null \
        || git -C "$CAGE_WS" checkout -B "$BRANCH" "refs/remotes/host/${BRANCH}"
    else
      git -C "$CAGE_WS" checkout -B "$BRANCH" "refs/remotes/host/${BRANCH}" 2>/dev/null \
        || git -C "$CAGE_WS" reset --hard "refs/remotes/host/${BRANCH}"
    fi
  else
    warn "could not create host/${BRANCH} on cage — skip git align"
  fi
  prepare_cage_writable
  log "to-cage git HEAD=$(git_short "$CAGE_WS")"
}

mirror_skills() {
  [[ -d "$CAGE_WS/bootstrap/grok-cli/skills" ]] || return 0
  mkdir -p "$CAGE_WS/.grok/skills"
  for d in "$CAGE_WS/bootstrap/grok-cli/skills"/*/; do
    [[ -d "$d" ]] || continue
    name=$(basename "$d")
    mkdir -p "$CAGE_WS/.grok/skills/$name"
    set +e
    rsync -r --delete --no-owner --no-group --no-perms --omit-dir-times \
      "$d" "$CAGE_WS/.grok/skills/$name/" 2>/dev/null
    set -e
  done
  log "project .grok/skills ← bootstrap first-party"
}

cmd_to_cage() {
  # Warn if cage commits would be orphaned
  if [[ -d "$CAGE_WS/.git" && "$FORCE" -ne 1 ]]; then
    git -C "$CATALOG_ROOT" fetch -q "$CAGE_WS" "+refs/heads/*:refs/remotes/${REMOTE_NAME}/*" 2>/dev/null || true
    cage_ref="refs/remotes/${REMOTE_NAME}/${BRANCH}"
    if git -C "$CATALOG_ROOT" rev-parse --verify "$cage_ref" >/dev/null 2>&1; then
      if ! git -C "$CATALOG_ROOT" merge-base --is-ancestor "$cage_ref" HEAD 2>/dev/null; then
        die "cage has commits not in host — run: $0 from-cage   (or --force to overwrite cage tip)"
      fi
    fi
  fi
  rsync_to_cage
  align_cage_git
  mirror_skills || warn "skills mirror had issues (non-fatal)"
  log "to-cage OK"
}

cmd_sync() {
  log "sync: from-cage → to-cage"
  cmd_from_cage
  cmd_to_cage
  if [[ "$DO_PUSH" -eq 1 ]]; then
    log "git push origin ${BRANCH}"
    if [[ "$DRY" -eq 1 ]]; then
      echo "dry-run: git -C $CATALOG_ROOT push origin $BRANCH"
    else
      git -C "$CATALOG_ROOT" push origin "$BRANCH"
    fi
  fi
  cmd_status
}

main() {
  need_host
  parse_args "$@"
  case "$CMD" in
    status) cmd_status ;;
    from-cage|import|pull) cmd_from_cage ;;
    to-cage|export|push-content) cmd_to_cage ;;
    sync|both) cmd_sync ;;
    *) die "usage: $0 status|from-cage|to-cage|sync [--push] [--force] [--dry-run]" ;;
  esac
}

main "$@"
