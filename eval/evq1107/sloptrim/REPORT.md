# sloptrim evq1107

Verdict: STAY I1. Pinned `detect.py` at v0.9.4 scored a planted marketing page 66 points above a plain page (83 vs 17) in 12.9735 s. Two passes on every file differed by 0. On 20 docs from this repo the median score is 20, the max is 31, and 0 files score above 40. Two em dashes in one paragraph changed the plain page by -1 and set the report-only flag. Five house ', not ' sentences left the score at 17 and set pattern 17 and pattern 18 to false. The upstream 'not just' sentence set pattern 17 and left the score at 17. Harness comparisons: 0. H1 stays with skill-up. Nothing was wired into a gate.

`STAY I1 planted separation 66 in 12.9735s, 0 of 20 docs above 40, em dash score delta -1, house ', not ' flags 0 of 18, harness comparisons 0`

## Catalog overlap

Same job, two parts. H1 is a repeatable with/without harness score (TOOLSET-RANKING 2026-11-07). The entry also offers a prose score for the house style rule (plain sentences, no em dash, no ', not ' contrast). Searched `data/stages/*.json` uses, features, and tags, plus that ranking section and the batch results under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

Sloptrim is entry 114. The 2026-11-07 ranking covers entries 137 to 167, so this entry is not in that table. That ranking assigns H1 to skill-up.

| Tool | Stage | What that card covers | How Sloptrim compares |
| --- | --- | --- | --- |
| skill-up | I3 | Grade a with-skill run against a no-skill baseline. Catch-up trial: both arms 5/5, delta 0, flake 0/10. `eval/catchup-1107/skill-up/`. | The H1 scorer already on disk. This probe recorded 0 harness comparisons. |
| eval-harness (pfy) | I1 | First-party structural and integration ladder (`make eval-structural`). | A repo ladder. It does not score a prose file. |
| neatroots | I2 | Offline rules on saved agent traces. `eval/ev1107/neatroots/` found a real repeated-call streak. | Trace rules. This probe did not read a trace. |
| DSPy | I1 | Compile a prompt program on a labeled local set. Held-out mean gain 1. `eval/ev1107/dspy/`. | A model compile. This probe called no model. |
| harness2 | I1 | Local harness edit trial. The card records gain 0, which is why H1 is open. | This probe does not re-measure that trial. |
| Harness Score | I0 | Offline L0-L4 grade of harness files. This repo stayed L1 (48/105, 41/105 with the skill tree removed). | A different score, on different files. |
| taste-skill | I0 | Design slop lint plus a browser layout check. Entry 143. No stage above I0. | UI and CSS. It does not read a markdown doc. |
| anti-slop (entry 105) | no card | Skill text that filters generic AI copy. Instructions, not a number. | Sloptrim was cataloged to add the number. On this corpus the number missed ', not ' on 18 of 18 files. |
| karpathy-guidelines | I1 | Coding-behavior skill already in the skill tree. | Instructions. No score. |
| ponytail (skills pack) | I1 | YAGNI skill pack already under skills-external. | Instructions. No score. |

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Repo | https://github.com/seyedehsanhadi/sloptrim |
| Tag | v0.9.4, annotated tag object `3ec1c608072c9935bad3b46113e2cd725bc655d1` (the tag is not itself a commit) |
| Commit | `38dbb7cb4e97de0b9bf157903c95bdcab016dda2` (2026-10-05, matches `examples/x-intake-local/smoke_112_114.py`) |
| detect.py | 98200 bytes, sha256 `057a19a7b483f0145f5b6d0d6bbfc9f8a6f9c8d2f1885ce8a76fcf9db9238e19` |
| License | Apache-2.0 (`LICENSE.txt`) |
| Tree | 870745 bytes excluding `.git` and `__pycache__` |
| Cache dir | 1315234 bytes under `~/.cache/pfy/tools/sloptrim/` after the clone and the probe |
| Entry checksum | The entry gives no file checksum. `git rev-parse HEAD` matched the full SHA, and `git describe --tags --exact-match` printed `v0.9.4`. |
| Python | 3.14.4. Stdlib only. No venv. |

No account and no key. The clone and the probe used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `GIT_CONFIG_GLOBAL` under the cache. `detect.py` writes JSON to stdout. It did not write this repo.

## Commands

```bash
BASE=/home/mark/.cache/pfy/tools/sloptrim
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" TMPDIR="$BASE/tmp" \
  GIT_CONFIG_GLOBAL="$BASE/home/.gitconfig" GIT_CONFIG_NOSYSTEM=1
git clone --depth 1 --branch v0.9.4 \
  https://github.com/seyedehsanhadi/sloptrim.git "$BASE/src"
git -C "$BASE/src" rev-parse HEAD
python3 eval/evq1107/sloptrim/probe.py
```

`probe.py` exit 0. Script clock 12.9735 s. No model lock. `ollama` was not called.

