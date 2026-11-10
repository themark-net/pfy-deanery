"""approvals.tsv: operator-approved GPU and over-25 GB blocks clear needs-mark and go to the GPU driver.

How this fails: an approved slug keeps its needs-mark row, the loop starts
approved GPU lanes in parallel, or an approval for one block hides another.
How we recover: block_reason ignores only the approved blocks,
--launch-check prints gpu-driver, and needs-mark drops only approved rows.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"
NEEDS = ROOT / "scripts" / "catalog_needs_mark.py"


def build(td: Path, approvals: str) -> Path:
    root = td / "repo"
    stages = root / "data" / "stages"
    stages.mkdir(parents=True)
    q = root / "eval" / "catalog-queue"
    q.mkdir(parents=True)
    (q / "exclusions.tsv").write_text("slug\treason\nbig-ex\tNeeds a GGUF over the 25 GB pull cap\n", encoding="utf-8")
    ops_q = root / "tmp" / "ops" / "eval" / "catalog-queue"
    ops_q.mkdir(parents=True)
    (ops_q / "approvals.tsv").write_text(approvals, encoding="utf-8")
    cards = {
        "gpu-ok": {"uses": "decode on the gpu"},
        "gpu-no": {"uses": "decode on the gpu"},
        "both": {"uses": "a 37.6 GB pull on the gpu"},
        "rel": {"uses": "gpu release tooling"},
    }
    for slug, extra in cards.items():
        body = {"name": slug, "integration_stage": "I1", "tier_ceiling": "I1", "risk_class": "none"}
        body.update(extra)
        (stages / f"{slug}.json").write_text(json.dumps(body) + "\n", encoding="utf-8")
    return root


NO_OPS = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}


def check(root: Path, slug: str) -> str:
    out = subprocess.run(["python3", str(RAISE), "--root", str(root), "--launch-check", slug], capture_output=True, text=True, timeout=30, env=NO_OPS)
    return out.stdout.strip() or out.stderr.strip()


APPROVALS = (
    "slug\tblock\tdecided\tnote\n"
    "gpu-ok\tgpu\t2026-11-10\tok\n"
    "both\tpull-over-25gb\t2026-11-10\tok\n"
    "rel\tgpu\t2026-11-10\tok\n"
    "big-ex\tpull-over-25gb\t2026-11-10\tok\n"
)


class GpuApprovalsTest(unittest.TestCase):
    def test_launch_check_and_needs_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build(Path(tmp), APPROVALS)
            self.assertEqual(check(root, "gpu-ok"), "skip\tgpu-ok\tgpu-driver")
            self.assertEqual(check(root, "gpu-no"), "skip\tgpu-no\tHS-gpu-unapproved")
            self.assertEqual(check(root, "both"), "skip\tboth\tHS-gpu-unapproved")  # pull approved, gpu not
            self.assertEqual(check(root, "rel"), "skip\trel\tHS-release-deploy")
            env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}
            out = root / "nm.tsv"
            proc = subprocess.run(["python3", str(NEEDS), "--root", str(root), "--out", str(out)], capture_output=True, text=True, timeout=30, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertNotIn("gpu-ok\t", text)
            self.assertIn("gpu-no\thard-stop\tHS-gpu-unapproved: ", text)
            self.assertNotIn("both\thard-stop\tHS-pull-over-25gb-unapproved", text)
            self.assertIn("both\thard-stop\tHS-gpu-unapproved: ", text)
            self.assertNotIn("big-ex\t", text)

    def test_bad_approval_rows_are_errors(self):
        for bad in ("slug\tblock\tdecided\tnote\nx\trelease-deploy\t2026-11-10\tno\n",
                    "slug\tblock\tdecided\tnote\nx\tgpu\tsoon\tno\n",
                    "slug\tblock\n"):
            with tempfile.TemporaryDirectory() as tmp:
                root = build(Path(tmp), bad)
                out = subprocess.run(["python3", str(RAISE), "--root", str(root), "--launch-check", "gpu-ok"], capture_output=True, text=True, timeout=30, env=NO_OPS)
                self.assertNotEqual(out.returncode, 0, bad)

    def test_missing_approvals_file_means_no_approvals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build(Path(tmp), APPROVALS)
            (root / "tmp" / "ops" / "eval" / "catalog-queue" / "approvals.tsv").unlink()
            self.assertEqual(check(root, "gpu-ok"), "skip\tgpu-ok\tHS-gpu-unapproved")

    def test_approvals_file_is_not_in_the_public_tree(self):
        self.assertFalse((ROOT / "eval" / "catalog-queue" / "approvals.tsv").exists())


if __name__ == "__main__":
    unittest.main()
