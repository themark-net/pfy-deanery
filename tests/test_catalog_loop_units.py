import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CatalogLoopUnitsTest(unittest.TestCase):
    def test_user_units_match_hourly_oneshot_contract(self):
        svc = (ROOT / "ops" / "systemd" / "catalog-loop.service").read_text()
        timer = (ROOT / "ops" / "systemd" / "catalog-loop.timer").read_text()
        self.assertIn("Type=oneshot", svc)
        self.assertIn("Nice=10", svc)
        self.assertIn("catalog_loop.sh", svc)
        self.assertNotIn("sudo", svc)
        self.assertIn("OnCalendar=hourly", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("RandomizedDelaySec=120", timer)
