"""C4 exit test: the replay diffs apply again and build-busy still holds."""
from __future__ import annotations

import unittest

from tests.test_cloud_lane_busy import *  # noqa: F401,F403
from tests.test_review_quality_replay import *  # noqa: F401,F403

if __name__ == "__main__":
    unittest.main()
