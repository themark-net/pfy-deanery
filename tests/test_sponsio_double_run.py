import unittest
from pathlib import Path


class SponsioDoubleRunTest(unittest.TestCase):
    def test_second_start_exits_2_and_names_flock(self):
        text = Path("eval/integrate/sponsio/run-on-main.sh").read_text()
        self.assertIn(
            "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/sponsio.dispatched",
            text,
        )
        self.assertRegex(text, r"exit\s+2")
        self.assertIn("flock", text.lower())
        self.assertNotIn("git push", text)


if __name__ == "__main__":
    unittest.main()