`python3 -m unittest tests.test_sloptrim_probe` drives the probe with a stub `detect.py` in a temp dir (no network, no clone). A stub that prints `not json` and exits 1 must leave `ok` false and must omit `summary`. The same probe then scores a stub plain file at 5 and a stub slop file at 80. With the failure return removed, that test failed: the probe exited 0 and wrote a summary. The return was restored. The test then passed.

## Probe

The corpus is the 20 paths in `eval/evq1107/sloptrim/probe.py`. Fixtures live in `eval/evq1107/sloptrim/fixtures/`. Each file is scored twice. Eight files also get `--ci` (60 sentence resamples, seed 11, upstream default). `zw.md` also gets `--clean`. Bands from the pin: clean through 20, light tells through 40, mixed through 60, heavy tells through 80, then pervasive.

House counts are the probe's own: em dash characters, and the lowercase form `, not `.

| Fixture | Words | Score | Band | Confidence | What changed vs plain |
| --- | ---: | ---: | --- | --- | --- |
| plain.md | 435 | 17 | clean | high | Only key `44_paragraph_monotony`. Interval 0 to 16. |
| slop.md | 321 | 83 | pervasive tells | high | Interval 63 to 83. Separation 66. |
| emdash.md | 449 | 16 | clean | high | Two em dashes in the first paragraph. Flag 58 true. Delta -1. |
| contrast.md | 471 | 17 | clean | high | Five `, not ` sentences. Flags 17 and 18 false. Delta 0. |
| notjust.md | 472 | 17 | clean | high | Upstream 'not just' / 'not only' lines. Flag 17 true, flag 18 false. Delta 0. |
| zw.md | 435 | 45 | mixed | high | One zero-width space. `invisible_chars` 1. Delta +28. Interval 13 to 45. `--clean` removed the character. |
| short.md | 18 | 11 | clean | none | Under the tool's 40-word floor. |

The plain interval does not contain the point score (17 vs a high of 16). The slop interval stays above 60. The two intervals do not overlap.

Point-score repeat: `max_abs_delta` 0 across 27 files, including the `--ci` pass, which did not move the point score.

| Doc | Words | Score | Band | Em dashes | Flag 58 | `, not ` |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| docs/DESIGN.md | 1142 | 31 | light tells | 7 | yes | 2 |
| docs/ops/integration-stages.md | 1628 | 30 | light tells | 13 | yes | 3 |
| docs/ops/skill-verification.md | 906 | 30 | light tells | 15 | yes | 0 |
| docs/PENDING-HANDOFF.md | 3965 | 26 | light tells | 38 | yes | 7 |
| docs/ops/product-operator-surface.md | 694 | 25 | light tells | 17 | yes | 1 |
| AGENTS.md | 1642 | 25 | light tells | 17 | yes | 1 |
| sources/entries/114-sloptrim.md | 484 | 20 | clean | 1 | no | 3 |
| sources/entries/146-skill-up.md | 774 | 20 | clean | 0 | no | 1 |
| docs/eval/TOOLSET-RANKING.md | 1661 | 20 | clean | 0 | no | 7 |
| docs/TODO.md | 3347 | 20 | clean | 49 | no | 2 |
| docs/OPEN_QUESTIONS.md | 621 | 20 | clean | 17 | yes | 0 |
| docs/adr/0010-reject-agenc-as-primary-runtime.md | 633 | 20 | clean | 9 | yes | 2 |
| docs/adr/0012-voice-half-duplex-local-first.md | 913 | 20 | clean | 9 | no | 4 |
| docs/build-dropins/hermes-eval.md | 2733 | 18 | clean | 0 | no | 3 |
| docs/build-dropins/skill-discovery.md | 2674 | 9 | clean | 0 | no | 6 |
| docs/ops/MODULAR-CI.md | 2560 | 6 | clean | 0 | no | 1 |
| docs/ops/HANDOFF-mvp-land-1031.md | 3765 | 6 | clean | 0 | no | 4 |
| docs/plans/MVP-PARALLEL-1031.md | 4632 | 6 | clean | 0 | no | 5 |
| docs/ops/MVP-DOD-WALKTHROUGH.md | 2728 | 0 | clean | 0 | no | 2 |
| docs/ops/AUTONOMOUS-DECISIONS-2026-10-26.md | 2968 | 0 | clean | 0 | no | 6 |

Corpus: 20 files, 14 clean, 6 light tells, 0 mixed or worse. Median 20. Min 0. Max 31. Files with at least one em dash: 11. Of those, 5 still score 20 or under. Flag 58: 8 files, and 2 of those 8 still score 20 (`docs/OPEN_QUESTIONS.md`, `docs/adr/0010-reject-agenc-as-primary-runtime.md`). `docs/TODO.md` has 49 em dashes, flag 58 is false, and the score is 20. The pin reports flag 58 only at two or more em dashes in one paragraph, and that flag does not add score weight. The probe measured the weight: delta -1 on the plant.

