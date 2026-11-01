"""Behavior tests for the daily cloud build: ./pfy build "<task>"."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
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


def _load_cloud():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pfy_build_cloud_under_test", CLOUD)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the cloud runner")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        self.assertEqual(payload["gate"]["cmd"], "python3 -m unittest discover -s tests -t .")
        self.assertEqual(payload["base"], "HEAD")
        self.assertIn(str(receipt), proc.stdout)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())

    def test_dry_run_uses_origin_main_when_it_matches_head(self) -> None:
        # Fail: a matching origin/main is ignored and the receipt says HEAD.
        # Recover: the default base name is origin/main when the shas match.
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        ref = _git(self.repo, "update-ref", "refs/remotes/origin/main", head)
        self.assertEqual(ref.returncode, 0, ref.stderr)
        receipt_dir = SCRATCH / (self.id().replace(".", "_") + "-receipt")
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add a note",
                "--repo",
                str(self.repo),
                "--dry-run",
                "--receipt-dir",
                str(receipt_dir),
            ],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["base"], "origin/main")
        self.assertEqual(payload["status"], "DRY-RUN")


class CloudBuildDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_p_help_reaches_dogfood_and_positional_reaches_cloud(self) -> None:
        dogfood = _run([str(PFY), "build", "-p", "--help"], self.repo)
        dogfood_text = (dogfood.stdout or "") + (dogfood.stderr or "")
        self.assertEqual(dogfood.returncode, 0, dogfood_text)
        self.assertIn("Apply local jev toolset", dogfood_text)
        self.assertNotIn("Daily cloud build", dogfood_text)

        shifted = _run([str(PFY), "build", "p", "--help"], self.repo)
        shifted_text = (shifted.stdout or "") + (shifted.stderr or "")
        self.assertEqual(shifted.returncode, 0, shifted_text)
        self.assertIn("Apply local jev toolset", shifted_text)

        prompt_file = self.repo / "prompt.txt"
        prompt_file.write_text(" \n", encoding="utf-8")
        prompted = _run([str(PFY), "build", "--prompt-file", str(prompt_file)], self.repo)
        prompted_text = (prompted.stdout or "") + (prompted.stderr or "")
        self.assertEqual(prompted.returncode, 2, prompted_text)
        self.assertIn("Apply local jev toolset", prompted_text)
        self.assertNotIn("DRY-RUN", prompted_text)

        local = _run([str(PFY), "build", "--local", "--help"], self.repo)
        local_text = (local.stdout or "") + (local.stderr or "")
        self.assertEqual(local.returncode, 0, local_text)
        self.assertIn("Headless local-model build", local_text)

        daily = _run([str(PFY), "build", "--help"], self.repo)
        daily_text = (daily.stdout or "") + (daily.stderr or "")
        self.assertEqual(daily.returncode, 0, daily_text)
        self.assertIn('./pfy build "<task>"', daily_text)
        self.assertIn("jev dogfood wrap", daily_text)
        self.assertIn("opt-in fallback", daily_text)

        receipt_dir = SCRATCH / (self.id().replace(".", "_") + "-receipt")
        positional = _run(
            [
                str(PFY),
                "build",
                "add a note",
                "--dry-run",
                "--repo",
                str(self.repo),
                "--receipt-dir",
                str(receipt_dir),
            ],
            self.repo,
        )
        positional_text = (positional.stdout or "") + (positional.stderr or "")
        self.assertEqual(positional.returncode, 0, positional_text)
        payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "pfy-cloud-build/1")
        self.assertEqual(payload["status"], "DRY-RUN")
        self.assertIsNone(payload["commit"])


class CloudBuildPassTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def test_pass_matches_receipt_and_leaves_caller_clean(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    print('reasons: matches the task')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        caller = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        porcelain = _git(self.repo, "status", "--porcelain").stdout
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept value",
                "--repo",
                str(self.repo),
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
                "--timeout",
                "30",
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch, receipt_path = match.group(1), match.group(2)
        self.assertTrue(branch.startswith("cloud/"), branch)
        payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "pfy-cloud-build/1")
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["reason"], "ok")
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["branch"], branch)
        self.assertRegex(payload["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(payload["review"]["verdict"], "accept")
        self.assertIsInstance(payload["review"]["reasons"], list)
        self.assertGreaterEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][-1]["status"], "PASS")
        self.assertEqual(payload["gate"]["cmd"], "%s %s" % (sys.executable, gate))
        self.assertIsNotNone(payload["gate"]["before"])
        self.assertIsNotNone(payload["gate"]["after"])
        self.assertEqual(payload["recovery"], "")
        self.assertIs(payload["pushed"], False)
        self.assertIs(payload["worktree_removed"], True)
        self.assertEqual(_git(self.repo, "rev-parse", branch).stdout.strip(), payload["commit"])
        self.assertEqual(_git(self.repo, "rev-parse", branch + "^").stdout.strip(), head)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(_git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), caller)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, porcelain)
        self.assertEqual(_git(self.repo, "stash", "list").stdout.strip(), "")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("secret.txt", names)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
        self.assertIn("pipelines/dogfood/build-cloud/", receipt_path)

    def _accepting_grok(self) -> Path:
        return _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )

    def test_head_that_is_not_origin_main_exits_2_before_grok(self) -> None:
        # Fail: the run builds origin/main and drops the caller HEAD with no
        # warning, which is how the gom clone lost its bot-branch commits.
        # Recover: exit 2 and name --base. Pass --base origin/main to build
        # that older commit on purpose (see the next test).
        first = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        (self.repo / "later.txt").write_text("later\n", encoding="utf-8")
        _git(self.repo, "add", "later.txt")
        later = _git(self.repo, "commit", "-m", "later")
        self.assertEqual(later.returncode, 0, later.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        ref = _git(self.repo, "update-ref", "refs/remotes/origin/main", first)
        self.assertEqual(ref.returncode, 0, ref.stderr)
        marker = self.side / "grok-was-started"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--grok-cmd",
                str(grok),
                "--timeout",
                "30",
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertIn("Pass --base", text)
        self.assertIn(head[:12], text)
        self.assertIn(first[:12], text)
        self.assertFalse(marker.exists(), text)
        self.assertEqual(_git(self.repo, "branch", "--list", "cloud/*").stdout.strip(), "")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_explicit_origin_main_still_excludes_caller_only_commits(self) -> None:
        # Fail: --base origin/main builds the caller HEAD and commits later.txt.
        # Recover: the worktree parent is origin/main, and later.txt stays out.
        first = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        (self.repo / "later.txt").write_text("later\n", encoding="utf-8")
        _git(self.repo, "add", "later.txt")
        later = _git(self.repo, "commit", "-m", "later")
        self.assertEqual(later.returncode, 0, later.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        ref = _git(self.repo, "update-ref", "refs/remotes/origin/main", first)
        self.assertEqual(ref.returncode, 0, ref.stderr)
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n")
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--base",
                "origin/main",
                "--retries",
                "0",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(self._accepting_grok()),
                "--timeout",
                "30",
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(payload["base"], "origin/main")
        self.assertEqual(_git(self.repo, "rev-parse", branch + "^").stdout.strip(), first)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("later.txt", names)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_explicit_base_selects_that_ref(self) -> None:
        (self.repo / "later.txt").write_text("later\n", encoding="utf-8")
        _git(self.repo, "add", "later.txt")
        later = _git(self.repo, "commit", "-m", "later")
        self.assertEqual(later.returncode, 0, later.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n")
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--base",
                "HEAD",
                "--retries",
                "0",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(self._accepting_grok()),
                "--timeout",
                "30",
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(payload["base"], "HEAD")
        self.assertEqual(_git(self.repo, "rev-parse", match.group(1) + "^").stdout.strip(), head)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", match.group(1)).stdout.splitlines()
        self.assertIn("later.txt", names)
        self.assertIn("kept.py", names)

    def test_pass_does_not_push_the_cloud_branch(self) -> None:
        remote = self.side / "origin.git"
        bare = _git(self.side, "init", "--bare", str(remote))
        self.assertEqual(bare.returncode, 0, bare.stderr)
        added = _git(self.repo, "remote", "add", "origin", str(remote))
        self.assertEqual(added.returncode, 0, added.stderr)
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--base",
                "HEAD",
                "--retries",
                "0",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(self._accepting_grok()),
                "--timeout",
                "30",
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertTrue(branch.startswith("cloud/"), branch)
        self.assertIs(payload["pushed"], False)
        remote_refs = _git(self.repo, "ls-remote", "origin")
        self.assertEqual(remote_refs.returncode, 0, remote_refs.stderr)
        self.assertNotIn("cloud/", remote_refs.stdout)
        self.assertEqual(remote_refs.stdout.strip(), "")
        self.assertEqual(_git(self.repo, "rev-parse", branch).stdout.strip(), payload["commit"])


class CloudBuildRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _run_task(self, grok: Path, gate: Path, task: str, retries: str) -> subprocess.CompletedProcess:
        return _run(
            [
                sys.executable,
                str(CLOUD),
                task,
                "--repo",
                str(self.repo),
                "--retries",
                retries,
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
                "--timeout",
                "30",
            ],
            self.repo,
            env={"PFY_PROMPT_LOG": str(self.side / "prompts.txt")},
            timeout=60,
        )

    def test_gate_red_then_pass_commits_only_the_green_attempt(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "print('GATE-TAIL-RED')\n"
            "raise SystemExit(0 if Path('ready.txt').is_file() else 1)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "count = Path(os.environ['PFY_PROMPT_LOG'] + '.n')\n"
            "n = int(count.read_text()) + 1 if count.exists() else 1\n"
            "count.write_text(str(n))\n"
            "if n == 1:\n"
            "    Path('kept.py').write_text('bad = True\\n', encoding='utf-8')\n"
            "else:\n"
            "    Path('ready.txt').write_text('ok\\n', encoding='utf-8')\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "make the gate green", "1")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["reason"], "tests")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        self.assertEqual(_git(self.repo, "rev-list", "--count", head + ".." + branch).stdout.strip(), "1")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("ready.txt", names)
        prompts = (self.side / "prompts.txt").read_text(encoding="utf-8").split("---PROMPT---")
        implement = [item for item in prompts if "PFY-CLOUD-IMPLEMENT" in item and "PFY-CLOUD-REVIEW" not in item]
        self.assertGreaterEqual(len(implement), 2)
        self.assertIn("GATE-TAIL-RED", implement[1])

    def test_review_reject_then_accept(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    count = Path(os.environ['PFY_PROMPT_LOG'] + '.review')\n"
            "    n = int(count.read_text()) + 1 if count.exists() else 1\n"
            "    count.write_text(str(n))\n"
            "    if n == 1:\n"
            "        print('verdict: reject')\n"
            "        print('reasons: NEEDS-FIX-77')\n"
            "    else:\n"
            "        print('verdict: accept')\n"
            "        print('reasons: ok now')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "add kept value", "1")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(payload["attempts"][0]["status"], "PASS-REJECTED")
        self.assertEqual(payload["attempts"][0]["reason"], "review-rejected")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        self.assertEqual(payload["review"]["verdict"], "accept")
        self.assertEqual(_git(self.repo, "rev-list", "--count", head + ".." + match.group(1)).stdout.strip(), "1")
        prompts = (self.side / "prompts.txt").read_text(encoding="utf-8").split("---PROMPT---")
        implement = [item for item in prompts if item.startswith("\n") or "PFY-CLOUD-IMPLEMENT" in item]
        implement = [item for item in implement if "PFY-CLOUD-IMPLEMENT" in item and "PFY-CLOUD-REVIEW" not in item]
        self.assertGreaterEqual(len(implement), 2, prompts)
        self.assertIn("NEEDS-FIX-77", implement[1])
        self.assertIn("kept.py", implement[1])

    def test_review_reject_retry_that_times_out_stays_rejected(self) -> None:
        """A review reject whose retry does not finish stays review-rejected.

        dogfood2 row 07 ended TIMEOUT after a reject, with recovery that told
        Mark to raise --timeout. The sleeper must still be killed inside the
        run budget.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys, time\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: reject')\n"
            "    print('reasons: volume command is wrong')\n"
            "    raise SystemExit(0)\n"
            "mark = Path('attempt.txt')\n"
            "n = int(mark.read_text()) + 1 if mark.exists() else 1\n"
            "mark.write_text(str(n))\n"
            "if n == 1:\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "time.sleep(30)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        started = time.monotonic()
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "fix the volume command",
                "--repo",
                str(self.repo),
                "--retries",
                "1",
                "--timeout",
                "1",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            timeout=20,
        )
        elapsed = time.monotonic() - started
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertLess(elapsed, 12, text)
        self.assertEqual(proc.returncode, 1, text)
        payload = json.loads(
            list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertIn("volume command is wrong", payload["review"]["reasons"])
        self.assertIn("review rejected", payload["recovery"].lower())
        self.assertNotIn("larger --timeout", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(payload["attempts"][0]["status"], "PASS-REJECTED")
        self.assertEqual(payload["attempts"][0]["reason"], "review-rejected")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_receipt_records_whether_the_review_diff_was_truncated(self) -> None:
        """The receipt says if the review prompt's diff was cut at the cap.

        Dogfood2 F2: a short patch is review.truncated false and the prompt
        has no cut marker. A patch past the cap is true and the marker is in
        the prompt the reviewer actually received.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )

        def run_case(width: int, task: str) -> tuple[dict, str]:
            log = self.side / ("prompts-%d.txt" % width)
            grok = _write_exe(
                self.side / ("grok-%d.py" % width),
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "from pathlib import Path\n"
                "blob = '\\n'.join(sys.argv)\n"
                "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
                "if 'PFY-CLOUD-REVIEW' in blob:\n"
                "    print('verdict: accept')\n"
                "    raise SystemExit(0)\n"
                "Path('wide.py').write_text('x' * %d, encoding='utf-8')\n"
                "raise SystemExit(0)\n" % width,
            )
            proc = _run(
                [
                    sys.executable,
                    str(CLOUD),
                    task,
                    "--repo",
                    str(self.repo),
                    "--retries",
                    "0",
                    "--timeout",
                    "30",
                    "--test-cmd",
                    "%s %s" % (sys.executable, gate),
                    "--grok-cmd",
                    str(grok),
                ],
                self.repo,
                env={"PFY_PROMPT_LOG": str(log)},
                timeout=60,
            )
            text = (proc.stdout or "") + (proc.stderr or "")
            self.assertEqual(proc.returncode, 0, text)
            match = re.search(r"PASS ok branch=\S+ receipt=(\S+)", proc.stdout or "")
            self.assertIsNotNone(match, text)
            payload = json.loads(Path(match.group(1)).read_text(encoding="utf-8"))
            prompts = log.read_text(encoding="utf-8").split("---PROMPT---")
            review = [item for item in prompts if "PFY-CLOUD-REVIEW" in item]
            self.assertEqual(len(review), 1, prompts)
            return payload, review[0]

        short_payload, short_review = run_case(40, "add a short marker")
        self.assertIs(short_payload["review"]["truncated"], False)
        self.assertNotIn("...[diff truncated]", short_review)
        self.assertEqual(short_payload["review"]["verdict"], "accept")

        long_payload, long_review = run_case(20000, "add a long marker file")
        self.assertIs(long_payload["review"]["truncated"], True)
        self.assertIn("...[diff truncated]", long_review)
        self.assertEqual(long_payload["review"]["verdict"], "accept")
        self.assertLess(len(long_review), 20000)

    def test_review_rejected_diff_stays_after_the_worktree_is_removed(self) -> None:
        """A review reject keeps its unified diff after the worktree is dropped.

        Dogfood2 F3: row 07's reject was followed by a timeout, finish()
        removed the worktree, and the receipt had prose tails only. The
        rejected patch has to be on the attempt even though the tree is gone.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: reject')\n"
            "    print('reasons: volume command is wrong')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('docker volume rm -f pfy-hr-smoke\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "fix the volume command",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = json.loads(
            list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertTrue(payload["worktree_removed"])
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
        attempt = payload["attempts"][0]
        self.assertEqual(attempt["reason"], "review-rejected")
        diff = attempt["diff"]
        self.assertIn("diff --git", diff)
        self.assertIn("kept.py", diff)
        self.assertIn("docker volume rm -f pfy-hr-smoke", diff)
        self.assertNotIn("docker volume rm", attempt["output_tail"])
        self.assertIn("review rejected", payload["recovery"].lower())
        self.assertIsNone(payload["branch"])

    def test_final_review_reject_leaves_no_branch(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: reject')\n"
            "    print('reasons: still wrong')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        caller = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "add kept value", "1")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        payload = json.loads(list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["exit_code"], 1)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(_git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), caller)

    def test_root_delete_is_rejected_even_when_review_accepts(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('danger.sh').write_text('rm -rf /\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "Create danger.sh whose only line is rm -rf /.", "2")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        payload = json.loads(
            list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["exit_code"], 1)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertEqual(len(payload["attempts"]), 3)
        self.assertTrue(all(row["reason"] == "review-rejected" for row in payload["attempts"]))
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("danger.sh", _git(self.repo, "ls-tree", "-r", "--name-only", "HEAD").stdout)

    def test_target_marker_is_rejected_even_when_review_accepts(self) -> None:
        """A symlink :target marker must not land when review says accept.

        Fail: the diff records is_symlink and stores :target instead of the
        linked file's bytes, review prints accept, and the runner still
        creates a cloud branch. A real-HOME snapshot then misses content edits.
        Recover: reason review-rejected, exit 1, no branch, caller HEAD unchanged.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('tree_sig.py').write_text(\n"
            "    'def record(f):\\n'\n"
            "    '    if f.is_symlink():\\n'\n"
            "    '        return str(f) + \":target\"\\n'\n"
            "    '    return \"bytes\"\\n',\n"
            "    encoding='utf-8',\n"
            ")\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(
            grok,
            gate,
            "Record a symlink with readlink. Keep hashing the linked file bytes.",
            "0",
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        payload = json.loads(
            list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("tree_sig.py", _git(self.repo, "ls-tree", "-r", "--name-only", "HEAD").stdout)

    def test_gate_stays_red_for_the_default_three_attempts(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-TAIL-SPENT')\nraise SystemExit(1)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "cannot go green",
                "--repo",
                str(self.repo),
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
                "--timeout",
                "30",
            ],
            self.repo,
            env={"PFY_PROMPT_LOG": str(self.side / "prompts.txt")},
            timeout=60,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = json.loads(list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "tests")
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(len(payload["attempts"]), 3)
        self.assertTrue(all(row["reason"] == "tests" for row in payload["attempts"]))
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        prompts = (self.side / "prompts.txt").read_text(encoding="utf-8").split("---PROMPT---")
        implement = [item for item in prompts if "PFY-CLOUD-IMPLEMENT" in item]
        self.assertGreaterEqual(len(implement), 3, prompts)
        self.assertIn("GATE-TAIL-SPENT", implement[1])
        self.assertIn("GATE-TAIL-SPENT", implement[2])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)


class CloudBuildNoChangeTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _run_task(self, grok: Path, gate: Path, task: str, retries: str, extra: list[str] | None = None) -> subprocess.CompletedProcess:
        argv = [
            sys.executable,
            str(CLOUD),
            task,
            "--repo",
            str(self.repo),
            "--retries",
            retries,
            "--test-cmd",
            "%s %s" % (sys.executable, gate),
            "--grok-cmd",
            str(grok),
            "--timeout",
            "30",
        ]
        if extra:
            argv.extend(extra)
        return _run(
            argv,
            self.repo,
            env={"PFY_PROMPT_LOG": str(self.side / "prompts.txt")},
            timeout=60,
        )

    def test_no_change_runs_the_gate_and_does_not_pass(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-TAIL-EMPTY')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "change nothing", "1")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        payload = json.loads(list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "no-change")
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["branch"])
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertTrue(all(row["reason"] == "no-change" for row in payload["attempts"]))
        prompts = (self.side / "prompts.txt").read_text(encoding="utf-8").split("---PROMPT---")
        implement = [item for item in prompts if "PFY-CLOUD-IMPLEMENT" in item and "PFY-CLOUD-REVIEW" not in item]
        self.assertGreaterEqual(len(implement), 2, prompts)
        self.assertIn("GATE-TAIL-EMPTY", implement[1])
        self.assertIn("no-change", implement[1])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_gitignored_extra_file_is_absent_from_the_commit(self) -> None:
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "secret.txt\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        committed = _git(self.repo, "commit", "-m", "ignore secret")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "import sys\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "Path('secret.txt').write_text('should-not-commit\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, gate, "add kept only", "0")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("secret.txt", names)
        grepped = _git(self.repo, "grep", "should-not-commit", branch)
        self.assertNotEqual(grepped.returncode, 0)

    def test_staged_name_outside_the_reviewed_set_resets_and_does_not_commit(self) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        _write_exe(
            self.side / "git",
            "#!/usr/bin/env python3\n"
            "import os, sys, subprocess\n"
            "real = os.environ['REAL_GIT']\n"
            "args = sys.argv[1:]\n"
            "if 'diff' in args and '--cached' in args and '--name-only' in args:\n"
            "    proc = subprocess.run([real, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n"
            "    sys.stdout.buffer.write(proc.stdout + b'extra-not-reviewed.txt\\0')\n"
            "    sys.stderr.buffer.write(proc.stderr)\n"
            "    raise SystemExit(proc.returncode)\n"
            "os.execv(real, [real, *args])\n",
        )
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        env = os.environ.copy()
        env["TMPDIR"] = str(SCRATCH)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PATH"] = str(self.side) + os.pathsep + env.get("PATH", "")
        env["REAL_GIT"] = real_git
        proc = subprocess.run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--no-review",
                "--retries",
                "0",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
                "--timeout",
                "30",
            ],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = json.loads(list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["reason"], "scope-commit-mismatch")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("extra-not-reviewed.txt", _git(self.repo, "status", "--porcelain").stdout)

    def test_star_filename_commits_that_file_and_not_the_pyc(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('*').write_text('star-body\\n', encoding='utf-8')\n"
            "Path('__pycache__').mkdir(exist_ok=True)\n"
            "Path('__pycache__/x.pyc').write_bytes(b'pyc')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, gate, "add a star file", "0", extra=["--no-review"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("*", names)
        self.assertNotIn("__pycache__/x.pyc", names)
        shown = _git(self.repo, "show", branch + ":*")
        self.assertEqual(shown.stdout, "star-body\n")

    def test_gitignored_helper_fails_recheck_then_a_clean_retry_lands(self) -> None:
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "helper.py\n", encoding="utf-8")
        added = _git(self.repo, "add", ".gitignore")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "ignore helper")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path('.').resolve()))\n"
            "try:\n"
            "    import kept\n"
            "except Exception as exc:\n"
            "    print('GATE-IMPORT-FAIL %s' % exc)\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "if 'commit-recheck-failed' in blob:\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "Path('helper.py').write_text('VALUE = 1\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('import helper\\nvalue = helper.VALUE\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, gate, "add kept", "1")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["reason"], "commit-recheck-failed")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        self.assertEqual(_git(self.repo, "rev-list", "--count", head + ".." + branch).stdout.strip(), "1")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("helper.py", names)
        shown = _git(self.repo, "show", branch + ":kept.py")
        self.assertEqual(shown.stdout, "value = 1\n")
        self.assertNotIn("import helper", shown.stdout)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_recheck_tmpdir_stays_inside_the_extract(self) -> None:
        """The archive recheck must see temp files under the extract, not the worktree.

        Fail: the worktree gate passes because TMPDIR is the worktree tmp, then
        the recheck runs in repo/tmp/recheck-<sha> and TemporaryDirectory is
        still the worktree tmp, so relative_to raises and the commit is reset.
        Recover: TMPDIR for that gate is the extract tmp. The same command
        passes, and kept.py lands.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import tempfile\n"
            "from pathlib import Path\n"
            "root = Path('.').resolve()\n"
            "if not Path('kept.py').is_file():\n"
            "    print('GATE-NO-KEPT')\n"
            "    raise SystemExit(1)\n"
            "made = Path(tempfile.mkdtemp())\n"
            "try:\n"
            "    made.relative_to(root)\n"
            "except ValueError:\n"
            "    print('TMPDIR-OUTSIDE')\n"
            "    print(os.environ.get('TMPDIR', ''))\n"
            "    raise SystemExit(1)\n"
            "print('TMPDIR-INSIDE')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "add kept", "0", extra=["--no-review"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertNotIn("TMPDIR-OUTSIDE", text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", match.group(1)).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_recheck_git_does_not_walk_up_to_the_caller_repo(self) -> None:
        """The archive recheck is its own checkout, not the parent repo.

        Selfhost2 kolibri: the extract has no .git, so git ls-files walked up
        to the caller repo and the gate failed after review had accepted.
        Recovery is a recheck whose toplevel is the extract and whose index
        is the committed tree. A walk-up fails the gate and keeps no branch.
        """
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os, subprocess\n"
            "top = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)\n"
            "if top.returncode != 0:\n"
            "    print('NO-GIT')\n"
            "    print(top.stderr)\n"
            "    raise SystemExit(1)\n"
            "root = os.path.realpath(top.stdout.strip())\n"
            "here = os.path.realpath(os.getcwd())\n"
            "if root != here:\n"
            "    print('PARENT-GIT')\n"
            "    print(root)\n"
            "    raise SystemExit(1)\n"
            "if not os.path.isfile('kept.py'):\n"
            "    print('NO-KEPT')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, gate, "add kept value", "0", extra=["--no-review"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertNotIn("PARENT-GIT", text)
        self.assertNotIn("NO-GIT", text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, text)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["reason"], "ok")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertFalse(any(self.repo.joinpath("tmp").glob("recheck-*")))


def _dead(pid: int) -> bool:
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _stop_proc(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        try:
            proc.kill()
        except OSError:
            return
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()
        proc.wait(timeout=3)


def _wait_file(path: Path, seconds: float = 10) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return True
        time.sleep(0.05)
    return False


class CloudBuildFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _run_task(self, grok: Path | None, gate: Path | None, task: str, extra: list[str] | None = None, env: dict | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
        argv = [sys.executable, str(CLOUD), task, "--repo", str(self.repo), "--timeout", "30"]
        if gate is not None:
            argv.extend(["--test-cmd", "%s %s" % (sys.executable, gate)])
        if grok is not None:
            argv.extend(["--grok-cmd", str(grok)])
        if extra:
            argv.extend(extra)
        return _run(argv, self.repo, env=env, timeout=timeout)

    def _receipt(self) -> dict:
        path = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0]
        return json.loads(path.read_text(encoding="utf-8"))

    def _gate(self, name: str = "gate.py") -> Path:
        return _write_exe(
            self.side / name,
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )

    def test_rate_limit_exits_4_and_does_not_start_local(self) -> None:
        sentinel = self.side / "local-started"
        _write_exe(
            self.side / "pfy",
            "#!/bin/sh\nprintf started >> \"%s\"\n" % sentinel,
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\nprint('rate limit')\nraise SystemExit(1)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "hit-the-limit",
            extra=["--retries", "1"],
            env={"PATH": str(self.side) + os.pathsep + os.environ.get("PATH", "")},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 4, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertEqual(payload["reason"], "rate-limit")
        self.assertEqual(payload["exit_code"], 4)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(payload["recovery"], "./pfy build --local hit-the-limit")
        self.assertIn("./pfy build --local hit-the-limit", proc.stderr or "")
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertFalse(sentinel.exists())

    def test_rate_limit_and_auth_phrases_use_the_failure_table(self) -> None:
        rate_phrases = ("usage limit", "Quota Exceeded", "too many requests", "429")
        for phrase in rate_phrases:
            with self.subTest(phrase=phrase):
                receipt_dir = self.side / ("rate-" + re.sub(r"[^a-z0-9]+", "-", phrase.lower()).strip("-"))
                grok = _write_exe(
                    self.side / "grok.py",
                    "#!/usr/bin/env python3\nprint(%r)\nraise SystemExit(1)\n" % phrase,
                )
                proc = self._run_task(
                    grok,
                    self._gate(),
                    "phrase-task",
                    extra=["--retries", "1", "--receipt-dir", str(receipt_dir)],
                )
                text = (proc.stdout or "") + (proc.stderr or "")
                self.assertEqual(proc.returncode, 4, text)
                payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "BLOCKED")
                self.assertEqual(payload["reason"], "rate-limit")
                self.assertEqual(payload["recovery"], "./pfy build --local phrase-task")
                self.assertIsNone(payload["branch"])
        home = self.side / "empty-home"
        home.mkdir(exist_ok=True)
        for phrase in ("unauthenticated", "please log in", "auth.json"):
            with self.subTest(phrase=phrase):
                receipt_dir = self.side / ("auth-" + re.sub(r"[^a-z0-9]+", "-", phrase.lower()).strip("-"))
                grok = _write_exe(
                    self.side / "grok.py",
                    "#!/usr/bin/env python3\nimport sys\nsys.stderr.write(%r + '\\n')\nraise SystemExit(1)\n" % phrase,
                )
                proc = self._run_task(
                    grok,
                    self._gate(),
                    "auth-task",
                    extra=["--retries", "1", "--receipt-dir", str(receipt_dir)],
                    env={"HOME": str(home)},
                )
                text = (proc.stdout or "") + (proc.stderr or "")
                self.assertEqual(proc.returncode, 1, text)
                self.assertNotIn("Traceback", text)
                payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["reason"], "unauthenticated")
                self.assertIn("run grok once", payload["recovery"])
                self.assertNotIn("--local", payload["recovery"])
                self.assertIsNone(payload["branch"])
                self.assertFalse((home / "auth.json").exists())

    def test_embedded_429_follows_the_preflight_classifier(self) -> None:
        receipt_dir = self.side / "embedded-429"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\nprint('code 4291')\nraise SystemExit(1)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "embedded-429",
            extra=["--retries", "0", "--receipt-dir", str(receipt_dir)],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 4, text)
        payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertEqual(payload["reason"], "rate-limit")
        self.assertEqual(payload["recovery"], "./pfy build --local embedded-429")
        self.assertIsNone(payload["branch"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_zero_exit_with_rate_limit_text_is_not_blocked(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "print('rate limit')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), "write kept", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["reason"], "ok")
        self.assertNotEqual(payload["reason"], "rate-limit")
        self.assertTrue(payload["branch"].startswith("cloud/"))

    def test_not_logged_in_exits_1_and_does_not_suggest_local(self) -> None:
        home = self.side / "empty-home"
        home.mkdir()
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\nprint('not logged in')\nraise SystemExit(1)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "not-logged-in",
            extra=["--retries", "1"],
            env={"HOME": str(home)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("Traceback", text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "unauthenticated")
        self.assertIn("run grok once", payload["recovery"])
        self.assertIn("./pfy build not-logged-in", payload["recovery"])
        self.assertNotIn("--local", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertFalse((home / ".grok" / "auth.json").exists())
        self.assertFalse((home / "auth.json").exists())

    def test_not_signed_in_is_unauthenticated_on_zero_and_nonzero_exit(self) -> None:
        home = self.side / "empty-home"
        home.mkdir()
        message = (
            "Not signed in. To authenticate without a browser, run:\n"
            "  grok login --device-code\n"
        )
        for code in (0, 1):
            with self.subTest(code=code):
                receipt_dir = self.side / ("signed-in-%s" % code)
                grok = _write_exe(
                    self.side / "grok.py",
                    "#!/usr/bin/env python3\n"
                    "import sys\n"
                    "sys.stdout.write(%r)\n"
                    "raise SystemExit(%s)\n" % (message, code),
                )
                proc = self._run_task(
                    grok,
                    self._gate(),
                    "signed-out",
                    extra=["--retries", "0", "--no-review", "--receipt-dir", str(receipt_dir)],
                    env={"HOME": str(home)},
                )
                text = (proc.stdout or "") + (proc.stderr or "")
                self.assertEqual(proc.returncode, 1, text)
                payload = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "FAIL")
                self.assertEqual(payload["reason"], "unauthenticated")
                self.assertIn("run grok once", payload["recovery"])
                self.assertNotIn("--local", payload["recovery"])
                self.assertIsNone(payload["branch"])
                self.assertIsNone(payload["commit"])
                self.assertFalse((home / ".grok" / "auth.json").exists())
                self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_missing_grok_with_empty_home_does_not_raise(self) -> None:
        home = self.side / "empty-home"
        home.mkdir()
        missing = self.side / "no-such-grok"
        proc = self._run_task(
            missing,
            self._gate(),
            "missing-grok",
            env={"HOME": str(home)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("Traceback", text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "unauthenticated")
        self.assertIn("run grok once", payload["recovery"])
        self.assertNotIn("--local", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
        self.assertFalse((home / "auth.json").exists())
        self.assertFalse((home / ".grok").exists())

    def test_dirty_caller_file_stays_dirty_and_out_of_the_commit(self) -> None:
        (self.repo / "caller-dirty.txt").write_text("caller-only\n", encoding="utf-8")
        (self.repo / "README.md").write_text("fixture\ndirty edit\n", encoding="utf-8")
        before = _git(self.repo, "status", "--porcelain").stdout
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        caller = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("caller-dirty.txt", names)
        shown = _git(self.repo, "show", payload["commit"] + ":README.md").stdout
        self.assertEqual(shown, "fixture\n")
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertIn("caller-dirty.txt", before)
        self.assertEqual(_git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), caller)

    def test_staged_caller_file_stays_staged_and_out_of_the_commit(self) -> None:
        (self.repo / "staged-dirty.txt").write_text("staged-only\n", encoding="utf-8")
        added = _git(self.repo, "add", "staged-dirty.txt")
        self.assertEqual(added.returncode, 0, added.stderr)
        (self.repo / "untracked-dirty.txt").write_text("free\n", encoding="utf-8")
        before = _git(self.repo, "status", "--porcelain").stdout
        self.assertIn("A  staged-dirty.txt", before)
        self.assertIn("?? untracked-dirty.txt", before)
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("staged-dirty.txt", names)
        self.assertNotIn("untracked-dirty.txt", names)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_sigint_interrupts_with_no_branch(self) -> None:
        pidfile = self.side / "grok.pid"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CLOUD_PIDFILE']).write_text(str(os.getpid()))\n"
            "time.sleep(60)\n",
        )
        gate = self._gate()
        proc = subprocess.Popen(
            [
                sys.executable,
                str(CLOUD),
                "sleeping task",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            cwd=self.repo,
            env={**os.environ, "TMPDIR": str(SCRATCH), "PYTHONDONTWRITEBYTECODE": "1", "PFY_CLOUD_PIDFILE": str(pidfile)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.addCleanup(_stop_proc, proc)
        self.assertTrue(_wait_file(pidfile), "grok did not start")
        time.sleep(0.1)
        grok_pid = int(pidfile.read_text(encoding="utf-8").strip())
        self.addCleanup(lambda: None if _dead(grok_pid) else os.kill(grok_pid, signal.SIGKILL))
        os.kill(proc.pid, signal.SIGINT)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            _stop_proc(proc)
            self.fail("runner did not exit after SIGINT")
        text = (out or "") + (err or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "interrupted")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertTrue(_dead(grok_pid))

    def test_sigterm_interrupts_with_no_branch(self) -> None:
        pidfile = self.side / "grok.pid"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CLOUD_PIDFILE']).write_text(str(os.getpid()))\n"
            "time.sleep(60)\n",
        )
        gate = self._gate()
        proc = subprocess.Popen(
            [
                sys.executable,
                str(CLOUD),
                "sleeping task",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            cwd=self.repo,
            env={**os.environ, "TMPDIR": str(SCRATCH), "PYTHONDONTWRITEBYTECODE": "1", "PFY_CLOUD_PIDFILE": str(pidfile)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.addCleanup(_stop_proc, proc)
        self.assertTrue(_wait_file(pidfile), "grok did not start")
        time.sleep(0.1)
        grok_pid = int(pidfile.read_text(encoding="utf-8").strip())
        self.addCleanup(lambda: None if _dead(grok_pid) else os.kill(grok_pid, signal.SIGKILL))
        os.kill(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            _stop_proc(proc)
            self.fail("runner did not exit after SIGTERM")
        text = (out or "") + (err or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "interrupted")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertTrue(_dead(grok_pid))

    def test_timeout_exits_3_and_kills_the_grok_group(self) -> None:
        pidfile = self.side / "grok.pid"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CLOUD_PIDFILE']).write_text(str(os.getpid()))\n"
            "time.sleep(60)\n",
        )
        started = time.monotonic()
        proc = self._run_task(
            grok,
            self._gate(),
            "too slow",
            extra=["--timeout", "1", "--retries", "0"],
            env={"PFY_CLOUD_PIDFILE": str(pidfile)},
            timeout=20,
        )
        elapsed = time.monotonic() - started
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        self.assertLess(elapsed, 15)
        payload = self._receipt()
        self.assertEqual(payload["status"], "TIMEOUT")
        self.assertEqual(payload["reason"], "timeout")
        self.assertEqual(payload["exit_code"], 3)
        self.assertIsNone(payload["branch"])
        self.assertTrue(_wait_file(pidfile))
        self.assertTrue(_dead(int(pidfile.read_text(encoding="utf-8").strip())))

    def test_review_call_stops_at_the_run_budget(self) -> None:
        """One attempt's review call does not get a fresh full --timeout.

        The run budget is --timeout times the attempt count. After the
        implement call has used most of it, the review call is killed on
        the time that is left, not after another full --timeout.
        """
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys, time\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    time.sleep(30)\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "time.sleep(2.0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        started = time.monotonic()
        proc = self._run_task(
            grok,
            self._gate(),
            "add kept value",
            extra=["--timeout", "3", "--retries", "0"],
            timeout=20,
        )
        elapsed = time.monotonic() - started
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        self.assertLess(elapsed, 6.0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "TIMEOUT")
        self.assertEqual(payload["reason"], "timeout")
        self.assertEqual(payload["exit_code"], 3)
        self.assertIn("larger --timeout", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])

    def test_sigkill_during_grok_reap_kills_that_grok(self) -> None:
        gate_pidfile = self.side / "gate.pid"
        grok_pidfile = self.side / "grok.pid"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_GATE_PIDFILE']).write_text(str(os.getpid()))\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CLOUD_PIDFILE']).write_text(str(os.getpid()))\n"
            "time.sleep(60)\n",
        )
        local_sleeper = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(_stop_proc, local_sleeper)
        local_pids = self.repo / "tmp" / "local-build.pids.json"
        local_pids.parent.mkdir(parents=True, exist_ok=True)
        local_pids.write_text(
            json.dumps({"pid": local_sleeper.pid, "pgid": os.getpgid(local_sleeper.pid)}),
            encoding="utf-8",
        )
        local_bytes = local_pids.read_bytes()
        proc = subprocess.Popen(
            [
                sys.executable,
                str(CLOUD),
                "sleeping task",
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
            ],
            cwd=self.repo,
            env={
                **os.environ,
                "TMPDIR": str(SCRATCH),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PFY_GATE_PIDFILE": str(gate_pidfile),
                "PFY_CLOUD_PIDFILE": str(grok_pidfile),
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.addCleanup(_stop_proc, proc)

        def _kill_grok() -> None:
            if not grok_pidfile.is_file():
                return
            pid = int(grok_pidfile.read_text(encoding="utf-8").strip() or "0")
            if pid > 0 and not _dead(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    return

        self.addCleanup(_kill_grok)
        self.assertTrue(_wait_file(grok_pidfile), "grok did not start")
        self.assertTrue(_wait_file(gate_pidfile), "gate did not start")
        cloud_pids = self.repo / "tmp" / "cloud-build.pids.json"
        self.assertTrue(cloud_pids.is_file(), "runner did not write a pid file")
        recorded = json.loads(cloud_pids.read_text(encoding="utf-8"))
        grok_pid = int(grok_pidfile.read_text(encoding="utf-8").strip())
        gate_pid = int(gate_pidfile.read_text(encoding="utf-8").strip())
        self.assertEqual(recorded.get("agent_pgid"), grok_pid)
        self.assertNotEqual(recorded.get("agent_pgid"), gate_pid)
        self.assertFalse(_dead(grok_pid))
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stderr is not None:
            proc.stderr.close()
        self.assertFalse(_dead(grok_pid))
        reap = _run([sys.executable, str(CLOUD), "--reap", "--repo", str(self.repo)], self.repo, timeout=20)
        text = (reap.stdout or "") + (reap.stderr or "")
        self.assertEqual(reap.returncode, 0, text)
        self.assertTrue(_dead(grok_pid), text)
        self.assertFalse(_dead(local_sleeper.pid))
        self.assertEqual(local_pids.read_bytes(), local_bytes)
        receipt_dir = Path(str(recorded.get("receipt_dir") or ""))
        aborted = json.loads((receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")
        self.assertIn("Mark:", aborted["recovery"])
        self.assertIn("--reap", aborted["recovery"])
        self.assertNotIn("--local", aborted["recovery"])
        self.assertIsNone(aborted["branch"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_reap_aborts_a_dead_cloud_pid_and_spares_a_local_only_pid(self) -> None:
        stale = self.side / "killed-run"
        stale.mkdir()
        local_sleeper = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(_stop_proc, local_sleeper)
        inner_path = self.side / "inner.pid"
        leader = subprocess.Popen(
            ["bash", "-c", 'sleep 60 & echo $! > "%s"; wait' % inner_path],
            start_new_session=True,
        )
        self.addCleanup(_stop_proc, leader)
        self.assertTrue(_wait_file(inner_path), "inner child did not start")
        inner = int(inner_path.read_text(encoding="utf-8").strip())
        self.addCleanup(lambda: None if _dead(inner) else os.kill(inner, signal.SIGKILL))
        os.kill(leader.pid, signal.SIGKILL)
        leader.wait(timeout=5)
        self.assertTrue(_dead(leader.pid))
        self.assertFalse(_dead(inner))
        cloud_pids = self.repo / "tmp" / "cloud-build.pids.json"
        local_pids = self.repo / "tmp" / "local-build.pids.json"
        cloud_pids.parent.mkdir(parents=True, exist_ok=True)
        cloud_pids.write_text(
            json.dumps(
                {
                    "pid": leader.pid,
                    "pgid": os.getpgid(inner),
                    "agent_pgid": os.getpgid(inner),
                    "receipt_dir": str(stale),
                }
            ),
            encoding="utf-8",
        )
        local_pids.write_text(
            json.dumps(
                {
                    "pid": local_sleeper.pid,
                    "pgid": os.getpgid(local_sleeper.pid),
                    "agent_pgid": os.getpgid(local_sleeper.pid),
                }
            ),
            encoding="utf-8",
        )
        local_bytes = local_pids.read_bytes()
        proc = _run([sys.executable, str(CLOUD), "--reap", "--repo", str(self.repo)], self.repo, timeout=20)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertFalse(_dead(local_sleeper.pid))
        self.assertEqual(local_pids.read_bytes(), local_bytes)
        self.assertTrue(_dead(inner))
        aborted = json.loads((stale / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")
        self.assertIn("Mark:", aborted["recovery"])
        self.assertIn("--reap", aborted["recovery"])
        self.assertFalse(cloud_pids.exists())

    def test_reap_leaves_a_live_recorded_pid_alone(self) -> None:
        stale = self.side / "live-run"
        stale.mkdir()
        sleeper = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(_stop_proc, sleeper)
        cloud_pids = self.repo / "tmp" / "cloud-build.pids.json"
        cloud_pids.parent.mkdir(parents=True, exist_ok=True)
        cloud_pids.write_text(
            json.dumps(
                {
                    "pid": sleeper.pid,
                    "pgid": os.getpgid(sleeper.pid),
                    "agent_pgid": os.getpgid(sleeper.pid),
                    "receipt_dir": str(stale),
                }
            ),
            encoding="utf-8",
        )
        proc = _run([sys.executable, str(CLOUD), "--reap", "--repo", str(self.repo)], self.repo, timeout=20)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("reaped: none", proc.stdout or "")
        self.assertFalse(_dead(sleeper.pid))
        self.assertTrue(cloud_pids.is_file())
        self.assertFalse((stale / "receipt.json").exists())

    def test_receipt_redacts_tokens_keys_and_private_key_blocks(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "print('key AKIAIOSFODNN7EXAMPLE')\n"
            "print('sk_live_abcdefghij')\n"
            "print('Authorization: Bearer FAKEBEARERTOKEN')\n"
            "print('API_TOKEN=FAKETOKENVALUE')\n"
            "print('-----BEGIN PRIVATE KEY-----')\n"
            "print('MIIBsecret')\n"
            "print('-----END PRIVATE KEY-----')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        raw = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(encoding="utf-8")
        self.assertNotIn("AKIA", raw)
        self.assertNotIn("BEGIN PRIVATE KEY", raw)
        self.assertNotIn("sk_", raw)
        self.assertNotIn("FAKEBEARERTOKEN", raw)
        self.assertNotIn("FAKETOKENVALUE", raw)
        self.assertIn("[redacted]", raw)
        payload = json.loads(raw)
        shown = _git(self.repo, "show", payload["commit"] + ":kept.py")
        self.assertEqual(shown.stdout, "value = 1\n")

    def test_receipt_redacts_an_xai_marker_in_the_task_and_the_reply(self) -> None:
        marker = "xai-FAKE0000"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "print(%r)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % marker,
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "Create kept.py containing exactly the line value = 1. Print %s once." % marker,
            extra=["--no-review", "--retries", "0"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        path = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0]
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        self.assertEqual(payload["status"], "PASS")
        self.assertNotIn(marker, raw)
        self.assertNotIn(marker.lower(), raw)
        self.assertIn("[redacted]", raw)
        self.assertNotIn(marker, payload["task"])
        self.assertNotIn(marker, payload["attempts"][0]["output_tail"])
        shown = _git(self.repo, "show", payload["commit"] + ":kept.py")
        self.assertEqual(shown.stdout, "value = 1\n")

    def test_receipt_keeps_fixture_ids_and_still_hides_secret_assignments(self) -> None:
        # Fail: user_key=list-user and token=RAWTOKEN-only-in-source become
        # [redacted], so the gate tail no longer shows the assertion.
        # Recover: leave those fixture values, and still hide API_TOKEN and
        # password values.
        secret_value = "abcd1234EFGHijkl"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "print('user_key=list-user')\n"
            "print('token=land-user')\n"
            "print('token=RAWTOKEN-only-in-source')\n"
            "print('API_TOKEN=%s')\n"
            "print('password=hunter2')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % secret_value,
        )
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        raw = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
            encoding="utf-8"
        )
        self.assertIn("user_key=list-user", raw)
        self.assertIn("token=land-user", raw)
        self.assertIn("token=RAWTOKEN-only-in-source", raw)
        self.assertNotIn(secret_value, raw)
        self.assertNotIn("hunter2", raw)
        self.assertIn("API_TOKEN=[redacted]", raw)
        self.assertIn("password=[redacted]", raw)

    def test_gate_drops_secret_env_and_grok_still_sees_it(self) -> None:
        # Fail: the product gate prints GROK_API_KEY set, so a foreign test
        # can read the operator environment.
        # Recover: the gate reports those names unset and still has PATH.
        # Grok still sees the key, so an env login is not stripped from it.
        marker = "fixture-not-a-live-key"
        saw = self.side / "grok-saw.txt"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(%r).write_text(\n"
            "    'GROK-SAW' if os.environ.get('GROK_API_KEY') == %r else 'GROK-MISSED',\n"
            "    encoding='utf-8',\n"
            ")\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % (str(saw), marker),
        )
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "for name in ('GROK_API_KEY', 'MY_PASSWORD', 'PATH'):\n"
            "    print('%s %s' % (name, 'set' if os.environ.get(name) else 'unset'))\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(
            grok,
            gate,
            "add kept",
            extra=["--no-review", "--retries", "0"],
            env={"GROK_API_KEY": marker, "MY_PASSWORD": "fixture-password"},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        raw = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0].read_text(
            encoding="utf-8"
        )
        self.assertIn("GROK_API_KEY unset", raw)
        self.assertIn("MY_PASSWORD unset", raw)
        self.assertIn("PATH set", raw)
        self.assertNotIn(marker, raw)
        self.assertNotIn("fixture-password", raw)
        self.assertEqual(saw.read_text(encoding="utf-8"), "GROK-SAW")

    def test_missing_gate_binary_exits_2_before_grok(self) -> None:
        # Fail: a missing gate is a product FAIL and grok still runs.
        # Recover: exit 2, reason gate-missing, and no grok call.
        marker = self.side / "grok-was-started"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        proc = self._run_task(
            grok,
            None,
            "add kept",
            extra=["--test-cmd", "/no/such/pfy-gate-1031", "--no-review", "--retries", "0"],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertIn("Pass --test-cmd", text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "gate-missing")
        self.assertEqual(payload["exit_code"], 2)
        self.assertIsNone(payload["branch"])
        self.assertFalse(marker.exists(), text)
        self.assertIn("--test-cmd", payload["recovery"])

    def test_default_gate_import_error_exits_2_before_grok(self) -> None:
        # Fail: python3 -m unittest discover cannot import the repo, and the
        # runner spends grok retries as if the product tests were red.
        # Recover: exit 2, reason gate-unusable, and ask for --test-cmd.
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_env.py").write_text(
            "import definitely_missing_pfy_mod_1031\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/__init__.py", "tests/test_env.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "red import")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        marker = self.side / "grok-was-started"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        proc = self._run_task(grok, None, "add kept", extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "gate-unusable")
        self.assertEqual(payload["exit_code"], 2)
        self.assertFalse(marker.exists(), text)
        self.assertIn("definitely_missing_pfy_mod_1031", payload["gate"]["before"]["tail"])
        self.assertIn("--test-cmd", payload["recovery"])

    def test_custom_gate_import_error_still_reaches_grok(self) -> None:
        # Fail: any "No module named" line exits 2, so a red product import
        # never reaches the model.
        # Recover: a custom --test-cmd that fails this way still calls grok
        # and records reason tests.
        marker = self.side / "grok-was-started"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path(%r).write_text('started\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n" % str(marker),
        )
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "print(\"No module named 'kept'\")\n"
            "raise SystemExit(1)\n",
        )
        proc = self._run_task(grok, gate, "add kept", extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests")
        self.assertTrue(marker.exists(), text)
        self.assertNotEqual(payload["reason"], "gate-unusable")

    def test_protected_auth_json_is_not_committed(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('auth.json').write_text('{}\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), "do not touch auth", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "protected-path-changed")
        self.assertIn("Mark:", payload["recovery"])
        self.assertIn("auth.json", payload["recovery"])
        self.assertNotIn("--local", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_every_failure_reason_receipt_has_a_recovery_line(self) -> None:
        mod = _load_cloud()
        samples = (
            (1, "rate limit hit", "", "rate-limit"),
            (1, "please log in", "", "unauthenticated"),
            (1, "Not signed in", "", "other"),
            (0, "rate limit", "", "other"),
            (1, "boom", "", "other"),
        )
        seen = set()
        for rc, out, err, expected in samples:
            got = mod.classify_cloud_failure(rc, out, err)
            self.assertEqual(got, expected, "%s %s" % (rc, out))
            seen.add(got)
        self.assertEqual(seen, {"rate-limit", "unauthenticated", "other"})
        reasons = tuple(mod.TERMINAL_FAILURE_REASONS)
        self.assertNotIn("other", reasons)
        self.assertNotIn("ok", reasons)
        self.assertNotIn("dry-run", reasons)
        for kind in ("rate-limit", "unauthenticated"):
            self.assertIn(kind, reasons)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        for reason in reasons:
            args = mod.parse_args(
                [
                    "task %s" % reason,
                    "--repo",
                    str(self.repo),
                    "--retries",
                    "0",
                    "--timeout",
                    "30",
                    "--test-cmd",
                    "true",
                ]
            )
            build = mod.CloudBuild(args, self.repo, "HEAD", head, None)
            status = "BLOCKED" if reason == "rate-limit" else "TIMEOUT" if reason == "timeout" else "FAIL"
            code = 4 if reason == "rate-limit" else 3 if reason == "timeout" else 1
            build.fail(status, reason, code, "")
            payload = json.loads(build.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["reason"], reason)
            self.assertNotEqual(payload["status"], "PASS")
            self.assertTrue((payload.get("recovery") or "").strip(), reason)
            if reason == "rate-limit":
                self.assertIn("./pfy build --local", payload["recovery"])
            elif reason == "unauthenticated":
                self.assertIn("run grok once", payload["recovery"])
                self.assertNotIn("--local", payload["recovery"])
            else:
                self.assertNotIn("--local", payload["recovery"])
                self.assertIn("Mark:", payload["recovery"])
        crashed = mod.CloudBuild(
            mod.parse_args(["task crash", "--repo", str(self.repo), "--retries", "0", "--test-cmd", "true"]),
            self.repo,
            "HEAD",
            head,
            None,
        )
        crashed.reason = "runner-crash"
        crashed.status = "FAIL"
        crashed.exit_code = 1
        crashed.recovery = ""
        crashed.record(0, "FAIL", "runner-crash", "boom")
        crashed.finish()
        crash_payload = json.loads(crashed.receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(crash_payload["reason"], "runner-crash")
        self.assertIn("Mark:", crash_payload["recovery"])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_direct_grok_home_fails_then_a_clean_retry_lands(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import shutil\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "if 'protected-path-changed' in blob:\n"
            "    shutil.rmtree('pipelines/dogfood/grok-home', ignore_errors=True)\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "Path('pipelines/dogfood/grok-home').mkdir(parents=True, exist_ok=True)\n"
            "Path('pipelines/dogfood/grok-home/token').write_text('secret-token\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--retries", "1"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["reason"], "protected-path-changed")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn("pipelines/dogfood/grok-home/token", names)
        shown = _git(self.repo, "show", branch + ":kept.py")
        self.assertEqual(shown.stdout, "value = 1\n")
        self.assertEqual(_git(self.repo, "rev-list", "--count", head + ".." + branch).stdout.strip(), "1")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_env_and_pem_fail_then_a_clean_retry_lands(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "if 'protected-path-changed' in blob:\n"
            "    Path('.env').unlink(missing_ok=True)\n"
            "    Path('keys/id.pem').unlink(missing_ok=True)\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "Path('keys').mkdir(parents=True, exist_ok=True)\n"
            "Path('.env').write_text('TOKEN=secret\\n', encoding='utf-8')\n"
            "Path('keys/id.pem').write_text('pem-body\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--retries", "1"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        match = re.search(r"PASS ok branch=(\S+) receipt=(\S+)", proc.stdout or "")
        self.assertIsNotNone(match, proc.stdout)
        branch = match.group(1)
        payload = json.loads(Path(match.group(2)).read_text(encoding="utf-8"))
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["reason"], "protected-path-changed")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        self.assertIn("kept.py", names)
        self.assertNotIn(".env", names)
        self.assertNotIn("keys/id.pem", names)
        self.assertEqual(_git(self.repo, "show", branch + ":kept.py").stdout, "value = 1\n")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_keep_worktree_leaves_the_directory(self) -> None:
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--keep-worktree", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertFalse(payload["worktree_removed"])
        self.assertTrue((self.repo / "tmp" / "cloud-build").is_dir())
        self.assertTrue(any((self.repo / "tmp" / "cloud-build").iterdir()))

    def test_no_review_skips_the_second_grok_call(self) -> None:
        count = self.side / "calls.txt"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_CALL_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(
            grok,
            self._gate(),
            "add kept",
            extra=["--no-review", "--retries", "2"],
            env={"PFY_CALL_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["review"]["verdict"], "skipped")
        self.assertNotEqual(payload["review"]["verdict"], "accept")
        self.assertEqual(count.read_text(encoding="utf-8"), "1")
        self.assertEqual(len(payload["attempts"]), 1)

    def test_long_task_subject_stops_on_a_word_and_the_body_keeps_the_rest(self) -> None:
        # Fail: the subject is task[:72], which ends inside "rather".
        # Recover: stop on the previous word and put the full task in the body.
        task = (
            "Timeout reasons must name the sub-step command overtimeandfestival "
            "rather than the entry"
        )
        flat = " ".join(task.split())
        self.assertGreater(len(flat), 72)
        self.assertNotEqual(flat[71], " ")
        self.assertNotEqual(flat[72], " ")
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), task, extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        subject = _git(self.repo, "log", "-1", "--format=%s", payload["commit"]).stdout.strip()
        body = _git(self.repo, "log", "-1", "--format=%b", payload["commit"]).stdout
        self.assertLessEqual(len(subject), 72, subject)
        self.assertTrue(subject.endswith("..."), subject)
        prefix = subject[:-3]
        self.assertTrue(flat.startswith(prefix + " "), subject)
        self.assertNotIn("rathe", subject)
        self.assertIn(flat, body)
        self.assertIn("rather than the entry", body)

    def test_short_task_subject_is_the_whole_task(self) -> None:
        # Fail: a short task grows an ellipsis or drops a word.
        # Recover: the subject is the task, and the body does not repeat it.
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = self._run_task(grok, self._gate(), "add kept", extra=["--no-review", "--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        subject = _git(self.repo, "log", "-1", "--format=%s", payload["commit"]).stdout.strip()
        body = _git(self.repo, "log", "-1", "--format=%b", payload["commit"]).stdout.strip()
        self.assertEqual(subject, "add kept")
        self.assertEqual(body, "")


class CloudBuildGateReasonTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _receipt(self) -> dict:
        path = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))[0]
        return json.loads(path.read_text(encoding="utf-8"))

    def test_changed_test_file_fails_before_the_gate_and_is_not_committed(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/test_keep.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "keep")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "print('GATE-SHOULD-NOT-RERUN')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests/test_keep.py').write_text('def test_keep():\\n    assert False\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "do not edit tests",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-tampered")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(count.read_text(encoding="utf-8"), "1")
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_writable_test_lets_that_base_file_change_and_land(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        (tests / "test_edit.py").write_text(
            "def test_edit():\n    assert True\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/test_keep.py", "tests/test_edit.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "tests")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "edit = Path('tests/test_edit.py').read_text(encoding='utf-8')\n"
            "keep = Path('tests/test_keep.py').read_text(encoding='utf-8')\n"
            "if 'assert 1 == 1' not in edit or 'assert True' not in keep:\n"
            "    print('GATE-NEED-EDIT')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('tests/test_edit.py').write_text('def test_edit():\\n    assert 1 == 1\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "update the named test",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--writable-test",
                "tests/test_edit.py",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["reason"], "ok")
        shown = _git(self.repo, "show", payload["commit"] + ":tests/test_edit.py")
        self.assertIn("assert 1 == 1", shown.stdout)
        kept = _git(self.repo, "show", payload["commit"] + ":tests/test_keep.py")
        self.assertEqual(kept.stdout, "def test_keep():\n    assert True\n")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("kept.py", names)

    def test_two_writable_tests_land_and_a_third_base_file_does_not(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
        (tests / "test_b.py").write_text("def test_b():\n    assert True\n", encoding="utf-8")
        (tests / "test_gate.py").write_text("def test_gate():\n    assert True\n", encoding="utf-8")
        added = _git(self.repo, "add", "tests/test_a.py", "tests/test_b.py", "tests/test_gate.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "tests")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "a = Path('tests/test_a.py').read_text(encoding='utf-8')\n"
            "b = Path('tests/test_b.py').read_text(encoding='utf-8')\n"
            "gate = Path('tests/test_gate.py').read_text(encoding='utf-8')\n"
            "if 'assert 1 == 1' not in a or 'assert 2 == 2' not in b or gate != 'def test_gate():\\n    assert True\\n':\n"
            "    print('GATE-NEED-BOTH')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "if 'tests-tampered' in blob:\n"
            "    Path('tests/test_gate.py').write_text('def test_gate():\\n    assert True\\n', encoding='utf-8')\n"
            "    Path('tests/test_a.py').write_text('def test_a():\\n    assert 1 == 1\\n', encoding='utf-8')\n"
            "    Path('tests/test_b.py').write_text('def test_b():\\n    assert 2 == 2\\n', encoding='utf-8')\n"
            "    Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "Path('tests/test_a.py').write_text('def test_a():\\n    assert 1 == 1\\n', encoding='utf-8')\n"
            "Path('tests/test_b.py').write_text('def test_b():\\n    assert 2 == 2\\n', encoding='utf-8')\n"
            "Path('tests/test_gate.py').write_text('def test_gate():\\n    assert False\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "edit the two named tests",
                "--repo",
                str(self.repo),
                "--retries",
                "1",
                "--timeout",
                "30",
                "--writable-test",
                "tests/test_a.py",
                "--writable-test",
                "tests/test_b.py",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(len(payload["attempts"]), 2)
        self.assertEqual(payload["attempts"][0]["reason"], "tests-tampered")
        self.assertEqual(payload["attempts"][1]["status"], "PASS")
        self.assertIn("assert 1 == 1", _git(self.repo, "show", payload["commit"] + ":tests/test_a.py").stdout)
        self.assertIn("assert 2 == 2", _git(self.repo, "show", payload["commit"] + ":tests/test_b.py").stdout)
        self.assertEqual(
            _git(self.repo, "show", payload["commit"] + ":tests/test_gate.py").stdout,
            "def test_gate():\n    assert True\n",
        )
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_writable_test_does_not_cover_a_different_base_file(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        (tests / "test_edit.py").write_text(
            "def test_edit():\n    assert True\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/test_keep.py", "tests/test_edit.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "tests")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "print('GATE-SHOULD-NOT-RERUN')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests/test_keep.py').write_text('def test_keep():\\n    assert False\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "do not edit the other test",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--writable-test",
                "tests/test_edit.py",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-tampered")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(count.read_text(encoding="utf-8"), "1")

    def test_deleted_base_test_fails_before_the_gate_and_is_not_committed(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/test_keep.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "keep")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "print('GATE-SHOULD-NOT-RERUN')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('tests/test_keep.py').unlink()\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "do not delete tests",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-tampered")
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["gate"]["after"])
        self.assertEqual(count.read_text(encoding="utf-8"), "1")
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_new_test_file_reaches_the_gate_and_lands(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_keep.py").write_text(
            "def test_keep():\n    assert True\n",
            encoding="utf-8",
        )
        added = _git(self.repo, "add", "tests/test_keep.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "keep")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "if not Path('tests/test_added.py').is_file():\n"
            "    print('GATE-NEED-NEW-TEST')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('tests').mkdir(exist_ok=True)\n"
            "Path('tests/test_added.py').write_text('def test_added():\\n    assert True\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add a new test",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["reason"], "ok")
        self.assertEqual(payload["gate"]["before"]["exit"], 1)
        self.assertEqual(payload["gate"]["after"]["exit"], 0)
        self.assertIn("GATE-OK", payload["gate"]["after"]["tail"])
        self.assertEqual(count.read_text(encoding="utf-8"), "4")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["commit"]).stdout.splitlines()
        self.assertIn("tests/test_added.py", names)
        self.assertIn("kept.py", names)
        shown = _git(self.repo, "show", payload["commit"] + ":tests/test_keep.py")
        self.assertEqual(shown.stdout, "def test_keep():\n    assert True\n")

    def test_second_green_gate_that_goes_red_is_flaky_and_not_committed(self) -> None:
        count = self.side / "gate-count"
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_GATE_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "print('GATE-FLAKY-TAIL')\n"
            "raise SystemExit(1 if n >= 3 else 0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--no-review",
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_GATE_COUNT": str(count)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "tests-flaky")
        self.assertEqual(payload["attempts"][0]["reason"], "tests-flaky")
        self.assertIsNone(payload["commit"])
        self.assertIn("GATE-FLAKY-TAIL", payload["gate"]["after"]["tail"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_worktree_add_failure_leaves_the_caller_dirty_file(self) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        _write_exe(
            self.side / "git",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "real = os.environ['REAL_GIT']\n"
            "args = sys.argv[1:]\n"
            "if 'worktree' in args and 'add' in args:\n"
            "    sys.stderr.write('worktree add refused\\n')\n"
            "    raise SystemExit(1)\n"
            "os.execv(real, [real, *args])\n",
        )
        calls = self.side / "calls.txt"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CALL_COUNT']).write_text('called\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        (self.repo / "caller-dirty.txt").write_text("stay\n", encoding="utf-8")
        before = _git(self.repo, "status", "--porcelain").stdout
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        env = os.environ.copy()
        env["TMPDIR"] = str(SCRATCH)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PATH"] = str(self.side) + os.pathsep + env.get("PATH", "")
        env["REAL_GIT"] = real_git
        env["PFY_CALL_COUNT"] = str(calls)
        proc = subprocess.run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "true",
                "--grok-cmd",
                str(grok),
            ],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "worktree-failed")
        self.assertIn("Mark:", payload["recovery"])
        self.assertIn("worktree", payload["recovery"].lower())
        self.assertNotIn("--local", payload["recovery"])
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertFalse(calls.exists())
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertIn("caller-dirty.txt", before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_missing_base_is_worktree_failed_and_leaves_the_caller(self) -> None:
        calls = self.side / "calls.txt"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CALL_COUNT']).write_text('called\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        (self.repo / "caller-dirty.txt").write_text("stay\n", encoding="utf-8")
        before = _git(self.repo, "status", "--porcelain").stdout
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        ref = "does-not-exist-realfail2-1031"
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--base",
                ref,
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "true",
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_CALL_COUNT": str(calls)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("usage:", text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "worktree-failed")
        self.assertEqual(payload["exit_code"], 1)
        self.assertEqual(payload["base"], ref)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertIs(payload["pushed"], False)
        recovery = payload["recovery"]
        self.assertTrue(recovery.strip(), recovery)
        self.assertIn("Mark:", recovery)
        self.assertIn(ref, recovery)
        self.assertIn("--base", recovery)
        self.assertIn("fetch", recovery.lower())
        self.assertNotIn("--local", recovery)
        self.assertFalse(calls.exists())
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertIn("caller-dirty.txt", before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())
        dry_dir = self.side / "dry-receipt"
        dry = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept",
                "--repo",
                str(self.repo),
                "--base",
                ref,
                "--dry-run",
                "--receipt-dir",
                str(dry_dir),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_CALL_COUNT": str(calls)},
        )
        dry_text = (dry.stdout or "") + (dry.stderr or "")
        self.assertEqual(dry.returncode, 1, dry_text)
        dry_payload = json.loads((dry_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(dry_payload["status"], "FAIL")
        self.assertEqual(dry_payload["reason"], "worktree-failed")
        self.assertIn(ref, dry_payload["recovery"])

    def test_unwritable_tmp_is_worktree_failed_and_does_not_call_grok(self) -> None:
        calls = self.side / "calls.txt"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_CALL_COUNT']).write_text('called\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        (self.repo / "app.py").write_text("value = 0\n", encoding="utf-8")
        added = _git(self.repo, "add", "app.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "app")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        blocked = self.repo / "tmp"
        blocked.mkdir()
        os.chmod(blocked, 0o555)

        def _restore_tmp() -> None:
            if blocked.exists():
                os.chmod(blocked, 0o755)

        self.addCleanup(_restore_tmp)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        before = _git(self.repo, "status", "--porcelain").stdout
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "set value to 1",
                "--repo",
                str(self.repo),
                "--base",
                "HEAD",
                "--retries",
                "0",
                "--no-review",
                "--timeout",
                "30",
                "--test-cmd",
                "true",
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_CALL_COUNT": str(calls)},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "worktree-failed")
        self.assertEqual(payload["exit_code"], 1)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertIn("Mark:", payload["recovery"])
        self.assertIn("writable", payload["recovery"].lower())
        self.assertIn("worktree", payload["recovery"].lower())
        self.assertNotIn("PermissionError", payload["recovery"])
        self.assertIsNone(payload["gate"]["before"])
        self.assertIsNone(payload["gate"]["after"])
        self.assertFalse(calls.exists())
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_hung_gate_is_timeout_and_does_not_commit(self) -> None:
        count = self.side / "hang-count"
        gate = _write_exe(
            self.side / "hang.py",
            "#!/usr/bin/env python3\n"
            "import os, time\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['PFY_HANG_COUNT'])\n"
            "n = int(path.read_text()) + 1 if path.exists() else 1\n"
            "path.write_text(str(n))\n"
            "if n == 1:\n"
            "    print('pass-before')\n"
            "    raise SystemExit(0)\n"
            "print('hang')\n"
            "time.sleep(30)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('app.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        (self.repo / "app.py").write_text("value = 0\n", encoding="utf-8")
        added = _git(self.repo, "add", "app.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "app")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "set value to 1",
                "--repo",
                str(self.repo),
                "--base",
                "HEAD",
                "--retries",
                "2",
                "--timeout",
                "1",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
            env={"PFY_HANG_COUNT": str(count)},
            timeout=30,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 3, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "TIMEOUT")
        self.assertEqual(payload["reason"], "timeout")
        self.assertEqual(payload["exit_code"], 3)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertIn("the gate timed out", payload["recovery"])
        self.assertIn("--timeout", payload["recovery"])
        self.assertNotIn("--local", payload["recovery"])
        self.assertEqual(payload["gate"]["before"]["exit"], 0)
        self.assertIn("pass-before", payload["gate"]["before"]["tail"])
        self.assertEqual(payload["gate"]["after"]["exit"], 124)
        self.assertIn("gate timeout", payload["gate"]["after"]["tail"])
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(count.read_text(encoding="utf-8"), "2")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

