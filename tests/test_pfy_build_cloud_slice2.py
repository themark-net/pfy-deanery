"""Exit tests for the short build worktree and the tests/ write default.

Slice 2. Ordinary files under tests/ may change without --writable-test.
Protected gate and eval files still fail tests-tampered unless the flag
names them. A deep repo still gets a harness2 socket under 107 bytes.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "cloud-build-tests"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"
# Box in tests/test_harness2_local_sandbox.py puts the relay socket at
# <repo>/tmp/s/<12-char name>/h/wt/tmp/state/r/s. sun_path holds 107 bytes.
SOCKET_TAIL = Path("tmp") / "s" / ("n" * 12) / "h" / "wt" / "tmp" / "state" / "r" / "s"
SUN_PATH_MAX = 107


def _run(
    argv: list[str],
    cwd: Path,
    env: dict | None = None,
    timeout: float = 60,
) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["TMPDIR"] = str(SCRATCH)
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        argv,
        cwd=cwd,
        env=merged,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], repo)


def _write_exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "cloud-test@example.com")
    _git(path, "config", "user.name", "cloud-test")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    (path / ".gitignore").write_text(
        "tmp/\npipelines/dogfood/build-cloud/\n",
        encoding="utf-8",
    )
    _git(path, "add", "README.md", ".gitignore")
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


def _commit(repo: Path, *paths: str) -> None:
    added = _git(repo, "add", "--", *paths)
    if added.returncode != 0:
        raise RuntimeError(added.stderr)
    committed = _git(repo, "commit", "-m", "seed")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)


def _hidden(path: Path) -> bool:
    try:
        text = os.path.realpath(path)
    except OSError:
        text = str(path)
    for root in ("/tmp", "/run"):
        if text == root or text.startswith(root + os.sep):
            return True
    return False


def _worktrees(repo: Path) -> list[Path]:
    proc = _git(repo, "worktree", "list", "--porcelain")
    found = []
    for line in (proc.stdout or "").splitlines():
        if line.startswith("worktree "):
            found.append(Path(line.split(" ", 1)[1]))
    return found


def _pfyb_dirs() -> set[Path]:
    """Short-root directories this user may have just created."""
    roots = [Path("/var/tmp"), Path.home() / ".cache"]
    xdg = (os.environ.get("XDG_RUNTIME_DIR") or "").strip()
    if xdg:
        roots.append(Path(xdg).expanduser())
    override = (os.environ.get("PFY_BUILD_WORKTREE_ROOT") or "").strip()
    if override:
        roots.append(Path(override).expanduser())
    found: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.glob("pfyb-*"):
            if path.is_dir():
                found.add(path.resolve())
    return found


class _BuildCase(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.kept: list[Path] = []
        self._repos = [self.repo]

    def tearDown(self) -> None:
        seen: set[str] = set()
        for repo in list(self._repos):
            if not repo.exists():
                continue
            for path in _worktrees(repo):
                try:
                    same = path.resolve() == repo.resolve()
                except OSError:
                    same = False
                if same:
                    continue
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                _git(repo, "worktree", "remove", "--force", str(path))
                shutil.rmtree(path, ignore_errors=True)
        for path in self.kept:
            shutil.rmtree(path, ignore_errors=True)
        for repo in self._repos:
            shutil.rmtree(repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _receipt(self) -> dict:
        path = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0]
        return json.loads(path.read_text(encoding="utf-8"))

    def _grok(self, body: str) -> Path:
        return _write_exe(self.side / "grok.py", body)

    def _gate(self, body: str) -> Path:
        return _write_exe(self.side / "gate.py", body)

    def _build(self, task: str, grok: Path, gate: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess:
        argv = [
            sys.executable,
            str(CLOUD),
            task,
            "--repo",
            str(self.repo),
            "--retries",
            "0",
            "--no-review",
            "--timeout",
            "30",
            "--test-cmd",
            "%s %s" % (sys.executable, gate),
            "--grok-cmd",
            str(grok),
        ]
        argv.extend(extra or [])
        return _run(argv, self.repo, timeout=60)


class OrdinaryTestWriteTests(_BuildCase):
    def test_ordinary_test_edit_lands_without_writable_test(self) -> None:
        # Fail: an edit of tests/test_keep.py is tests-tampered unless the
        # flag names it, so the task cannot update an ordinary test.
        # Recover: files under tests/ that are not gate files may change.
        # The gate sees the new assertion and the commit keeps it.
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        _commit(self.repo, "tests/test_keep.py")
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests/test_keep.py').write_text("
            "'def test_keep():\\n    assert 1 == 1\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "text = Path('tests/test_keep.py').read_text(encoding='utf-8')\n"
            "if 'assert 1 == 1' not in text:\n"
            "    print('GATE-NEED-EDIT')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build("update the ordinary test", grok, gate)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "ok", payload)
        shown = _git(self.repo, "show", payload["commit"] + ":tests/test_keep.py")
        self.assertIn("assert 1 == 1", shown.stdout)

    def test_new_test_file_lands_without_writable_test(self) -> None:
        # Fail: a new tests/test_added.py is tests-tampered and never committed.
        # Recover: a new file under tests/ is allowed. The gate requires it.
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        _commit(self.repo, "tests/test_keep.py")
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests').mkdir(exist_ok=True)\n"
            "Path('tests/test_added.py').write_text("
            "'def test_added():\\n    assert True\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "if not Path('tests/test_added.py').is_file():\n"
            "    print('GATE-NEED-NEW-TEST')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build("add a test", grok, gate)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "ok", payload)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("tests/test_added.py", names)
        kept = _git(self.repo, "show", payload["commit"] + ":tests/test_keep.py")
        self.assertEqual(kept.stdout, "def test_keep():\n    assert True\n")


class ProtectedGateWriteTests(_BuildCase):
    def _expect_tamper(self, rel: str, body: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        _commit(self.repo, rel)
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('changed = True\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % rel
        )
        gate = self._gate(
            "#!/usr/bin/env python3\n"
            "print('GATE-SHOULD-NOT-RERUN')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build("do not edit the protected file", grok, gate)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-tampered", payload)
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["gate"]["after"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_eval_harness_edit_is_tests_tampered(self) -> None:
        # Fail: examples/eval-harness/marker.py is not a base test, so the
        # edit is committed and the eval gate can be rewritten.
        # Recover: that tree stays hashed. Restore the file or pass
        # --writable-test for it. No branch is published.
        self._expect_tamper("examples/eval-harness/marker.py", "marker = 1\n")

    def test_pregate_edit_is_tests_tampered(self) -> None:
        # Fail: scripts/pregate.sh is outside the test snapshot, so a build
        # can rewrite the gate hash check and land it.
        # Recover: pregate stays hashed unless --writable-test names it.
        self._expect_tamper("scripts/pregate.sh", "#!/bin/sh\necho ok\n")

    def test_workflow_edit_is_tests_tampered(self) -> None:
        # Fail: a workflow file is not hashed, so the build can change CI.
        # Recover: .github/workflows stays tests-tampered without the flag.
        self._expect_tamper(".github/workflows/ci.yml", "name: ci\n")

    def test_gate_basename_under_tests_is_tests_tampered(self) -> None:
        # Fail: tests/conftest.py is treated as an ordinary test and the
        # build commits a conftest that exits 0.
        # Recover: gate basenames stay hashed even under tests/.
        self._expect_tamper("tests/conftest.py", "def pytest_configure(config):\n    return None\n")

    def test_writable_test_unlocks_the_named_protected_file(self) -> None:
        # Fail: --writable-test is ignored for a protected file, so the
        # named eval file stays tests-tampered and nothing lands.
        # Recover: the flag unlocks that one file. A second protected file
        # that was not named stays as it was.
        harness = self.repo / "examples" / "eval-harness"
        harness.mkdir(parents=True)
        (harness / "marker.py").write_text("marker = 1\n", encoding="utf-8")
        (harness / "other.py").write_text("other = 1\n", encoding="utf-8")
        _commit(self.repo, "examples/eval-harness/marker.py", "examples/eval-harness/other.py")
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('examples/eval-harness/marker.py').write_text("
            "'marker = 2\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "text = Path('examples/eval-harness/marker.py').read_text(encoding='utf-8')\n"
            "other = Path('examples/eval-harness/other.py').read_text(encoding='utf-8')\n"
            "if text != 'marker = 2\\n' or other != 'other = 1\\n':\n"
            "    print('GATE-NEED-UNLOCK')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build(
            "update the named eval file",
            grok,
            gate,
            extra=["--writable-test", "examples/eval-harness/marker.py"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "ok", payload)
        shown = _git(self.repo, "show", payload["commit"] + ":examples/eval-harness/marker.py")
        self.assertEqual(shown.stdout, "marker = 2\n")
        other = _git(self.repo, "show", payload["commit"] + ":examples/eval-harness/other.py")
        self.assertEqual(other.stdout, "other = 1\n")

    def test_new_eval_file_is_tests_tampered(self) -> None:
        # Fail: a new file under examples/eval-harness is not in the base
        # snapshot, so it is committed and the eval set grows.
        # Recover: a new protected path is tests-tampered. Nothing lands.
        harness = self.repo / "examples" / "eval-harness"
        harness.mkdir(parents=True)
        (harness / "marker.py").write_text("marker = 1\n", encoding="utf-8")
        _commit(self.repo, "examples/eval-harness/marker.py")
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('examples/eval-harness/cheat.py').write_text("
            "'cheat = True\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate(
            "#!/usr/bin/env python3\n"
            "print('GATE-SHOULD-NOT-RERUN')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build("do not add an eval file", grok, gate)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-tampered", payload)
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["gate"]["after"])


class ShortWorktreeTests(_BuildCase):
    def test_deep_repo_keeps_a_short_socket_and_sandbox_tests_pass(self) -> None:
        # Fail: the worktree is <deep-repo>/tmp/cloud-build/<stamp>, so
        # state/r/s is longer than 107 bytes and the harness2 suite cannot
        # bind its socket.
        # Recover: the worktree is a 0700 directory outside /tmp and /run,
        # removed unless --keep-worktree. The sandbox suite passes there.
        deep = self.side / ("d" * 90) / "repo"
        self.repo = _init_repo(deep)
        self._repos.append(self.repo)
        self.assertGreater(len(str(self.repo)), SUN_PATH_MAX)
        # The sandbox imports examples/x-intake-local/smoke.py. A checkout
        # that only has harness2-local fails that import before it binds.
        for name in ("harness2-local", "x-intake-local"):
            shutil.copytree(
                ROOT / "examples" / name,
                self.repo / "examples" / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        tests = self.repo / "tests"
        tests.mkdir()
        shutil.copy(
            ROOT / "tests" / "test_harness2_local_sandbox.py",
            tests / "test_harness2_local_sandbox.py",
        )
        _commit(self.repo, "examples", "tests")
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate("#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n")
        proc = self._build(
            "add kept",
            grok,
            gate,
            extra=["--keep-worktree"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "ok", payload)
        self.assertFalse(payload["worktree_removed"])
        extras = [path for path in _worktrees(self.repo) if path.resolve() != self.repo.resolve()]
        self.kept.extend(extras)
        self.assertEqual(len(extras), 1, _git(self.repo, "worktree", "list").stdout)
        worktree = extras[0]
        sock = worktree / SOCKET_TAIL
        self.assertLessEqual(len(str(sock)), SUN_PATH_MAX, str(sock))
        self.assertLessEqual(len(os.fsencode(str(sock))), SUN_PATH_MAX, str(sock))
        self.assertFalse(_hidden(worktree), str(worktree))
        self.assertTrue(worktree.name.startswith("pfyb-"), worktree.name)
        self.assertEqual(stat.S_IMODE(worktree.stat().st_mode), 0o700)
        self.assertEqual(worktree.stat().st_uid, os.getuid())
        self.assertFalse(str(worktree.resolve()).startswith(str(self.repo.resolve())))
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["TMPDIR"] = str(worktree / "tmp")
        suite = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_harness2_local_sandbox"],
            cwd=worktree,
            env=env,
            text=True,
            capture_output=True,
            timeout=900,
            check=False,
        )
        tail = ((suite.stdout or "") + (suite.stderr or ""))[-4000:]
        self.assertEqual(suite.returncode, 0, tail)

    def test_short_worktree_is_removed_when_keep_is_off(self) -> None:
        # Fail: the short directory is left behind after a PASS, so later
        # runs share a tree or fill the short root.
        # Recover: without --keep-worktree the directory is gone and git
        # lists only the caller repo.
        before = _pfyb_dirs()
        grok = self._grok(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate = self._gate("#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n")
        proc = self._build("add kept", grok, gate)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertTrue(payload["worktree_removed"], payload)
        listed = _worktrees(self.repo)
        self.assertEqual(len(listed), 1, listed)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
        after = _pfyb_dirs()
        self.assertEqual(after - before, set())


if __name__ == "__main__":
    unittest.main()
