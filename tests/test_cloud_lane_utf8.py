"""Exit test F5: a changed file that is not valid UTF-8 does not crash the runner."""

from __future__ import annotations

import unittest

from tests.test_cloud_lane_manifest import _Rewrite


class InvalidUtf8File(_Rewrite):
    def test_invalid_utf8_new_file_ends_with_a_clear_reason(self) -> None:
        r = self.build("Path('data.txt').write_bytes(b'\\xff\\xfe not utf8 but no NUL\\n')\n", "print('ok')\n")
        self.assertNotEqual(r.get("reason"), "runner-crash", r)
        self.assertNotIn("Traceback", r["_out"], r)
        self.assertIn(r["_rc"], (0, 1), r)
        if r.get("status") == "FAIL":
            self.assertTrue(r.get("recovery"), r)


if __name__ == "__main__":
    unittest.main()
