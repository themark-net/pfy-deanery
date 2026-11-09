import json
import os
import pwd
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/opencode-mem/run-on-main.sh"
REAL_MARKER = (Path.home() / "DEVELOP/pfy-mentat/tmp/integrate2/opencode-mem.dispatched")
VERDICT = ROOT / "eval/integrate/opencode-mem/VERDICT.json"
CARD = ROOT / "data/stages/opencode-mem.json"

STUB = """#!/usr/bin/env python3
import json, sys
out = sys.argv[sys.argv.index("--out") + 1]
doc = {
    "store_ok": True,
    "recall_ok": True,
    "recall_search_hits": 8,
    "recall_list_hits": 8,
    "real_home_changed": [],
}
with open(out, "w", encoding="utf-8") as handle:
    json.dump(doc, handle)
"""


def _cache_ready() -> bool:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    pkg = home / ".cache/pfy/tools/opencode-mem/prefix/node_modules/opencode-mem/package.json"
    onnx = home / ".cache/pfy/tools/opencode-mem/home/.opencode-mem/data/.cache"
    return pkg.is_file() and onnx.is_dir()


def _git(root: Path, *args: str) -> None:
    subprocess.check_call(["git", *args], cwd=root, stdout=subprocess.DEVNULL)


def _repo(on_main: bool) -> Path:
    root = Path(tempfile.mkdtemp(prefix="ocm-gate-"))
    _git(root, "init", "-q")
    (root / "README").write_text("base\n", encoding="utf-8")
    _git(root, "add", "README")
    _git(
        root,
        "-c",
        "user.email=lane@example.com",
        "-c",
        "user.name=lane",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "base",
    )
    if on_main:
        _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        probe_dir = root / "eval" / "evq1107" / "opencode-mem"
        probe_dir.mkdir(parents=True)
        (probe_dir / "probe.py").write_text(STUB, encoding="utf-8")
        scripts = root / "scripts"
        scripts.mkdir()
        lock = scripts / "model_lock.sh"
        lock.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
        lock.chmod(0o755)
    else:
        _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
        (root / "README").write_text("ahead\n", encoding="utf-8")
        _git(root, "add", "README")
        _git(
            root,
            "-c",
            "user.email=lane@example.com",
            "-c",
            "user.name=lane",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "ahead",
        )
    return root


def _run(root: Path, receipt: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    env["OCM_LANE_MARKER"] = str(root / "missing-marker")
    env["PFY_MODEL_LOCK"] = str(root / "model.lock")
    env["TMPDIR"] = str(root / "tmp")
    (root / "tmp").mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


class OpenCodeMemReceiptGateTest(unittest.TestCase):
    def setUp(self):
        self._dirs = []
        self._marker = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self._card = CARD.read_bytes()

    def tearDown(self):
        for path in self._dirs:
            shutil.rmtree(path, ignore_errors=True)
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(after, self._marker)
        self.assertEqual(CARD.read_bytes(), self._card)

    def test_pipeline_kind_and_ancestor_guard(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        self.assertNotIn("gate", text.split("run_kind")[-1][:80])
        self.assertIn("origin/main", text)
        self.assertIn("ancestor", text.lower())
        self.assertIn("main_sha", text)
        self.assertIn("opencode-mem", text)
        verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(verdict["metric"], "temp_home_recall_search_hits")
        self.assertEqual(verdict["threshold"], 8)
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
        self.assertNotIn("tier_ceiling", verdict)
        card_main = subprocess.check_output(
            ["git", "show", "origin/main:data/stages/opencode-mem.json"],
            cwd=ROOT,
        )
        self.assertEqual(CARD.read_bytes(), card_main)
        card = json.loads(card_main.decode("utf-8"))
        self.assertEqual(card["tier_ceiling"], "I3")
        self.assertNotEqual(card["integration_stage"], "I3")

    def test_off_main_head_writes_no_receipt(self):
        root = _repo(False)
        self._dirs.append(root)
        receipt = root / "receipt.json"
        receipt.write_text("keep\n", encoding="utf-8")
        proc = _run(root, receipt)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("not an ancestor", proc.stderr)
        self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

    def test_clearing_probe_writes_a_pipeline_receipt_without_a_dump(self):
        if not _cache_ready():
            self.skipTest("opencode-mem cache is absent")
        root = _repo(True)
        self._dirs.append(root)
        receipt = root / "out" / "receipt.json"
        proc = _run(root, receipt)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(receipt.is_file(), proc.stderr)
        raw = receipt.read_text(encoding="utf-8")
        for banned in ("auth.json", "api_key", "BEGIN ", "sk-", "/home/", "OCM1107"):
            self.assertNotIn(banned, raw)
        doc = json.loads(raw)
        self.assertEqual(
            set(doc),
            {
                "slug",
                "run_kind",
                "main_sha",
                "run_id",
                "started",
                "finished",
                "outcome",
                "tool_version",
                "did",
            },
        )
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        self.assertEqual(doc["slug"], "opencode-mem")
        self.assertEqual(doc["run_kind"], "pipeline")
        self.assertEqual(doc["main_sha"], sha)
        self.assertEqual(len(doc["main_sha"]), 40)
        self.assertEqual(doc["outcome"], "ok")
        self.assertEqual(doc["tool_version"], "2.41.1")
        self.assertEqual(
            doc["did"],
            "Ran the offline probe in a temp HOME and searched 8 of 8 stored salts.",
        )
        self.assertRegex(doc["started"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertRegex(doc["finished"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertNotIn("gate", doc["run_kind"])
        self.assertFalse((root / "missing-marker").exists())


if __name__ == "__main__":
    unittest.main()
