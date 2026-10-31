"""Behavior tests for the daily cloud build: ./pfy build "<task>"."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "cloud-build-tests"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"
PFY = ROOT / "pfy"


def _run(argv: list[str], cwd: Path, env: dict | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
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


class CloudBuildSkeletonTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_no_task_exits_2_and_names_the_daily_command(self) -> None:
        proc = _run([sys.executable, str(CLOUD)], self.repo)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertIn('./pfy build "<task>"', text)
        self.assertIn("jev dogfood wrap", text)
        self.assertIn("-p", text)
        self.assertIn("opt-in fallback", text)
        self.assertIn("--local", text)
        self.assertEqual(_git(self.repo, "branch", "--list", "cloud/*").stdout.strip(), "")

    def test_help_exits_0_and_names_the_daily_command(self) -> None:
        for flag in ("--help", "-h"):
            proc = _run([sys.executable, str(CLOUD), flag], self.repo)
            text = (proc.stdout or "") + (proc.stderr or "")
            self.assertEqual(proc.returncode, 0, text)
            self.assertIn('./pfy build "<task>"', text)
            self.assertIn("jev dogfood wrap", text)
            self.assertIn("opt-in fallback", text)
            self.assertIn("--local", text)

    def test_dry_run_writes_receipt_and_starts_no_grok(self) -> None:
        marker = self.repo / "grok-was-started"
        grok = self.repo / "fake-grok.py"
        grok.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n" % str(marker),
            encoding="utf-8",
        )
        grok.chmod(0o755)
        receipt_dir = SCRATCH / (self.id().replace(".", "_") + "-receipt")
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        porcelain = _git(self.repo, "status", "--porcelain").stdout
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add a note",
                "--repo",
                str(self.repo),
                "--dry-run",
                "--grok-cmd",
                str(grok),
                "--receipt-dir",
                str(receipt_dir),
            ],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertFalse(marker.exists(), text)
        self.assertNotIn("cloud/", _git(self.repo, "branch", "--list").stdout)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(_git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), branch)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, porcelain)
        receipt = receipt_dir / "receipt.json"
        self.assertTrue(receipt.is_file(), text)
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "pfy-cloud-build/1")
        self.assertEqual(payload["status"], "DRY-RUN")
        self.assertIsNone(payload["commit"])
        self.assertFalse(payload["pushed"])
        self.assertEqual(payload["base"], "HEAD")
        self.assertIn(str(receipt), proc.stdout)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
