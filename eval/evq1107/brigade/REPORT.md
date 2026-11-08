# Brigade evq1107

STAY I0. Eight workers claimed 94 tasks with 0 duplicate ids. Exclusive marker files did the same in 0.004s. Brigade's claim burst took 4.9699s, after 29.6643s to add the tasks. Nothing was wired into a gate.

## Pins

| Item | Value |
| --- | --- |
| Package | `brigade-cli==0.27.0` |
| Wheel sha256 | `ac63094d379459338adde3be6dc49d54d928d5a06663342dec71eee975fed8c1` |
| Tag object `v0.27.0` | `7b57fc909611f3bf8caaf10f5d6c11c7afbd65dd` (annotated) |
| Commit the tag peels to | `2e008c24e6636a7db9b64059b7576f4523492abe` |
| Commit date | 2026-09-06, `chore: release v0.27.0 (#1484)` |
| Python | 3.14.4 |
| Install | `~/.cache/pfy/tools/brigade/` (venv 32 MB, wheel 3.3 MB, shallow source 337 KB) |

The wheel hash matches `sources/entries/110-brigade.md`. The annotated tag object is not the commit. `git rev-parse v0.27.0^{}` on a depth-1 clone of that tag is the commit above. `main` on the 0.28 beta line was not installed.

`brigade --version` printed `brigade 0.27.0`. No `brigade setup`, no harness wiring, no fleet, no account, no key.

## Catalog overlap

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167. Brigade is entry 110, so it is not in that table. That section says no entry in 137 to 167 closes gap B (`./pfy build` still hits the timeout). The 2026-10-06 section names kanbots for kanban fan-out into worktrees, beside our loops.

Stage cards whose uses, features, or tags are about the same job (two runs, one piece of work):

| Tool | Stage | What it already covers |
| --- | --- | --- |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees. |
| gitai | I0 | CAS lands for many agents on one branch. |
| Emdash | I0 | Parallel agents, one worktree each. |
| Kanzo | I0 | Local kanban plus MCP. AGPL. Potential low. |
| Multica | I1 | Multi-agent board. Not our orchestrator. |
| Atomic Task Graph (ATG) | I2 | Parallel tool waves inside one DAG. |
| LangGraph (LangChain) | I1 | Graph orchestration. Our loops already cover that path. |
| Auto-Company | I1 | Consensus baton. Not a task claim, and not a runtime to adopt. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards. Already the orchestration toolset. |

A word scan also hit Bumblebee (package lockfiles), destructive_command_guard (shell blocks), Elephant-Goldfish (spec review), HiRoute (routing), SkillSpector, and Hermes Teammates. Those are other jobs.

First-party, not a catalog card: one worktree and branch per slug, scheduler markers (`.pid`, `.dispatched`, `.done`, `.parked`), `scripts/model_lock.sh`, and a fast-forward land that fails if main moved. That is the live answer to "what stops two runs doing the same work."

Brigade does not beat that set. It ties the marker primitive on exclusivity and loses on time. It does not close the `./pfy build` timeout.

## Commands

Install, with `HOME` still the real home. The venv and the wheel stay under the cache path.

```bash
CACHE="$HOME/.cache/pfy/tools/brigade"
mkdir -p "$CACHE/home" "$CACHE/tmp" "$CACHE/wheels"
python3 -m venv "$CACHE/venv"
"$CACHE/venv/bin/pip" download 'brigade-cli==0.27.0' -d "$CACHE/wheels" --no-deps
sha256sum "$CACHE/wheels/brigade_cli-0.27.0-py3-none-any.whl"
"$CACHE/venv/bin/pip" install --no-index --find-links "$CACHE/wheels" 'brigade-cli==0.27.0'
```

Tag peel, also under the cache path:

```bash
git clone --filter=blob:none --no-checkout --branch v0.27.0 --depth 1 \
  https://github.com/escoffier-labs/brigade.git "$CACHE/src/brigade"
git -C "$CACHE/src/brigade" rev-parse 'v0.27.0^{}'
```

Probe. `HOME` and the XDG dirs point at the cache home. The ledger repo is a throwaway git dir under `$CACHE/tmp`, not this worktree. `BRIGADE_NO_UPDATE_CHECK=1`.

```bash
export PFY_REAL_HOME="$HOME"
export BRIGADE_CACHE="$PFY_REAL_HOME/.cache/pfy/tools/brigade"
export BRIGADE_BIN="$BRIGADE_CACHE/venv/bin/brigade"
export HOME="$BRIGADE_CACHE/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
export TMPDIR="$BRIGADE_CACHE/tmp"
export BRIGADE_NO_UPDATE_CHECK=1
python3 eval/evq1107/brigade/probe.py
```

The probe reads every `data/stages/*.json` stem except `_registry` and adds one task per stem. This run saw 94 stems, including `brigade`. That is the worktree at probe start (2026-11-07 18:52 PT), after rebasing onto the cedr card. A stage file that lands after that is not in the 94.

## Numbers

