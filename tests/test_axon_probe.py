#!/usr/bin/env python3
"""Drive the axon probe with a stub CLI. No network and no real axon binary.

A stub that wraps the caller path across lines and resolves `main` to the
wrong file must not count that miss as a qualified hit. A stub that names
the importing test on both paths must. A missing binary is SKIPPED.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "axon" / "probe.py"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os
    import sys
    from pathlib import Path

    MODE = %r
    out = Path(os.environ.get("STUB_LOG", "stub-log.txt"))
    out.write_text(os.environ.get("HOME", ""), encoding="utf-8")
    args = sys.argv[1:]
    if "--version" in args:
        print("Axon v1.0.1")
        raise SystemExit(0)
    if "analyze" in args:
        if "--no-embeddings" not in args:
            sys.stderr.write("embeddings requested\\n")
            raise SystemExit(2)
        print("Indexing complete.")
        print("  Files:          3")
        print("  Symbols:        4")
        print("  Duration:       0.01s")
        raise SystemExit(0)
    if "impact" in args:
        if MODE == "aligned":
            print("Impact analysis for: main (Function)")
            print("Depth: 1 | Total: 1 symbols")
            print("")
            print("Depth 1 - Direct callers (will break):")
            print("  1. test_main (Function) -- tests/test_app.py:4")
        else:
            print("No upstream callers found for 'main'.")
        raise SystemExit(0)
    if "context" in args:
        if MODE == "aligned":
            print("File: scripts/app.py:1-2")
        else:
            print("File: other.py:1-2")
        raise SystemExit(0)
    if "cypher" in args:
        query = args[-1]
        if query.startswith("MATCH (n:Function)"):
            print("Results (2 rows):")
            print("")
            print("  1. function:scripts/app.py:main | main | scripts/app.py | 1 | 2")
            print("  2. function:other.py:main | main | other.py | 1 | 2")
            raise SystemExit(0)
        if query.startswith("MATCH (caller)") and "callee:Function" in query:
            print("Results (1 rows):")
            print("")
            print("  1. function:scripts/app.py:main | ")
            print("tests/test_app.py | ")
            print("test_main")
            raise SystemExit(0)
        print("Query returned no results.")
        raise SystemExit(0)
    sys.stderr.write("unexpected argv\\n")
    raise SystemExit(2)
    """
)


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "pfy-probe",
            "GIT_AUTHOR_EMAIL": "probe@localhost",
            "GIT_COMMITTER_NAME": "pfy-probe",
            "GIT_COMMITTER_EMAIL": "probe@localhost",
        },
        stdout=subprocess.DEVNULL,
    )


def fixture(repo: Path) -> None:
    (repo / "scripts").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "scripts" / "app.py").write_text(
        "def main():\n    return 1\n\ndef helper():\n    return main()\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_app.py").write_text(
        "from scripts.app import main\n\ndef test_main():\n    assert main() == 1\n",
        encoding="utf-8",
    )
    (repo / "other.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "init")
    text = (repo / "scripts" / "app.py").read_text(encoding="utf-8")
    (repo / "scripts" / "app.py").write_text(text.replace("return 1", "return 2"), encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "change main")


def write_stub(path: Path, mode: str) -> None:
    path.write_text(STUB % mode, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def run_probe(repo: Path, stub: Path, out: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp/axon-probe-should-not-use-this",
        "AXON_BIN": str(stub),
        "AXON_TOOL_HOME": str(home),
        "STUB_LOG": str(repo / "stub-home.txt"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [os.environ.get("PYTHON", "python3"), str(PROBE), "--fixture", str(repo), "--out", str(out)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class AxonProbeTests(unittest.TestCase):
    def test_wrapped_caller_stays_qualified_when_bare_name_misses(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            fixture(repo)
            out = root / "results.json"
            home = root / "tool-home"
            collision = root / "axon-collision"
            write_stub(collision, "collision")
            proc = run_probe(repo, collision, out, home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["qualified_tests"], ["tests/test_app.py"])
            self.assertEqual(data["bare_tests"], [])
            self.assertTrue(data["qualified_agree"])
            self.assertFalse(data["bare_agree"])
            self.assertEqual(data["resolved_file"], "other.py")
            self.assertEqual((repo / "stub-home.txt").read_text(encoding="utf-8"), str(home))

            aligned = root / "axon-aligned"
            write_stub(aligned, "aligned")
            proc = run_probe(repo, aligned, out, home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["bare_tests"], ["tests/test_app.py"])
            self.assertEqual(data["qualified_tests"], ["tests/test_app.py"])
            self.assertTrue(data["bare_agree"])
            self.assertTrue(data["qualified_agree"])
            self.assertEqual(data["resolved_file"], "scripts/app.py")

    def test_missing_axon_is_skipped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            fixture(repo)
            out = root / "results.json"
            missing = root / "no-axon"
            proc = run_probe(repo, missing, out, root / "tool-home")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "SKIPPED")
            self.assertNotIn("bare_agree", data)
            self.assertFalse((repo / "stub-home.txt").exists())


if __name__ == "__main__":
    unittest.main()
