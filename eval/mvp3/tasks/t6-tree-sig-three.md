# t6 content hash for the three older tree signatures

Level: slightly hard
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: examples/x-intake-local/smoke_112_114.py, examples/x-intake-local/smoke_115_116.py, examples/x-intake-local/smoke_117_118.py
Gate: python3 -m unittest tests.test_mvp2_t6_tree_sig_three
files: examples/x-intake-local/smoke_112_114.py, examples/x-intake-local/smoke_115_116.py, examples/x-intake-local/smoke_117_118.py

The acceptance test is already in the tree. Do not edit it. Do not edit any other test file. Do not commit. Do not change `smoke_119_121.py` or `smoke_122_124.py`.

`tree_sig` in these three files still hashes size and mtime, and it drops a path on `OSError`:

- examples/x-intake-local/smoke_112_114.py
- examples/x-intake-local/smoke_115_116.py
- examples/x-intake-local/smoke_117_118.py

Replace each function with the content hash already used by `tree_sig` in `examples/x-intake-local/smoke_122_124.py`, including the `:unreadable` marker and the directory marker. Keep the name `tree_sig` and return None when the path does not exist. Callers stay as they are. An mtime-only touch must not change the signature. A same-size byte change that restores mtime must change it. A file the process cannot read must be recorded, not omitted.

Gate command: `python3 -m unittest tests.test_mvp2_t6_tree_sig_three`
