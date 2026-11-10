"""A loop tick re-opens a fixable park once main is green and launches it under the caps."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.test_catalog_loop_tick import build_repo, card, run_tick


class LoopParkRetryTest(unittest.TestCase):
    def _tick(self, green: str):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        td = Path(tmp.name)
        clone = build_repo(td, {"aa-fix": card("aa-fix"), "aa-grok": card("aa-grok")})
        ev = td / "state" / "eval"
        ev.mkdir(parents=True)
        old = time.time() - 30 * 3600
        for slug, reason in (("aa-fix", "run_tests failed"), ("aa-grok", "grok failed")):
            marker = ev / f"{slug}.parked"
            marker.write_text(reason + "\n", encoding="utf-8")
            (ev / f"{slug}.dispatched").write_text("pid 1\n", encoding="utf-8")
            os.utime(marker, (old, old))
        with mock.patch.dict(os.environ, {"PFY_MAIN_GREEN": green}):
            proc, state, wt, log = run_tick(td, clone)
        self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-3000:])
        status = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
        return status, ev, log

    def test_green_main_relaunches_the_fixable_park_only(self):
        status, ev, log = self._tick("1")
        self.assertEqual(status["park_retry"], ["retry eval aa-fix 1", "hold eval aa-grok not-retryable"])
        self.assertIn("aa-fix", status["launched"])
        self.assertNotIn("aa-grok", status["launched"])
        self.assertTrue((ev / "aa-fix.parked.1").is_file())
        self.assertEqual((ev / "aa-fix.retry-count").read_text(), "1\n")
        self.assertLessEqual(len(status["launched"]), 4)
        history = (ev.parent / "park-history.tsv").read_text(encoding="utf-8")
        self.assertIn("aa-fix\teval\trun_tests failed\t", history)
        self.assertIn("aa-grok\teval\tgrok failed\t", history)

    def test_red_main_keeps_the_park(self):
        status, ev, log = self._tick("0")
        self.assertIn("hold eval aa-fix main-not-green", status["park_retry"])
        self.assertNotIn("aa-fix", status["launched"])
        self.assertTrue((ev / "aa-fix.parked").is_file())


if __name__ == "__main__":
    unittest.main()
