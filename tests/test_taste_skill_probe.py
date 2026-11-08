#!/usr/bin/env python3
"""Drive the taste-skill probe with a stub node. No network, no Chrome, no real lint.

A stub that clears the planted page must not count as a floor. A stub that
writes history under HOME/.taste-skill must not count as contained. The same
probe accepts a stub that flags the planted page and keeps history on
TASTE_SKILL_HISTORY.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "taste-skill" / "probe.py"
FIXTURES = ROOT / "eval" / "evq1107" / "taste-skill" / "fixtures"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    args = sys.argv[1:]
    if args and args[0] == "-p":
        print("v0")
        raise SystemExit(0)
    script = args[0] if args else ""
    rest = args[1:]
    name = script.rsplit("/", 1)[-1]
    leak = LEAK
    blind = BLIND
    if name == "lint.mjs":
        target = rest[0] if rest else ""
        if not os.path.exists(target):
            print("Not found: " + target, file=sys.stderr)
            raise SystemExit(2)
        if blind or os.path.isdir(target):
            print(json.dumps({"files": 1, "findings": []}))
            raise SystemExit(0)
        text = open(target, encoding="utf-8").read().lower()
        if "lorem ipsum" in text or "linear-gradient" in text:
            findings = [
                {"level": "FAIL", "id": "gradient", "line": 1, "match": "linear-gradient"},
                {"level": "FAIL", "id": "purple", "line": 1, "match": "#6366f1"},
                {"level": "FAIL", "id": "emoji", "line": 1, "match": "emoji"},
                {"level": "FAIL", "id": "lorem", "line": 1, "match": "Lorem ipsum"},
            ]
            print(json.dumps({"files": 1, "findings": findings}))
            raise SystemExit(1)
        print(json.dumps({"files": 1, "findings": []}))
        raise SystemExit(0)
    if name == "draw.mjs":
        hist = os.environ.get("TASTE_SKILL_HISTORY") or ""
        prior = ""
        if hist and os.path.isfile(hist):
            with open(hist, encoding="utf-8") as handle:
                prior = handle.read()
        style = "data-terminal" if "steer" in prior else "true-black-flat"
        if "--options" in rest:
            sys.stdout.write("# 2 app styles dealt\\n\\n## `" + style + "` - flat\\n")
            raise SystemExit(0)
        if "--out" in rest:
            out = rest[rest.index("--out") + 1]
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, "direction.json"), "w", encoding="utf-8") as handle:
                json.dump({
                    "kind": "app",
                    "seed": 7,
                    "style": {"id": style},
                    "shell": {"id": "ruled-t-frame"},
                    "screens": [],
                }, handle)
        hist = os.environ.get("TASTE_SKILL_HISTORY")
        if hist and not leak:
            os.makedirs(os.path.dirname(hist), exist_ok=True)
            with open(hist, "w", encoding="utf-8") as handle:
                handle.write("[]")
        if leak:
            home = os.path.join(os.environ["HOME"], ".taste-skill")
            os.makedirs(home, exist_ok=True)
            with open(os.path.join(home, "history.json"), "w", encoding="utf-8") as handle:
                handle.write("[]")
        raise SystemExit(0)
    raise SystemExit(2)
    """
)