`, not ` appears in 18 of 20 docs. Pattern 17 and pattern 18 are absent on all 18. The notjust fixture shows pattern 17 can fire, and the score still does not move.

Resampled intervals on real docs: `docs/ops/MODULAR-CI.md` point 6, interval 0 to 30. `docs/PENDING-HANDOFF.md` point 26, interval 20 to 45. The second interval crosses clean, light tells, and mixed. A second identical run does not. The band from a resample does.

`truncated` is 0. The pin's scan cap is 262144 characters. None of these files hit it.

Common keys on the 20 docs, counted by the probe: boldface 15, AI vocabulary 14, inline-header lists 14, opener repetition 12, curly quotes 9, em dash overuse 8. The pin skips AI vocabulary when it builds the number. The highest score in the set is still 31.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. H1 already has skill-up, plus the structural ladder, neatroots on traces, and the harness2 trial that opened the gap. The prose number does not move when the house em dash or ', not ' form is added. A cutoff above 40 flags 0 of these 20 docs.
2. Operator leverage: no. A person still has no with/without harness score from this tool (0 comparisons). The style rule stays in the agent instructions. One invisible character did move a clean page to 45, and `--clean` removed it. That is a scrub, not the gap.
3. Evidence: yes. The pin, the two passes, the interval, and the scrub ran on this host. `results.json` holds the numbers.
4. Blast radius: yes. Apache-2.0 Python in the cache, 1315234 bytes, no key, no daemon, no copy in this repo. Deleting the cache leaves the pin and this report.

Modularity, all four, for a cache probe only:

1. Local code was required. The README does not say that flag 58 and pattern 17 leave the score unchanged, or that 49 em dashes in `docs/TODO.md` never raise flag 58.
2. `scripts/detect.py` is a bounded entry point. Hooks and `/sloptrim init` were not run.
3. The tree sits under `~/.cache/pfy/tools/sloptrim/` and is not the product runtime.
4. Deleting that directory does not remove the catalog pin or this report.

The working tree is 870745 bytes, under the 50 MB I2 size bar. I2 is for ambiguous potential. After these numbers the potential is low. Stage stays I1.

I3 would also need this probe applied to the repo pipeline. `self_pipeline` is `not_applicable`. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Light tells on our own docs | DESIGN.md scores 31 and a person treats that as a failed handoff | The clean band goes through 20. This run had 0 files above 40. Keep the number advisory. |
| House em dash is invisible to the score | Two em dashes change the plant by -1. TODO.md has 49 and scores 20 with flag 58 false | Keep the house rule in the agent instructions. Do not replace it with this score. |
| House ', not ' is invisible | 18 of 18 corpus files miss pattern 17 and pattern 18. The notjust plant fires pattern 17 and the score stays 17 | Same recovery. The flag is a hint. The score ignores it. |
| One invisible character dominates | zw.md jumps by 28 into mixed, while its interval runs from 13 to 45 | Read `invisible_chars` before rewriting the prose. `--clean` removed the character on this pin. |
| Short text | 18 words, confidence none, score 11 | Skip files under 120 words. The tool already says the number is noise. |
| Resample crosses a band | PENDING-HANDOFF.md is 26, and the interval is 20 to 45 | Use the point score. Two identical runs differed by 0. Do not gate on the band. |
| Paragraph monotony | The plain warehouse note scores 17 from key 44 and is still clean | A uniform note is inside the clean band. Do not chase 0. |
| Upstream drift | A later tag rescores these files | Stay on commit `38dbb7cb4e97de0b9bf157903c95bdcab016dda2` until a deliberate bump. |
| Init rewrites AGENTS.md | `/sloptrim init` writes a contract into the repo | This lane did not run it. Hooks were not installed. |

## Next gate

Stay I1. Do not wire Sloptrim into pregate, CI, or `./pfy`. Reopen only if a later pin moves the score when an em dash or a ', not ' sentence is added, and these 20 docs still have 0 files above 40. That result would still leave H1 at 0 harness comparisons. Wiring a gate is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? Nothing triggers it today. A person would have to point `detect.py` at a markdown file before a handoff. This lane did not add that call.
2. What does it do, and which services does it read and write? It reads one file and writes JSON to stdout, or scrubbed text with `--clean`. No network, no model, no account. It does not write a gate result.
3. What does it trigger next? A person reads the score. It does not start pregate, CI, or a merge.
4. Where does a human re-enter? On any file whose point score is above 40, and before anyone treats flag 58 or pattern 17 as a failure. Mark GO is required before a gate uses it.
5. What stops two runs doing the same work? The point score is deterministic on this pin (delta 0). Two lanes would still both scan the same file. One worktree per slug stays the lock. This lane did not add a second runner.

Numbers: `eval/evq1107/sloptrim/results.json`.
