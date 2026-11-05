"""First-day contract: README and make help match ./pfy build defaults.

Fail: a reader follows an older card, runs ./pfy build from a scratch
clone, and the runner builds the catalog repo instead of that clone.
Recover: the daily command with no --repo writes its dry-run receipt
inside the current repo. This test fails if that receipt lands elsewhere
or if the README drops the gate command the receipt records.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "first-day-tests"
PFY = ROOT / "pfy"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"


def _cloud():
    spec = importlib.util.spec_from_file_location("pfy_build_cloud_first_day", CLOUD)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pfy_build_cloud")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["TMPDIR"] = str(SCRATCH)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], repo)


def _init_repo(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "first-day@example.com")
    _git(path, "config", "user.name", "first-day")
    (path / "README.md").write_text("scratch\n", encoding="utf-8")
    (path / ".gitignore").write_text(
        "tmp/\npipelines/dogfood/build-cloud/\n",
        encoding="utf-8",
    )
    added = _git(path, "add", "README.md", ".gitignore")
    if added.returncode != 0:
        raise RuntimeError(added.stderr)
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


class FirstDayBuildDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.catalog_head = _git(ROOT, "rev-parse", "HEAD").stdout

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_readme_and_help_match_a_dry_run_in_the_current_repo(self) -> None:
        cloud = _cloud()
        defaults = cloud.parse_args(["first-day-marker"])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('## Daily build', readme)
        self.assertIn('./pfy build "<task>"', readme)
        self.assertIn("git toplevel of the current directory", readme)
        self.assertIn(defaults.test_cmd, readme)
        self.assertIn(str(int(defaults.timeout)), readme)
        self.assertIn("exits 2", readme)
        self.assertIn("does not read `auth.json`", readme)
        self.assertIn("`--local` is opt-in", readme)

        help_proc = _run([str(PFY), "build", "--help"], self.repo)
        help_text = " ".join(((help_proc.stdout or "") + (help_proc.stderr or "")).split())
        self.assertEqual(help_proc.returncode, 0, help_text)
        self.assertIn("default: cwd", help_text)
        self.assertIn("Required when HEAD is not origin/main", help_text)
        self.assertIn("else HEAD if origin/main is absent", help_text)

        make_help = _run(["make", "help"], ROOT)
        self.assertEqual(make_help.returncode, 0, make_help.stderr)
        self.assertIn("./pfy build <task>", make_help.stdout or "")

        before = _git(self.repo, "status", "--porcelain").stdout
        proc = _run([str(PFY), "build", "first-day-marker", "--dry-run"], self.repo)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        receipts = list(
            (self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json")
        )
        self.assertEqual(len(receipts), 1, text)
        payload = json.loads(receipts[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "DRY-RUN")
        self.assertEqual(payload["task"], "first-day-marker")
        self.assertEqual(payload["base"], "HEAD")
        self.assertEqual(payload["gate"]["cmd"], defaults.test_cmd)
        self.assertFalse(payload["pushed"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertEqual(_git(ROOT, "rev-parse", "HEAD").stdout, self.catalog_head)
        self.assertNotIn("cloud/", _git(self.repo, "branch", "--list").stdout)

    def test_no_task_exits_2_and_stays_out_of_the_dogfood_wrap(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("exits 2", readme)
        proc = _run([str(PFY), "build"], self.repo)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertIn('./pfy build "<task>"', text)
        self.assertNotIn("Apply local jev toolset", text)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, "")