def _stub(path: Path, leak: bool, blind: bool) -> None:
    body = STUB.replace("LEAK", "True" if leak else "False").replace("BLIND", "True" if blind else "False")
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class TasteSkillProbeTest(unittest.TestCase):
    def _run(self, folder: Path, node: Path, out: Path) -> subprocess.CompletedProcess[str]:
        scripts = folder / "scripts"
        scripts.mkdir(exist_ok=True)
        for name in ("lint.mjs", "draw.mjs", "inspect.mjs"):
            (scripts / name).write_text("// stub\n", encoding="utf-8")
        frontend = folder / "frontend"
        frontend.mkdir(exist_ok=True)
        (frontend / "index.html").write_text("<html><body><h1>Launch session</h1></body></html>\n", encoding="utf-8")
        (folder / "login").mkdir(exist_ok=True)
        cmd = [
            sys.executable,
            str(PROBE),
            "--node",
            str(node),
            "--scripts",
            str(scripts),
            "--fixtures",
            str(FIXTURES),
            "--operator-html",
            str(FIXTURES / "operator-clean.html"),
            "--frontend",
            str(frontend),
            "--repo",
            str(folder / "repo"),
            "--out",
            str(out),
            "--home",
            str(folder / "home"),
            "--tmp",
            str(folder / "tmp"),
            "--skip-inspect",
            "--login-home",
            str(folder / "login"),
        ]
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def test_blind_lint_fails_and_a_flagged_page_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-taste-blind-") as raw:
            folder = Path(raw)
            blind = folder / "blind-node"
            _stub(blind, leak=False, blind=True)
            blind_out = folder / "blind.json"
            bad = self._run(folder, blind, blind_out)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertTrue(blind_out.is_file())
            blind_body = json.loads(blind_out.read_text(encoding="utf-8"))
            self.assertEqual(blind_body["separation_app"], 0)
            self.assertFalse(blind_body["home_leak"])
            self.assertEqual(blind_body["lint"]["planted_slop_app"]["fail_n"], 0)

            recover = folder / "recover-node"
            _stub(recover, leak=False, blind=False)
            recover_out = folder / "recover.json"
            good = self._run(folder, recover, recover_out)
            self.assertEqual(good.returncode, 0, good.stderr + good.stdout)
            fixed = json.loads(recover_out.read_text(encoding="utf-8"))
            self.assertEqual(fixed["separation_app"], 4)
            self.assertEqual(fixed["lint"]["operator_html_app"]["fail_n"], 0)
            self.assertEqual(fixed["lint"]["smoke_slop"]["rc"], 1)
            self.assertEqual(fixed["lint"]["smoke_clean"]["rc"], 0)
            self.assertEqual(fixed["lint"]["missing"]["rc"], 2)
            self.assertFalse(fixed["home_leak"])
            self.assertTrue(fixed["draw"]["fresh_agree"])
            self.assertEqual(fixed["draw"]["fresh"][0]["style"], "true-black-flat")
            self.assertEqual(fixed["tauri_bins"], [])

    def test_history_leak_fails_and_the_temp_history_path_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-taste-leak-") as raw:
            folder = Path(raw)
            leaking = folder / "leak-node"
            _stub(leaking, leak=True, blind=False)
            leak_out = folder / "leak.json"
            bad = self._run(folder, leaking, leak_out)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            leaked = json.loads(leak_out.read_text(encoding="utf-8"))
            self.assertTrue(leaked["home_leak"])
            self.assertGreater(leaked["separation_app"], 0)
            self.assertTrue((folder / "home" / ".taste-skill" / "history.json").is_file())

        with tempfile.TemporaryDirectory(prefix="pfy-taste-held-") as raw:
            folder = Path(raw)
            seeded = folder / "tmp"
            seeded.mkdir()
            for name in ("h-fresh-a.json", "h-fresh-b.json"):
                (seeded / name).write_text('[{"style": "steer"}]\n', encoding="utf-8")
            contained = folder / "contained-node"
            _stub(contained, leak=False, blind=False)
            contained_out = folder / "contained.json"
            good = self._run(folder, contained, contained_out)
            self.assertEqual(good.returncode, 0, good.stderr + good.stdout)
            held = json.loads(contained_out.read_text(encoding="utf-8"))
            self.assertFalse(held["home_leak"])
            self.assertEqual(held["separation_app"], 4)
            self.assertEqual(held["draw"]["fresh"][0]["style"], "true-black-flat")
            self.assertFalse((folder / "home" / ".taste-skill").exists())
            self.assertTrue((folder / "tmp" / "h-shared.json").is_file())


if __name__ == "__main__":
    unittest.main()
