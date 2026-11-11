"""Offline unit tests for pfylib (ADR-0017). Run: python3 -m unittest discover -s tests -t ."""

import os as _os

# Tests never export spans to the operator's loopback Phoenix, also when a
# module is run directly with python3 -m unittest (scripts/run_tests.py sets
# the same). tests.test_otel enables tracing per test against its own
# in-process collector. PFY_TEST_OTEL=1 leaves the environment alone.
if _os.environ.get("PFY_TEST_OTEL") != "1":
    _os.environ["PFY_OTEL"] = "0"
