# gitai evq1107

STAY I1. Eight agents each added one new file on one branch. gitai landed 8/8 in 117.9 ms, 1 attempt each, in two batches (6 and 2). Plain git landed 1/8 on the first push, then the other 7 over 8 rounds, 36 pushes, 436.0 ms. A same-line edit landed 1 and conflicted 1 on both sides. The 3 hour `./pfy build` timeout is unchanged. Nothing was wired.

## Catalog tools on this job

Searched `data/stages/*.json` uses, features, and tags, plus the 2026-11-07 section of `docs/eval/TOOLSET-RANKING.md`. Batch-1 notes are under `eval/ev1107/` and `eval/catchup-1107/`. The job is many short agent changes landing on one branch.

| Tool | Stage | What it covers | How gitai compares |
| --- | --- | --- | --- |
| Foremerge | I1 | Pre-edit intent ledger. Same-path modify blocked 0/6. | Acts before a write. gitai acts at land time. |
| kanbots | I1 | Kanban that fans CLIs into worktrees. Probe did not move the 3 hour timeout. | Isolation by worktree. No land protocol. |
| Emdash | I0 | Parallel agents GUI, one worktree each. | Same shape, no land server. |
| HAR | I0 | Per-slot worktree plus a verify receipt. Slower than a worktree plus catalog_check. | A receipt, not a compare-and-swap land. |
| Brigade | I0 | Exclusive claim on a task id. 0 duplicate claims, slower than a marker file. | Stops two actors taking one task. Does not land commits. |
| Kander | I1 | Branch overlap check. Tied a git intersection and was slower. | Read-only overlap. No land. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | Allows or denies one write. |
| Atomic Task Graph | I2 | Compile, parallel tool waves, freeze, localized repair. | A scheduler lock. Not a git server. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build. The probe missed the fast-forward parks. | Adjacent to gap B. It does not land. |
| Aider | I1 | Git-native terminal editor. Overlaps OpenCode and Grok. | One editor. Not a multi-agent land server. |
| Festival | I1 | Plan and checklist gates. The probe did not close the 3 hour timeout. | A checklist. Not a land. |

The 2026-11-07 ranking holds entry 144 for a post-MVP scratch trial and says no entry in 137 to 167 closes gap B. This probe agrees on the timeout. On the disjoint fast-forward race the card names, gitai lands the whole wave with 1 attempt each. Plain git needs one round per winner.

What we already do: one worktree and one stage card per lane, then a fast-forward push that fails when main has moved, then a rebase. Disjoint card files are the common case. Shared files (Makefile, AGENTS.md, and the rest of the lane deny list) are the conflict case. This probe used a throwaway repo with that shape. It did not push this worktree.

gitai beats plain git on the disjoint race (8 lands, 8 attempts, 117.9 ms, against 36 pushes and 436.0 ms). It ties plain git on a same-line edit (1 land, 1 conflict). The saved time on 8 files is under a second. That does not move a parked lane. The install is a Gitaly fork, so the modularity gate fails and the stage stays I1.

## Pins

Entry records tag `v0.3.1`. The annotated tag object is `173a281aa5594d2c347c9bdb2178f699b5a66a47`. The commit is `914e481ef057ca7b9dc9a5a7338d96bca16790e1` (2026-10-23 00:22:21 +0200, subject `docs: README for 0.3.1`). `git rev-parse v0.3.1^{}` matches that commit. No upstream checksum was published for the tree. The release has no binary assets.

Go is the `.tool-versions` pin at that tag: `golang 1.26.8`. The tarball sha256 is `d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b` (`sha256sum -c` matched). Meson 1.7.0 and Ninja 1.12.1 are the same file's build pins. `gitaly --version` printed `Gitaly, version 0.3.1` with `go1.26.8`.

