import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "headson" / "run-on-main.sh"
PINNED = Path.home() / ".cache" / "pfy" / "tools" / "headson" / "bin" / "hson"


def _ancestor_repo(fixture_text: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="headson-receipt-"))
    subprocess.check_call(["git", "init", "-q"], cwd=root)
    dest = root / "eval" / "integrate" / "headson"
    dest.mkdir(parents=True)
    (dest / "fixture.json").write_text(fixture_text, encoding="utf-8")
    subprocess.check_call(["git", "add", "eval/integrate/headson/fixture.json"], cwd=root)
    subprocess.check_call(
        [
            "git",
            "-c",
            "user.email=lane@example.com",
            "-c",
            "user.name=lane",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
    )
    subprocess.check_call(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=root)
    return root


def _run(root: Path, receipt: Path, env_extra: dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("HSON_BIN", None)
    env["HSON_LANE_MARKER"] = str(root / "missing-marker")
    env["TMPDIR"] = str(root / "tmp")
    (root / "tmp").mkdir(exist_ok=True)
    env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


class TestHeadsonFailClosed(unittest.TestCase):
    def test_ancestry_and_timeout_block_receipt(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertIn("merge-base --is-ancestor", script)
        self.assertIn("origin/main", script)
        self.assertIn("timeout", script)
        self.assertNotIn("git fetch", script)
        self.assertNotIn("git pull", script)

    def test_preview_receipt_only_when_output_is_valid(self):
        if not os.access(PINNED, os.X_OK):
            self.skipTest("pinned hson is absent")
        blob = "x" * 4000
        good = json.dumps(
            {"slug": "headson", "kind": "preview-fixture", "rows": list(range(80)), "note": blob}
        )
        root = _ancestor_repo(good)
        try:
            self.assertGreater((root / "eval/integrate/headson/fixture.json").stat().st_size, 1024)
            receipt = root / "receipt.json"
            proc = _run(root, receipt, {})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(doc["slug"], "headson")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["outcome"], "pass")
            self.assertEqual(len(doc["main_sha"]), 40)
            self.assertIn("0.17.1", doc["tool_version"])
            self.assertIn("-c", doc["did"])
            self.assertIn("-t strict", doc["did"])
            log = Path(doc["log_path"])
            self.assertTrue(log.is_file())
            raw = log.read_bytes()
            body = raw[:-1] if raw.endswith(b"\n") else raw
            self.assertLessEqual(len(body), 1024)
            json.loads(body.decode("utf-8"))
            self.assertEqual(len(list((root / "tmp").iterdir())), 1)
            self.assertFalse((root / "missing-marker").exists())
            kept = receipt.read_bytes()
            kept_log = log.read_bytes()

            bad = root / "receipt-bad.json"
            stub = root / "stub-hson"
            stub.write_bytes(b"#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
            denied = _run(root, bad, {"HSON_BIN": str(stub)})
            self.assertNotEqual(denied.returncode, 0, denied.stderr)
            self.assertFalse(bad.exists())

            missing = root / "receipt-missing.json"
            gone = _run(root, missing, {"HSON_BIN": str(root / "no-such-hson")})
            self.assertNotEqual(gone.returncode, 0, gone.stderr)
            self.assertFalse(missing.exists())

            (root / "eval/integrate/headson/fixture.json").write_text("not-json\n", encoding="utf-8")
            invalid = root / "receipt-invalid.json"
            broke = _run(root, invalid, {})
            self.assertNotEqual(broke.returncode, 0, broke.stderr)
            self.assertFalse(invalid.exists())
            self.assertEqual(receipt.read_bytes(), kept)
            self.assertEqual(log.read_bytes(), kept_log)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
