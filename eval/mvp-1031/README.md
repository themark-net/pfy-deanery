# mvp-1031 fixture and receipt check

Integration runs the demo below from the repo root. This lane does not run it and does not call grok.

```text
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
python3 eval/mvp-1031/check_receipt.py "$PWD/tmp/mvp-fixture-receipt/receipt.json"
```

`bash eval/mvp-1031/init_fixture.sh` writes a git repo on branch `main`. The committed `add` does not return the sum, so `python3 -m unittest test_add` fails in that repo until a later edit returns `a + b`.

`python3 eval/mvp-1031/check_receipt.py` exits 0 only for a PASS receipt with schema `pfy-cloud-build/1`. Any other receipt exits 1 and prints one reason on stderr. A receipt whose text contains `AKIA`, `BEGIN PRIVATE KEY`, or `sk_` plus eight characters is rejected.

The fixture repo and the receipt directory stay under `tmp/`. Integration copies a keeper receipt to `eval/mvp-1031/demo-receipt.json` and writes `eval/mvp-1031/REPORT.md`. This lane does not write those two files.
