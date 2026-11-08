# Open Steps evq1107

STAY I0. Pack 0.4.8 nags once when the git fingerprint changes, then the next stop exits 0. In 4 work-landed endings, 0 second stops stayed blocked. In 3 of those 4, the outside report file was absent. A pre-written report still got exit 2 on the first stop. Setting the 3 hour mark and a pregate FAIL on the environment changed 0 exits. That does not close gap B.

`STAY I0 0 of 4 work-landed second stops stay blocked, 3 of those 4 have no report file, and a 10800s pregate FAIL env changes 0 exits`

## Catalog overlap

Same job: a done-or-not session report, plus a stop hook that demands one, for `./pfy build` lanes (gap B in `docs/eval/TOOLSET-RANKING.md`, 2026-11-07). Searched `data/stages/*.json` uses, features, and tags, plus that ranking and the batch-1 verdicts under `eval/ev1107/` and `eval/catchup-1107/`.

| Tool | Stage | Why it covers this job | How Open Steps compares |
| --- | --- | --- | --- |
| Finn Loop / 8 exits (`agent-loops`) | I1 | Exit card and loop report. Features include 8 exits. Tags include `#loops`, `#exits`, `#stop-conditions`. Wall clock is exit 4. | The hook's exit 2 is a fingerprint nag. It has no clock, no turn cap, and no budget. 0 of 4 second stops stayed at exit 2. It does not beat the exit card. |
| Hermes feedback loops | I1 | Session retro, already a skill. The runtime stays off the card. | `os-done-or-not` is another report template. The hook never opens the report file. |
| odai | I0 | Evidence-before-done skill. | The skill text says a yes needs proof. The hook accepts a second stop with 0 report files, so the proof is never required. |
| claude-codex-settings | I1 | Hook pack for other CLIs. Tag `#hooks`. | `adapter.sh grok stop` exits 1. Cursor's stop exits 0 and returns a followup. The pack we already declined to vendor is the same class. |
| Festival | I1 | Checklist gates for a long goal. Its 2026-11-07 probe left the build timeout open. | Same gap. Festival names a next task. This hook returns in under 40 ms and then allows the stop. |
| Rulora | I1 | The host still decides when a Build lane stops. LoopControl covered 2 of 8 exits, and the 3 hour stream stayed active. | Same shape. Here the 10800 second environment leaves a clean stop at 0 and a dirty stop at 2. |
| HAR | I0 | A verify receipt keyed by the worktree tree. Stayed I0 because gap B was unchanged. | The fingerprint is a checksum in `~/.claude/open-steps/`. The build never reads it. |
| neatroots | I2 | Offline rules on saved traces. | This hook does not read a trace. |
| mattpocock/skills | I1 | Planning and review skills already on the path. Tag `#review`. | `os-check-work` overlaps "a report is a claim". Its allowed tools include `gh pr merge`. Those skills were not copied. The skills on the path do not merge on their own. |
| Elephant-Goldfish | I1 | Fresh-eyes spec review before Build. STAY I1 on the recheck parks. | Different moment. It does not run at stop. |
| Chiasmus | I1 | Call-graph impact for per-file review. STAY I1. | Not a stop hook. |
| agentgg | I0 | Local SAST on a risky diff. STAY I0. | Not a session report. |
| imcodes | I0 | Idle verdict and final-answer memory. Reference only. Auto deliver does not commit. | `os-check-work` allows `gh pr merge`. This lane did not install that skill. |
| Pi-Harness | I0 | Run trace and review gates. Reference only. | Not this hook, and not installed. |
| TeaQL Agent Kit | I0 | Verification policy patterns. | No stop behavior in that card. The live count here is still 0 of 4. |

Gap B in the 2026-11-07 ranking is the 3 hour `./pfy build` timeout and a recheck fix parked after two pregate FAILs. That section says no entry from 137 to 167 closes it. Entry 099 is older and lands in the same place. Batch-1 skill-up, SkillSpector, Strata, HiRoute, DSPy, and Bumblebee close other gaps.

Beats what we have: no.

## Pins

