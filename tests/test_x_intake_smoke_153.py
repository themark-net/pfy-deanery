"""Entry 153 smoke (dsh-superagent static check): a missing clone, wrong commit, missing node_modules, unsupported
node and a bad timeout exit 2; a typecheck failure, an unexpected test failure, too few tests, a build that writes no
lib/index.js, a step that edits tracked sources, a missing vitest report, or a write into the real HOME FAILs; a
failure of the one known-flaky upstream test is only a warning. Stubs are tiny Python scripts (shebang = this
interpreter) standing in for node and node_modules/.bin/{tsc,vitest,tsdown}; receipts go to a temp dir."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_153.py"
PIN = "6337fc823ce20251c8de8085948165c81aaa701e"
FLAKY = ("feishu event consumer takes in the event lines it reads, records each chat as direct or not, "
         "and reports a malformed line without stopping")

TSC = r'''
import sys
sys.exit(K.get("tsc_exit", 0))
'''
VITEST = r'''
import json, os, pathlib, sys
out = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--outputFile=")][0]
if K.get("touch_src"):
    pathlib.Path("src/a.ts").write_text("changed\n")
if K.get("touch_real"):
    try:
        pathlib.Path(K["touch_real"], ".dsh").mkdir(exist_ok=True)
    except OSError:
        pass
fails = K.get("fails", [])
results = [{"name": "/x/tests/a.spec.ts", "status": "failed" if fails else "passed",
            "assertionResults": [{"fullName": n, "status": "failed"} for n in fails]
            + [{"fullName": "ok %d" % i, "status": "passed"} for i in range(3)]}]
if not K.get("no_report"):
    pathlib.Path(out).write_text(json.dumps({"numPassedTests": K.get("passed", 1197), "testResults": results}))
sys.exit(1 if fails else 0)
'''
TSDOWN = r'''
import pathlib, sys
if not K.get("no_lib"):
    pathlib.Path("lib").mkdir(exist_ok=True)
    pathlib.Path("lib/index.js").write_text("export {}\n")
sys.exit(K.get("build_exit", 0))
'''
NODE = r'''
import sys
print(K.get("node", "v24.22.1"))
'''


def write_stub(path: Path, knobs: dict, body: str) -> None:
    path.write_text(f"#!{sys.executable}\nK = {knobs!r}\n" + body, encoding="utf-8")
    path.chmod(0o755)


class Smoke153(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, head=PIN, deps=True, clone=True, packed=False):
        k = dict(knobs or {})
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            if k.get("touch_real"):
                k["touch_real"] = str(real)
            repo = td / "clone"
            if clone:
                (repo / "src").mkdir(parents=True)
                (repo / "src/a.ts").write_text("export const a = 1\n")
                (repo / "package.json").write_text("{}\n")
                (repo / ".git").mkdir()
                if packed:
                    (repo / ".git/HEAD").write_text("ref: refs/heads/main\n")
                    (repo / ".git/packed-refs").write_text(f"# pack-refs with: peeled\n{head} refs/heads/main\n")
                else:
                    (repo / ".git/HEAD").write_text(head + "\n")
                if deps:
                    bins = repo / "node_modules/.bin"
                    bins.mkdir(parents=True)
                    write_stub(bins / "tsc", k, TSC)
                    write_stub(bins / "vitest", k, VITEST)
                    write_stub(bins / "tsdown", k, TSDOWN)
            nodedir = td / "nodebin"
            nodedir.mkdir()
            write_stub(nodedir / "node", k, NODE)
            env2 = {"PATH": os.environ.get("PATH", ""), "HOME": str(real), "DSH_SUPERAGENT_DIR": str(repo),
                    "NODE_BIN": str(nodedir / "node"), "PFY_SMOKE_RECEIPT_DIR": str(td / "r")}
            env2.update(env or {})
            p = subprocess.run([sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=120)
            rec = json.loads((td / "r" / "latest.json").read_text())
            return p.returncode, rec

    def test_pass(self):
        code, rec = self.run_smoke()
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["warnings"], [])

    def test_known_flaky_failure_is_warning(self):
        code, rec = self.run_smoke({"fails": [FLAKY]})
        self.assertEqual(code, 0, rec)
        self.assertEqual(len(rec["warnings"]), 1)

    def test_packed_ref_head_resolves(self):
        self.assertEqual(self.run_smoke(packed=True)[0], 0)

    def test_missing_clone_exit_2(self):
        code, rec = self.run_smoke(clone=False)
        self.assertEqual(code, 2)
        self.assertIn("not staged", rec["reason"])

    def test_wrong_commit_exit_2(self):
        code, rec = self.run_smoke(head="0" * 40)
        self.assertEqual(code, 2)
        self.assertIn("pinned commit", rec["reason"])

    def test_missing_deps_exit_2(self):
        code, rec = self.run_smoke(deps=False)
        self.assertEqual(code, 2)
        self.assertIn("node_modules", rec["reason"])

    def test_unsupported_node_exit_2(self):
        for v in ("v22.18.0", "v23.5.0", "v20.11.1"):
            self.assertEqual(self.run_smoke({"node": v})[0], 2, v)

    def test_bad_timeout_exit_2(self):
        self.assertEqual(self.run_smoke(env={"PFY_XINTAKE_TIMEOUT": "0"})[0], 2)

    def test_typecheck_failure_fails(self):
        code, rec = self.run_smoke({"tsc_exit": 2})
        self.assertEqual(code, 1)
        self.assertIn("typecheck_ok", rec["failed"])

    def test_unexpected_test_failure_fails(self):
        code, rec = self.run_smoke({"fails": [FLAKY, "authorization refuses a bot request"]})
        self.assertEqual(code, 1)
        self.assertIn("tests_no_unexpected_failures", rec["failed"])

    def test_too_few_tests_fails(self):
        code, rec = self.run_smoke({"passed": 12})
        self.assertEqual(code, 1)
        self.assertIn("tests_at_least_1100_pass", rec["failed"])

    def test_missing_report_fails(self):
        code, rec = self.run_smoke({"no_report": True})
        self.assertEqual(code, 1)
        self.assertIn("tests_no_unexpected_failures", rec["failed"])

    def test_build_without_lib_fails(self):
        code, rec = self.run_smoke({"no_lib": True})
        self.assertEqual(code, 1)
        self.assertIn("build_wrote_lib", rec["failed"])

    def test_source_edit_fails(self):
        code, rec = self.run_smoke({"touch_src": True})
        self.assertEqual(code, 1)
        self.assertIn("sources_unchanged", rec["failed"])

    def test_real_home_write_fails(self):
        # No bwrap on PATH, so the stub can reach the real HOME (bwrap's read-only bind would block it).
        code, rec = self.run_smoke({"touch_real": True}, {"PATH": "/nonexistent"})
        self.assertEqual(code, 1)
        self.assertIn("real_home_unchanged", rec["failed"])


if __name__ == "__main__":
    unittest.main()
