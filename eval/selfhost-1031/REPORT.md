# Selfhost 1031 report

Lane `mvp-selfhost-1031` on `bot/mvp-selfhost-1031`. Each item was a real `./pfy build` from this worktree against a throwaway clone under `tmp/selfhost-clones/`. Product commits were cherry-picked only when the runner gate passed, review accepted, and a careful human would keep the diff. The red behavior test was planted on this branch before the build, because the runner refuses test edits.

Exit: lane empty. Clock at stop 2026-10-31T23:06:23Z, before the 2026-11-01T04:10:12Z handoff cutoff. Host at stop: MemAvailable about 80 GiB, load about 3.3 on 32 cores.

## Counts

| | |
|---|---|
| Tried | 15 |
| Runner PASS | 14 |
| Human accept | 13 |
| Human or review reject | 2 (items 03 and 08) |
| Median wall of the 13 accepts | 119 seconds |

Accepted walls, seconds: 129, 435, 330, 296, 88, 89, 119, 114, 119, 262, 110, 116, 602.

## Cherry-picked

| n | SHA | Subject |
|---|---|---|
| 01 | 00dbdd9 | Refuse a relative PFY_SMOKE_RECEIPT_DIR in smoke.write |
| 02 | 89d34af | Record file mode in smoke_122_124.tree_sig |
| 04 | ff86c4d | Record symlink readlink in smoke_122_124.tree_sig and still hash bytes |
| 05 | f8fcac9 | Record a symlinked root in smoke_122_124.tree_sig |
| 06 | 4b01771 | Correct the home_sig docstring |
| 07 | c6f0cbd | Port the 122 signature to smoke_119_121.tree_sig |
| 09 | 90c9037 | Port the 122 signature to smoke_115_116.tree_sig |
| 10 | b9b8898 | Port the 122 signature to smoke_117_118.tree_sig |
| 11 | 828063b | Port the 122 signature to smoke_112_114.tree_sig |
| 12 | 15fbf71 | Fail overtime when daemon stop times out and no lock remains |
| 13 | a663854 | Refuse a relative PFY_SMOKE_RECEIPT_DIR in smoke_148 |
| 14 | b06e41a | Refuse a relative PFY_SMOKE_RECEIPT_DIR in smoke_149 |
| 15 | f2f43f9 | Record bytes, mode, mtime, and readlink in smoke_148.home_sig |

Each of those commits carries `Built-by: ./pfy build (cloud) receipt eval/selfhost-1031/<n>-<slug>/receipt.json`. Receipts are the redacted runner files. Per-item commands, attempts, and notes are in `eval/selfhost-1031/LOG.md`.

## Not kept

| n | Runner | Human | Why |
|---|---|---|---|
| 03 | PASS, review accept | reject | The diff recorded readlink and replaced the content hash of any regular file a symlink names with a `:target` marker. A real-HOME snapshot must still see those content edits. The planted test had required the skip. Receipt kept at `eval/selfhost-1031/03-tree-sig-symlink/receipt.json`. Not cherry-picked. |
| 08 | FAIL, review reject | reject | `smolvm_image_evidence` was asked to prefer a same-image stderr pull over a stdout cache line. `test_h_oci_cache_stdout_branch` feeds that stub a pull progress sequence and a cache line and expects the cache line. Attempts 1 and 3 passed the gate only by narrowing what counts as a pull. Review rejected both. Attempt 2 implemented the pull rule and failed `test_h`. The runner cannot edit tests. Receipt at `eval/selfhost-1031/08-smolvm-stderr/receipt.json`. |

## Findings for lane mvp-cloudfix-1031

1. Review accepted item 03. A symlink record that stores readlink must not drop the content hash of an in-tree regular file the link names. The planted oracle was wrong, and review did not catch the lost content hash.
2. The cloud runner marks any new or edited file under `tests/` as tests-tampered, and it has no `--writable-test` flag. The local runner does. Item 08 could not update `test_h`, and a faithful pull-wins diff failed that test. Review correctly rejected the special cases that tried to satisfy both tests. The two tests encode opposite priorities: a same-image stderr pull should win, and the OCI cache stub expects the stdout cache line whenever it also prints pull progress. Do not add the flag from this lane. `scripts/pfy_build_cloud.py` is owned by the cloud lane.
3. Item 08 should not be retried until one of those tests is the contract. A second run with the same pair of gates will fail the same way.

## Also left for other lanes

- dogfood2 was driving the overtime and festival timeout-label task in `smoke_112_114.py` (MVP-2 t4) while this lane landed the daemon-stop exit (`15fbf71`) and the 112 tree signature (`828063b`). t4 is still open on this branch. Leave the label change to that lane so two clouds do not edit the same strings.
- MVP-2 t5 (117 and 119 tests must pass without writing `pipelines/smoke`) contradicts those tests, which read the repo receipt. Fixing it means editing tests. That is tests-tampered on the cloud runner.
- `smoke_149.home_sig` is still size and mtime only. Watched paths include `.cache/chroma`. A content hash there can read an embedding cache on every smoke. Not ported.
- `smoke_109_111.state_snapshot` is still newest mtime. Watched paths include smolvm and runx caches. Not ported.
- `examples/harness2-local/common.py` skips file bodies on trees over 32 MiB by decision D1. Not reopened.
