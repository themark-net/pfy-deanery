# Lane cage

**Status:** Operator note for the rootless lane runner.  
**Code:** `scripts/lane_cage.py`, `scripts/lane_git_env.sh`, `scripts/build_lane.sh`, `scripts/eval_lane.sh`, `scripts/integrate_lane.sh`, `scripts/loop_worktree.sh`  
**Architecture:** [ARCHITECTURE.md](../ARCHITECTURE.md). This runner lives under `scripts/`. The lab program in `harness/agent-cage/` is a different component. This note does not move that boundary.

## Operator

### What it does

`scripts/lane_cage.py` runs one lane agent under rootless podman and, when the agent exits 0, copies verified git objects back onto the shared repository.

The container uses `--userns=keep-id`. Processes run as the invoking operator's uid and gid, mapped into a user namespace. All capabilities are dropped, `no-new-privileges` is set, and there is no network except the egress proxy socket. `HOME` inside the container is a throwaway directory created for that run. The process is not root on the host. It has no access to the operator's real home directory, ssh directory, or global gitconfig.

`keep-id` keeps ownership of the bind-mounted worktree correct without granting root on the host.

Git commit identity inside the cage comes only from repo-local `user.name` and `user.email`. The host git helper reads those keys and ignores global and system config. When a key is unset, the fallback is `Deanery lane` / `lane@localhost`. A lane commit therefore carries only an identity the repository opted into.

### How to run

Build lane (one worktree, one prompt):

```bash
scripts/build_lane.sh --wt WORKTREE --prompt FILE [--log FILE]
```

Catalog eval and integrate lanes take a slug. Pass `--root` when the checkout under test is not the one that contains the driver.

```bash
scripts/eval_lane.sh --slug SLUG [--root DIR] [--state DIR] [--date MMDD]
scripts/integrate_lane.sh --slug SLUG [--root DIR] [--date MMDD]
```

Loop worktree (fetch and a detached worktree, then the command):

```bash
scripts/loop_worktree.sh [--wt DIR] -- command
```

Print the podman argv and run nothing:

```bash
python3 scripts/lane_cage.py grok --print --kind build --wt WORKTREE --prompt FILE
python3 scripts/lane_cage.py exec --print --wt WORKTREE -- true
```

### Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| `lane-cage: copy-back refused:` and exit 2 | Private git objects failed verification, or host git could not be executed | Shared refs and objects are left as they were. Fix the worktree or install git on the fixed safe path, then rerun. |
| `build_lane.sh` exits 6 | The cage reported a copy-back refusal | Read the log. Do not push. |
| eval or integrate parks `copy-back refused` | Same refusal, classified inside the driver | The park file holds that reason. The process exit stays the driver's park exit. |
| `lane cage unavailable` (driver result 5) | Podman or the lane image is missing | Install the runtime and image. This is not a copy-back refusal. |
| `refusing: ... is not a git worktree` (build exit 2) | The path is not a worktree | Pass a real worktree. A caller `GIT_DIR` does not count. |

A missing git binary is a copy-back refusal. The runner exits 2 with the refusal line. It does not print a traceback.

### Git environment

Host, pack, and query git inside `lane_cage.py` use one absolute binary. It is resolved once with `shutil.which("git", path=_SAFE_GIT_PATH)`. There is no environment override for that path. The process environment is an allowlist: that path, `LANG=C`, `LC_ALL=C`, an empty `HOME`, `GIT_CONFIG_NOSYSTEM=1`, and `GIT_CONFIG_GLOBAL=/dev/null`. Caller `HOME`, `PATH`, and `GIT_*` values are not passed through.

Lane drivers source `scripts/lane_git_env.sh`.

- `lane_git` is for local reads: `rev-parse`, `status --porcelain`, `diff --name-only`, `hash-object`, `show`, `merge-base`, `symbolic-ref`. It runs the absolute git from the same fixed path under `env -i` with only `PATH`, `LANG=C`, `LC_ALL=C`, a throwaway `HOME`, `GIT_CONFIG_NOSYSTEM=1`, and `GIT_CONFIG_GLOBAL=/dev/null`.
- `lane_git_scrub_env` runs once near the top of each lane driver. It unsets repository-redirect and config-injection variables so later operator-identity commands cannot be redirected.
- `commit`, `fetch`, `push`, `rebase`, and `worktree add` stay on plain `git` after that scrub. `HOME` and the operator's ssh transport settings stay on purpose, because those commands need the operator identity and credentials.
- Where a read used to go through `run_checked`, the driver uses `lane_git_checked`. The guard still classifies the command as `git`, then `lane_git` runs it.

### Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `_SAFE_GIT_PATH` | `scripts/lane_cage.py` | Fixed search path for the host git binary. Not an environment variable. |
| `LANE_GIT_SAFE_PATH` | `scripts/lane_git_env.sh` | Same path for driver reads. Not an environment variable. |
| `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR`, `GIT_NAMESPACE`, `GIT_CEILING_DIRECTORIES`, `GIT_DISCOVERY_ACROSS_FILESYSTEM` | caller env, unset by `lane_git_scrub_env` | Would point git at a different repository or object store. |
| `GIT_CONFIG`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*`, `GIT_CONFIG_VALUE_*`, `GIT_CONFIG_SYSTEM`, `GIT_TEMPLATE_DIR`, `GIT_EXEC_PATH`, `GIT_TRACE*`, `GIT_REPLACE_REF_BASE`, `GIT_ATTR_SOURCE`, `GIT_EXTERNAL_DIFF`, `GIT_PAGER`, `GIT_EDITOR` | caller env, unset by `lane_git_scrub_env` | Would inject config, trace output, or a helper program. |
| `HOME`, ssh transport variables | caller env, kept for plain `git` | Operator identity for commit, fetch, push, rebase, and worktree add. |
| `PFY_PODMAN`, `PFY_LANE_IMAGE` | environment | Container runtime and image. |
| `PFY_CAGE_PACK_MAX_BYTES`, `PFY_CAGE_LOOSE_MAX_BYTES`, `PFY_CAGE_LOOSE_MAX_INFLATE`, `PFY_CAGE_PACK_GIT_TIMEOUT_SECS` | environment, clamped in `lane_cage.py` | Copy-back size and pack-git time limits. |

## Agent

### Entry points

- `scripts/lane_cage.py` `main`: `grok` and `exec`, plus `--print`
- `prepare_git_store`, `finalize_git_store`: private store and copy-back
- `_git_bin`: absolute git from `_SAFE_GIT_PATH` (cache key is that path)
- `base_run`: podman argv, including keep-id and repo-local identity
- `lane_git`, `lane_git_scrub_env`, `lane_git_checked` in `scripts/lane_git_env.sh`

### Data shapes

- Copy-back refusal is one stderr line: `lane-cage: copy-back refused: ...` and process exit 2.
- `build_lane.sh` maps that line to exit 6. Eval and integrate map it to an internal result 6 and then park the text `copy-back refused`.
- Any other `lane-cage:` line with exit 2 is "lane cage unavailable" (driver result 5).

### Callers / callees

- `build_lane.sh`, `eval_lane.sh`, and `integrate_lane.sh` call `lane_cage.py`.
- `loop_worktree.sh` does not call the cage. It uses `lane_git` for the worktree ownership checks and plain `git` for fetch, worktree add, reset, and clean.
- Host git helpers call the absolute git binary. They do not call the operator's `git` from `PATH`.

### Invariants

- A git helper that cannot execute git raises `GitStoreError`. The shared store and refs stay unchanged.
- Host, pack, and query git argv starts with the absolute binary. The child environment is the allowlist above.
- The post-flush inflate length check in `_verify_loose_file` stays in place.
- Driver worktree reads do not inherit the caller git environment. Operator-identity git commands run only after `lane_git_scrub_env`.
- Repo-local identity, with the Deanery lane fallback when unset. No global gitconfig.

### Extension points

- New lane drivers that read the worktree source `lane_git_env.sh`, call `lane_git_scrub_env`, and use `lane_git` for reads.
- New host git calls in `lane_cage.py` go through `_git_bin` and the allowlisted environment.

### Do not

- Do not invoke host git by the bare name `git` or with the caller environment.
- Do not add an environment override for the git binary path.
- Do not pass the operator's real `HOME` or ssh directory into the container.
- Do not take commit identity from global or system gitconfig.
- Do not weaken the loose-object inflate check.
- Do not treat `harness/agent-cage/` as this runner.
