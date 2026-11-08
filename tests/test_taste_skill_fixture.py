import unittest


class TestTasteSkillFixture(unittest.TestCase):
    def test_fixture_is_operator_index(self):
        text = open(
            "eval/integrate/taste-skill/run-on-main.sh", encoding="utf-8"
        ).read()
        self.assertIn("gui/operator/frontend/index.html", text)
        self.assertNotIn("npx skills add", text)


if __name__ == "__main__":
    unittest.main()
