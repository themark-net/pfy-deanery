import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "ops" / "systemd" / "catalog-counts.service"
TIMER = ROOT / "ops" / "systemd" / "catalog-counts.timer"


class UnitKeptTest(unittest.TestCase):
    def test_oneshot_nice_and_daily_timer_stay(self):
        service = SERVICE.read_text()
        timer = TIMER.read_text()
        self.assertIn("Type=oneshot", service)
        self.assertIn("Nice=10", service)
        self.assertIn("OnCalendar=*-*-* 04:17:00", timer)
        self.assertIn("Persistent=true", timer)
