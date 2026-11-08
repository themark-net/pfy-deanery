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
REAL_MARKER = Path("/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/opencode-mem.dispatched")
HOME_DIRS = (
    ".config/opencode",
    ".opencode",
    ".opencode-mem",
    ".local/share/opencode",
    ".cache/opencode",
)

STUB = """#!/usr/bin/env python3
import json, os, sys
out = sys.argv[sys.argv.index("--out") + 1]
mode = os.environ.get("OCM_STUB_MODE", "good")
if mode == "crash":
    raise SystemExit(1)
doc = {
    "store_ok": True,
    "recall_ok": True,
    "recall_search_hits": 8,
    "recall_list_hits": 8,
    "real_home_changed": [],
}
if mode == "miss":
    doc["recall_search_hits"] = 0
    doc["recall_list_hits"] = 0
elif mode == "home":
    doc["real_home_changed"] = [".config/opencode"]
elif mode == "store":
    doc["store_ok"] = False
with open(out, "w", encoding="utf-8") as handle:
    json.dump(doc, handle)
raise SystemExit(0)
"""


def _cache_ready() -> bool:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    pkg = home / ".cache/pfy/tools/opencode-mem/prefix/node_modules/opencode-mem/package.json"
    onnx = home / ".cache/pfy/tools/opencode-mem/home/.opencode-mem/data/.cache"
    return pkg.is_file() and onnx.is_dir()


def _home_stamp() -> tuple:
    base = Path(pwd.getpwuid(os.getuid()).pw_dir)
    stamp = []
    for name in HOME_DIRS:
        path = base / name
        stamp.append(path.stat().st_mtime_ns if path.exists() else None)
    return tuple(stamp)


def _git(root: Path, *args: str) -> None:
    subprocess.check_call(["git", *args], cwd=root, stdout=subprocess.DEVNULL)


def _ancestor_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ocm-fail-"))
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
    probe_dir = root / "eval" / "evq1107" / "opencode-mem"
    probe_dir.mkdir(parents=True)
    (probe_dir / "probe.py").write_text(STUB, encoding="utf-8")
    scripts = root / "scripts"
    scripts.mkdir()
    lock = scripts / "model_lock.sh"
    lock.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
    lock.chmod(0o755)
    return root


def _run(root: Path, receipt: Path, extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    env["OCM_LANE_MARKER"] = str(root / "missing-marker")
    env["PFY_MODEL_LOCK"] = str(root / "model.lock")
    env["TMPDIR"] = str(root / "tmp")
    (root / "tmp").mkdir(exist_ok=True)
    if extra:
        env.update(extra)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


class OpenCodeMemFailClosedTest(unittest.TestCase):
    def setUp(self):
        self._dirs = []
        self._home = _home_stamp()
        self._marker = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self._card = (ROOT / "data/stages/opencode-mem.json").read_bytes()

    def tearDown(self):
        for path in self._dirs:
            shutil.rmtree(path, ignore_errors=True)
        self.assertEqual(_home_stamp(), self._home)
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(after, self._marker)
        self.assertEqual((ROOT / "data/stages/opencode-mem.json").read_bytes(), self._card)

    def test_timeout_or_missing_probe_is_not_a_pass(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        self.assertIn("receipt", lowered)
        self.assertNotRegex(lowered, r"timeout[^\n]{0,80}pass")
        self.assertIn("HOME", text)
        self.assertNotIn(
            ".config/opencode",
            text.replace("~/.config/opencode", "").replace("$HOME/.config/opencode", ""),
        )
        for banned in ("ollama pull", "ollama stop", "systemctl", "auth.json", "config.toml"):
            self.assertNotIn(banned, text)
        mv_at = text.find('mv "$tmp" "$receipt"')
        self.assertGreater(mv_at, 0)
        self.assertLess(lowered.find("timeout"), mv_at)
        self.assertLess(text.find('if [ "$rc" -ne 0 ]'), mv_at)

    def test_missing_probe_writes_no_receipt(self):
        root = _ancestor_repo()
        self._dirs.append(root)
        (root / "eval" / "evq1107" / "opencode-mem" / "probe.py").unlink()
        receipt = root / "receipt.json"
        proc = _run(root, receipt)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("offline probe missing", proc.stderr)
        self.assertFalse(receipt.exists())
        self.assertFalse((root / "missing-marker").exists())

    def test_timeout_exit_writes_no_receipt(self):
        if not _cache_ready():
            self.skipTest("opencode-mem cache is absent")
        root = _ancestor_repo()
        self._dirs.append(root)
        bindir = root / "bin"
        bindir.mkdir()
        timeout_bin = bindir / "timeout"
        timeout_bin.write_text("#!/bin/sh\nexit 124\n", encoding="utf-8")
        timeout_bin.chmod(0o755)
        receipt = root / "receipt.json"
        proc = _run(root, receipt, {"PATH": "%s:%s" % (bindir, os.environ.get("PATH", "/usr/bin:/bin"))})
        self.assertEqual(proc.returncode, 124, proc.stderr)
        self.assertIn("probe exit 124", proc.stderr)
        self.assertFalse(receipt.exists())

    def test_probe_error_or_short_recall_or_real_home_change_writes_no_receipt(self):
        if not _cache_ready():
            self.skipTest("opencode-mem cache is absent")
        root = _ancestor_repo()
        self._dirs.append(root)
        for mode in ("crash", "miss", "home", "store"):
            receipt = root / ("receipt-%s.json" % mode)
            proc = _run(root, receipt, {"OCM_STUB_MODE": mode})
            self.assertNotEqual(proc.returncode, 0, mode + " " + proc.stderr)
            self.assertFalse(receipt.exists(), mode)
            self.assertNotIn("pass", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
