"""The asm probe must not score a copied high-risk skill as blocked.

A stub asm prints High Risk, exits 0, and writes SKILL.md. The probe's
high_risk_blocked stays 0/1. A second run where that install exits 1 and
writes nothing scores 1/1. A third run reports success with an empty path
while a SKILL.md sits in the process directory. That score stays unknown.
No network and no real asm binary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "eval/evq1107/asm-agent-skill-manager"

STUB = textwrap.dedent(
    r"""
    #!/usr/bin/env python3
    import json, shutil, sys
    from pathlib import Path
    args = sys.argv[1:]
    if args[:1] == ["--version"]:
        print("asm v9.9.9 (abc1234)")
        raise SystemExit(0)
    if args[:2] == ["audit", "security"]:
        target = args[2] if len(args) > 2 else ""
        if target == "planted":
            print(json.dumps({
                "verdict": "safe",
                "totalFiles": 0,
                "totalLines": 0,
                "verdictReason": "No suspicious patterns detected.",
            }))
            raise SystemExit(0)
        print("Error: Skill not found.", file=sys.stderr)
        raise SystemExit(1)
    if args[:1] == ["install"]:
        source = Path(args[1])
        provider = args[args.index("-p") + 1]
        folder = ".grok" if provider == "grok" else ".opencode"
        dest = Path.cwd() / folder / "skills" / source.name
        here = Path(__file__).resolve().parent
        refuse = (here / "refuse-planted").is_file() and source.name == "planted"
        if refuse:
            print("refused", file=sys.stderr)
            raise SystemExit(1)
        if (here / "empty-path").is_file() and source.name == "planted":
            print("Risk:        [!] High Risk")
            print("[Shell commands] (1 matches)")
            print("[Credentials] (1 matches)")
            print("[External URLs] (1 matches)")
            print(json.dumps({
                "success": True,
                "path": "",
                "provider": provider,
                "resolutionSource": "github",
            }))
            raise SystemExit(0)
        dest.mkdir(parents=True)
        shutil.copy(source / "SKILL.md", dest / "SKILL.md")
        if source.name == "planted":
            print("Risk:        [!] High Risk")
            print("[Shell commands] (1 matches)")
            print("[Credentials] (1 matches)")
            print("[External URLs] (1 matches)")
        else:
            print("Risk:        [ok] Safe")
        print(json.dumps({
            "success": True,
            "path": str(dest),
            "provider": provider,
            "resolutionSource": "github",
        }))
        raise SystemExit(0)
    raise SystemExit(2)
    """
)


class ProbeScoreTests(unittest.TestCase):
    def _run(self, refuse: bool = False, empty_path: bool = False, cache_mode: str = "xdg") -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "lane"
            shutil.copytree(
                PROBE_DIR,
                dest,
                ignore=shutil.ignore_patterns("results.json", "REPORT.md", "VERDICT", "__pycache__"),
            )
            stub = Path(tmp) / "asm"
            stub.write_text(STUB.lstrip("\n"), encoding="utf-8")
            stub.chmod(0o755)
            if refuse:
                (Path(tmp) / "refuse-planted").write_text("1\n", encoding="utf-8")
            # A SKILL.md next to the process would look landed if an empty
            # receipt path collapsed to ".".
            if empty_path:
                (Path(tmp) / "empty-path").write_text("1\n", encoding="utf-8")
                (Path(tmp) / "SKILL.md").write_text(
                    "bash -c\nchild_process\nAPI_KEY=\nhttps://example.invalid\n",
                    encoding="utf-8",
                )
            env = os.environ.copy()
            env["ASM_BIN"] = str(stub)
            home = Path(tmp) / "home"
            xdg = Path(tmp) / "xdg-cache"
            home.mkdir()
            xdg.mkdir()
            (Path(tmp) / "xdg-config").mkdir()
            env["HOME"] = str(home)
            env["XDG_CONFIG_HOME"] = str(Path(tmp) / "xdg-config")
            if cache_mode == "home":
                env.pop("XDG_CACHE_HOME", None)
                cache = home / ".cache" / "pfy" / "tools" / "asm-agent-skill-manager"
            else:
                env["XDG_CACHE_HOME"] = str(xdg)
                cache = xdg / "pfy" / "tools" / "asm-agent-skill-manager"
            # The old probe always mkdir'd this login path. A hosted runner
            # has no /home/mark. Missing stays missing. An existing dir must
            # not be rewritten.
            hard = Path("/home/mark/.cache/pfy/tools/asm-agent-skill-manager/tmp/asm-probe")
            before = hard.stat().st_mtime_ns if hard.exists() else None
            proc = subprocess.run(
                [sys.executable, str(dest / "probe.py")],
                cwd=Path(tmp) if empty_path else ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            after = hard.stat().st_mtime_ns if hard.exists() else None
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertEqual(before, after)
            self.assertTrue((cache / "tmp" / "asm-probe").is_dir(), proc.stderr + proc.stdout)
            if cache_mode != "home":
                self.assertFalse(
                    (home / ".cache" / "pfy" / "tools" / "asm-agent-skill-manager").exists()
                )
            return json.loads((dest / "results.json").read_text(encoding="utf-8"))

    def test_cache_uses_home_when_xdg_cache_home_is_unset(self) -> None:
        data = self._run(cache_mode="home")
        self.assertEqual(data["high_risk_blocked"], "0/1")
        self.assertTrue(data["real_homes_unchanged"])

    def test_copied_high_risk_is_not_a_block_and_a_refusal_is(self) -> None:
        copied = self._run(refuse=False)
        self.assertTrue(copied["planted_install"]["landed"])
        self.assertEqual(copied["planted_install"]["risk"], "high")
        self.assertEqual(copied["planted_install"]["categories"], [
            "Shell commands",
            "Credentials",
            "External URLs",
        ])
        self.assertFalse(copied["planted_install"]["blocked"])
        self.assertEqual(copied["high_risk_blocked"], "0/1")
        self.assertEqual(copied["audit_after_install"]["verdict"], "safe")
        self.assertEqual(copied["audit_after_install"]["total_files"], 0)
        self.assertFalse(copied["local_audit_before_copy"]["scanned"])
        self.assertEqual(copied["providers_landed"], "2/2")
        self.assertEqual(copied["clean_safe"], "2/2")
        self.assertTrue(copied["real_homes_unchanged"])

        refused = self._run(refuse=True)
        self.assertFalse(refused["planted_install"]["landed"])
        self.assertEqual(refused["planted_install"]["exit"], 1)
        self.assertTrue(refused["planted_install"]["blocked"])
        self.assertEqual(refused["high_risk_blocked"], "1/1")
        self.assertEqual(refused["providers_landed"], "2/2")

        empty = self._run(empty_path=True)
        self.assertEqual(empty["planted_install"]["path"], "")
        self.assertFalse(empty["planted_install"]["landed"])
        self.assertFalse(empty["planted_install"]["blocked"])
        self.assertEqual(empty["planted_install"]["risk"], "high")
        self.assertTrue(all(value is False for value in empty["planted_install"]["planted_tokens_present"].values()))
        self.assertEqual(empty["high_risk_blocked"], "unknown")
        self.assertEqual(empty["preview_categories"], "3/3")


if __name__ == "__main__":
    unittest.main()
