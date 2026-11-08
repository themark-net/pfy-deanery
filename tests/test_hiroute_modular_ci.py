import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "hiroute" / "run-on-main.sh"


class HirouteModularCiTest(unittest.TestCase):
    def test_script_stays_off_model_lock_and_hosted_jobs(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("# modular-ci: no .github/workflows job, no ci/ job, no model_lock.sh", text)
        self.assertNotIn("scripts/model_lock.sh", text)
        for base in (ROOT / ".github" / "workflows", ROOT / "ci"):
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if path.is_file():
                    body = path.read_text(encoding="utf-8", errors="ignore")
                    self.assertNotIn("eval/integrate/hiroute", body)


if __name__ == "__main__":
    unittest.main()
