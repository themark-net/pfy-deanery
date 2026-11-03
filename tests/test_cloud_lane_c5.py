"""C5 exit test: saved mutants apply again, overlapping default gates pass, gate-rewrote still holds."""
from __future__ import annotations

import unittest

from tests.test_cloud_lane_gate_rewrite import *  # noqa: F401,F403
from tests.test_mut_cloud2_harness import *  # noqa: F401,F403
from tests.test_pfy_build_phase_clock import *  # noqa: F401,F403

if __name__ == "__main__":
    unittest.main()
