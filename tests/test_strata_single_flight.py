import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"
MARKER = "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/strata.dispatched"


class StrataSingleFlightTest(unittest.TestCase):
    def test_second_start_exits_2_and_names_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MARKER, text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)


if __name__ == "__main__":
    unittest.main()
