# squadra evq1107

Verdict: STAY I1. Pin v3.10.1, commit `5081a06ae054bc80072d8109ee2ef088b52513c3`. The probe ran offline in 2.8925s. Start before an acknowledgement exited 1. An always-passing test passed on both the base and the candidate, and the challenge exited 1. The same test id failed by assertion on the registered base and passed on the candidate. The builder's own review exited 1. Close before the reader's review exited 1. After the reader's acknowledgement and an accepted review, close exited 0 and `doctor` reported integrity passed with no pending acknowledgement. `./pfy build` was not started. The 3 hour timeout and the two parked pregate FAILs are unchanged.

## Catalog tools on this job

The job is gap B from the 2026-11-07 ranking: `./pfy build` is not proven bot-usable after a 3 hour timeout, and the recheck fix is parked after two pregate FAILs. Squadra (entry 124) is a local registry: several seats, an acknowledgement before work, a source-bound proof, a non-author review, and a defect-fix challenge that must fail on the original and pass on the candidate. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` are about other gaps. The in-repo rule `prefer-behavior-and-fail-recover-tests` is a skill, not a stage card. It already says a regression test fails without the change.

| Tool | Stage | What that card covers | How squadra compares |
|------|-------|----------------------|----------------------|
| Festival | I1 | Plan, next task, and checklist gates. `fest next` matched a pending-filename sort 3/3 in 0.553s. The testing gate completed with 11 unchecked boxes. | This probe refused the always-passing test (both runs `native_rc` 0, outcome `passed`). Festival's checklist did not. Neither moves the 3 hour timeout. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards and loop types, already the orchestration toolset. | Those exits are how a lane stops. Squadra has no timeout and no pregate status. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, open questions, AGENTS. | `docs/TODO.md` is the queue. Squadra's task list is a second queue. |
| Brigade | I0 | File ledger with an exclusive claim. 0 duplicate ids out of 94 slugs. Marker files did the same in 0.004s. | Squadra's acknowledgement is a different check. It does not claim a worktree. |
| Foremerge | I1 | Pre-edit intent ledger. The probe blocked 0/6 same-path modify pairs. | Squadra does not see two editors on one path. |
| kanbots | I1 | Kanban that fans out to coding CLIs in worktrees. | This probe registered `manual` seats and started no agent. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | Same. A board we would not adopt. |
| Auto-Company | I1 | Persona and pre-mortem patterns. Not a runtime. | Squadra is a runtime registry. The patterns we keep are already in docs. |
| gstack | I1 | Role patterns already ported in docs. | The coordinator, builder, and reader names match that shape. The port already says not to clone a second kit. |
| Open Steps | I0 | One stop nag. A second stop exits 0 with no report. It does not see a 3 hour build. | Squadra's close exits 1 until the review exists. It still does not see the build clock. |
| Sponsio | I2 | Pre-call check. An ordering rule blocked 2/2 premature copies that a one-call check missed (0/2). | Squadra also refuses a later step (start before ack, close before review). Sponsio does that on one tool call. It does not keep a task registry or a red/green defect check. |
| Kander | I1 | Branch overlap and a two-role reviewer done gate. Both roles set to N/A reached done with 0 reviewer runs. | Squadra refused the author review 1/1 and closed only after a different seat accepted. Kander's N/A path reached done with no review. Neither moves the 3 hour timeout. |
| MCO | I1 | Parallel raw-answer review across provider CLIs. The probe kept 2 of 2 disagreeing answers and made 0 comparison decisions. The pfy build timeout did not move. | Squadra's review is one non-author seat on a registered diff. MCO keeps two raw answers and does not decide. Neither closes gap B. |
| Moira | I1 | Per-step JSON Schema on an agent directive, plus a condition that routes fields the agent already sent. Schema rejected 8/8 bad shapes and stopped 3/3 FAIL reports. 4/4 schema-valid lies still finished. | Squadra refuses a missing ack, an always-passing test, and an author review. Moira stops a FAIL field and still accepts a well-shaped lie. Neither is the build clock. |
| Overtime | I0 | Wake and budget for an ACP agent whose folder outlives one process. That probe left the pfy build timeout unchanged. Usable backends were 0. | Same gap. Squadra's seats were `manual` and it has no build clock. |
| HAR | I0 | Worktree slot plus a tree-hash receipt, slower than git (0.837s vs 0.222s). | A receipt for a different subject. |
| odai | I0 | Evidence-before-done governance skill. | Squadra ran the evidence check. odai is still unread as a skill port. The check we need is already the test skill. |
| Hermes Teammates | I0 | Fixed tester and reviewer roster inside Hermes. | Blocked on Hermes. These seats were `manual`. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build. It named one bug and missed the parks. | A diff read, not a registry. |
| OpenQodex | I1 | A finding has to cite a real scanner token. | Different review check. |
| agentgg | I0 | Local SAST on deploy and secret diffs. | Different review check. |
| Rulora | I1 | Loop counters. The host still decides when a Build lane stops. | Squadra does not stop the lane. |
| Atomic Task Graph (ATG) | I2 | Compile, parallel waves, freeze, repair. | Different job. |
| Pi-Harness | I0 | Desktop control plane. Reference only. | Not a registry we run. |

Squadra does not beat git, the 8 exits, TODO, or the test skill on gap B. The acknowledgement and the red/green split are real. They do not make `./pfy build` finish.

CodeGuard (I0), trailofbits-skills (I0), and the Cloudflare security-audit skill (I0) read a diff or a findings schema. repository-harness (I0) installs a map beside AGENTS.md. imcodes (I0) is a review-loop reference and Tree-sitter Analyzer (I1) is a change-impact map. None of those is a seat registry, and none of them moved gap B.

## Pin

Host is linux x86_64. Python 3.14.4. No account, no key, no hosted call. `selftest` and `dash` were not run (they want Node for the dashboard checks). No plugin install. The GitHub release API returned 403, so there is no release-asset checksum. The pin is the tag from `git ls-remote`.

```bash
git ls-remote https://github.com/dagoSte/squadra.git 'refs/tags/v3.10.1*'
# acd9e6d6099903e5fd128eb0906f061a4e72e88e  refs/tags/v3.10.1
# 5081a06ae054bc80072d8109ee2ef088b52513c3  refs/tags/v3.10.1^{}
```

Annotated tag object `acd9e6d6099903e5fd128eb0906f061a4e72e88e`. Commit `5081a06ae054bc80072d8109ee2ef088b52513c3` (2026-10-16). `python3 -B scripts/squadra.py --version` printed `3.10.1`. `scripts/squadra.py` sha256 `fdef7bf4b459f42a5e1d91ec4fe2a9b58092d76ea80fb5e7afa14ac78d626261`.

```bash
BASE=$HOME/.cache/pfy/tools/squadra
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --depth 1 --branch v3.10.1 https://github.com/dagoSte/squadra "$BASE/src"
```

The clone prints that the tag is not a commit and checks out `5081a06ae054bc80072d8109ee2ef088b52513c3`. Checkout size is 21356777 bytes (about 20.4 MB), under the 50 MB bar. Files outside `.git` are 12364971 bytes. Nothing from the clone is in the git tree. License file is MIT.

The probe's child process sets `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` under `tmp/squadra-probe/`. That home stayed empty. `~/.local/state/squadra`, `~/.cache/squadra`, and `~/.squadra` were absent before and after.

## Probe

`python3 eval/evq1107/squadra/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/squadra/results.json`. The registry and the one-file git repo stay under `tmp/squadra-probe/` (gitignored). The product checkout is not the squadra project. The scope file names gap B and then checks `VALUE = 1` against a test that expects `VALUE = 2`.

| Step | Exit | Seconds | Error |
|------|-----:|--------:|-------|
| version | 0 | 0.0578 | |
| init `--temporary --lang en` | 0 | 0.1024 | |
| agent c1, w1, r1 | 0 | 0.1046, 0.0882, 0.0905 | three `manual` seats |
| task `--defect-fix` | 0 | 0.1786 | |
| start before ack | 1 | 0.0871 | Assignment has no recipient ACK |
| close before deliver | 1 | 0.0999 | Candidate drift; no delivery has set a candidate yet |
| ack `assign-T1` | 0 | 0.1118 | |
| always-passing challenge | 1 | 0.2305 | both runs `native_rc` 0, outcome `passed` |
| real challenge | 0 | 0.2759 | original `native_rc` 1 outcome `assertion`; remedy `native_rc` 0 outcome `passed` |
| prove | 0 | 0.2582 | agreed argv, `print('contract passed')` |
| deliver | 0 | 0.1342 | handoff id returned |
| review by the builder | 1 | 0.1232 | Author cannot independently review own changes |
| close before that review | 1 | 0.1049 | Independent current code review pending |
| ack handoff, reader review, check, close | 0 | 0.0975, 0.1295, 0.1058, 0.1327 | four calls, each exit 0 |
| doctor | 0 | 0.1283 | integrity `passed`, events 23, `pending_ack` `[]` |

Whole script 2.8925s. Refuses that held: 5/5. Real challenge matched: 1/1. Final close: 0. Gap B counters: build invoked false, timeout hours changed 0, pregate fails cleared 0.

`tests/test_squadra_probe.py` drives this script with a stub CLI. A stub that allows the start, the always-passing challenge, and the author review exits non-zero. A stub that refuses those three and returns the red/green split exits 0.

## Gates

Value gate, 2 of 4. Short of I3.

1. Gap fill. Not met. The 3 hour timeout and the two pregate FAILs are unchanged. Festival's empty checklist is weaker on the always-passing test. git, the 8 exits, TODO, and `prefer-behavior-and-fail-recover-tests` already cover the lane.
2. Operator leverage. Not met. A 2.8925s toy task does not make `./pfy build` finish. Seats here are `manual`. The CLI has 50 subcommands. Adopting the registry adds a second record beside GitHub.
3. Evidence. Met. The pinned checkout exited 0 on this probe.
4. Blast radius. Met for a cache copy. MIT, no weights, no account, about 20.4 MB. The installer was not run. `--root` kept the registry out of the real home.

Modularity gate, all four hold. That allows a local probe. It does not by itself promote.

1. Local code needed. Met. The early close says "Candidate drift" when nothing has been delivered. The red/green split is host behavior.
2. Bounded surface. Met. One entrypoint, `scripts/squadra.py`. This probe used `init`, `agent`, `task`, `start`, `ack`, `challenge`, `prove`, `deliver`, `review`, `check`, `close`, and `doctor`.
3. Isolatable. Met. Cache checkout plus a registry under `tmp/`. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I2 is for a probe that measurably helps while potential is still open. This probe answered the question. The checks work. Gap B does not move. Potential is low.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Registry in the real home | `~/.local/state/squadra` appears | This probe passed `--root` and `--temporary`. The three real paths were absent before and after. The child `HOME` under `tmp/squadra-probe/home` stayed empty. |
| Two records | GitHub says one thing and the registry says another | GitHub stays the gate of record. This lane did not register the product checkout. |
| Early close wording | Close before any delivery exits 1 with "Candidate drift", which reads like a fingerprint miss | After deliver, close exits 1 with "Independent current code review pending". Trust the exit and the later text. |
| Always-passing test | Both inputs pass, so the defect is not shown | The challenge exited 1 and `doctor` still had work to do until the real id failed on the base. |
| Author seat | The builder files an accepted review | The review exited 1 and named the author. The reader seat is a different identity. |
| Installer | Skills copy into host config dirs | This lane did not run the installer, `plugin`, `dash`, or `selftest`. |
| Default language | `--lang` defaults to Italian | This probe passed `--lang en`. |
| Upstream speed | 3.x moves | The probe exits 2 when a checkout with `.git` is not commit `5081a06ae054bc80072d8109ee2ef088b52513c3`, or when `--version` is not `3.10.1`. |
| Second queue | Agents ack Squadra and the lane still runs for 3 hours | Stay I1. Do not point a Build seat at this registry. |

## Next gate

Stay I1. Reopen only if a later ticket shows the 3 hour `./pfy build` timeout or the two pregate FAILs move because a squadra registry is in that lane, and that ticket grills wiring first. Copying the red/green idea into a test we already require is a separate note. No pregate, CI, or other gate in this lane. Not a Feature GO. I3 would also need `self_pipeline` evidence, because this card's uses name a review.

## Five questions (this tool in the pipeline)

1. What triggers it? Nothing added here. A person would run `python3 -B scripts/squadra.py` against a `--root` under `tmp/` for one trial task. Build lanes stay on git, TODO, and the 8 exits.
2. What does it do, and which services does it read and write? It reads the pinned checkout and one git repo. It writes the registry directory named with `--root`. This probe used no hosted model, no account, and no network after the clone.
3. What does it trigger next? Nothing. It does not call `./pfy build`, pregate, or GitHub.
4. Where does a human re-enter? Before any seat is registered on a real checkout. A promotion needs a later grilled ticket and Mark's GO. This lane does not ask.
5. What stops two runs doing the same work? This lane does not share a registry. The eval slot is one worktree. The task id `T1` cannot be created twice in one registry. No second scheduler is added.
