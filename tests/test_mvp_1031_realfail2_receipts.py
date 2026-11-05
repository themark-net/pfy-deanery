"""Receipts under eval/mvp-1031/realfail2 match REPORT.md and carry no secret-like text.

A pending row has no receipt yet. A row whose observed status is none means the
runner wrote no receipt.json. A filled row must match the receipt on disk.
Case meta pins the fail/recover facts (a live grok after reap, a leaked marker
on a matches row, a dirty caller). The planted bad receipt lives in a temp dir
under the worktree tmp/ and is not committed.

How this fails: a receipt status that drifts from the report, a secret-like
string in a case dir, or a matches row whose meta contradicts the DoD.
How we recover: fix the runner in mvp-cloudfix-1031 or correct the row to
FINDING with notes. Do not strip a real mismatch to force a green test.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "eval" / "mvp-1031" / "realfail2" / "REPORT.md"
SCRATCH = ROOT / "tmp" / "realfail2-receipt-tests"

SECRET_PARTS = (
    ("AKIA", "0000000000000000"),
    ("-----BEGIN ", "PRIVATE KEY-----"),
    ("bearer ", "abcdefghij"),
    ("sk_", "abcdefgh"),
    ("xai-", "FAKE0000"),
)


def _secret_patterns():
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


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return exc


def _case_rule(row: dict, meta: dict, receipt: dict | None, blob: str) -> list[str]:
    """Extra fail/recover checks. Empty means the row's own facts hold."""
    case = row["case"]
    problems = []
    if case == "sigkill-reap" and row["verdict"] == "matches":
        if meta.get("reap_exit") != 0:
            problems.append("sigkill-reap reap_exit is not 0")
        if meta.get("grok_alive_after_reap") is not False:
            problems.append("sigkill-reap matches but grok was alive after reap")
        if meta.get("sleeper_alive_after_reap") is not True:
            problems.append("sigkill-reap matches but reap killed the planted sleeper")
        if meta.get("caller_unchanged") is not True:
            problems.append("sigkill-reap caller changed")
        if meta.get("cloud_branch_count") != 0:
            problems.append("sigkill-reap left a cloud branch")
    if case == "review-reject" and row["verdict"] == "matches":
        if not receipt or receipt.get("commit") is not None or receipt.get("branch") is not None:
            problems.append("review-reject matches but a commit or branch exists")
        if meta.get("danger_in_commit") is not False:
            problems.append("review-reject danger file was committed")
    if case == "auth-failure" and row["verdict"] == "matches":
        recovery = "" if not receipt else str(receipt.get("recovery") or "")
        if "run grok once to log in" not in recovery:
            problems.append("auth-failure recovery does not name grok login")
        if meta.get("auth_read") is not False:
            problems.append("auth-failure read a credential file")
        if meta.get("caller_unchanged") is not True:
            problems.append("auth-failure caller changed")
    if case == "redaction" and row["verdict"] == "matches":
        if meta.get("marker_in_receipt") is not False:
            problems.append("redaction matches but meta says the marker is in the receipt")
        if receipt and "[redacted]" not in json.dumps(receipt):
            problems.append("redaction matches but the receipt has no redaction token")
    if case == "review-retry-accept" and row["verdict"] == "matches":
        attempts = [] if not receipt else receipt.get("attempts") or []
        if len(attempts) != 2:
            problems.append("review-retry-accept attempts length is not 2")
        elif attempts[0].get("reason") != "review-rejected" or attempts[-1].get("status") != "PASS":
            problems.append("review-retry-accept did not reject then pass")
        if not receipt or not receipt.get("commit"):
            problems.append("review-retry-accept has no commit")
        if meta.get("danger_in_commit") is not False or meta.get("kept_in_commit") is not True:
            problems.append("review-retry-accept commit contents are wrong")
    if case == "scope-commit-mismatch" and row["verdict"] == "matches":
        if meta.get("index_clean") is not True:
            problems.append("scope-commit-mismatch index was not reset")
        if meta.get("caller_unchanged") is not True or meta.get("cloud_branch_count") != 0:
            problems.append("scope-commit-mismatch moved the caller or left a branch")
    if case == "worktree-failed":
        if meta.get("caller_unchanged") is not True:
            problems.append("worktree-failed changed the caller")
        if row["verdict"] == "matches":
            if str(meta.get("process_exit")) != "1":
                problems.append("worktree-failed matches but exit is not 1")
            if not receipt or receipt.get("reason") != "worktree-failed":
                problems.append("worktree-failed matches without that reason")
    if case == "dry-run" and row["verdict"] == "matches":
        if meta.get("grok_calls") != 0:
            problems.append("dry-run started grok")
        if meta.get("cloud_branch_count") != 0:
            problems.append("dry-run created a branch")
        if not receipt or receipt.get("status") != "DRY-RUN" or receipt.get("commit") is not None:
            problems.append("dry-run receipt is not a clean DRY-RUN")
    if case == "usage" and row["verdict"] == "matches":
        if meta.get("saw_daily") is not True or meta.get("saw_p") is not True or meta.get("saw_local") is not True:
            problems.append("usage text missed the daily command or a pointer")
        if str(meta.get("process_exit")) != "2":
            problems.append("usage exit is not 2")
    if case == "dogfood-p" and row["verdict"] == "matches":
        if meta.get("help_exit") != 0 or meta.get("help_mentions_prompt") is not True:
            problems.append("dogfood help did not show the -p path")
        if meta.get("run_exit") != 0 or meta.get("hello") is not True:
            problems.append("dogfood real -p run did not write hello.txt")
    if case == "keep-worktree" and row["verdict"] == "matches":
        if not receipt or receipt.get("worktree_removed") is not False:
            problems.append("keep-worktree receipt does not record the kept tree")
        if meta.get("worktree_still_present") is not True:
            problems.append("keep-worktree directory is gone")
    if case == "worktree-default" and row["verdict"] == "matches":
        if not receipt or receipt.get("worktree_removed") is not True:
            problems.append("worktree-default receipt says the tree was kept")
        if meta.get("worktree_still_present") is not False:
            problems.append("worktree-default left the directory on disk")
    if case == "protected-paths" and row["verdict"] == "matches":
        if meta.get("auth_in_any_commit") is not False or meta.get("env_in_any_commit") is not False:
            problems.append("protected path was committed")
        if not receipt or receipt.get("commit") is not None:
            problems.append("protected-paths left a commit")
    if case == "concurrent" and row["verdict"] == "matches":
        if meta.get("repo_intact") is not True or meta.get("caller_unchanged") is not True:
            problems.append("concurrent run damaged the repo or moved HEAD")
        if meta.get("outcome") not in {"distinct-branches", "clean-refusal", "mixed-intact"}:
            problems.append("concurrent outcome %r is not an allowed result" % meta.get("outcome"))
    if case == "review-cap" and row["verdict"] == "matches":
        if meta.get("files_in_commit") != 4 or meta.get("cap_blocked") is not False:
            problems.append("review-cap matches without four committed files")
        if meta.get("recovery_usable") not in {"yes", "not-needed"}:
            problems.append("review-cap recovery was not usable and was not unneeded")
    if row["verdict"] == "FINDING" and case == "review-cap":
        if "recovery_usable" not in meta:
            problems.append("review-cap FINDING does not say whether recovery was usable")
    if case == "redaction" and row["verdict"] == "matches" and re.search(r"\bxai-[A-Za-z0-9]{6,}\b", blob):
        problems.append("redaction verdict matches but the planted marker is still present")
    return problems


