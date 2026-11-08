# Kander evq1107

Verdict: STAY I1. Pinned kander 0.9.5 ran offline under a redirected HOME. On four throwaway branch pairs built from files in this repo, `check overlap` matched a rename-aware git path intersection 4/4 (0.1104s vs 0.0142s). On merge `0bbfecf7` in this repo it matched 2/2 paths (0.1618s vs 0.0126s). A destination-only intersection missed the rename pair (3/4). Five premature `move done` attempts were blocked 5/5. Close failed twice when PMQA was required and no reviewer had run. Both roles set to N/A reached done. Each aggregate view listed 0 runs, and the probe did not call `start`. Worktrees stayed at 1. The 3 hour `./pfy build` timeout and the two pregate FAILs were not changed. Nothing was wired into a gate.

## Catalog comparison

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167. Kander is entry 117, so it is not in that table. That section says no entry in 137 to 167 closes gap B (`./pfy build` still hits the timeout). The 2026-10-06 section names kanbots for kanban fan-out into worktrees, beside `/agent-loops`.

A scan of `data/stages/*.json` uses, features, and tags for the words worktree, kanban, review, reviewer, parallel, and orchestrat hit 18 cards. The same job is parallel work plus an independent review before done.

| Card | Stage | What it already covers | How kander compares |
| --- | --- | --- | --- |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees. | Same board job. This probe created 0 extra worktrees and started 0 agents. |
| Emdash | I0 | Parallel agents, one worktree each. | Kander's start path was not run. Overlap is a report, not a worktree. |
| HAR | I0 | Per-slot git worktree plus a verify receipt. | Same. The slot receipt is already the smaller primitive. |
| Foremerge | I1 | Pre-edit intent ledger for parallel agents on one machine. | Kander reports paths after both sides have commits. It does not reserve a file. |
| Kanzo | I0 | Local kanban plus MCP. | Same queue job, not run here. |
| Hermes Teammates | I0 | Fixed tester/reviewer roster inside Hermes. | Kander names PMQA and Security, and both can be set to N/A. |
| Pi-Harness | I0 | Desktop control plane. Features include a task dag and worktrees. | Reference read only. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | Same. A board we would not adopt. |
| Atomic Task Graph (ATG) | I2 | Parallel tool waves inside one DAG. | Different job. Kander does not compile a DAG. |
| LangGraph (LangChain) | I1 | Graph orchestration. Our loops already cover that path. | Kander is a card directory plus git checks. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards, already the orchestration toolset. | Those exits already say when a lane stops. |
| mattpocock/skills | I1 | Planning and review skills already on the skill path. | Kander did not review a diff. |
| Chiasmus | I1 | Call-graph impact for per-file review. | Not this probe. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build starts. | Does not fix the timeout. Kander's N/A path is not a fresh reader. |
| OpenQodex | I1 | Scanner candidates on changed lines. Not the review gate. | Kander's overlap list is paths, not findings. |
| Tree-sitter Analyzer | I1 | Local change-impact map for a per-file review. | Not this probe. |
| imcodes | I0 | Reference for a supervised review loop. Not an install. | Not a binary we would run. |
| multi-agent-generator | I0 | Scaffolds CrewAI or LangGraph teams. | Not this job. |

The word scan missed three cards whose uses lines use other words. They are the same job:

| Card | Stage | What it already covers | How kander compares |
| --- | --- | --- | --- |
| Brigade | I0 | Exclusive claim so two actors do not take the same item. | This probe did not claim a task id. Overlap does not lock a card. |
| Festival | I1 | Filesystem plan, next step, and checklist gates. | Festival marked a testing file completed with 11 unchecked boxes. Kander blocked 5/5 premature dones, then accepted an explicit N/A for both roles. |
| odai | I0 | Evidence-before-done governance skill. | The N/A closure is a written waiver, not a second reader. |
| gitai | I0 | CAS lands for many agents on one branch. | Kander did not land a commit on a shared branch. |

First-party, not a catalog card: one worktree and branch per slug, scheduler markers (`.pid`, `.dispatched`, `.done`, `.parked`), Tester and Reviewer bots on the PR, `scripts/model_lock.sh`, and a fast-forward land that fails if main moved.

Kander does not beat that set. Overlap ties `git diff --name-status -M` and is slower. The done gate blocks an empty card, and it also lets both reviewer roles be waived with zero reviewer processes. It does not close the `./pfy build` timeout.

## Pins

