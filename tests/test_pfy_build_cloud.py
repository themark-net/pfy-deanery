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
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertFalse(sentinel.exists())

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
        self.assertIn("[redacted]", raw)

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
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

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
            "Path('tests').mkdir(exist_ok=True)\n"
            "Path('tests/test_sneak.py').write_text('def test_sneak():\\n    assert True\\n', encoding='utf-8')\n"
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
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertFalse(calls.exists())
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, before)
        self.assertIn("caller-dirty.txt", before)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