Throwaway: `/home/mark/.cache/pfy/tools/brigade/tmp/probe-20261108T025244Z/repo` (2026-11-07 18:52 PT). `init` exit 0. Add errors 0. Ready count before the burst: 94. Product worktree `.brigade` was absent before and after. These real-home paths contained 0 files before and after: `~/.brigade`, `~/.config/brigade`, `~/.cache/brigade`, `~/.local/share/brigade`, `~/.local/state/brigade`. No `update-notify` file appeared under the cache home.

| Method | Claim rows | Unique ids | Duplicate ids | Extra claims | Wall |
| --- | ---: | ---: | ---: | ---: | ---: |
| `brigade work claim --next` | 94 | 94 | 0 | 0 | 4.9699s |
| `O_EXCL` marker file per slug | 94 | 94 | 0 | 0 | 0.004s |
| Unlocked JSON pop, 8 writers | 752 | 94 | 94 | 658 | 4.7401s |

Adding the 94 tasks took 29.6643s. That cost sits in front of the claim burst.

Brigade details: 0 error rows, 8 `no_ready` rows (one per worker after the ready set was empty), ledger status `in_progress` 94. In actor order `c0` to `c7` the counts are 12, 12, 12, 12, 12, 12, 11, 11. The sum is 94.

The unlocked control is not a catalog tool. Eight processes pop the head of one JSON list, sleep 0.05s, and write the tail back, for a 5.0s window. Every id was taken more than once. That shows the probe counts a real race. The marker control is `open` with `O_CREAT|O_EXCL`, the safe form of "create a marker or lose." All three methods use the same 8-process start barrier.

Receipts were not re-run on nimo. The entry already records the sequential receipt smoke from the Grok Bot box. This lane's number is the concurrent claim.

## Gates

Value gate (3 of 4 needed for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. Markers, per-slug worktrees, the model lock, and fast-forward land already stop two runs. Brigade ties markers at 0 duplicate ids and is slower. |
| Operator leverage | No. The claim CLI does not make `./pfy build` finish. Loading 94 tasks took 29.6643s. |
| Evidence | Yes. This probe runs offline with no key. |
| Blast radius | Yes, while it stays a cache venv and a throwaway target. MIT, no weights, wheel 3.3 MB, venv 32 MB. `init` writes `.brigade/` into whatever directory it is pointed at. |

Score: 2 of 4. Not I3.

Modularity gate (all 4 needed to keep a local copy as I2):

| Check | Result |
| --- | --- |
| Local code needed | Yes. A sequential second actor cannot show an 8-way burst. |
| Bounded surface | Yes for this slice. One wheel, CLI `brigade work claim`. No native components, no `setup`. |
| Isolatable | Yes. Venv and `HOME` under `~/.cache/pfy/tools/brigade/`. |
| Reversible | Yes. Delete that cache dir. The entry pin remains. This lane did not edit the product tree. |

Modularity passes for the claim slice. The size gate also passes (under 50 MB, no weights). The value comparison does not. I2 is for a probe that still helps. This one ties a faster primitive we already have.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Phone-home | A shell without `BRIGADE_NO_UPDATE_CHECK` writes an update-check cache. | Set the variable. This run found no `update-notify` file. |
| Repo takeover | `brigade init` writes `.brigade/` and can edit `.gitignore` in the target. | Throwaway repo only. `--harnesses none --no-wire`. This worktree had no `.brigade` after the run. |
| Dropped duplicate | The probe reports 0 because it forgot a repeated task id. | `tests/test_brigade_claim_probe.py` feeds a stub that awards one id to all 8 workers. The test fails if `duplicate_ids` is forced to 0. |
| Claim error swallowed | A lock error is counted as a win, or the probe dies with no summary. | The same test uses a stub that exits 1 with `ledger busy`. The summary records 8 error rows and 0 wins. |
| Tag drift | `v0.27.0` is an annotated tag. A moved tag would change the commit. | Pin the wheel sha256. Re-check `v0.27.0^{}` before any later install. |

## Next gate

Stay I0. Do not wire Brigade into pregate, CI, or `./pfy`. A later ticket has to name a collision that exclusive markers, per-slug worktrees, and the model lock do not already stop, and gate wiring needs its own grill.

## Five questions (Brigade in this pipeline)

1. What triggers it? An operator command: `brigade work claim` or `brigade work verify run`. Nothing starts by itself. This lane did not run a daemon.
2. What does it do, and which services does it read and write? It reads and writes `.brigade/` in the target repo (the task ledger). With `BRIGADE_NO_UPDATE_CHECK=1` the probe did not run `update`, `setup`, or fleet, and no `update-notify` file appeared. No hosted model and no account.
3. What does it trigger next? Nothing. The next step is another explicit command. It does not enqueue `./pfy build`.
4. Where does a human re-enter? A lock timeout, a receipt mismatch, a product-checkout `init`, or any proposal to wire a gate. Gate wiring is a separate ticket.
5. What stops two runs doing the same work? The task-ledger lock around claim. Measured here: 0 duplicate task ids out of 94, 8 workers, 4.9699s. The same stop is already an exclusive marker per slug: 0 duplicate ids in 0.004s, plus one worktree per slug and `scripts/model_lock.sh` for live model steps.
