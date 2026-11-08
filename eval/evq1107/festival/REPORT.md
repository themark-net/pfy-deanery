# festival evq1107

Verdict: STAY I1. `fest` v0.9.5 and `camp` v0.14.0 ran offline under a redirected HOME. On one filled plan that restates gap B, `fest next` matched a pending-filename sort 3/3 and returned the same file from a second process. The testing checklist was then marked completed with 11 boxes still unchecked. Promote stayed blocked at 4 of 11 tasks. The 3 hour `./pfy build` timeout and the two pregate FAILs were not changed. Nothing was wired into a gate.

## Catalog comparison

Same job: a plan, a next step, and a gate for long agent work.

| Card | Stage | What it already does | How festival compares |
| --- | --- | --- | --- |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards and loop types, already the orchestration toolset | Festival is a second methodology on top of those exits. The phase gate waits on an operator, which our lanes already do. |
| project-process bootstrap | I3 | Scaffold DESIGN, ADR, TODO, open questions, AGENTS | `docs/TODO.md` is the ordered queue. `fest next` agreed with a sort of pending task files 3/3. |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees | Festival did not fan out and did not lock a claim. |
| kanzo | I0 | Local kanban + MCP | Same queue job, not run here. Festival's next step is one markdown file. |
| LangGraph | I1 | Graph orchestration. Our loops already cover the operator path | Festival is files on disk, not a graph runtime. |
| Multica | I1 | Multi-agent board. Not our orchestrator | Same. A board we would not adopt. |
| Atomic Task Graph (ATG) | I2 | Compile, parallel waves, freeze, localized repair | Different job. Festival does not compile a DAG. |
| mattpocock skills | I1 | Planning and review skills already on the skill path | Those skills already say what to do next. |
| Auto-Company | I1 | Patterns, including a pre-mortem gate. Not a runtime | Festival's testing gate did not run a check. |
| odai | I0 | Evidence-before-done governance skill | Festival marked the testing gate done with 11 empty boxes, so it does not add that check. |
| gstack | I1 | Role patterns already ported in docs | Do not clone a second process kit. |
| Hermes Teammates | I0 | Fixed tester/reviewer roster inside Hermes | Not a plan file loop. |
| Brigade (entry 110, no stage card) | I0 | Work ledger with atomic claims | `fest task completed` on task 3 returned success while `fest next` still returned task 1. No claim. |

Gap B's review side is already probed elsewhere: Elephant-Goldfish Model (STAY I1), Chiasmus (STAY I1), neatroots (I2), agentgg (I0). Festival's review file is a checklist, not a diff review.

It does not beat what we have.

## Pins

| Item | Value |
| --- | --- |
| Suite | v0.3.20, commit `90fb33f3f516f0764e1b5e69e63cfee23ec5a93e` |
| Tarball | `festival-0.3.20-linux-x86_64.tar.gz`, 32,363,082 bytes, sha256 `0202a7b15cc385d1687d756ae6f513283a5adef445037f70a054b754e6ec716f` (matches release `checksums.txt`) |
| fest | v0.9.5, commit `a2694c468b2ff7ffd3aa9a1aa31ce914e905dee0`, 34,406,584 bytes, sha256 `21767cacd8a7dd346e634c99a9c21f99ba8c25424e762b42b746cd32cb29e4db` |
| camp | v0.14.0, commit `4aaf41aca025edb5ece63443bd0e2f343cdc6c2d`, 36,065,464 bytes, sha256 `550df7ee2716d0cc298d5e6f571cb719b9b611eafe4861c55d9e0e945cf20464` |
| Templates | `fest system sync --tag v0.9.5 --force`. A bare `fest init --minimal` first resolved the stable channel to v0.10.1. The measured run used the v0.9.5 templates. |
| Install | `~/.cache/pfy/tools/festival/` (82 MB). `HOME`, `XDG_*`, and `TMPDIR` point under that directory. No brew, no `npm install -g`, no `festival update`, no shell-init. |
| Isolation | Real `~/.obey` and `~/campaigns` stayed absent. This worktree has no `.camp` file. The linked project was `projects/probe-notes` inside the camp, not this repo. |

## Commands

```bash
# checksums.txt and the x86_64 tarball from the v0.3.20 release, then unpack
# under ~/.cache/pfy/tools/festival/unpack/. HOME and the XDG dirs stay under
# that cache path. Put unpack/ on PATH.
camp create probe -d "festival eval probe" -m "measure fest next on one backlog slice"
fest init --minimal --no-checksums
# From the camp root. That init synced the stable channel (v0.10.1).
fest system sync --tag v0.9.5 --force
rm -rf festivals && fest init --minimal --no-checksums
# Back in this worktree.
python3 eval/evq1107/festival/probe.py
```

