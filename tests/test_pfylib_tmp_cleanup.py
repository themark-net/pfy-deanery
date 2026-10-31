"""A run of the mkdtemp modules leaves no temp dirs behind.

The child gets a fresh TMPDIR from tempfile (the runner's TMPDIR is honored)
and a sitecustomize that records mkdir calls on the host /tmp outside that
directory. A sibling /tmp/pfy-hr-* directory is not one of those calls.

A planted leaker must fail the same checker: one leak stays in the private
TMPDIR, and one leak is a host /tmp directory that ignores TMPDIR.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAKER = ROOT / "tests" / "support_tmpclean_leaker.py"

MODULES = (
    "tests.test_cli",
    "tests.test_toolsets",
    "tests.test_hedge",
    "tests.test_loop_paint",
    "tests.test_attach",
    "tests.test_pfy_launcher_p1",
    "tests.test_x_intake_smoke_098_100",
    "tests.test_x_intake_smoke_103_105",
    "tests.test_x_intake_smoke_103_111_receipts",
    "tests.test_x_intake_smoke_106_108",
    "tests.test_x_intake_smoke_109_111",
    "tests.test_x_intake_smoke_112_114",
    "tests.test_x_intake_smoke_115_116",
    "tests.test_x_intake_smoke_117_118",
    "tests.test_x_intake_smoke_119_121",
    "tests.test_x_intake_smoke_122_124",
)

# Loaded in the child before the modules import. Logs host /tmp mkdirs that
# sit outside the child's TMPDIR. Writes a ready file so a missed hook fails
# closed instead of looking clean.
_HOOK = r"""
import os

_log = os.environ.get("PFY_TMPCLEAN_LOG", "")
_child = os.environ.get("PFY_TMPCLEAN_CHILD_TMP", "")
_ready = os.environ.get("PFY_TMPCLEAN_READY", "")


def _host_leak(path):
    if not path or not _log:
        return
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    try:
        resolved = os.path.realpath(path)
        host = os.path.realpath("/tmp")
    except OSError:
        return
    if resolved == host:
        return
    try:
        if os.path.commonpath([resolved, host]) != host:
            return
    except ValueError:
        return
    if _child:
        try:
            child = os.path.realpath(_child)
            if resolved == child or os.path.commonpath([resolved, child]) == child:
                return
        except (ValueError, OSError):
            pass
    try:
        with open(_log, "a", encoding="utf-8") as handle:
            handle.write(resolved + "\n")
    except OSError:
        pass


_mkdir = os.mkdir


def _wrapped_mkdir(*args, **kwargs):
    _mkdir(*args, **kwargs)
    if args:
        _host_leak(args[0])


os.mkdir = _wrapped_mkdir
_makedirs = os.makedirs


def _wrapped_makedirs(name, *args, **kwargs):
    _makedirs(name, *args, **kwargs)
    _host_leak(name)


os.makedirs = _wrapped_makedirs

if _ready:
    try:
        with open(_ready, "w", encoding="utf-8") as handle:
            handle.write("ok\n")
    except OSError:
        pass
"""


def _marker_ok(marker: str) -> bool:
    return bool(marker) and marker not in (".", "..") and "/" not in marker and "\\" not in marker


def _assert_child_clean(argv: list[str], marker: str | None = None) -> None:
    """Run argv with a private TMPDIR. Raise AssertionError('leaked: ...') on a leftover."""
    marker = marker or ("pfy-tmpclean-" + uuid.uuid4().hex)
    if not _marker_ok(marker):
        raise AssertionError("bad marker")
    base = Path(tempfile.mkdtemp(prefix="pfy-tmpclean-"))
    marker_path = Path("/tmp") / marker
    try:
        hook_dir = base / "hook"
        child_tmp = base / "child"
        hook_dir.mkdir()
        child_tmp.mkdir()
        (hook_dir / "sitecustomize.py").write_text(_HOOK, encoding="utf-8")
        log_path = base / "mkdir.log"
        ready_path = base / "ready"
        env = os.environ.copy()
        env["TMPDIR"] = str(child_tmp)
        env["PFY_TMPCLEAN_LOG"] = str(log_path)
        env["PFY_TMPCLEAN_CHILD_TMP"] = str(child_tmp)
        env["PFY_TMPCLEAN_READY"] = str(ready_path)
        env["PFY_TMPCLEAN_MARKER"] = marker
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        previous = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(hook_dir) + (os.pathsep + previous if previous else "")
        proc = subprocess.run(
            argv,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if not ready_path.is_file():
            tail = (proc.stderr or "")[-400:]
            raise AssertionError("hook did not load\n" + tail)
        names = sorted(path.name for path in child_tmp.iterdir())
        still: list[str] = []
        if log_path.is_file():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if line and Path(line).exists():
                    still.append(line)
        problems: list[str] = []
        if names:
            problems.append("private TMPDIR not empty: " + ", ".join(names))
        if still:
            problems.append("host /tmp paths still present: " + ", ".join(still))
        if problems:
            raise AssertionError("leaked: " + "; ".join(problems))
    finally:
        shutil.rmtree(base, ignore_errors=True)
        if marker_path.is_dir():
            shutil.rmtree(marker_path, ignore_errors=True)


class PfylibTmpCleanupTests(unittest.TestCase):
    def test_module_run_stays_clean_when_sibling_creates_pfy_hr_dir(self):
        sibling = Path("/tmp") / f"pfy-hr-{os.getpid()}"
        stop = threading.Event()
        created: list[Path] = []
        errors: list[BaseException] = []

        def hold() -> None:
            try:
                time.sleep(0.3)
                sibling.mkdir()
                created.append(sibling)
                stop.wait()
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=hold, daemon=True)
        thread.start()
        try:
            _assert_child_clean([sys.executable, "-m", "unittest", *MODULES])
            self.assertEqual(errors, [])
            self.assertTrue(created, "sibling dir was not created during the run")
            self.assertTrue(sibling.is_dir())
        finally:
            stop.set()
            thread.join(timeout=5)
            if created and sibling.is_dir():
                sibling.rmdir()

    def test_private_tmpdir_leak_fails_the_checker(self):
        with self.assertRaisesRegex(AssertionError, "leaked"):
            _assert_child_clean([sys.executable, str(LEAKER), "private"])

    def test_host_tmp_leak_fails_the_checker_and_is_removed(self):
        marker = "pfy-tmpclean-" + uuid.uuid4().hex
        with self.assertRaisesRegex(AssertionError, "leaked"):
            _assert_child_clean([sys.executable, str(LEAKER), "host"], marker=marker)
        self.assertFalse((Path("/tmp") / marker).exists())


if __name__ == "__main__":
    unittest.main()
