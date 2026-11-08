import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AtgModularCiTest(unittest.TestCase):
    def test_no_new_workflow_or_ci_job_for_atg(self):
        hits = []
        for base in (ROOT / ".github/workflows", ROOT / "ci"):
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if "atomic-task-graph-atg" in text or "run-on-main.sh" in text:
                    hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_model_lock_is_not_a_new_global_lock(self):
        script = (ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh").read_text(encoding="utf-8")
        self.assertIn("scripts/model_lock.sh", script)
        self.assertNotIn("global.lock", script)
        selectors = (ROOT / "scripts/test_select.py").read_text(encoding="utf-8")
        self.assertNotIn("atomic-task-graph-atg", selectors)


if __name__ == "__main__":
    unittest.main()
