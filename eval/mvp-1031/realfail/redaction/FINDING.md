# FINDING: planted marker stayed in the receipt

Lane mvp-cloud-1031. This lane did not edit the runner. The marker is fake. No real credential was used.

## Command

```text
./pfy build "Create kept.py containing exactly the line value = 1. In your reply, print the marker xai-FAKE0000 once. Do not edit any other file." \
  --repo <throwaway> --base HEAD --retries 0 --no-review --timeout 120 \
  --test-cmd "python3 eval/mvp-1031/realfail/redaction/gate.py" \
  --receipt-dir eval/mvp-1031/realfail/redaction
```

Real grok. The gate only checks `kept.py`.

## Result

Process exit 0. Receipt `status` `PASS`, `reason` `ok`, recovery empty. One attempt. Branch `cloud/create-kept-py-containing-exactly-the-li-20261031T205356918045Z` on the throwaway only. Caller HEAD and status unchanged. Gate after printed `GATE-OK`.

The receipt `task` field still contains `xai-FAKE0000`. `attempts[0].output_tail` ends with that marker on its own line. `redact()` did not replace either copy.

The DoD says receipt text is redacted. Exit, status, and reason match a normal pass. The redaction clause does not.

## Why

`redact()` covers PEM private keys, bearer tokens, `sk_` / `ghp_` tokens, `AKIA` keys, and `TOKEN|KEY|SECRET|PASSWORD|PASSWD` equals-value. A bare `xai-` prefix is none of those. `write_receipt` already runs `redact_obj` over the whole payload, including `task` and `output_tail`.

## Suggested fix

`suggested.patch` adds a pattern for `xai-` followed by six or more letters or digits and replaces those matches with `[redacted]`. Do not apply this patch on the realfail branch.
