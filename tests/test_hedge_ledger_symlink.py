"""save_ledger must not write through a symlink.

Path.write_text follows the link. A mode-000 target raises, and a
readable target is overwritten. The ledger has to land as a regular
file, the outside bytes have to stay, and a later save of a regular
file has to load back.
"""
from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from pfylib import hedge

ROOT = Path(__file__).resolve().parents[1]


class HedgeLedgerSymlinkTests(unittest.TestCase):
    def test_symlink_ledger_is_replaced_and_regular_file_still_loads(self) -> None:
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hedge-ledger-", dir=scratch) as td:
            root = Path(td)
            state = root / "state"
            state.mkdir()
            outside = root / "outside"
            outside.mkdir()
            secret = outside / "secret.json"
            secret.write_bytes(b"secret-ledger\n")
            secret.chmod(0)
            link = state / hedge.LEDGER_FILE
            link.symlink_to(secret)
            ledger = {
                "version": 1,
                "entries": [{"lane": "cloud", "amount": 1, "task": "hard"}],
                "spent": 1,
            }
            try:
                got = hedge.save_ledger(ledger, state)
            finally:
                secret.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(got, link)
            self.assertFalse(link.is_symlink(), "ledger path is still a symlink")
            self.assertTrue(link.is_file())
            self.assertEqual(secret.read_bytes(), b"secret-ledger\n")
            saved = json.loads(link.read_text(encoding="utf-8"))
            self.assertEqual(saved["entries"][0]["task"], "hard")
            loaded = hedge.load_ledger(state)
            self.assertEqual(loaded["entries"][0]["task"], "hard")
            self.assertEqual(loaded["spent"], 1)

            hedge.save_ledger(
                {
                    "version": 1,
                    "entries": [{"lane": "local", "amount": 0, "task": "bulk"}],
                    "spent": 0,
                },
                state,
            )
            again = hedge.load_ledger(state)
            self.assertEqual(again["entries"][0]["task"], "bulk")
            self.assertEqual(again["spent"], 0)
            self.assertEqual(secret.read_bytes(), b"secret-ledger\n")
            self.assertFalse(link.is_symlink())


if __name__ == "__main__":
    unittest.main()