def evaluate(root: Path) -> list[str]:
    """Return human-readable problems. Empty means the tree agrees with its report."""
    problems = []
    report_path = root / "eval" / "mvp-1031" / "realfail2" / "REPORT.md"
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
        case_dir = root / "eval" / "mvp-1031" / "realfail2" / case
        receipt_path = case_dir / "receipt.json"
        meta_path = case_dir / "meta.json"
        if row["obs_status"] == "none":
            if receipt_path.is_file():
                problems.append("%s says no receipt but receipt.json exists" % case)
            receipt = None
        elif not receipt_path.is_file():
            problems.append("%s missing receipt.json" % case)
            continue
        else:
            loaded = _load(receipt_path)
            if isinstance(loaded, json.JSONDecodeError):
                problems.append("%s receipt is not json: %s" % (case, loaded))
                continue
            receipt = loaded
            if receipt.get("status") != row["obs_status"]:
                problems.append(
                    "%s receipt status %r != report %r" % (case, receipt.get("status"), row["obs_status"])
                )
            if receipt.get("reason") != row["obs_reason"]:
                problems.append(
                    "%s receipt reason %r != report %r" % (case, receipt.get("reason"), row["obs_reason"])
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
        if receipt is not None and row["attempts"] not in {"-", ""}:
            try:
                want = int(row["attempts"])
            except ValueError:
                problems.append("%s attempts cell is not an integer" % case)
            else:
                got = receipt.get("attempts")
                if not isinstance(got, list) or len(got) != want:
                    problems.append("%s attempts length %r != %s" % (case, got, want))
        if receipt is not None and row["recovery"] not in {"-", ""}:
            recovery = receipt.get("recovery")
            if row["recovery"] == "empty":
                if recovery != "":
                    problems.append("%s recovery is not empty: %r" % (case, recovery))
            elif not isinstance(recovery, str) or row["recovery"] not in recovery:
                problems.append("%s recovery missing %r" % (case, row["recovery"]))
        if not meta_path.is_file():
            problems.append("%s missing meta.json" % case)
            continue
        loaded_meta = _load(meta_path)
        if isinstance(loaded_meta, json.JSONDecodeError):
            problems.append("%s meta is not json: %s" % (case, loaded_meta))
            continue
        meta = loaded_meta
        if str(meta.get("process_exit")) != row["obs_exit"]:
            problems.append("%s meta exit %r != report %r" % (case, meta.get("process_exit"), row["obs_exit"]))
        blob_parts = []
        for extra in case_dir.rglob("*"):
            if extra.is_file():
                blob_parts.append(extra.read_text(encoding="utf-8", errors="replace"))
        blob = "\n".join(blob_parts)
        hits = secret_hits(blob)
        marker_pat = r"\bxai-[A-Za-z0-9]{6,}\b"
        if (
            case == "redaction"
            and row["verdict"] == "FINDING"
            and meta.get("marker_in_receipt") is True
            and marker_pat in hits
        ):
            hits = [item for item in hits if item != marker_pat]
        if hits:
            problems.append("%s secret-like text matched %s" % (case, ", ".join(hits)))
        problems.extend(_case_rule(row, meta, receipt, blob))
    return problems


def _write_tree(root: Path, row: str, receipt: dict | None, meta: dict, extra: str = "") -> None:
    base = root / "eval" / "mvp-1031" / "realfail2"
    case_dir = base / "sample"
    case_dir.mkdir(parents=True)
    header = (
        "| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | "
        "Obs exit | Verdict | Attempts | Recovery | Notes |\n"
        "|------|------|------------|------------|----------|------------|------------|"
        "----------|---------|----------|----------|-------|\n"
    )
    (base / "REPORT.md").write_text(header + row + "\n", encoding="utf-8")
    if receipt is not None:
        (case_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    (case_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    if extra:
        (case_dir / "run.log").write_text(extra, encoding="utf-8")


class Realfail2ReceiptTests(unittest.TestCase):
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

    def test_missing_runner_receipt_is_accepted_when_the_row_says_none(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            _write_tree(
                root,
                "| sample | real | none | usage | 2 | none | usage | 2 | matches | - | - | no receipt |",
                None,
                {"process_exit": 2},
            )
            self.assertEqual(evaluate(root), [])

    def test_planted_bad_receipt_is_rejected(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        marker = "".join(SECRET_PARTS[0])
        planted = "".join(SECRET_PARTS[4])
        self.assertTrue(secret_hits(marker))
        self.assertTrue(secret_hits(planted))
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
                    "tail": planted,
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
