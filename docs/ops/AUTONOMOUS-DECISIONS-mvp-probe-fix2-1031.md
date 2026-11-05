# Autonomous decisions mvp-probe-fix2-1031

1. Choice: treat `repo-handoff-doc-required` and `write-loop-exits-first` as the drop-in states them (exit card in the run log before probe work, handoff on every exit). Alternatives: block until those skill files appear. Why: no SKILL.md with either name is in this checkout or `~/.grok/skills`. `prefer-behavior-and-fail-recover-tests` and `agent-loops` are present and are followed.

2. Choice: the five parenthetical variants are the new probe families (hardlink, symlink to a directory, rename plus edit, NFC vs NFD, gate mode bits), each aimed at the blocker it extends, with a few neighbor cases so a single happy path cannot hide a miss. Alternatives: a full 5x5 matrix, or only the five names with no neighbors. Why: the parenthetical lists five families; neighbors stay inside the same blocker and still finish inside the wall cap.

3. Choice: scratch repos and TMPDIR stay under this worktree `tmp/`. Hardlink targets live in the stub-notes directory the test seam already bind-mounts, so the probe does not need the host `/tmp`. Alternatives: put sentinels in `/tmp`. Why: the drop-in forbids `/tmp`.

4. Choice: a probe is a FINDING only when the tip commits bytes or a mode the reviewer did not see, leaks sentinel bytes into a receipt or review prompt, mangles a name, or accepts a review body that should fail closed. A fail-closed result is a hold. Alternatives: treat every non-PASS as a bug. Why: S7's old bug was a false fail, so a legitimate rename or unicode path that still fails closed is also a FINDING. Speculative policy beyond those two shapes waits for a probe result.

5. Choice: treat bx1-mode-set-x and bx1-mode-clear-x as one finding. The digest gains the git executable bit only when core.filemode is on. Alternatives: hash the full unix mode, or ignore mode. Why: git stores 100644 or 100755. A 0600 tweak stays 100644 and must still commit. The probe bx1-mode-0600 passed faithfully.

6. Choice: s7-rename-low-similarity is a hold. Alternatives: treat the judge flag as a bug. Why: the commit was A new / D old / M calc and the review prompt contained EDITED_RENAME_LINE. The judge only kept the last 180 bytes of the blob, so it missed the marker at the top.

7. Choice: s8-nfc-and-nfd-both is a hold on this host. Alternatives: teach the loop to commit two unicode names. Why: the dataset normalization is formD (`zfs get normalization` on rpool/USERDATA/home_wgyfpj). NFC and NFD are the same directory entry, so the worktree cannot hold both. Single NFC and single NFD each committed under the bytes git stored.

8. Choice: refuse a commit when a changed regular file has more hard links than names inside the worktree. Strip those hunks, record the marker `hardlink-outside`, and do not retry. Alternatives: hash the outside path into the digest, or reject only when the path is off the allow list. Why: the blob is the host file's bytes in both the in-scope and out-of-scope probes at d2521b5, and the out-of-scope probe still left those bytes in `patch.diff`. Two names that both live in the worktree still commit. The behavior test hides bwrap, because a working bwrap returns EXDEV for a link that crosses the worktree bind.
