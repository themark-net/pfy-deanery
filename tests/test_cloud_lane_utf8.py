"""A change that git cannot show as UTF-8 text ends review-binary-change.

Covers a new non-UTF-8 file, non-UTF-8 OLD content, a deleted non-UTF-8
file, and a non-UTF-8 filename. None may end runner-crash or PASS.
"""

from __future__ import annotations

import os
import unittest

from tests.test_cloud_lane_manifest import _Rewrite
from tests.test_pfy_build_cloud import _git


class NonUtf8Changes(_Rewrite):
    def seed_bytes(self, rel: str, data: bytes) -> None:
        (self.repo / rel).write_bytes(data)
        _git(self.repo, "add", rel)
        _git(self.repo, "commit", "-qm", "seed bytes")

    def assert_binary(self, r: dict) -> None:
        self.assertNotIn("Traceback", r["_out"], r)
        self.assertEqual((r.get("status"), r.get("reason"), r.get("commit")), ("FAIL", "review-binary-change", None), r)
        self.assertEqual(r["_rc"], 1, r)
        self.assertTrue(r.get("recovery"), r)

    def test_new_non_utf8_file(self) -> None:
        self.assert_binary(self.build("Path('data.txt').write_bytes(b'\\xff\\xfe not utf8 but no NUL\\n')\n", "print('ok')\n"))

    def test_non_utf8_old_content_rewritten_as_text(self) -> None:
        self.seed_bytes("legacy.txt", b"caf\xe9 latin-1\n")
        self.assert_binary(self.build("Path('legacy.txt').write_text('cafe utf8\\n')\n", "print('ok')\n"))

    def test_deleted_non_utf8_file(self) -> None:
        self.seed_bytes("legacy.txt", b"caf\xe9 latin-1\n")
        self.assert_binary(self.build("Path('legacy.txt').unlink()\n", "print('ok')\n"))

    def test_non_utf8_filename(self) -> None:
        probe = os.path.join(os.fsencode(str(self.repo)), b"probe\xff")
        try:
            open(probe, "wb").close()
            os.unlink(probe)
        except OSError:
            self.skipTest("this filesystem rejects non-UTF-8 filenames (utf8only)")
        self.assert_binary(self.build("open(os.fsencode('n') + b'\\xff.txt', 'w').write('plain\\n')\n", "print('ok')\n"))


if __name__ == "__main__":
    unittest.main()