| Item | Value |
| --- | --- |
| Release | v0.9.5, 2026-10-14 |
| Tag object | `0ab6f671747c2bfdb7ee69f190aaa4fa9bde3962` (annotated) |
| Commit the tag peels to | `590f1ced69af6e144bf78f43eee01fa050734b3c` |
| Asset | `kander-linux-amd64.tar.gz`, 7,962,607 bytes, sha256 `f8e08b0f3d07f00bf47f7c3416586d7d06a309fde6e2713a0880de5e464fc7e6` |
| Binary | `kander`, 21,880,106 bytes, sha256 `3a5f8979f94fc1325dbcf9aa30e73831d1db907302c13b5273362313c327e254` (matches `sources/entries/117-kander.md`) |
| `kander version` | `kander 0.9.5` |
| Install | `~/.cache/pfy/tools/kander/`. Binary 21,880,106 bytes plus the tarball 7,962,607 bytes. After doctor and the throwaway repos, `du -sb` on that directory is 30,636,523 bytes. `HOME`, `XDG_*`, and `TMPDIR` for every child point under that directory. |
| Doctor default | `kanban_agent` codex. PMQA and Security are codex for large and small. |
| tmux | absent at `/usr/bin/tmux`. Doctor also reported herdr absent. |

No `kander start`, `pick`, `orchestrate`, or reviewer-agent run. No `kander issue`. No account and no key. The probe's child `PATH` is `/usr/bin:/bin`.

## Commands

Download and pin, then one `doctor` so the rules and `config.json` land under the cache home:

```bash
CACHE="$HOME/.cache/pfy/tools/kander"
mkdir -p "$CACHE/home" "$CACHE/tmp" "$CACHE/bin"
curl -fsSL -o "$CACHE/kander-linux-amd64.tar.gz" -L \
  "https://github.com/dualface/kander/releases/download/v0.9.5/kander-linux-amd64.tar.gz"
tar -xzf "$CACHE/kander-linux-amd64.tar.gz" -C "$CACHE/bin"
sha256sum "$CACHE/bin/kander"
export HOME="$CACHE/home"
export XDG_CONFIG_HOME="$CACHE/xdg-config"
export XDG_CACHE_HOME="$CACHE/xdg-cache"
export XDG_DATA_HOME="$CACHE/home/.local/share"
export XDG_STATE_HOME="$CACHE/home/.local/state"
export TMPDIR="$CACHE/tmp"
"$CACHE/bin/kander" --lang en doctor
```

Probe. The script sets the child env itself. `PFY_REAL_HOME` is optional. It reads four files from this repo, builds a throwaway git dir under the cache tmp, and runs one read-only overlap on merge `0bbfecf753a3b4fb554590b6aadfa0ecb89efede` (parents `e5133c74` and `529be536`). It does not `init` this worktree.

```bash
python3 eval/evq1107/kander/probe.py
```

Numbers are in `results.json`. Fixture for the recorded run: `/home/mark/.cache/pfy/tools/kander/tmp/probe-20261108T032545Z/repo`.

## Numbers

Throwaway files copied from this repo: `sources/entries/117-kander.md`, `data/stages/brigade.json`, `data/stages/festival.json`, `data/stages/kanbots.json`. Branches `lane-entry`, `lane-card`, `lane-both`, and `lane-rename` diverge from `base`.

| Pair | Kander paths | Rename-aware git | Destination-only git | Kander | Git |
| --- | --- | --- | --- | ---: | ---: |
| disjoint | none | none | none | 0.0291s | 0.0034s |
| entry overlap | `sources/entries/117-kander.md` | same | same | 0.0266s | 0.0036s |
| card overlap | `data/stages/festival.json` | same | same | 0.0256s | 0.0034s |
| rename overlap | `sources/entries/117-kander.md` | same | none | 0.0291s | 0.0038s |
| this repo merge `0bbfecf7` | `.gitignore`, `examples/x-intake-local/smoke.py` | same | same | 0.1618s | 0.0126s |

Fixture total: kander 0.1104s, git 0.0142s. The git column times both the rename-aware diffs and the destination-only diffs, so a single intersection is a fraction of that and the gap is at least this wide. Agreement with the rename-aware intersection: 4/4, plus the merge. Agreement with a destination-only intersection: 3/4. Kander status was `pass` on the disjoint pair (exit 0) and `action-required` on the other four (exit 1). `action-required` does not lock either branch.

| Done attempt | Result |
| --- | --- |
| backlog to done | blocked, `Move not allowed: backlog -> done` |
| todo to done | blocked, `Move not allowed: todo -> done` |
| working, summary still `<FILL_IN>` | blocked, `Complete the summary before moving a small task to done` |
| working, summary filled, no plan | blocked, `review plan required for execution cycle` |
| plan with PMQA and Security required, batch not closed | blocked, `unclosed review batches` |
| close, both roles required, 0 runs | exit 2, `required successful role conclusion: PMQA` |
| close, PMQA required and Security `N/A`, 0 runs | exit 2, same PMQA error |
| close, both roles `N/A`, 0 runs | exit 0 |
| `move done --result completed` after that N/A close | exit 0, card in `done/` |

