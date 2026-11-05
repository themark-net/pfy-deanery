# t2 content hash for the 119 tree signature

Level: trivial
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: examples/x-intake-local/smoke_119_121.py
Gate: python3 -m unittest tests.test_mvp2_t2_tree_sig_119
files: examples/x-intake-local/smoke_119_121.py

The acceptance test is already in the tree. Do not edit it. Do not edit any other test file. Do not commit.

`tree_sig` in `examples/x-intake-local/smoke_119_121.py` still hashes size and mtime. Replace that function with the content hash already used by `tree_sig` in `examples/x-intake-local/smoke_122_124.py`, including the unreadable marker. Same function name and None for a missing path. Do not change the other smoke files. An unchanged tree, including an mtime-only touch, must keep the same signature. A same-size byte change that restores mtime must change it.

Gate command: `python3 -m unittest tests.test_mvp2_t2_tree_sig_119`