The probe creates a camp-local plan with three tasks taken from the gap B row in `docs/eval/TOOLSET-RANKING.md`: the 3 hour timeout, the two pregate FAILs, and the recovery line (do not start another 3 hour build). It does not run `./pfy build`. Numbers are in `results.json`.

## Numbers

| Check | Result |
| --- | --- |
| Scripted loop | 0.553 s (download and template sync are outside this) |
| Markers on the empty scaffold | 38 |
| Markers after the sequence and three tasks, before the second fill | 50 |
| Markers after the fill | 0 |
| `fest validate` | valid, score 100, exit 0 |
| Unfilled control `fest next` | exit 1, `VALIDATION FAILED` |
| First `fest next` | `01_record_timeout.md`, exit 0 |
| Second process, no edits | same file (`resume_same` true) |
| Progress at that point | 11 tasks, 0 completed |
| Complete task 3 while task 1 is still next | exit 0, status completed. The next file stays task 1 |
| Order vs a pending-filename sort | 3/3 |
| Next file after those three | `04_testing.md` |
| Complete that testing gate | exit 0, file status `completed`, unchecked boxes 11, checked boxes 0 |
| `fest next` after the sequence gates | exit 0. Text says the phase gate needs operator approval and "do not approve it yourself" |
| Promote | exit 1, `4 of 11 tasks incomplete` |
| Complete the four `gates/implementation/QUALITY_GATE_*.md` copies | CLI says completed. Each file stays `pending`. Unchecked boxes stay 8, 7, 13, and 11 |
| Promote again | exit 1, same `4 of 11 tasks incomplete` |
| Gap B closed | 0. The timeout and the two pregate FAILs are untouched |

`fest next` is a stable read of the first pending task file. It is not a claim, and the checklist is not a test.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. The next file matches a filename sort we can do without Festival. It does not move gap B.
2. Operator leverage: no. The plan needed 50 markers, a camp, two promotes to become active, and a working directory before the first real `fest next`. The phase gate then waits on a person.
3. Evidence: yes. The pinned binaries ran offline and `results.json` records the exits.
4. Blast radius: yes, while it stays in the cache. Apache-2.0. No model weights. About 82 MB of binaries and templates. It did not become the product runtime.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The docs do not say that `fest init` pulls a newer template channel, or that a gate file can be completed with empty boxes.
2. Bounded surface: yes. `fest` and `camp` are the entry points.
3. Isolatable: yes. The cache path with a redirected HOME held every write.
4. Reversible: yes. Deleting the cache leaves the pin and this entry.

Modularity passes for a cache probe. That is not a promotion. The result is no longer ambiguous, and it does not help, so the card stays I1. I3 would also need a pipeline script and `self_pipeline` evidence. This lane wires nothing. `self_pipeline` is `not_applicable`.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Template channel drift | `fest init` synced stable v0.10.1 while the CLI is v0.9.5 | `fest system sync --tag v0.9.5 --force` before a run. Pin the tag in the note. |
| Writes into the real HOME | `~/campaigns` and `~/.obey` | Redirect `HOME`. This run left both real paths absent. |
| Empty gate counts as done | `fest task completed` on `04_testing.md` returns success with 11 unchecked boxes | Do not use Festival as a gate. Pregate stays the check. |
| False complete on the template copies | The CLI says completed and the file stays `pending`, so promote never finishes | Treat a completed status as real only when the file's `fest_status` changed. |
| No claim | Two sessions get the same next file, and a later task can be marked done early | One worktree per slug stays the lock. |
| Second methodology | Agents follow Festival and our skills at once | Leave it unwired. |
| Phase gate waits | `fest next` tells the agent not to approve the phase | That is the tool's own stop. It does not shorten a 3 hour build. |

## Next gate

Stay I1. Do not wire Festival into pregate, CI, or `./pfy`. Reopen only if a later ticket shows that TODO, git, and the 8 exits lose the next step on a real lane, and that ticket grills wiring first.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? A long goal that should still have a next step after the session ends.
2. What does it do, and which services does it read and write? It reads the camp, the template cache under `~/.obey`, and an optional linked project. It writes festival markdown and, if linked, a `.camp` file in that project. This probe linked nothing in pfy-mentat.
3. What does it trigger next? `fest next`, then the agent, then `fest task completed`, then a phase gate that waits for `fest workflow advance` from an operator.
4. Where does a human re-enter? At that phase gate, and again when promote reports tasks still incomplete.
5. What stops two runs doing the same work? Festival does not. Both calls return the same pending file. Our one worktree per slug is the lock.
