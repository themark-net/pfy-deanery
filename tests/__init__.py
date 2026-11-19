"""Offline unit tests for pfylib (ADR-0017). Run: python3 -m unittest discover -s tests -t ."""

import os as _os

# Tests never export spans to the operator's loopback Phoenix, also when a
# module is run directly with python3 -m unittest (scripts/run_tests.py sets
# the same). tests.test_otel enables tracing per test against its own
# in-process collector. PFY_TEST_OTEL=1 leaves the environment alone.
if _os.environ.get("PFY_TEST_OTEL") != "1":
    _os.environ["PFY_OTEL"] = "0"

# Lane tests drive the real lane scripts, which start agents through
# scripts/lane_cage.py (rootless podman). The container runtime is replaced by
# tests/fixtures/fake_podman.py, which runs the command on the host. Tests of
# the real cage set PFY_PODMAN themselves; PFY_TEST_REAL_PODMAN=1 leaves it alone.
if _os.environ.get("PFY_TEST_REAL_PODMAN") != "1":
    _os.environ.setdefault(
        "PFY_PODMAN",
        _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fixtures", "fake_podman.py"),
    )
