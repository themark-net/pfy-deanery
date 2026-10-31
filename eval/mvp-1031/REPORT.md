# mvp-1031 integrate demo

One real cloud `./pfy build` from the integrate worktree. No `--local`. The task target was a temp fixture repo, not this checkout.

Command:

```text
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
```

The fixture test was red before the build (`add(2, 3)` returned 0).

| Field | Value |
|-------|--------|
| Exit code | 0 |
| Branch | `cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z` |
| Commit | `ebef4238a7eff8f938747623f7920b3fde74e586` |
| Review verdict | accept |
| Receipt path | `eval/mvp-1031/demo-receipt.json` |
| Checker | `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json` exit 0 |

Demo: PASS.

`git -C` the fixture repo shows that `cloud/` branch at the receipt commit. `add` on that commit returns `a + b`, and `python3 -m unittest test_add` passes on that tree. `pushed` is false. The integrate branch stayed `bot/mvp-integrate-1031`.