Source tree at the pin, excluding `.git` and `_build`, is 31 MB (3073 files, `find -type f`). Under the 50 MB copy limit. The build tree is 1.7 GB (`du -sh _build`) and stays in `~/.cache/pfy/tools/gitai/`. Nothing from the install is committed.

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` point under that cache. No model, no key, no account. Token files are created inside the probe work dir and deleted with it. `results.json` has no token (no 64-hex string).

## Commands

```bash
BASE=$HOME/.cache/pfy/tools/gitai
mkdir -p "$BASE"/{home,config,cache,tmp,dl,src,pkg,venv}
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache"
export npm_config_cache="$BASE/cache/npm" TMPDIR="$BASE/tmp" GITAI_CACHE="$BASE"
curl -fsSL -o "$BASE/dl/go1.26.8.linux-amd64.tar.gz" https://go.dev/dl/go1.26.8.linux-amd64.tar.gz
echo 'd0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b  go1.26.8.linux-amd64.tar.gz' | (cd "$BASE/dl" && sha256sum -c)
tar -C "$BASE/pkg" -xzf "$BASE/dl/go1.26.8.linux-amd64.tar.gz"
curl -fsSL -o "$BASE/dl/ninja-linux.zip" https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-linux.zip
unzip -o "$BASE/dl/ninja-linux.zip" -d "$BASE/pkg"
python3 -m venv "$BASE/venv" && "$BASE/venv/bin/pip" install 'meson==1.7.0'
git clone --branch v0.3.1 --depth 1 https://github.com/feder-cr/git-ai.git "$BASE/src/git-ai"
# pkg-config, libpcre2-dev, and libcurl4-openssl-dev are extracted under $BASE/pkg/root.
# Headers need $BASE/pkg/pc and a curl include symlink. Attempt 3 is the link line below.
export PATH="$BASE/pkg/go/bin:$BASE/venv/bin:$BASE/pkg:$BASE/pkg/root/usr/bin:$PATH"
export LD_LIBRARY_PATH="$BASE/pkg/root/usr/lib/x86_64-linux-gnu"
export PKG_CONFIG_PATH="$BASE/pkg/pc:/usr/lib/x86_64-linux-gnu/pkgconfig"
export C_INCLUDE_PATH="$BASE/pkg/root/usr/include"
export GOTOOLCHAIN=local CGO_ENABLED=1
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
rm -f "$BASE/pkg/root/usr/lib/x86_64-linux-gnu/libcurl.a"
ln -sfn /usr/lib/x86_64-linux-gnu/libcurl.so.4 "$BASE/pkg/root/usr/lib/x86_64-linux-gnu/libcurl.so"
make -C "$BASE/src/git-ai" -j8 build
export GITAI_CACHE="$BASE"
python3 eval/evq1107/gitai/probe.py
```

Attempt 1 stopped in the bundled Git compile: `curl/curl.h` was under the multiarch include dir, and the compiler `-I` was the parent include dir. A symlink fixed the header. Attempt 2 stopped at link: `libcurl.a` referenced `ZSTD_createDStream` and the link line had no libzstd. Attempt 3 deleted that archive, pointed `libcurl.so` at the system shared library, and `make -j8 build` exited 0.

The probe writes a throwaway bare repo, seeds it with the text of `data/stages/gitai.json`, and races the lands there. The same-line seed sets `integration_stage` back to I0 so both writers change that one line. The recorded run read the card while it was still I0, which is the same seed. It listens on a Unix socket under the cache tmp. It does not bind TCP and it does not start graft-cache. The plain-git timer covers the push rounds. The gitai timer covers `graft commit --land` after the clones exist. Both sides prepare the workspaces before the timer.

## Numbers

Recorded run of `probe.py`. Rows are in `results.json`.

| Case | Plain git | gitai |
| --- | --- | --- |
| 8 disjoint new files | first push 1/8, 8 rounds, 36 pushes, 8 landed, 0 conflicts, 436.0 ms, 9 files on the tip | 8/8 landed, 0 conflicts, 0 errors, 8 attempts, 8 batched, 117.9 ms, 9 files on the tip |
| 2 edits of the same line | 1 landed, 1 conflict, 2 pushes, 23.7 ms | 1 landed, 1 merge conflict, 62.9 ms |

The eight gitai notes are one attempt each. Six share a batch and the other two share a second batch. A loser push on the plain side was rejected with `incorrect old value provided`. That is this git's refusal of a push that is not a fast-forward. The installed git has no `git push --ff-only` flag. A normal push already refuses that update.

## Gates

Value gate (3 of 4 needed for I3, not claimed):

1. Gap fill: Fail. No other card lands a compare-and-swap wave, and this run did (8 attempts against 36 pushes). The hole named for this lane is the 3 hour `./pfy build` timeout. This run does not change that timeout. A same-line edit still conflicts.
2. Operator leverage: Fail. The gain on 8 files is 318 ms. Putting a Gitaly fork under every lane is not a day's glue on `./pfy build`.
3. Evidence: Pass. This probe, with the pins and the command above.
4. Blast radius: Pass. MIT, no key, source 31 MB, cache delete removes the install. The build tree is 1.7 GB and the server binary is 378 MB (file size). It is not a weight download. It is not the product runtime.

Score 2 of 4.

Modularity gate (all 4 required for I2):

1. Local code needed: yes. The batch split (6 and 2) and the same-line conflict showed up only in the run.
2. Bounded surface: no. The unit is a Gitaly fork, 3073 files, and a bundled Git built three times.
3. Isolatable: yes. Cache home, Unix socket, throwaway repos.
4. Reversible: yes. Delete `~/.cache/pfy/tools/gitai`. The entry and this report remain.

Not all 4, so the stage is not I2. `uses` and `features` do not name a CI, testing, or review role, so `self_pipeline` is not set. No `TOOLS.md` row and no `data/tools.json` row. I3 would need both a repeatable product script and `self_pipeline` evidence. This lane builds neither.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Bundled Git build | The compile misses a header or links `libcurl.a` without zstd | Keep the shared libcurl symlink in the cache. Do not commit the build. |
| Batch window | Two batches on 8 lands, so a wave is not one compare-and-swap | Read the land notes. Do not assume one batch. |
| Same-line edit | The second land returns `merge conflict` and the tip keeps one side | Keep the lane deny list for shared files. No resolver in this probe. |
| Fast-forward park | Plain git still needs a rebase after `incorrect old value provided` | Leave the current land path in place. |
| Heavy server | A 378 MB `gitaly` plus three bundled Gits | Cache only. The product git stays the system git. |
| Token files | `openssl rand` writes agent tokens next to the socket | The probe deletes the work dir. The report stores no token. |
| Young fork | v0.3.1 behavior moves (upstream README now says 0.4.2) | Stay on the entry pin. |

## Next gate

Stay I1. Do not wire a gate. Re-open only if a later pin lands a same-line conflict with the project's own checks and no hosted model, and the land wave is still one attempt on a throwaway copy of this repo. That ticket grills wiring first. Not a Feature GO.

## Pipeline questions

How gitai would run if a later ticket adopted it. This lane did not add that path.

1. What triggers it? A lane finishes and calls `graft commit --land` on the branch the scheduler is landing. Not a pfy scheduler event today.
2. What does it do, and which services does it read and write? A local `gitaly serve` on a Unix socket reads the bare repo and writes the landed tip plus a changeset log. No hosted model and no account. The server does not call a model.
3. What does it trigger next? The tip moves, or the agent gets a merge conflict and stops. The driver would still run the quick sanity check on the landed tree.
4. Where does a human re-enter? A same-line conflict, a policy denial, or a pin that no longer builds. Mark still owns `tmp/evq/STOP` and a PROMOTE that needs gate wiring.
5. What stops two runs doing the same work? The compare-and-swap on the branch, plus the one-worktree-per-slug rule we already have. Two servers on one repo are out of scope. This lane ran one server in the cache tmp.
