import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "hiroute" / "run-on-main.sh"


class HirouteSingleFlightTest(unittest.TestCase):
    def test_second_start_exits_2_under_named_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/hiroute.dispatched", text)
        self.assertIn("exit 2", text)
        self.assertIn("# extra lock: flock eval/integrate/hiroute/hiroute-ff.lock", text)


if __name__ == "__main__":
    unittest.main()
