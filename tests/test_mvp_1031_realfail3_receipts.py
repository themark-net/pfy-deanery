"""Receipts under eval/mvp-1031/realfail3 match REPORT.md and carry no secret-like text.

A partial report may omit cases. `Rows: complete` requires all nine.
A FINDING row must have notes and a FINDING.md that names a suggested fix.
The planted bad receipt lives under the worktree tmp/ and is not committed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "eval" / "mvp-1031" / "realfail3" / "REPORT.md"
SCRATCH = ROOT / "tmp" / "realfail3-receipt-tests"
REQUIRED = (
    "detached-head",
    "dirty-tree",
    "gate-hang",
    "network-down",
    "no-tests",
    "non-ascii",
    "over-cap",
    "tmp-unwritable",
    "two-builds",
)

SECRET_PARTS = (
    ("AKIA", "0000000000000000"),
    ("-----BEGIN ", "PRIVATE KEY-----"),
    ("bearer ", "abcdefghij"),
    ("sk_", "abcdefgh"),
)


def _secret_patterns():
    import re

    return (
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"BEGIN PRIVATE KEY"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
        re.compile(r"(?i)\b(?:sk|ghp)_[A-Za-z0-9_\-]{8,}"),
        re.compile(r"\bxai-[A-Za-z0-9]{6,}\b"),
    )


def parse_report(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 12:
            continue
        if cells[0] in {"Case", "case"}:
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(
            {
                "case": cells[0],
                "mode": cells[1],
                "exp_status": cells[2],
                "exp_reason": cells[3],
                "exp_exit": cells[4],
                "obs_status": cells[5],
                "obs_reason": cells[6],
                "obs_exit": cells[7],
                "verdict": cells[8],
                "attempts": cells[9],
                "recovery": cells[10],
                "notes": cells[11],
            }
        )
    return rows


def secret_hits(text: str) -> list[str]:
    hits = []
    for pattern in _secret_patterns():
        if pattern.search(text or ""):
            hits.append(pattern.pattern)
    return hits


def evaluate(root: Path) -> list[str]:
    """Return human-readable problems. Empty means the tree agrees with its report."""
    problems = []
    report_path = root / "eval" / "mvp-1031" / "realfail3" / "REPORT.md"
    if not report_path.is_file():
        return ["missing REPORT.md"]
    text = report_path.read_text(encoding="utf-8")
    if "Rows: partial" not in text and "Rows: complete" not in text:
        problems.append("report missing Rows marker")
    rows = parse_report(text)
    complete = "Rows: complete" in text
    seen = set()
    if complete:
        missing = [name for name in REQUIRED if name not in {row["case"] for row in rows}]
        if missing:
            problems.append("complete report missing %s" % ", ".join(missing))
        if any(row["obs_status"] == "pending" for row in rows):
            problems.append("complete report still has a pending row")
    for row in rows:
        case = row["case"]
        if case in seen:
            problems.append("%s listed twice" % case)
        seen.add(case)
        if row["obs_status"] == "pending":
            continue
        case_dir = root / "eval" / "mvp-1031" / "realfail3" / case
        receipt_path = case_dir / "receipt.json"
        meta_path = case_dir / "meta.json"
        if row["obs_status"] != "none" and not receipt_path.is_file():
            problems.append("%s missing receipt.json" % case)
            continue
        payload = {}
        if receipt_path.is_file():
            try:
                payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append("%s receipt is not json: %s" % (case, exc))
                continue
            if payload.get("status") != row["obs_status"]:
                problems.append(
                    "%s receipt status %r != report %r" % (case, payload.get("status"), row["obs_status"])
                )
            if payload.get("reason") != row["obs_reason"]:
                problems.append(
                    "%s receipt reason %r != report %r" % (case, payload.get("reason"), row["obs_reason"])
                )
        if row["verdict"] == "matches":
            if row["exp_status"] != row["obs_status"] or row["exp_reason"] != row["obs_reason"]:
                problems.append("%s verdict matches but expected and observed differ" % case)
            if row["exp_exit"] != row["obs_exit"]:
                problems.append("%s verdict matches but exits differ" % case)
        elif row["verdict"] == "FINDING":
            if not row["notes"]:
                problems.append("%s FINDING has empty notes" % case)
            finding = case_dir / "FINDING.md"
            if not finding.is_file():
                problems.append("%s FINDING missing FINDING.md" % case)
            elif "Suggested fix" not in finding.read_text(encoding="utf-8"):
                problems.append("%s FINDING.md has no suggested fix" % case)
        else:
            problems.append("%s verdict %r is not matches or FINDING" % (case, row["verdict"]))
        if row["attempts"] not in {"-", ""}:
            try:
                want = int(row["attempts"])
            except ValueError:
                problems.append("%s attempts cell is not an integer" % case)
            else:
                got = payload.get("attempts")
                if not isinstance(got, list) or len(got) != want:
                    problems.append("%s attempts length %r != %s" % (case, got, want))
        if row["recovery"] not in {"-", ""}:
            recovery = payload.get("recovery")
            if row["recovery"] == "empty":
                if recovery != "":
                    problems.append("%s recovery is not empty: %r" % (case, recovery))
            elif not isinstance(recovery, str) or row["recovery"] not in recovery:
                problems.append("%s recovery missing %r" % (case, row["recovery"]))
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append("%s meta is not json: %s" % (case, exc))
                meta = {}
            else:
                if str(meta.get("process_exit")) != row["obs_exit"]:
                    problems.append(
                        "%s meta exit %r != report %r" % (case, meta.get("process_exit"), row["obs_exit"])
                    )
                if row["verdict"] == "matches" and meta.get("invariant_problems"):
                    problems.append("%s matches but meta lists invariant problems" % case)
        elif row["obs_exit"] != "pending":
            problems.append("%s missing meta.json" % case)
        if case == "non-ascii" and row["verdict"] == "matches" and "café" not in str(payload.get("task") or ""):
            problems.append("non-ascii verdict matches but the receipt task dropped the non-ASCII text")
        blob_parts = []
        if case_dir.is_dir():
            for extra in case_dir.rglob("*"):
                if extra.is_file():
                    blob_parts.append(extra.read_text(encoding="utf-8", errors="replace"))
        hits = secret_hits("\n".join(blob_parts))
        if hits:
            problems.append("%s secret-like text matched %s" % (case, ", ".join(hits)))
    base = root / "eval" / "mvp-1031" / "realfail3"
    if base.is_dir():
        for child in base.iterdir():
            if child.is_dir() and (child / "receipt.json").is_file() and child.name not in seen:
                problems.append("%s has a receipt and no report row" % child.name)
    return problems


def _write_tree(root: Path, row: str, receipt: dict | None, meta: dict, finding: str = "") -> None:
    base = root / "eval" / "mvp-1031" / "realfail3"
    case_dir = base / "sample"
    case_dir.mkdir(parents=True)
    header = (
        "Rows: partial\n"
        "| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | "
        "Obs exit | Verdict | Attempts | Recovery | Notes |\n"
        "|------|------|------------|------------|----------|------------|------------|"
        "----------|---------|----------|----------|-------|\n"
    )
    (base / "REPORT.md").write_text(header + row + "\n", encoding="utf-8")
    if receipt is not None:
        (case_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    (case_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if finding:
        (case_dir / "FINDING.md").write_text(finding, encoding="utf-8")


class Realfail3ReceiptTests(unittest.TestCase):
    def test_committed_report_matches_receipts_and_has_no_secrets(self) -> None:
        problems = evaluate(ROOT)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_matching_temp_receipt_is_accepted(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | tests | 1 | FAIL | tests | 1 | matches | 1 | empty | gate stayed red |",
                {"status": "FAIL", "reason": "tests", "recovery": "", "attempts": [{}]},
                {"process_exit": 1, "invariant_problems": []},
            )
            self.assertEqual(evaluate(root), [])

    def test_planted_status_mismatch_is_rejected(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | tests | 1 | FAIL | tests | 1 | matches | 1 | empty | ok |",
                {"status": "PASS", "reason": "ok", "recovery": "", "attempts": [{}]},
                {"process_exit": 1, "invariant_problems": []},
            )
            problems = evaluate(root)
            self.assertTrue(any("status" in item for item in problems), problems)

    def test_finding_without_a_suggested_fix_is_rejected(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | worktree-failed | 1 | FAIL | runner-crash | 1 | FINDING | 1 | empty | mkdir raised |",
                {"status": "FAIL", "reason": "runner-crash", "recovery": "", "attempts": [{}]},
                {"process_exit": 1, "invariant_problems": ["mkdir raised"]},
            )
            problems = evaluate(root)
            self.assertTrue(any("FINDING.md" in item for item in problems), problems)

    def test_finding_with_a_suggested_fix_is_accepted(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | worktree-failed | 1 | FAIL | runner-crash | 1 | FINDING | 1 | empty | mkdir raised |",
                {"status": "FAIL", "reason": "runner-crash", "recovery": "", "attempts": [{}]},
                {"process_exit": 1, "invariant_problems": ["mkdir raised"]},
                finding="# FINDING\n\nSuggested fix: return worktree-failed when tmp cannot be created.\n",
            )
            self.assertEqual(evaluate(root), [])

    def test_planted_secret_is_rejected(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        marker = "".join(SECRET_PARTS[0])
        self.assertTrue(secret_hits(marker))
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | tests | 1 | FAIL | tests | 1 | matches | 0 | empty | ok |",
                {"status": "FAIL", "reason": "tests", "recovery": "", "attempts": [], "note": marker},
                {"process_exit": 1, "invariant_problems": []},
            )
            problems = evaluate(root)
            self.assertTrue(any("secret" in item for item in problems), problems)
