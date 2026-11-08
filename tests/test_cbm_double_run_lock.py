import unittest
from pathlib import Path

SCRIPT = Path("eval/integrate/codebase-memory-mcp/run-on-main.sh")
MARKER = "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched"


class DoubleRunLockTest(unittest.TestCase):
    def test_second_start_exits_2_without_receipt(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MARKER, text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        comment = "\n".join(line for line in text.splitlines() if line.strip().startswith("#"))
        self.assertIn(MARKER, comment)
        self.assertIn("flock", comment)


if __name__ == "__main__":
    unittest.main()
