# Handoff mvp-selfhost-1031

Branch `bot/mvp-selfhost-1031`. Worktree `tmp/mvp-selfhost-1031`. Base `origin/bot/mvp-cloud-1031`. Not merged. No PR. No tag.

Exit: lane empty at 2026-10-31T23:06:23Z. Thirteen human-accepted `./pfy build` cherry-picks are on the branch. Two builds were not kept. The wall cap (stop new items 2026-11-01T04:10:12Z) had not fired. Host pressure had not fired. Pregate was not run: host busy (`Runner.Worker` was present, and another pregate was already running).

Gate for this branch: Tester plus Reviewer. The commits change runtime smoke behavior. This lane does not request the gate and does not merge.

## Items done

| Item | Product SHA | What a careful read kept |
|---|---|---|
| Relative receipt dir in `smoke.write` | `00dbdd9` | Non-empty relative `PFY_SMOKE_RECEIPT_DIR` returns 1, writes nothing, prints a line containing "absolute". Absolute still writes. Unset keeps `pipelines/smoke`. |
| `smoke_122_124.tree_sig` mode | `89d34af` | chmod changes the signature. mtime-only does not. Same-size bytes do. |
| `smoke_122_124.tree_sig` symlink entries | `ff86c4d` | Retarget changes the signature. In-tree file bytes still do. An outside target does not. |
| `smoke_122_124.tree_sig` symlinked root | `f8fcac9` | Retarget of the path itself changes the signature. Entries under it are still hashed. A missing path is still None. |
| `home_sig` docstring | `4b01771` | The docstring no longer says `tree_sig` was left as is. No executable line changed. |
| `smoke_119_121.tree_sig` | `c6f0cbd` | Same signature as 122. |
| `smoke_115_116.tree_sig` | `90c9037` | Same signature as 122. |
| `smoke_117_118.tree_sig` | `b9b8898` | Same signature as 122. |
| `smoke_112_114.tree_sig` | `828063b` | Same signature as 122. Daemon-stop and timeout text were not in that diff. |
| Overtime daemon-stop timeout | `15fbf71` | A stop timeout with no live lock returns 1 and reuses `timeout_reason("overtime daemon stop", ...)`. A live lock still fails as daemon still running. A clean stop still passes. |
| `smoke_148` relative receipt dir | `a663854` | Same refuse rule as `smoke.write`. Absolute still writes `latest.json`. |
| `smoke_149` relative receipt dir | `b06e41a` | Same refuse rule. Absolute still writes `latest.json`. |
| `smoke_148.home_sig` | `f2f43f9` | Files keep mode, mtime, size, and a streamed sha256. Symlinks keep readlink and are not opened. A missing path stays None. An unreadable file does not raise. |

Each product SHA has trailer `Built-by: ./pfy build (cloud) receipt eval/selfhost-1031/<n>-<slug>/receipt.json`. The red tests landed in the parent commits of those cherry-picks. Receipts and the row log are under `eval/selfhost-1031/`. Summary counts are in `eval/selfhost-1031/REPORT.md`.

## How a failure shows, and how it recovers

- Relative receipt dir: a relative value returns 1 and leaves the cwd and the repo receipt untouched. An absolute directory still receives `latest.json` (or `entry/latest.json` from `smoke.write`) and returns the caller's code. Unset or empty still uses `pipelines/smoke`.
- Tree signature: an mtime-only touch does not change it. A same-size byte change, a chmod, a symlink retarget, and a symlinked-root retarget do. Editing a file outside the tree through a symlink does not. A missing path returns None. An unreadable file is recorded, not dropped.
- `home_sig` docstring: the old "left as is" sentence is gone. An mtime-only touch still changes `home_sig` and still does not change `tree_sig`.
- Daemon stop: the step still stores `overtime daemon stop timeout after 0.4s`. With no live `overtimed.lock`, the process now exits 1 with that reason instead of the success sentence. A live lock still exits 1 with `daemon still running after daemon stop`. A clean stop with no live lock still exits 0.
- `smoke_148.home_sig`: an mtime-only touch still changes the signature. A same-size edit that restores mtime now does too. chmod and a symlink retarget do. An outside target edit does not. chmod 0 does not raise. A new `~/.skillspector` directory still fails the real-HOME check (`test_real_home_write_fails`).

## Skipped

Up front, before any build: voice, local TTS, Pipecat catalog, new scorer, local eval-auto, OpenCode-in-cage, EBUSY, write-guard wiring, Laguna, AgenC re-evaluation, aggregate synthesis, colibri lab, integration-stage promotion, the OpenCode attach fold, and the pfy-build operator card. Reasons are in the run log. Those need Mark, a local model, hardware, a catalog edit, or another lane's files.

After the builds, still not taken:

- MVP-2 t1 (`smolvm_image_evidence`): item 08. The pull-wins rule and `test_h` disagree. Not retried.
- MVP-2 t4 timeout labels in `smoke_112_114.py`: dogfood2 was already running that cloud build. Left there.
- MVP-2 t5 repo receipts: the 117 and 119 tests read `pipelines/smoke`. A fix that moves the receipt has to edit those tests. The cloud runner will not commit a test edit.
- `smoke_149.home_sig` and `smoke_109_111.state_snapshot`: same content-blind shape as the 148 fix, but the watched trees include `.cache/chroma` and smolvm or runx caches. A full content hash on those paths can read large caches. Not ported.
- `examples/harness2-local/common.py`: large trees skip file bodies by decision D1.
- HarnessRouter happy path: the handoff says to treat the first Docker run as the test. Not a small planted edit.

## Test evidence

Targeted modules only, `nice -n 19 python3 -m unittest ...`. Each accept line in `docs/ops/RUN-LOG-mvp-selfhost-1031.md` names the modules and the OK count. The Built-by checker (`tests.test_selfhost_1031_log`) was in those runs and stayed green. No full `unittest discover`. No `make eval-*`.

## Cross-lane requests

For `mvp-cloudfix-1031`, the three findings in `eval/selfhost-1031/REPORT.md`: the `:target` review miss, the missing cloud `--writable-test` (do not edit `scripts/pfy_build_cloud.py` from this lane), and the t1 test contradiction. For integrate: dogfood2 may also land a daemon-stop diff; this branch already has `15fbf71`.

## Next step

Tester plus Reviewer on this branch tip. Do not merge from this lane. The next small smoke gap that is safe to build is a bounded content fingerprint for `smoke_149.home_sig` that does not read `.cache/chroma` bodies, and that needs a size cap written down before anyone implements it.
