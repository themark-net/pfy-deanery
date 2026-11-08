#!/usr/bin/env python3
"""Drive the assay probe with a stub binary. No network and no Chromium.

A stub that says the page works must not count as help. A stub that fails
all four planted defects must. A missing binary must not write a result.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "assay" / "probe.py"

PAGE = textwrap.dedent(
    """\
    <!DOCTYPE html><html><head><style>
    .view{display:none;padding:16px}.view.on{display:block}
    </style></head><body>
    <section class="view on" id="view-loop">
    <button type=button id=shown>Shown</button>
    </section>
    <section class=view id=view-engine>
    <button type=button id=hid>Hidden</button>
    <input id=pullname type=text>
    </section>
    <button type=button id=orgnav style=display:none>Org</button>
    </body></html>
    """
)

GREEN = {
    "version": "0.3.0",
    "works": True,
    "failed": 0,
    "passed": 2,
    "planned": 2,
    "surface": [
        {"kind": "button", "selector": "#dead", "label": "Launch session", "enabled": True}
    ],
    "cases": [
        {
            "id": "C002",
            "what": "press Launch session",
            "outcome": "passed",
            "detail": "",
            "measured": "the visible text is unchanged",
            "acts": [{"click": "#dead"}],
            "rules": [],
        },
        {
            "id": "C003",
            "what": "press Launch env",
            "outcome": "passed",
            "detail": "",
            "measured": "the visible text changed",
            "acts": [{"click": "#failpaint"}],
            "rules": [],
        },
    ],
    "console_errors": [],
    "failed_requests": [],
}

RECOVER = {
    "version": "0.3.0",
    "works": False,
    "failed": 4,
    "passed": 1,
    "planned": 5,
    "surface": [
        {"kind": "button", "selector": "#dead", "label": "Launch session", "enabled": True},
        {"kind": "button", "selector": "#hidden-throw", "label": "Pull", "enabled": True},
    ],
    "cases": [
        {
            "id": "C010",
            "what": "press Refresh status",
            "outcome": "failed",
            "detail": "undefinedFn is not defined",
            "measured": "",
            "acts": [{"click": "#throw"}],
            "rules": ["threw"],
        },
        {
            "id": "C011",
            "what": "press Launch session",
            "outcome": "failed",
            "detail": "nothing on the page changed at all",
            "measured": "the visible text is unchanged",
            "acts": [{"click": "#dead"}],
            "rules": ["no-change"],
        },
        {
            "id": "C012",
            "what": "press Launch env",
            "outcome": "failed",
            "detail": "the page says FAIL launch",
            "measured": "",
            "acts": [{"click": "#failpaint"}],
            "rules": ["fail-text"],
        },
        {
            "id": "C013",
            "what": "press Pull",
            "outcome": "failed",
            "detail": "hiddenBoom is not defined",
            "measured": "",
            "acts": [{"click": "#hidden-throw"}],
            "rules": ["threw"],
        },
    ],
    "console_errors": [],
    "failed_requests": [],
}


def _stub(path: Path, payload: dict) -> None:
    path.write_text(
        "#!/usr/bin/env python3\nimport json, sys\n"
        "sys.stdout.write(json.dumps(%r))\n" % (payload,),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class AssayProbeTest(unittest.TestCase):
    def _run(self, assay: str, folder: Path, out: Path) -> subprocess.CompletedProcess:
        page = folder / "page.html"
        page.write_text(PAGE, encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--assay",
                assay,
                "--frontend",
                str(page),
                "--out",
                str(out),
                "--tmp",
                str(folder / "work"),
                "--timeout",
                "30",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={"PATH": "/usr/bin:/bin", "HOME": str(folder), "LANG": "C.UTF-8"},
        )

    def test_green_stub_is_not_help_and_a_full_catch_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="assay-probe-test-") as tmp:
            folder = Path(tmp)
            missing = folder / "missing-out.json"
            gone = self._run(str(folder / "no-such-assay"), folder, missing)
            self.assertEqual(gone.returncode, 2)
            self.assertFalse(missing.exists())

            green_bin = folder / "green-assay"
            _stub(green_bin, GREEN)
            green_out = folder / "green.json"
            green = self._run(str(green_bin), folder, green_out)
            self.assertEqual(green.returncode, 1, green.stderr)
            body = json.loads(green_out.read_text(encoding="utf-8"))
            self.assertFalse(body["helps"])
            self.assertEqual(body["planted"]["caught"], 0)
            self.assertEqual(
                body["planted"]["items"],
                {
                    "visible-throw": False,
                    "dead-button": False,
                    "fail-text": False,
                    "hidden-throw": False,
                },
            )
            self.assertTrue(body["operator"]["works"])
            self.assertEqual(body["operator"]["markup_controls"], 4)
            self.assertEqual(body["operator"]["markup_hidden"], 3)
            self.assertEqual(body["operator"]["markup_visible"], 1)

            recover_bin = folder / "recover-assay"
            _stub(recover_bin, RECOVER)
            recover_out = folder / "recover.json"
            recover = self._run(str(recover_bin), folder, recover_out)
            self.assertEqual(recover.returncode, 0, recover.stderr)
            fixed = json.loads(recover_out.read_text(encoding="utf-8"))
            self.assertTrue(fixed["helps"])
            self.assertEqual(fixed["planted"]["caught"], 4)
            self.assertTrue(all(fixed["planted"]["items"].values()))
