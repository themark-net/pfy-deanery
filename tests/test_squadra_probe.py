#!/usr/bin/env python3
"""Drive the Squadra probe with a stub CLI. No network and no real checkout.

A stub that allows a start with no ACK, matches an always-passing test, and
accepts the author's own review must not exit 0. A stub that refuses those
three and records a red-then-green split must.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "squadra" / "probe.py"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys
    from pathlib import Path

    MODE = %r
    args = sys.argv[1:]
    if "--version" in args:
        print("3.10.1")
        raise SystemExit(0)

    def flag(name):
        if name not in args:
            return ""
        return args[args.index(name) + 1]

    root = Path(flag("--root")) if flag("--root") else None
    command = ""
    skip = False
    for token in args:
        if skip:
            skip = False
            continue
        if token == "--root":
            skip = True
            continue
        if token.startswith("-"):
            continue
        command = token
        break
    state_path = (root / "stub-state.json") if root else None

    def load():
        if state_path and state_path.is_file():
            return json.loads(state_path.read_text(encoding="utf-8"))
        return {"delivered": False, "reviewed": False}

    def save(state):
        if state_path:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")

    def runs(kind):
        if kind == "real":
            return [
                {"label": "original", "native_rc": 1, "outcome": "assertion", "status": "completed"},
                {"label": "remedy", "native_rc": 0, "outcome": "passed", "status": "completed"},
            ]
        return [
            {"label": "original", "native_rc": 0, "outcome": "passed", "status": "completed"},
            {"label": "remedy", "native_rc": 0, "outcome": "passed", "status": "completed"},
        ]

    if command == "challenge" and flag("--output"):
        out = Path(flag("--output"))
        out.mkdir(parents=True, exist_ok=True)
        kind = "green" if "challenge-green" in str(out) else "real"
        if MODE == "leak":
            kind = "green"
        (out / "RESULT.json").write_text(json.dumps({"runs": runs(kind)}), encoding="utf-8")
        if MODE == "match" and kind == "green":
            sys.stderr.write("Squadra: fix_challenge_not_matched; read retained logs\\n")
            raise SystemExit(1)
        print(json.dumps({"status": "matched"}))
        raise SystemExit(0)

    if command == "deliver":
        state = load()
        state["delivered"] = True
        save(state)
        print(json.dumps({"handoff": "review-stub"}))
        raise SystemExit(0)

    if command == "doctor":
        print(json.dumps({"integrity": "passed", "events": 4, "pending_ack": []}))
        raise SystemExit(0)

    if MODE == "leak":
        raise SystemExit(0)

    state = load()
    if command == "start":
        sys.stderr.write("Squadra: Assignment has no recipient ACK\\n")
        raise SystemExit(1)
    if command == "close":
        if not state["delivered"]:
            sys.stderr.write("Squadra: Candidate drift; deliver/prove the new exact source\\n")
            raise SystemExit(1)
        if not state["reviewed"]:
            sys.stderr.write("Squadra: Independent current code review pending\\n")
            raise SystemExit(1)
        raise SystemExit(0)
    if command == "review" and flag("--actor") == "w1":
        sys.stderr.write(
            "Squadra: Author cannot independently review own changes, even under another seat ID\\n"
        )
        raise SystemExit(1)
    if command == "review" and flag("--actor") == "r1":
        state["reviewed"] = True
        save(state)
        raise SystemExit(0)
    raise SystemExit(0)
    """
)


class SquadraProbeTest(unittest.TestCase):
    def _run(self, mode: str) -> subprocess.CompletedProcess[str]:
        folder = Path(self.folder)
        stub = folder / ("stub-%s.py" % mode)
        stub.write_text(STUB % mode, encoding="utf-8")
        out = folder / ("results-%s.json" % mode)
        work = folder / ("work-%s" % mode)
        return subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--squadra",
                str(stub),
                "--work",
                str(work),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(folder / "home"),
                "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )

    def test_leaking_cli_fails_and_a_refusing_cli_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="squadra-probe-test-") as tmp:
            self.folder = tmp
            leaked = self._run("leak")
            self.assertNotEqual(leaked.returncode, 0, leaked.stderr + leaked.stdout)
            leaked_path = Path(tmp) / "results-leak.json"
            self.assertTrue(leaked_path.is_file(), leaked.stderr)
            leaked_body = json.loads(leaked_path.read_text(encoding="utf-8"))
            self.assertLess(leaked_body["refuse_count"], leaked_body["refuse_of"])
            self.assertFalse(leaked_body["refuses"]["start_before_ack"])
            self.assertFalse(leaked_body["refuses"]["always_passing_not_matched"])
            self.assertFalse(leaked_body["refuses"]["author_review"])

            matched = self._run("match")
            self.assertEqual(matched.returncode, 0, matched.stderr + matched.stdout)
            body = json.loads((Path(tmp) / "results-match.json").read_text(encoding="utf-8"))
            self.assertEqual(body["problems"], [])
            self.assertEqual(body["refuse_count"], 5)
            self.assertTrue(body["real_challenge_matched"])
            self.assertEqual(body["close_exit"], 0)
            self.assertEqual(body["gap_b"]["pfy_build_invoked"], False)
            self.assertTrue(body["real_home_untouched"])


if __name__ == "__main__":
    unittest.main()