| Item | Value |
| --- | --- |
| Repo | `https://github.com/kharmanskyi/open-steps` |
| Entry short pin | `4fa744ba8ea0` |
| Full pin | `4fa744ba8ea06ccf128a39853824c46ac391dd00` |
| `git ls-remote` HEAD and `refs/heads/main` | the same full pin (main has not moved past the entry) |
| Commit | `chore: release 0.4.8` (2026-10-05 18:36:10 +0400) |
| Pack version | `0.4.8` in `.claude-plugin/plugin.json` |
| License | MIT |
| Install | `~/.cache/pfy/tools/open-steps/src/repo` (detached at the pin) |
| Working tree | 651376 bytes excluding `.git` (under the 50 MB I2 copy limit) |
| `hooks/stop-report.sh` sha256 | `0703722011433929720ef19be2ee2f05af266205b1c2a95aaebd6f6a1815d516` |
| `hooks/session-start.sh` sha256 | `dedac20072244c15660611cda903dfccc6447fc299ae372f99f600081e7bd248` |
| `hooks/fingerprint.sh` sha256 | `0433d8ed704260668a3974c6c9eee85949fef3feb01b0b17a2813b62f4f8bb0b` |
| `hooks/adapter.sh` sha256 | `2515d92ce7189f9df97f326e7092c8b898d030be2749a70085704c3590852968` |
| `hooks/hooks.json` sha256 | `b4cbdd575260c2f77ebd7c8f1d53f1676d4c9bf55b8d885df478974edfa6608c` |
| `hooks/test.sh` sha256 | `8334035ce60e25289fab019464bc57e6798c5a01e83d137590180efe38546b8f` |

The entry records no checksum. The hashes above are the pin we ran. No account, no key, no hosted model. `ollama` was not called. The model lock was not taken.

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for the clone and for every hook process pointed under `~/.cache/pfy/tools/open-steps/`. `/home/mark/.claude/open-steps` was absent before the probe and absent after it.

## Commands

```bash
CACHE="$HOME/.cache/pfy/tools/open-steps"
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,xdg/data,tmp,src}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config"
export XDG_CACHE_HOME="$CACHE/xdg/cache" XDG_DATA_HOME="$CACHE/xdg/data"
export TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git ls-remote https://github.com/kharmanskyi/open-steps.git HEAD refs/heads/main
git clone --filter=blob:none https://github.com/kharmanskyi/open-steps.git "$CACHE/src/repo"
git -C "$CACHE/src/repo" checkout --detach 4fa744ba8ea06ccf128a39853824c46ac391dd00
sha256sum hooks/stop-report.sh hooks/session-start.sh hooks/fingerprint.sh \
  hooks/adapter.sh hooks/hooks.json hooks/test.sh
```

The probe repeats the upstream suite with the same redirected `TMPDIR` and a per-case `HOME`. Upstream `hooks/test.sh` already points each case at its own temp `HOME`.

```bash
# parent HOME stays the operator home so the cache path resolves
python3 eval/evq1107/open-steps/probe.py
```

`probe.py` writes `eval/evq1107/open-steps/results.json`. Wall time for that run was 5933.4 ms. The suite inside it passed 290, failed 0, in 4821.5 ms. That matches the entry's "290 passed, 0 failed" from the Grok Bot box.

## Probe

Gap B is the 2026-11-06 `./pfy build` trial: a 3 hour timeout, and a recheck fix parked after two pregate FAILs. The entry says the stop hook keeps the session going until an `os-done-or-not` report exists. The hook compares a git fingerprint with a baseline. On a change it prints the ask to stderr and exits 2, and it saves the new fingerprint in the same step. The report path is `~/.claude/open-steps/reports/<directory-name>/latest.md`. The hook does not read that file.

The clean session ran in this worktree and did not edit it. `git status --porcelain` already had 3 lines: the untracked `eval/evq1107/open-steps/` directory, the new stage card, and the entry edit. That is the upstream "already dirty before the session" shape. Session start exited 0 in 37.8 ms. Stop exited 0 in 36.9 ms. Porcelain was unchanged. Report markdown files: 0. Hook state went to the temp `HOME` at `reports/open-steps/.stop-state`.

