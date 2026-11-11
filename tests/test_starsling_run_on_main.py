"""Advisory ci-score receipt: fail closed, and score only on origin/main.

How this fails: a second start, a worktree that is not on origin/main, a
missing pin, a pin mismatch, a collect error, a timeout, or a worktree edit.
Recovery: exit nonzero and leave any existing receipt bytes alone. Workflows
stay as they were when the collect step itself does not edit them. Private
logs replace the home prefix with $HOME.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "starsling-skills" / "run-on-main.sh"

STUB_OK = textwrap.dedent(
    """\
    import json, os, sys
    out = "findings.json"
    args = sys.argv[1:]
    if "--out" in args:
        out = args[args.index("--out") + 1]
    Path = __import__("pathlib").Path
    home = os.environ.get("HOME", "")
    Path(out).write_text(json.dumps({
        "scanned_workflows": 2,
        "spec_path": home + "/.cache/pfy/tools/starsling-skills/spec.json",
        "ci_score": {"value": 41, "spec_version": "stub-v9"},
    }), encoding="utf-8")
    sys.stdout.write("score \\u2014 ok\\n")
    """
)

STUB_SLEEP = textwrap.dedent(
    """\
    import time
    time.sleep(30)
    """
)

STUB_FAIL = textwrap.dedent(
    """\
    import sys
    sys.stderr.write("collect refused\\n")
    raise SystemExit(3)
    """
)

STUB_MUTATE = textwrap.dedent(
    """\
    import pathlib, sys
    repo = pathlib.Path(sys.argv[sys.argv.index("--repo") + 1])
    target = repo / ".github" / "workflows" / "ci.yml"
    target.write_text(target.read_text(encoding="utf-8") + "\\n# edited\\n", encoding="utf-8")
    raise SystemExit(0)
    """
)


def _git(repo: Path, *args: str) -> None:
    subprocess.check_call(
        [
            "git", "-C", str(repo),
            "-c", "user.email=lane@example.com",
            "-c", "user.name=lane",
            "-c", "commit.gpgsign=false",
            *args,
        ],
        stdout=subprocess.DEVNULL,
    )


def _skill(td: Path, body: str) -> tuple[Path, str]:
    skill = td / "skill"
    scripts = skill / "skills" / "ci-score" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "collect_config.py").write_text(body, encoding="utf-8")
    subprocess.check_call(["git", "init", "-q", str(skill)])
    _git(skill, "add", "-A")
    _git(skill, "commit", "-qm", "pin")
    pin = subprocess.check_output(
        ["git", "-C", str(skill), "rev-parse", "HEAD"], text=True
    ).strip()
    return skill, pin


def _repo(td: Path, *, ahead: bool = False) -> Path:
    repo = td / "repo"
    dest = repo / "eval" / "integrate" / "starsling-skills"
    dest.mkdir(parents=True)
    shutil.copy2(SCRIPT, dest / "run-on-main.sh")
    wf = repo / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: ci\non: push\n", encoding="utf-8")
    subprocess.check_call(["git", "init", "-q", str(repo)])
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    if ahead:
        _git(repo, "commit", "--allow-empty", "-qm", "ahead")
    return repo


def _env(skill: Path, pin: str, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    env["STARSLING_ROOT"] = str(skill)
    env["STARSLING_PIN"] = pin
    env["STARSLING_TIMEOUT"] = "30"
    env.update(extra)
    return env


def _run(repo: Path, receipt: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "eval/integrate/starsling-skills/run-on-main.sh"), str(receipt)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


class StarslingRunOnMainTest(unittest.TestCase):
    def test_second_start_exits_2_without_receipt(self):
        self.assertTrue(SCRIPT.is_file())
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            dest = td / "eval" / "integrate" / "starsling-skills"
            dest.mkdir(parents=True)
            shutil.copy2(SCRIPT, dest / "run-on-main.sh")
            lock_path = dest / ".run.lock"
            holder = subprocess.Popen(
                [
                    "flock", "-n", str(lock_path),
                    "bash", "-c", "echo ready; sleep 30",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
            receipt = td / "receipt.json"
            try:
                ready = holder.stdout.readline().strip() if holder.stdout else ""
                self.assertEqual(ready, "ready")
                proc = subprocess.run(
                    ["bash", str(dest / "run-on-main.sh"), str(receipt)],
                    cwd=td,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertFalse(receipt.exists())
                self.assertIn("run lock held", proc.stderr)
            finally:
                if holder.stdout is not None:
                    holder.stdout.close()
                if holder.poll() is None:
                    try:
                        os.killpg(holder.pid, signal.SIGTERM)
                    except OSError:
                        holder.terminate()
                try:
                    holder.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(holder.pid, signal.SIGKILL)
                    except OSError:
                        pass
                    holder.wait(timeout=5)

    def test_off_main_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_OK)
            repo = _repo(td, ahead=True)
            kept = td / "kept.json"
            kept.write_text("keep\n", encoding="utf-8")
            proc = _run(repo, kept, _env(skill, pin))
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(kept.read_text(encoding="utf-8"), "keep\n")
            self.assertIn("not an ancestor", proc.stderr)

    def test_missing_pin_leaves_receipt_and_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_OK)
            repo = _repo(td)
            workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
            kept = td / "kept.json"
            kept.write_text("keep\n", encoding="utf-8")
            env = _env(skill, pin, STARSLING_ROOT=str(td / "missing"))
            proc = _run(repo, kept, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(kept.read_text(encoding="utf-8"), "keep\n")
            self.assertIn("pinned ci-score missing", proc.stderr)
            self.assertEqual(
                (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
                workflow,
            )

    def test_timeout_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_SLEEP)
            repo = _repo(td)
            receipt = td / "receipt.json"
            receipt.write_text("keep\n", encoding="utf-8")
            proc = _run(repo, receipt, _env(skill, pin, STARSLING_TIMEOUT="1"))
            self.assertEqual(proc.returncode, 124, proc.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")
            self.assertIn("timeout is not a pass", proc.stderr)
            self.assertFalse((repo / "tmp" / "ops").exists())

    def test_pin_mismatch_leaves_receipt_and_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_OK)
            repo = _repo(td)
            workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
            kept = td / "kept.json"
            kept.write_text("keep\n", encoding="utf-8")
            wrong = "0" * 40 if pin != "0" * 40 else "1" * 40
            proc = _run(repo, kept, _env(skill, pin, STARSLING_PIN=wrong))
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(kept.read_text(encoding="utf-8"), "keep\n")
            self.assertIn("commit mismatch", proc.stderr)
            self.assertEqual(
                (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
                workflow,
            )
            self.assertFalse((repo / "tmp" / "ops").exists())

    def test_collect_error_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_FAIL)
            repo = _repo(td)
            receipt = td / "receipt.json"
            receipt.write_text("keep\n", encoding="utf-8")
            proc = _run(repo, receipt, _env(skill, pin))
            self.assertEqual(proc.returncode, 3, proc.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), "keep\n")

    def test_worktree_edit_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_MUTATE)
            repo = _repo(td)
            receipt = td / "receipt.json"
            proc = _run(repo, receipt, _env(skill, pin))
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("changed the worktree", proc.stderr)

    def test_on_main_writes_pipeline_receipt_and_leaves_workflow(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            skill, pin = _skill(td, STUB_OK)
            repo = _repo(td)
            workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
            sha = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            receipt = repo / "eval" / "integrate" / "starsling-skills" / "receipt.json"
            proc = _run(repo, receipt, _env(skill, pin))
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(body["slug"], "starsling-skills")
            self.assertEqual(body["run_kind"], "pipeline")
            self.assertEqual(body["main_sha"], sha)
            self.assertEqual(body["outcome"], "ok")
            self.assertEqual(body["tool_version"], "stub-v9")
            self.assertIn(body["run_id"], {f"starsling-skills-{sha[:12]}-{body['started']}"})
            self.assertIn("Score 41/100", body["did"])
            self.assertIn("Scanned 2 workflows", body["did"])
            self.assertIn("Workflows unchanged", body["did"])
            self.assertIn("ci-speedup was not run", body["did"])
            self.assertNotIn("/", body["tool_version"])
            self.assertNotIn(os.environ["HOME"], receipt.read_text(encoding="utf-8"))
            self.assertNotIn("/home/", receipt.read_text(encoding="utf-8"))
            ops = repo / "tmp" / "ops" / "eval" / "integrate" / "starsling-skills"
            findings = (ops / "ci-score-findings.json").read_text(encoding="utf-8")
            logged = (ops / "ci-score.out").read_text(encoding="utf-8")
            self.assertNotIn(os.environ["HOME"], findings)
            self.assertNotIn(os.environ["HOME"], logged)
            self.assertIn("$HOME/", findings)
            self.assertIn("score - ok", logged)
            self.assertNotIn("\u2014", logged)
            self.assertFalse((repo / "eval" / "integrate" / "starsling-skills" / "ci-score-findings.json").exists())
            self.assertEqual(
                (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
                workflow,
            )
            porcelain = subprocess.check_output(
                ["git", "-C", str(repo), "status", "--porcelain"], text=True
            )
            self.assertNotIn(".github/workflows/ci.yml", porcelain)


if __name__ == "__main__":
    unittest.main()
