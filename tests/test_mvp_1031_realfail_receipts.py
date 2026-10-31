"""Receipts under eval/mvp-1031/realfail match REPORT.md and carry no secret-like text.

A pending row has no receipt yet. A filled row must match the receipt on disk.
The planted bad receipt lives in a temp dir under the worktree tmp/ and is not committed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "eval" / "mvp-1031" / "realfail" / "REPORT.md"
SCRATCH = ROOT / "tmp" / "realfail-receipt-tests"

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
    )


def parse_report(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 11:
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
                "notes": cells[11] if len(cells) > 11 else "",
            }
        )
    return rows


def secret_hits(text: str) -> list[str]:
    hits = []
    for pattern in _secret_patterns():
        found = pattern.search(text or "")
        if found:
            hits.append(pattern.pattern)
    return hits


def evaluate(root: Path) -> list[str]:
    """Return human-readable problems. Empty means the tree agrees with its report."""
    problems = []
    report_path = root / "eval" / "mvp-1031" / "realfail" / "REPORT.md"
    if not report_path.is_file():
        return ["missing REPORT.md"]
    rows = parse_report(report_path.read_text(encoding="utf-8"))
    if not rows:
        problems.append("REPORT.md has no case rows")
    seen = set()
    for row in rows:
        case = row["case"]
        if case in seen:
            problems.append("%s listed twice" % case)
        seen.add(case)
        if row["obs_status"] == "pending":
            continue
        case_dir = root / "eval" / "mvp-1031" / "realfail" / case
        receipt_path = case_dir / "receipt.json"
        meta_path = case_dir / "meta.json"
        if not receipt_path.is_file():
            problems.append("%s missing receipt.json" % case)
            continue
        try:
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append("%s receipt is not json: %s" % (case, exc))
            continue
        if payload.get("status") != row["obs_status"]:
            problems.append(
                "%s receipt status %r != report %r"
                % (case, payload.get("status"), row["obs_status"])
            )
        if payload.get("reason") != row["obs_reason"]:
            problems.append(
                "%s receipt reason %r != report %r"
                % (case, payload.get("reason"), row["obs_reason"])
            )
        if row["verdict"] == "matches":
            if row["exp_status"] != row["obs_status"] or row["exp_reason"] != row["obs_reason"]:
                problems.append("%s verdict matches but expected and observed differ" % case)
            if row["exp_exit"] != row["obs_exit"]:
                problems.append("%s verdict matches but exits differ" % case)
        elif row["verdict"] == "FINDING":
            if not row["notes"]:
                problems.append("%s FINDING has empty notes" % case)
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
            else:
                if str(meta.get("process_exit")) != row["obs_exit"]:
                    problems.append(
                        "%s meta exit %r != report %r"
                        % (case, meta.get("process_exit"), row["obs_exit"])
                    )
        elif row["obs_exit"] != "pending":
            problems.append("%s missing meta.json" % case)
        blob_parts = []
        for extra in case_dir.rglob("*"):
            if extra.is_file():
                blob_parts.append(extra.read_text(encoding="utf-8", errors="replace"))
        blob = "\n".join(blob_parts)
        hits = secret_hits(blob)
        if hits:
            problems.append("%s secret-like text matched %s" % (case, ", ".join(hits)))
        if case == "redaction" and row["verdict"] == "matches" and "xai-FAKE0000" in blob:
            problems.append("redaction verdict matches but the planted marker is still present")
    return problems


def _write_tree(root: Path, row: str, receipt: dict, meta: dict, extra: str = "") -> None:
    base = root / "eval" / "mvp-1031" / "realfail"
    case_dir = base / "sample"
    case_dir.mkdir(parents=True)
    header = (
        "| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | "
        "Obs exit | Verdict | Attempts | Recovery | Notes |\n"
        "|------|------|------------|------------|----------|------------|------------|"
        "----------|---------|----------|----------|-------|\n"
    )
    (base / "REPORT.md").write_text(header + row + "\n", encoding="utf-8")
    (case_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    (case_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if extra:
        (case_dir / "run.log").write_text(extra, encoding="utf-8")


class RealfailReceiptTests(unittest.TestCase):
    def test_committed_report_matches_receipts_and_has_no_secrets(self) -> None:
        problems = evaluate(ROOT)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_matching_temp_receipt_is_accepted(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | - | empty | ok |",
                {
                    "status": "FAIL",
                    "reason": "interrupted",
                    "recovery": "",
                    "attempts": [],
                },
                {"process_exit": 1},
            )
            self.assertEqual(evaluate(root), [])

    def test_planted_bad_receipt_is_rejected(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        marker = "".join(SECRET_PARTS[0])
        self.assertTrue(secret_hits(marker))
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | - | - | ok |",
                {
                    "status": "PASS",
                    "reason": "ok",
                    "recovery": "",
                    "attempts": [],
                    "note": marker,
                },
                {"process_exit": 0},
                extra="bearer " + "abcdefghij",
            )
            problems = evaluate(root)
            joined = "\n".join(problems)
            self.assertIn("receipt status", joined)
            self.assertIn("secret-like", joined)
            self.assertNotEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
