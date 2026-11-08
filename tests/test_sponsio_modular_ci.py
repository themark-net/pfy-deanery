import unittest
from pathlib import Path


class SponsioModularCiTest(unittest.TestCase):
    def test_no_workflow_job_or_model_lock(self):
        text = Path("eval/integrate/sponsio/run-on-main.sh").read_text()
        self.assertNotIn("model_lock.sh", text)
        roots = [Path(".github/workflows"), Path("ci")]
        hits = []
        for root in roots:
            if root.exists():
                hits.extend(p for p in root.rglob("*") if "sponsio" in p.name)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