The other cases use a throwaway git repo under the cache tmp dir, seeded with the first line of this repo's `AGENTS.md`, so the lane worktree stays unmodified. Each case has its own `HOME`.

| Case | First stop | Second stop | Report markdown files |
| --- | ---: | ---: | ---: |
| One file edit, no report written | 2, asks for `os-done-or-not` | 0 | 0 |
| Report file written before the first stop | 2, still asks | 0 | 1 |
| `docs/HANDOFF.md` written in the repo | 2, asks | 0 | 0 outside the repo |
| Commit, clean worktree after the commit | 2, asks | 0 | 0 |

Second stops still blocked: 0 of 4. The in-repo handoff is the path this repo already requires. The hook treats it as more dirty work. `BIG-PICTURE.md` alone exits 0, because the pack excludes that one filename. `docs/` is not excluded.

Default cooldown is 900 seconds. After the first nag, a second new file and an immediate stop exited 0, with 0 report files. `OPEN_STEPS_MIN_FILES=5` stayed silent on 1 file (exit 0) and asked on 5 files (exit 2). `OPEN_STEPS_DISABLE=1` on a dirty tree exited 0.

Gap B inputs, set on the hook environment and not read by the script: `PFY_ELAPSED_S=10800` and `PFY_PREGATE=FAIL`. Clean stop stayed 0. Dirty stop stayed 2. That is the same pair as the no-env shapes. Changed exits: 0.

Hosts in `hooks/adapter.sh`:

| Host | First stop after one edit | Next stop | Report files | Adapter exit |
| --- | --- | --- | --- | ---: |
| cursor (`status` completed) | followup message, stop not blocked | `{}` | 0 | 0 then 0 |
| gemini (`AfterAgent`) | `decision` deny | `{}` when `stop_hook_active` is true | 0 | 0 then 0 |
| grok | usage on stderr | not a host | 0 | 1 |

Two sessions, one repo, one `HOME`. Lane A took the baseline, then a file was edited, and lane B stopped before lane A did. Lane B exited 0 and did not ask. Lane A's stop after that also exited 0 and did not ask. Report files: 0. A new session id stores the dirty tree as its baseline. The edit produced no exit 2.

On this repo, the last 30 commits (`b4bcaf058feaef2d3ec7a9bfbde265eb42481fc7` through `dc7340da3983f5855498224361d761353377c6c4`) all change the tree. 3 of 30 touch `docs/`. 0 of 30 have `HANDOFF` in a path. The live commit case is that shape: HEAD moves, the first stop exits 2, the second exits 0, report files stay 0. The hook was not invoked once per historical commit. One clean commit was enough to see the exit pair, and every one of the 30 moves HEAD.

`skills/os-check-work/SKILL.md` allows `Bash(gh pr merge *)`. The probe did not copy any skill into an agent home, and it did not run `gh`.

## Gates

Value gate (3 of 4 needed for I3):

1. Gap fill: no. The 10800 second variable and `PFY_PREGATE=FAIL` change 0 exits. The hook returns in under 40 ms on this worktree. `agent-loops` already names the wall clock. A `docs/HANDOFF.md` file, which a lane here already has to leave, gets the same nag as any other edit, then the second stop exits 0 with 0 outside reports.
2. Operator leverage: no. Grok is not an adapter host (exit 1). Cursor cannot block the stop. Gemini's retry exits 0 with 0 report files. A one-shot nag does not make a parked pregate pass, and this lane does not wire the hook into `./pfy build`.
3. Evidence: yes. Pin matches `git ls-remote`. Suite 290/290 in 4821.5 ms. Probe wall 5933.4 ms. Receipt: `results.json`.
4. Blast radius: yes for the hooks that ran. MIT, 651376 bytes, bash and git, cache `HOME`, no account. The merge line in `os-check-work` stays unwired. Skills were not copied.

Value score: 2 of 4.

Modularity gate (all 4, required before an I2 copy is called a promotion):

1. Local code needed: yes. The README claim is that the session stays open until a report exists. The second-stop count is visible only by running the hook.
2. Bounded surface: yes. `hooks/*.sh` and the markdown skills. The unit of the eval is the two hooks plus `adapter.sh`.
3. Isolatable: yes. The clone sits under `~/.cache/pfy/tools/open-steps/`. It is not on `PATH` and not a Make target.
4. Reversible: yes. Deleting the cache clone leaves the pin, the entry, and this report.

