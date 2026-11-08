import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "grok_trace_export.py"


class GrokTraceExportRedactTest(unittest.TestCase):
    def test_fixture_token_absent_from_trace(self):
        self.assertTrue(SCRIPT.is_file(), "scripts/grok_trace_export.py is missing")
        token = "sk-test-REDACTME-0000"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "session.log"
            out = Path(tmp) / "trace.json"
            src.write_text("tool_call authorization=" + token + "\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(src), "-o", str(out)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.is_file(), "trace output was not written")
            text = out.read_text(encoding="utf-8")
            self.assertNotIn(token, text)
            self.assertNotIn("REDACTME", text)


if __name__ == "__main__":
    unittest.main()
