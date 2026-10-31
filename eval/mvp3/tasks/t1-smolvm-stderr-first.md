# t1 smolvm stderr pull wins

Level: trivial
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: examples/x-intake-local/smoke_109_111.py
Gate: python3 -m unittest tests.test_mvp2_t1_smolvm_evidence
files: examples/x-intake-local/smoke_109_111.py

The acceptance test is already in the tree. Do not edit it. Do not edit any other test file. Do not commit.

`smolvm_image_evidence` in `examples/x-intake-local/smoke_109_111.py` currently returns a stdout `Caching image` / `Using cached image` line before it looks at stderr. When both are present, the stderr `Pulling image <image>` line must win. When stderr has no pull line, a stdout cache line is still the evidence, so the existing cache-only behavior stays.

Update the comment at the top of that function's smoke section so it matches this rule. Touch no other file.

Gate command: `python3 -m unittest tests.test_mvp2_t1_smolvm_evidence`
