import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/opencode-mem/run-on-main.sh"
REAL_MARKER = (Path.home() / "DEVELOP/pfy-mentat/tmp/integrate2/opencode-mem.dispatched")


def _git(root: Path, *args: str) -> None:
    subprocess.check_call(["git", *args], cwd=root, stdout=subprocess.DEVNULL)


def _off_main_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ocm-flight-"))
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


def _run(cwd: Path, receipt: Path, marker: Path | None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    if marker is None:
        env["OCM_LANE_MARKER"] = str(cwd / "missing-marker")
    else:
        env["OCM_LANE_MARKER"] = str(marker)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


class OpenCodeMemSingleFlightTest(unittest.TestCase):
    def setUp(self):
        self._dirs = []
        self._marker = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None

    def tearDown(self):
        for path in self._dirs:
            shutil.rmtree(path, ignore_errors=True)
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(after, self._marker)

    def test_second_start_exits_2_and_names_push_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("opencode-mem.dispatched", text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        self.assertIn("model_lock.sh", text)
        self.assertNotIn("ollama pull", text)
        self.assertNotIn("git push", text)
        mv_at = text.find('mv "$tmp" "$receipt"')
        self.assertGreater(mv_at, 0)
        self.assertLess(text.find("exit 2"), mv_at)
        self.assertIn("$HOME/DEVELOP/pfy-mentat/tmp/integrate2/push.lock", text)
        self.assertNotRegex(text, r">\s*\"\$receipt\"")

    def test_usage_exits_2_without_a_receipt_path(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("receipt.json", proc.stdout)

    def test_foreign_marker_exits_2_and_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            marker.write_text("pid 1\n", encoding="utf-8")
            receipt = Path(tmp) / "receipt.json"
            proc = _run(ROOT, receipt, marker)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "pid 1\n")

    def test_own_lane_is_admitted_and_still_writes_no_receipt_off_main(self):
        root = _off_main_repo()
        self._dirs.append(root)
        marker = root / "marker"
        marker.write_text("pid %s\n" % os.getpid(), encoding="utf-8")
        receipt = root / "receipt.json"
        receipt.write_text("keep\n", encoding="utf-8")
        proc = _run(root, receipt, marker)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("not an ancestor", proc.stderr)
        self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(marker.read_text(encoding="utf-8"), "pid %s\n" % os.getpid())

    def test_missing_marker_is_not_created(self):
        root = _off_main_repo()
        self._dirs.append(root)
        missing = root / "missing-marker"
        receipt = root / "receipt.json"
        proc = _run(root, receipt, None)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertFalse(missing.exists())
        self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
