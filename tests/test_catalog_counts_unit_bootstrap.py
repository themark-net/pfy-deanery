import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "ops" / "systemd" / "catalog-counts.service"


class UnitBootstrapTest(unittest.TestCase):
    def test_execstart_fetches_before_show_and_cwd_is_home(self):
        self.assertTrue(UNIT.is_file(), "catalog-counts.service missing")
        text = UNIT.read_text()
        execs = [ln for ln in text.splitlines() if ln.startswith("ExecStart=")]
        self.assertEqual(len(execs), 1, execs)
        line = execs[0]
        self.assertIn("git fetch", line)
        self.assertIn("show origin/main:scripts/loop_worktree.sh", line)
        self.assertLess(line.index("git fetch"), line.index("show origin/main:scripts/loop_worktree.sh"))
        self.assertIn("%t/pfy-loop-worktree.sh", line)
        self.assertIn("catalog_counts_publish.sh", line)
        self.assertNotIn("tmp/loop/wt/scripts/loop_worktree.sh", line)
        self.assertNotIn("DEVELOP/pfy-mentat/scripts/catalog_counts.py", line)
        wd = [ln.strip() for ln in text.splitlines() if ln.startswith("WorkingDirectory=")]
        self.assertEqual(wd, ["WorkingDirectory=%h"])
