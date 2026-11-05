"""Entry 155 smoke (RoBrain VetoBench offline): a missing clone, wrong commit, unbuilt clone, old node and a bad
timeout exit 2; recall under the upstream gate, recall that drifts from the pinned numbers, a missing scenario row, a
non-zero bench exit, a missing offline marker, node:test failures, an archive written into results/, or a write into
the real HOME FAILs; a correct stub PASSes. The stub is a tiny Python `node` (shebang = this interpreter) that prints
VetoBench-shaped output; receipts go to a temp dir."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_155.py"
PIN = "ac53011016e5f7dd42bae9c00c1a9b7d207a68b8"

NODE = r'''
import pathlib, sys
a = sys.argv[1:]
if a[:1] == ["--version"]:
    print(K.get("node", "v24.22.1")); sys.exit(0)
if K.get("touch_real"):
    try:
        pathlib.Path(K["touch_real"], ".robrain").mkdir(exist_ok=True)
    except OSError:
        pass
if a[:1] == ["--test"]:
    print("\u2139 tests %d\n\u2139 pass %d\n\u2139 fail %d" % (22, 22 - K.get("test_fail", 0), K.get("test_fail", 0)))
    sys.exit(1 if K.get("test_fail") else 0)
suite = "lifecycle" if "lifecycle" in a else "default"
rows = {"default": 10, "lifecycle": 4}[suite] - K.get("drop_rows", 0)
files, nofiles = K.get("recall", {}).get(suite, {"default": (1.0, 0.7), "lifecycle": (1.0, 1.0)}[suite])
if K.get("write_results"):
    pathlib.Path("results/new.json").write_text("{}")
print("VetoBench\nscenario  veto   files known  no files")
for i in range(rows):
    print("s%02d       d1%02d           1 \u2713       2 \u2713" % (i + 1, i + 1))
print("\nveto recall@5: %.2f with files known (gate: \u2265 0.80) \u00b7 %.2f without\n" % (files, nofiles))
if not K.get("no_offline"):
    print("(offline run \u2014 add --live with an LLM key for the behavioral layer)")
print("\n\u2713 PASS" if files >= 0.8 else "\n\u2717 FAIL \u2014 veto retrieval below threshold")
sys.exit(K.get("bench_exit", 0 if files >= 0.8 else 1))
'''


class Smoke155(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, head=PIN, built=True, clone=True):
        k = dict(knobs or {})
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            if k.get("touch_real"):
                k["touch_real"] = str(real)
            repo = td / "robrain"
            vb = repo / "packages/vetobench"
            if clone:
                (vb / "results").mkdir(parents=True)
                (vb / "results/old.json").write_text("{}")
                (vb / "package.json").write_text("{}\n")
                (repo / ".git").mkdir()
                (repo / ".git/HEAD").write_text("ref: refs/heads/main\n")
                (repo / ".git/refs/heads").mkdir(parents=True)
                (repo / ".git/refs/heads/main").write_text(head + "\n")
                if built:
                    (vb / "dist").mkdir()
                    for f in ("run.js", "score.test.js", "adapters.test.js", "mem0-adapter.test.js"):
                        (vb / "dist" / f).write_text("")
                    (repo / "packages/shared/dist").mkdir(parents=True)
                    (vb / "node_modules/@robrain/shared").mkdir(parents=True)
            nodedir = td / "nodebin"
            nodedir.mkdir()
            node = nodedir / "node"
            node.write_text(f"#!{sys.executable}\nK = {k!r}\n" + NODE, encoding="utf-8")
            node.chmod(0o755)
            env2 = {"PATH": os.environ.get("PATH", ""), "HOME": str(real), "ROBRAIN_DIR": str(repo),
                    "NODE_BIN": str(node), "PFY_SMOKE_RECEIPT_DIR": str(td / "r")}
            env2.update(env or {})
            p = subprocess.run([sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=120)
            rec = json.loads((td / "r" / "latest.json").read_text())
            return p.returncode, rec

    def test_pass(self):
        code, rec = self.run_smoke()
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["default_recall_files_known_nofiles"], [1.0, 0.7])

    def test_missing_clone_exit_2(self):
        self.assertEqual(self.run_smoke(clone=False)[0], 2)

    def test_wrong_commit_exit_2(self):
        code, rec = self.run_smoke(head="1" * 40)
        self.assertEqual(code, 2)
        self.assertIn("pinned commit", rec["reason"])

    def test_unbuilt_exit_2(self):
        code, rec = self.run_smoke(built=False)
        self.assertEqual(code, 2)
        self.assertIn("not built", rec["reason"])

    def test_old_node_exit_2(self):
        self.assertEqual(self.run_smoke({"node": "v18.19.0"})[0], 2)

    def test_bad_timeout_exit_2(self):
        self.assertEqual(self.run_smoke(env={"PFY_XINTAKE_TIMEOUT": "-1"})[0], 2)

    def test_recall_below_gate_fails(self):
        code, rec = self.run_smoke({"recall": {"default": (0.6, 0.5)}})
        self.assertEqual(code, 1)
        self.assertIn("default_recall_meets_gate", rec["failed"])
        self.assertIn("default_exit_0", rec["failed"])

    def test_recall_drift_fails(self):
        # Still above the gate, but the deterministic bench no longer gives the pinned numbers.
        code, rec = self.run_smoke({"recall": {"lifecycle": (1.0, 0.75)}})
        self.assertEqual(code, 1)
        self.assertEqual(rec["failed"], ["lifecycle_recall_matches_pin"])

    def test_missing_row_fails(self):
        code, rec = self.run_smoke({"drop_rows": 1})
        self.assertEqual(code, 1)
        self.assertIn("default_rows_10", rec["failed"])

    def test_bench_exit_fails(self):
        code, rec = self.run_smoke({"bench_exit": 3})
        self.assertEqual(code, 1)
        self.assertIn("default_exit_0", rec["failed"])

    def test_not_offline_fails(self):
        code, rec = self.run_smoke({"no_offline": True})
        self.assertEqual(code, 1)
        self.assertIn("default_offline", rec["failed"])

    def test_node_test_failure_fails(self):
        code, rec = self.run_smoke({"test_fail": 2})
        self.assertEqual(code, 1)
        self.assertIn("node_test_no_failures", rec["failed"])

    def test_results_write_fails(self):
        code, rec = self.run_smoke({"write_results": True}, {"PATH": "/nonexistent"})
        self.assertEqual(code, 1)
        self.assertIn("results_dir_unchanged", rec["failed"])

    def test_real_home_write_fails(self):
        code, rec = self.run_smoke({"touch_real": True}, {"PATH": "/nonexistent"})
        self.assertEqual(code, 1)
        self.assertIn("real_home_unchanged", rec["failed"])


if __name__ == "__main__":
    unittest.main()
