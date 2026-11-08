import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"
CARD = ROOT / "data/stages/atomic-task-graph-atg.json"


class ReceiptFailClosedTest(unittest.TestCase):
    def test_not_ancestor_writes_no_receipt(self):
        before = CARD.read_bytes() if CARD.exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["ATG_FORCE_NOT_ANCESTOR"] = "1"
            env.pop("ATG_SKIP_MAIN_ANCESTOR", None)
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertFalse(receipt.exists())
        if before is not None:
            self.assertEqual(CARD.read_bytes(), before)

    def test_unloaded_model_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = ""
            env["ATG_MODEL_LOADED"] = "0"
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(receipt.exists())

    def test_missing_checkout_does_not_run_model_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            calls = Path(tmp) / "model_calls"
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = ""
            env["ATG_MODEL_LOADED"] = "1"
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            env["ATG_REPO"] = str(Path(tmp) / "missing-atg")
            env["ATG_BASE_URL"] = "http://127.0.0.1:9"
            env["ATG_MODEL_CMD"] = f"sh -c 'echo called >> {calls}'"
            env.pop("ATG_FORCE_NOT_ANCESTOR", None)
            env.pop("ATG_LANE_MARKER", None)
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("ATG checkout is missing", proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(calls.exists())

    def test_bad_checkout_runs_bench_and_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = td / "atg"
            repo.mkdir()
            subprocess.check_call(
                ["git", "init", "-b", "main", str(repo)],
                stdout=subprocess.DEVNULL,
            )
            subprocess.check_call(
                ["git", "-C", str(repo), "config", "user.email", "atg-lane@example.com"]
            )
            subprocess.check_call(
                ["git", "-C", str(repo), "config", "user.name", "atg-lane"]
            )
            subprocess.check_call(
                [
                    "git",
                    "-C",
                    str(repo),
                    "commit",
                    "--allow-empty",
                    "-m",
                    "not-the-pin",
                ],
                stdout=subprocess.DEVNULL,
            )
            receipt = td / "receipt.json"
            calls = td / "model_calls"
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = ""
            env["ATG_MODEL_LOADED"] = "1"
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            env["ATG_REPO"] = str(repo)
            env["ATG_BASE_URL"] = "http://127.0.0.1:9"
            env["ATG_MODEL_CMD"] = f"sh -c 'echo called >> {calls}'"
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env.pop("ATG_FORCE_NOT_ANCESTOR", None)
            env.pop("ATG_LANE_MARKER", None)
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("pinned", proc.stdout + proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(calls.exists())

    def test_real_ancestor_writes_receipt_and_other_head_does_not(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            repo.mkdir()
            subprocess.check_call(
                ["git", "init", "-b", "main", str(repo)],
                stdout=subprocess.DEVNULL,
            )
            subprocess.check_call(
                ["git", "-C", str(repo), "config", "user.email", "atg-lane@example.com"]
            )
            subprocess.check_call(
                ["git", "-C", str(repo), "config", "user.name", "atg-lane"]
            )
            dest = repo / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"
            dest.parent.mkdir(parents=True)
            shutil.copy2(SCRIPT, dest)
            (repo / "README").write_text("fixture\n", encoding="utf-8")
            subprocess.check_call(["git", "-C", str(repo), "add", "-A"])
            subprocess.check_call(
                ["git", "-C", str(repo), "commit", "-m", "wiring"],
                stdout=subprocess.DEVNULL,
            )
            bare = td / "origin.git"
            subprocess.check_call(
                ["git", "init", "--bare", "-b", "main", str(bare)],
                stdout=subprocess.DEVNULL,
            )
            subprocess.check_call(
                ["git", "-C", str(repo), "remote", "add", "origin", str(bare)]
            )
            pushed = subprocess.run(
                ["git", "-C", str(repo), "push", "-u", "origin", "main"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(pushed.returncode, 0, pushed.stderr)
            offline = td / "offline_ok"
            offline.write_text("#!/bin/sh\necho offline\n", encoding="utf-8")
            offline.chmod(0o755)
            receipt = td / "receipt.json"
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = str(offline)
            env.pop("ATG_SKIP_MAIN_ANCESTOR", None)
            env.pop("ATG_FORCE_NOT_ANCESTOR", None)
            env.pop("ATG_LANE_MARKER", None)
            env.pop("ATG_MODEL_CMD", None)
            script = dest
            proc = subprocess.run(
                ["bash", str(script), str(receipt)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(receipt.read_text(encoding="utf-8"))
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(body["slug"], "atomic-task-graph-atg")
            self.assertEqual(body["run_kind"], "pipeline")
            self.assertEqual(body["main_sha"], head)
            self.assertEqual(len(body["main_sha"]), 40)
            self.assertTrue(body["run_id"].startswith("atg-"))
            self.assertEqual(body["outcome"], "ok")
            self.assertTrue(body["tool_version"])
            self.assertTrue(body["did"])
            self.assertTrue(body["started"])
            self.assertTrue(body["finished"])
            before = receipt.read_bytes()
            subprocess.check_call(
                [
                    "git",
                    "-C",
                    str(repo),
                    "commit",
                    "--allow-empty",
                    "-m",
                    "not on main",
                ],
                stdout=subprocess.DEVNULL,
            )
            missed = td / "missed.json"
            again = subprocess.run(
                ["bash", str(script), str(missed)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(again.returncode, 0, again.stdout)
            self.assertFalse(missed.exists())
            self.assertEqual(receipt.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
