"""CLI toolset apply and Loop Launch session share one apply ledger.

Temp HOME / PFY_STATE_DIR / harness homes only. Never touch the real
login-home ~/.pfy-mentat or ~/.local/state/pfy.
"""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from tests._model_choice_isolation import begin as iso_begin, end as iso_end
from pfylib import loop_paint, toolsets


def _login_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def _tree_snapshot(root: Path) -> tuple:
    if not root.exists() and not root.is_symlink():
        return ("missing",)
    if root.is_symlink() or not root.is_dir():
        st = root.lstat()
        return ("not-dir", st.st_ino, st.st_mtime_ns, st.st_size, st.st_mode)
    rows = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in sorted(dirnames) + sorted(filenames):
            path = base / name
            info = path.lstat()
            rel = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(path).encode("utf-8")
            elif stat.S_ISREG(info.st_mode):
                data = path.read_bytes()
            else:
                rows.append((rel, "other", info.st_mode, info.st_ino, info.st_mtime_ns))
                continue
            rows.append((rel, hashlib.sha256(data).hexdigest(), info.st_mode, info.st_ino, info.st_mtime_ns))
    return ("dir", tuple(rows))


_REAL_STATE = _login_home() / ".pfy-mentat"
_REAL_XDG = Path(os.environ.get("XDG_STATE_HOME") or (_login_home() / ".local" / "state")) / "pfy"
_REAL_STATE_BEFORE = _tree_snapshot(_REAL_STATE)
_REAL_XDG_BEFORE = _tree_snapshot(_REAL_XDG)


def _records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    recs = data.get("records") if isinstance(data, dict) else data
    return [r for r in (recs or []) if isinstance(r, dict)]


def _sig(recs: list[dict]) -> set[tuple]:
    out = set()
    for r in recs:
        out.add(
            (
                str(r.get("harness") or ""),
                str(r.get("item") or ""),
                str(r.get("kind") or ""),
                str(r.get("path") or ""),
                str(r.get("sha256_after") or ""),
            )
        )
    return out


class ApplyLedger(unittest.TestCase):
    def setUp(self) -> None:
        self._iso, self._iso_saved = iso_begin(prefix="pfy-apply-ledger-")
        self._saved = {
            k: os.environ.get(k)
            for k in ("PFY_STATE_DIR", "GROK_HOME", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "PFY_JEV_OFFLINE", "GAB_API_KEY")
        }
        self.tmp = self._iso
        self.state = self.tmp / "state"
        os.environ["PFY_STATE_DIR"] = str(self.state)
        os.environ["GROK_HOME"] = str(self.tmp / "grok-home")
        os.environ["CODEX_HOME"] = str(self.tmp / "codex-home")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmp / "claude-home")
        os.environ["PFY_JEV_OFFLINE"] = "1"
        os.environ.pop("GAB_API_KEY", None)

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        iso_end(self._iso, self._iso_saved)
        self.assertEqual(_tree_snapshot(_REAL_STATE), _REAL_STATE_BEFORE, "touched login-home ~/.pfy-mentat")
        self.assertEqual(_tree_snapshot(_REAL_XDG), _REAL_XDG_BEFORE, "touched login-home ~/.local/state/pfy")

    def ledger_path(self) -> Path:
        return self.state / "installed.json"

    def cli_apply(self, toolset: str = "jev", harness: str = "grok"):
        p = toolsets.plan(toolset, harness, root_dir=ROOT, state=self.state)
        return toolsets.apply(p, yes=True, state=self.state, root_dir=ROOT)

    def gui_apply(self, toolset: str = "jev", harness: str = "grok"):
        rec = loop_paint.toggle(toolset, True, state=self.state, root_dir=ROOT)
        self.assertTrue(rec.get("ok"), rec)
        return loop_paint.apply_enabled(hid=harness, state=self.state, root_dir=ROOT, yes=True)

    def test_gui_and_cli_write_equivalent_ledger_entries(self) -> None:
        cli = self.cli_apply()
        self.assertTrue(cli.get("ok"), cli)
        cli_recs = _records(self.ledger_path())
        self.assertTrue(cli_recs, "CLI apply wrote no ledger")
        self.assertTrue(all(r.get("item") == "jev" and r.get("harness") == "grok" for r in cli_recs), cli_recs)
        self.assertTrue(all(r.get("kind") == "file" for r in cli_recs), cli_recs)
        cli_sig = _sig(cli_recs)

        shutil.rmtree(self.state, ignore_errors=True)
        shutil.rmtree(self.tmp / "grok-home", ignore_errors=True)
        self.assertFalse(self.ledger_path().exists())

        gui = self.gui_apply()
        self.assertTrue(gui, gui)
        self.assertTrue(all(row.get("ok") for row in gui), gui)
        gui_recs = _records(self.ledger_path())
        self.assertEqual(_sig(gui_recs), cli_sig)

    def test_dry_run_and_stub_write_no_ledger(self) -> None:
        p = toolsets.plan("jev", "grok", root_dir=ROOT, state=self.state)
        out = toolsets.apply(p, yes=False, state=self.state, root_dir=ROOT)
        self.assertTrue(out["dry_run"])
        self.assertFalse(self.ledger_path().exists())
        stub = toolsets.plan("jev", "gemini", root_dir=ROOT, state=self.state)
        toolsets.apply(stub, yes=True, state=self.state, root_dir=ROOT)
        self.assertFalse(self.ledger_path().exists())

    def test_unwritable_ledger_fails_with_existing_copy_then_recovers(self) -> None:
        self.state.mkdir(parents=True)
        blocker = self.ledger_path()
        blocker.mkdir()
        (blocker / "junk").write_text("nope")
        out = self.cli_apply()
        self.assertFalse(out.get("ok"), out)
        self.assertEqual(out.get("live"), "FAIL")
        copy = str(out.get("copy") or "")
        nxt = str(out.get("next_step") or "")
        self.assertIn("FAIL apply", copy)
        self.assertTrue(nxt.startswith("FAIL:"), nxt)
        self.assertIn("installed.json", nxt)
        skill = Path(os.environ["GROK_HOME"]) / "skills" / "pfy-jev-decision" / "SKILL.md"
        self.assertTrue(skill.is_file(), "partial write: files already landed")
        self.assertTrue(blocker.is_dir())

        shutil.rmtree(blocker)
        again = self.cli_apply()
        self.assertTrue(again.get("ok"), again)
        recs = _records(self.ledger_path())
        self.assertTrue(recs)
        self.assertTrue(all(r.get("item") == "jev" for r in recs), recs)
        self.assertTrue(skill.is_file())
