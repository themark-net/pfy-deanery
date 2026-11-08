import re
import unittest


class TestTasteSkillRunKind(unittest.TestCase):
    def test_run_kind_is_pipeline(self):
        text = open(
            "eval/integrate/taste-skill/run-on-main.sh", encoding="utf-8"
        ).read()
        self.assertRegex(text, r"run_kind")
        self.assertIn("pipeline", text)
        self.assertIsNone(re.search(r"run_kind[^\n]*gate", text))


if __name__ == "__main__":
    unittest.main()