Modularity passes, and the tree is under 50 MB. I2 is for a probe whose value is still ambiguous, and this ticket promotes I2 when the probe measurably helps. The help measured here is 0 of 4 second stops held, and 0 gap-B exits flipped. Potential is low. Stage stays I0. No in-repo copy. No gate.

The card's uses and features do not contain the CI, testing, or review role words, so `self_pipeline` is not required at I0. Nothing in this lane is wired into pregate, CI, or a gate.

## Risks

| Risk | How it fails | How we recover | What this probe saw |
| --- | --- | --- | --- |
| Report nag | Every small edit during a long run exits 2 | `OPEN_STEPS_MIN_FILES`, `OPEN_STEPS_COOLDOWN` (default 900 s), `OPEN_STEPS_DISABLE=1` | 1 file with `MIN_FILES=5` exited 0. 5 files exited 2. A second file inside the default cooldown exited 0. Disable on a dirty tree exited 0. |
| Report place | The report is under `~/.claude`, so an in-repo handoff never satisfies it | Keep the handoff in `docs/`. Do not retarget it. | `docs/HANDOFF.md` got exit 2, then exit 0, with 0 outside reports. A report written first was ignored on the exit 2. |
| Merge bypass | `os-check-work` may merge when it believes the claims | Do not copy the skills. Merge stays Tester plus Reviewer. | Allowed tool string `Bash(gh pr merge *)` is present. No skill was copied. `gh` was not run. |
| Harness mismatch | Grok Build does not use Claude's exit 2 contract | Do not wire the hook. A pfy wrapper would have to enforce the second stop itself. | `adapter.sh grok stop` exited 1. Cursor and the Gemini retry both finished with 0 report files. |
| Shared state | Two lanes with the same directory name and `HOME` share one state file | One `HOME` per lane, or do not install the hook | Lane B stopped after the edit and before lane A. Both exits were 0. The edit produced no ask. Report files: 0. |

## Next gate

Stay I0. Re-open only if a later pin keeps exit 2 on the second stop until a report file exists, that file is the in-repo handoff, and the exit changes when the wall clock is 10800 seconds or pregate is FAIL. Wiring into a gate is a separate ticket. This lane is not a Feature GO.

## Five questions (this tool in our pipeline)

1. What triggers it? A host Stop hook. Claude Code runs `hooks/stop-report.sh` on Stop. Cursor and Gemini CLI run `hooks/adapter.sh`. `./pfy build` does not call either script. `adapter.sh grok stop` exits 1.
2. What does it do, and which services does it read and write? It reads `git status`, `git diff`, and `HEAD` for the working directory's repository (up to `OPEN_STEPS_MAX_REPOS`, default 25). It writes `~/.claude/open-steps/reports/<directory-name>/.stop-state`. The agent is asked to write `latest.md` beside that file. No hosted model, no account, no build receipt, no pregate log.
3. What does it trigger next? Exit 2 asks the agent to run the `os-done-or-not` skill and stop again. The next stop exits 0 once the fingerprint is saved, including when `latest.md` was never written. It does not start a build, a smoke, or a gate. `os-check-work`, if someone installed it, can call `gh pr merge`. We do not install it.
4. Where does a human re-enter? The report template has a row for one action the person must take. The hook does not wait for that row. On our pipeline the human re-entry stays Tester and Reviewer at the commit, and Mark for a GO. `OPEN_STEPS_DISABLE=1` is the kill switch if the hook is ever wired.
5. What stops two runs doing the same work? Nothing in the hook. One state file per `HOME` and directory name. A second session id stores the current tree as a new baseline and exits 0. Measured: lane A had the baseline, a file changed, lane B stopped first (exit 0, no ask), then lane A stopped (exit 0, no ask), with 0 report files. Cooldown is 900 seconds after a nag, and a stop inside that window exits 0 even when more files changed. Build lanes already serialize on their own worktree, branch, and the local-model lock. This hook does not take that lock.
