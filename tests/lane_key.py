"""Fake cloud key for lane tests whose fake grok must run.

The lanes fail closed without XAI_API_KEY (fix #53), which is right in
production. Tests that drive a lane through a fake grok need the gate open,
so they import setUpModule/tearDownModule from here. The value is a fixed
placeholder, never a real key, and the real environment is restored after.
Tests of the no-key path (tests.test_lane_cost_gate) do not use this.
"""
import os

DUMMY = "dummy-not-a-key"
_saved = []


def setUpModule():
    _saved.append(os.environ.get("XAI_API_KEY"))
    os.environ["XAI_API_KEY"] = DUMMY


def tearDownModule():
    old = _saved.pop() if _saved else None
    if old is None:
        os.environ.pop("XAI_API_KEY", None)
    else:
        os.environ["XAI_API_KEY"] = old
