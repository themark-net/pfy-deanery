#!/usr/bin/env python3
"""Exit 0 only for a pfy-cloud-build/1 PASS receipt. Otherwise exit 1.

One reason line goes to stderr. The line names a secret marker class and
does not echo the matched text. This checker does not read grok auth.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCHEMA = "pfy-cloud-build/1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
SK_RE = re.compile(r"sk_.{8,}", re.DOTALL)


def reason_for(raw: str) -> str | None:
    """Return a one-line reject reason, or None when the receipt is PASS."""
    if "AKIA" in raw:
        return "rejected: receipt text contains AKIA"
    if "BEGIN PRIVATE KEY" in raw:
        return "rejected: receipt text contains BEGIN PRIVATE KEY"
    if SK_RE.search(raw):
        return "rejected: receipt text contains sk_ secret"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "rejected: receipt is not json"
    if not isinstance(data, dict):
        return "rejected: receipt is not a json object"
    if data.get("schema") != SCHEMA:
        return "rejected: schema is not pfy-cloud-build/1"
    if data.get("status") != "PASS":
        return "rejected: status is not PASS"
    if data.get("reason") != "ok":
        return "rejected: reason is not ok"
    if type(data.get("exit_code")) is not int or data.get("exit_code") != 0:
        return "rejected: exit_code is not 0"
    branch = data.get("branch")
    if not isinstance(branch, str) or not branch.startswith("cloud/"):
        return "rejected: branch does not start with cloud/"
    commit = data.get("commit")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        return "rejected: commit is not 40 hex chars"
    review = data.get("review")
    verdict = review.get("verdict") if isinstance(review, dict) else None
    if verdict != "accept":
        return "rejected: review.verdict is not accept"
    attempts = data.get("attempts")
    if not isinstance(attempts, list) or len(attempts) == 0:
        return "rejected: attempts is empty"
    if data.get("pushed") is not False:
        return "rejected: pushed is not false"
    gate = data.get("gate")
    cmd = gate.get("cmd") if isinstance(gate, dict) else None
    if not isinstance(cmd, str) or cmd == "":
        return "rejected: gate.cmd is empty"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] == "":
        print("rejected: usage: check_receipt.py <receipt.json>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    if not path.is_file():
        print("rejected: receipt file is missing", file=sys.stderr)
        return 1
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeError:
        print("rejected: receipt is not utf-8 text", file=sys.stderr)
        return 1
    reason = reason_for(raw)
    if reason is None:
        return 0
    print(reason, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
