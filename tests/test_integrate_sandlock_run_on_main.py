"""run-on-main.sh against a fixture repo, not this feature branch.

HEAD must be an ancestor of origin/main before the fixture install and run.
A checkout that is ahead exits nonzero and writes no receipt.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_REL = Path("eval/integrate/sandlock/run-on-main.sh")
COPY_REL = (
    Path("scripts/integrations/sandlock/wrap.py"),
    Path("scripts/integrations/sandlock/confine.py"),
    Path("eval/integrate/sandlock/fixtures/hello.sh"),
    SCRIPT_REL,
)
FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    trace = os.environ.get("SANDLOCK_TRACE", "")
    if trace:
        Path(trace).open("a").write(json.dumps(sys.argv[1:]) + "\\n")
    os.execvp(sys.argv[1], sys.argv[1:])
    """
)


def git(repo: Path, *args: str) -> None:
    subprocess.check_call(["git", "-C", str(repo), *args])


def init_repo(repo: Path) -> None:
    repo.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(repo)])
    git(repo, "config", "user.email", "lane@example.com")
    git(repo, "config", "user.name", "Lane")


class SandlockRunOnMainTest(unittest.TestCase):
    def test_ancestor_writes_receipt_and_other_head_does_not(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            bare = td / "origin.git"
            init_repo(repo)
            for rel in COPY_REL:
                dest = repo / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, dest)
            (repo / "README").write_text("fixture\n")
            git(repo, "add", "-A")
            git(repo, "commit", "-m", "wiring")
            subprocess.check_call(["git", "init", "--bare", "-b", "main", str(bare)])
            git(repo, "remote", "add", "origin", str(bare))
            git(repo, "push", "-u", "origin", "main")

            fake = td / "sandlock"
            fake.write_text(FAKE)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            trace = td / "trace.log"
            cache = td / "cache"
            receipt = td / "receipt.json"
            env = os.environ.copy()
            env["SANDLOCK_BIN"] = str(fake)
            env["SANDLOCK_TRACE"] = str(trace)
            env["PFY_SANDLOCK_CACHE"] = str(cache)
            env.pop("SANDLOCK_REAL", None)
            script = repo / SCRIPT_REL
            proc = subprocess.run(
                ["bash", str(script), str(receipt)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            body = json.loads(receipt.read_text(encoding="utf-8"))
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            self.assertEqual(body["slug"], "sandlock")
            self.assertEqual(body["run_kind"], "pipeline")
            self.assertEqual(body["main_sha"], head)
            self.assertEqual(len(body["main_sha"]), 40)
            self.assertTrue(body["run_id"].startswith("sandlock-"))
            self.assertEqual(body["outcome"], "ok")
            self.assertEqual(body["tool_version"], "sandlock-bin")
            self.assertEqual(body["log_path"], "eval/integrate/sandlock/notes.md")
            self.assertIn("fixture", body["did"])
            self.assertNotIn("unsandboxed", body["did"])
            stage = cache / "stage" / "out.txt"
            self.assertEqual(stage.read_text(encoding="utf-8").strip(), "ok")
            rows = [json.loads(row) for row in trace.read_text().splitlines() if row.strip()]
            user = [row for row in rows if row != ["true"]]
            self.assertEqual(len(user), 2, rows)
            before = trace.read_text(encoding="utf-8")
            again = subprocess.run(
                ["bash", str(script), str(receipt)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(again.returncode, 0, again.stderr + again.stdout)
            self.assertEqual(trace.read_text(encoding="utf-8"), before)

            git(repo, "commit", "--allow-empty", "-m", "not on main")
            missed = td / "missed.json"
            refused = subprocess.run(
                ["bash", str(script), str(missed)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(refused.returncode, 0, refused.stdout)
            self.assertIn("not an ancestor", refused.stderr)
            self.assertFalse(missed.exists())

            usage = subprocess.run(
                ["bash", str(ROOT / SCRIPT_REL)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(usage.returncode, 2, usage.stderr)


if __name__ == "__main__":
    unittest.main()