Aggregate `runs` length: 0 on every close. The probe did not call `start`, `pick`, `orchestrate`, or the reviewer-agent form of `kander review`. Git worktrees in the fixture: 1 before the board commands and 1 after. The `reviewer_processes` field in `results.json` records that choice. It is not a process listing. Product `kanban/` stayed absent. Product `.git/info/exclude` was unchanged. Real `~/.agents/kander` and `~/.config/kander` stayed absent. Gap B closed: 0.

Live agent start, pick, orchestrate, and the reviewer-agent form of `kander review`: SKIPPED. This lane is offline, `/usr/bin/tmux` is absent, and doctor defaulted the executor and both reviewers to codex.

## Gates

Value gate (3 of 4 needed for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. Git already computes the path intersection. Kanbots, worktrees, and the review bots already cover parallel cards and a second reader. The N/A path reaches done with 0 reviewers. |
| Operator leverage | No. Overlap does not make `./pfy build` finish. No worktree and no agent was started. |
| Evidence | Yes. This probe runs offline with no key. |
| Blast radius | Yes, while it stays a cache binary and a throwaway board. MIT, no weights, cache dir 30,636,523 bytes. `init` writes `kanban/` and a line in `.git/info/exclude` of whatever repo it is pointed at. |

Score: 2 of 4. Not I3.

Modularity gate (all 4 needed to keep a local copy as I2):

| Check | Result |
| --- | --- |
| Local code needed | Yes. The rule file `doctor` writes (`snippets/review-evidence-gate.md`) already describes the N/A sequence, and `check.md` says overlap is read-only. Neither gives the agreement count, the wall time, or the `action-required` status. Those needed a run. |
| Bounded surface | Yes for this slice. One static binary. Commands used: `check overlap`, `init`, `new`, `update`, `move`, `review plan`, `review aggregate`, `review close`. |
| Isolatable | Yes. Cache dir under `~/.cache/pfy/tools/kander/`. Not the product runtime. |
| Reversible | Yes. Delete the cache dir. The pin and the entry remain. |

Modularity passes, and the tree is under 50 MB. The ticket promotes to I2 only when the probe measurably helps. It does not. Potential is low, not ambiguous. Stay I1.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| N/A waiver | Both roles set to `N/A` reach done with 0 runs in the aggregate view | Do not treat a sealed N/A plan as a review pass. Keep the Tester and Reviewer bots. |
| Doctor default is codex | The first `doctor` sets the executor and both reviewers to codex, a hosted CLI | A later trial must set the agent explicitly and stay offline. This lane did not start one. |
| Writes on the real HOME | `doctor` rewrites `~/.agents/kander` and `~/.config/kander` | Set `HOME` and the XDG dirs under the cache. The probe checked the real paths stayed absent. |
| `init` writes the repo | `kanban/` plus a line in `.git/info/exclude` | Throwaway git dir only. This worktree's exclude was unchanged. |
| `releases/latest` moves | A new binary changes the gate | Pin version, binary sha256, and commit `590f1ced`. |
| Overlap is advisory | `action-required` does not stop the second writer | Do not replace the per-slug worktree and the scheduler markers. |

## Next gate

Stay I1. Do not wire a gate. Reopen only if a later ticket runs PMQA and Security as separate read-only agents, on a real lane, and shows must-fix findings our review bots miss. That ticket grills wiring first. Live `start` stays skipped until tmux or herdr exists and the executor is not codex.

## How this tool would run in our pipeline

1. What triggers it? Nothing in this repo calls kander. A person or an agent would run `kander new` and `kander start` when a card should run beside other cards.
2. What does it do, and which services does it read and write? It reads the git worktree. It writes `kanban/` in that repo and rule files under `HOME` (`~/.agents/kander`, `~/.config/kander`). `start` can launch Codex, Claude, Grok, Cursor, Pi, Devin, OpenCode, or Kimi. It does not store a GitHub token. `kander issue` uses the local `gh` login. This probe did not start an agent and did not call `issue`.
3. What does it trigger next? A started card would open an agent in tmux or herdr, then the PMQA and Security roles, then `move done`. Those steps were not run. Nothing in CI listens for a kander card.
4. Where does a human re-enter? The board is a terminal UI. Archive and trash want a decision reference. The N/A review path is an agent-written waiver, not a human gate. A human would re-enter to pick an executor other than the codex default, and to refuse a waiver.
5. What stops two runs doing the same work? `check overlap` lists paths changed on both sides of the merge base. It does not lock a card. One worktree per slug and the scheduler markers already stop two lanes. Overlap tied that git check and created no worktree.
