# Design: Cage Grok session resumption (repo-isolated)

**Status:** Implemented (T-0047) — sessions volume + host import + resume targets  
**Related:** T-0045 (launch path), ADR-0002 (Grok primary), ADR-0010 (not AgenC)  
**Upstream behavior:** Grok Build sessions under `$GROK_HOME/sessions/<url-encoded-cwd>/`

## Problem

Today:

- Cage mounts **only** `auth.json` into `/home/agent/.grok/`.
- Conversation sessions live under `/home/agent/.grok/sessions/` **inside the container filesystem** (ephemeral relative to host intent — lost or orphaned on image recreate / container wipe).
- Host Grok sessions live under `~/.grok/sessions/` keyed by **host** cwd (e.g. `$HOME/DEVELOP/…`), not cage cwd (`/workspace/pfy-mentat`).
- `make cage-workspace-sync` can refresh code, but **does not** preserve agent chat continuity.

Operators need: **resume the same agent thread after re-entering the cage**, with **isolation per repo** so work on project A does not bleed into project B.

## Goals

| # | Goal |
|---|------|
| G1 | Sessions **survive** `cage-down` / re-up / overlay rebuild (as long as host store is kept). |
| G2 | Isolation by **repo identity** (not by host username path alone). |
| G3 | Resume works **inside cage** via native Grok: `-c` / `--continue`, `-r` / `--resume`, `/resume`, `grok sessions list`. |
| G4 | Auth stays separate (OIDC `auth.json` import) — never bake tokens into session tarballs. |
| G5 | Works with multi-repo later: catalog + gom-jobbar + atg, etc. |

## Non-goals (v1)

- Syncing host-desktop TUI sessions into cage when host cwd ≠ cage cwd (different keys; optional import tool later).
- Cross-machine cloud session sync.
- Replacing Grok’s session format.
- AgenC session store.

## How Grok already keys sessions

From Grok user guide + live cage:

```text
$GROK_HOME/sessions/<url-encoded-absolute-cwd>/<session-uuid>/
  summary.json
  updates.jsonl          # resume source of truth
  chat_history.jsonl
  plan.json
  …
```

In cage today, cwd is `/workspace/pfy-mentat` → dir name `%2Fworkspace%2Fpfy-mentat`.

**Implication:** If we keep a **stable absolute workspace path per repo** inside the cage and **persist `$GROK_HOME/sessions` on the host**, resume is native — no custom session engine.

## Design

### 1. Host session store (canonical)

```text
~/.agentcage/grok-state/                 # GROK_STATE_ROOT (default)
  auth.json → optional symlink/copy of grok-home/auth.json  # keep existing grok-home
  sessions/                              # mounted → /home/agent/.grok/sessions
  memory/                                # optional later: cross-session memory
  repos/
    <repo-id>/
      meta.json                          # path, remote, last_sync
```

Keep **auth** in existing `~/.agentcage/grok-home/auth.json` (file mount).  
Add **sessions volume** (directory mount) for persistence.

### 2. Repo identity

| Field | Example |
|-------|---------|
| `repo_id` | `pfy-deanery` or slug of git remote + short hash |
| Stable cage path | `/workspace/repos/<repo_id>` **or** keep `/workspace/pfy-mentat` for catalog |
| Host mirror | `~/.agentcage/workspace/<repo_id>` (already used) |

v1 catalog: keep **`/workspace/pfy-mentat`** for zero breakage.  
v1.1 multi-repo: `/workspace/repos/<repo_id>` + register map in `repos/meta.json`.

### 3. Compose mount (Grok overlay)

Extend `docker-compose.override.yaml`:

```yaml
volumes:
  - ../grok-home/auth.json:/home/agent/.grok/auth.json
  - ../grok-state/sessions:/home/agent/.grok/sessions
  # optional: ../grok-state/memory:/home/agent/.grok/memory
```

Idempotent `make grok-overlay-install` creates `grok-state/sessions` with mode `700` and agent-readable ownership.

### 4. Make surface (idempotent)

| Target | Behavior |
|--------|----------|
| `grok-state-init` | mkdir sessions store; no-op if present |
| `workspace-sync` | unchanged; repo tree under stable path |
| `grok-run` / `grok-shell` | default cwd = `/workspace/<repo>` |
| `grok-resume` | `docker exec … grok --continue` (or `--resume <id>`) in that cwd |
| `grok-sessions` | `grok sessions list` in that cwd |
| `grok-ensure` | includes state-init + existing ready checks |

### 5. Resume UX

```bash
make cage-grok                 # ensure stack + sync
make cage-grok-sessions        # list for this repo
make cage-grok-resume          # grok -c  (most recent for cwd)
make cage-grok-resume ID=uuid  # grok -r uuid
make cage-grok-run             # new session (default)
```

Inside TUI: `/resume` still works once sessions are on the persisted mount.

### 6. Isolation rules

| Case | Behavior |
|------|----------|
| Repo A vs B | Different absolute cwd → different session group dirs → **isolated** |
| Same repo, two worktrees | Prefer **one stable cage path** per repo_id; optional worktree suffix in repo_id |
| Host vs cage | Host sessions under `~/.grok/sessions/%2Fhome%2F…` **do not auto-merge** with cage `%2Fworkspace%2F…` |
| Optional import | `grok sessions` / export-import only if operator explicitly maps host session into cage (out of v1) |

### 7. Security

- Session transcripts may contain secrets — store under `~/.agentcage/grok-state` with `0700`, never commit.
- Do not bind-mount entire host `~/.grok` (hides binary path; mixes host/cage skills).
- Auth file mount remains **file-only** for `auth.json`.

### 8. Implementation sketch (T-0047)

1. Create `overlays/grok/docker-compose.override.yaml` sessions volume + install mkdir.  
2. `grok-state-init` + chown agent-friendly.  
3. `grok-resume` / `grok-sessions` Make targets.  
4. Smoke: start session → down → up → `grok -c` sees prior summary.  
5. Doc: update grok overlay README + one-shot DoD.  
6. Optional: project file `.agentcage-repo.json` `{ "repo_id": "pfy-deanery", "cage_path": "/workspace/pfy-mentat" }`.

### 9. Acceptance (T-0047 DoD)

1. After `cage-down` + `cage-grok-up`, `ls ~/.agentcage/grok-state/sessions` still has data.  
2. In cage, `cd /workspace/pfy-mentat && grok sessions list` shows prior session.  
3. `make cage-grok-resume` continues it.  
4. Second repo path (if staged) does not list the first repo’s sessions.  
5. Auth import still works; no regression on `cage-grok-ready`.

### 10. Rejected alternatives

| Option | Why not |
|--------|---------|
| Mount full host `~/.grok` | Breaks binary layout; mixes host/cage config |
| Custom session DB | Reimplements Grok; high cost |
| Store sessions only in git workspace | Pollutes repo; risk of committing transcripts |
| Path-rewrite import of host sessions | Fragile; different cwd keys; defer |

## Session brief (this design session) for cage import

See: a private ops note

## References

- Grok Build: `~/.grok/docs/user-guide/17-sessions.md`  
- Live cage path: `/home/agent/.grok/sessions/%2Fworkspace%2Fpfy-mentat/`  
- Launch: `make cage-grok` / `cage-grok-run` / `cage-grok-shell`
