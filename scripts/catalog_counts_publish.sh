#!/bin/bash
# Regenerate catalog counts in the loop worktree and fast-forward main.
# loop_worktree.sh is the caller. This script refuses to run in PFY_LOOP_REPO.
# PFY_LOOP_NO_PUSH=1 prints the result and does not commit.
# Allowed commits touch only:
#   data/stages/_registry.json
#   pipelines/catalog/dashboard.latest.md
#   pipelines/catalog/counts.latest.json
set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export GIT_AUTHOR_NAME=catalog-loop
export GIT_AUTHOR_EMAIL=catalog-loop@localhost
export GIT_COMMITTER_NAME=catalog-loop
export GIT_COMMITTER_EMAIL=catalog-loop@localhost

cd "$(dirname "$0")/.."

repo="${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}"
if [[ -d "$repo" ]]; then
  top=$(git rev-parse --show-toplevel 2>/dev/null || true)
  if [[ -n "$top" && "$(realpath -m "$top")" == "$(realpath -m "$repo")" ]]; then
    echo "refusing: catalog counts publish will not run in the repo top-level: $repo" >&2
    exit 2
  fi
fi

python3 scripts/catalog_counts.py

allowed=" data/stages/_registry.json pipelines/catalog/dashboard.latest.md pipelines/catalog/counts.latest.json "
paths=()
bad=0
while IFS= read -r line; do
  [[ -n "$line" ]] || continue
  [[ ${#line} -ge 4 ]] || continue
  path=${line:3}
  if [[ "$path" == *" -> "* ]]; then
    path=${path##* -> }
  fi
  paths+=("$path")
  if [[ "$allowed" != *" $path "* ]]; then
    bad=1
  fi
done < <(git status --porcelain)

if [[ ${#paths[@]} -eq 0 ]]; then
  echo unchanged
  exit 0
fi

if [[ "$bad" -eq 1 ]]; then
  printf '%s\n' "${paths[@]}"
  echo "refusing to commit: a path is outside the three counts outputs" >&2
  exit 3
fi

if [[ "${PFY_LOOP_NO_PUSH:-}" == "1" ]]; then
  printf '%s\n' "${paths[@]}"
  exit 0
fi

git add -- \
  data/stages/_registry.json \
  pipelines/catalog/dashboard.latest.md \
  pipelines/catalog/counts.latest.json
git commit -m "catalog: regenerate counts"

attempt=1
while [[ "$attempt" -le 3 ]]; do
  git fetch -q origin
  if ! git merge-base --is-ancestor origin/main HEAD; then
    if ! git rebase --onto origin/main HEAD~1; then
      git rebase --abort || true
      echo "rebase of the counts commit failed" >&2
      exit 1
    fi
  fi
  if git push origin HEAD:refs/heads/main; then
    exit 0
  fi
  attempt=$((attempt + 1))
done

echo "counts push did not fast-forward after 3 attempts" >&2
exit 1
