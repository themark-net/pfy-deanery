"""Behavior tests for the daily cloud build: ./pfy build "<task>"."""

from __future__ import annotations

import json
import os
import re
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
        self.assertEqual(payload["base"], "HEAD")
        self.assertIn(str(receipt), proc.stdout)
        self.assertFalse((self.repo / "tmp" / "cloud-build").exists())


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

