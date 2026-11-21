"""Pregate runs the suite with TMPDIR under its own scratch root.

That root is longer than /tmp, and an operator may also set
PREGATE_STATE_ROOT. Tests that passed on hosted CI (TMPDIR unset) must
still pass there. This replays the affected cases in a child process
with a long TMPDIR and a decoy PREGATE_STATE_ROOT, the way pregate's
ubuntu-parity step does.

Fail: any listed case fails under the long root. Recover: the same cases
pass with the default environment, so a failure here is environment
sensitivity, not a product regression.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Long enough that TMPDIR + a short socket leaf exceeds the 108-byte
# AF_UNIX sun_path, and that a head-truncated error loses its file name.
LONG_LEN = 120

CASES = [
    # Chrome builds its singleton socket under TMPDIR.
    "tests.test_lane_graph.FrontendRenderTests.test_headless_chrome_paints_nodes_edges_and_tabs",
    # The error text names the ledger file at the end of a long path.
    "tests.test_apply_ledger.ApplyLedger.test_unwritable_ledger_fails_with_existing_copy_then_recovers",
    # The probes accept work dirs under the caller's TMPDIR.
    "tests.test_squadra_probe.SquadraProbeTest.test_leaking_cli_fails_and_a_refusing_cli_recovers",
    "tests.test_ai_memory_probe.AiMemoryProbeTests.test_server_down_skips_without_calling_the_mailbox",
    # The over-limit guard measures the default state root.
    "tests.test_workflow_image_pin.WorkflowImagePinTests.test_root_path_over_the_limit_is_refused",
]


def long_tmpdir(base: Path) -> Path:
    pad = LONG_LEN - len(str(base)) - 1
    path = base / ("t" * max(pad, 8))
    path.mkdir(parents=True)
    return path


class PregateLongTmpdirTest(unittest.TestCase):
    def test_affected_cases_pass_under_a_long_tmpdir_and_a_set_state_root(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="plt-"))
        try:
            tmp = long_tmpdir(base)
            self.assertGreaterEqual(len(str(tmp)), LONG_LEN - 1)
            # A short state root: its scratch path fits under the
            # default-root limit the over-limit case computes.
            decoy = "tmp/plt-state-%d" % os.getpid()
            env = os.environ.copy()
            env["TMPDIR"] = str(tmp)
            env["PREGATE_STATE_ROOT"] = decoy
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", *CASES],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-4000:])
        finally:
            shutil.rmtree(base, ignore_errors=True)
            shutil.rmtree(ROOT / decoy, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
