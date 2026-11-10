"""The hermes-feedback probe scores the ported skill. It does not install Hermes.

A Reflect row that drops /hermes-feedback must fail even when that name
remains elsewhere in AGENTS.md. Dropping the curator sentence drops one
loop. A missing skill file exits 2. Recovery is to put the text back.
"""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval/evals/hermes-agent-feedback-loops/probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("hermes_feedback_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE_MOD = _load()


def _stage(mod) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="hermes-probe-"))
    for rel in (
        mod.SKILL_REL,
        mod.PORT_REL,
        mod.MIRROR_SKILL_REL,
        mod.MIRROR_PORT_REL,
        mod.MANIFEST_REL,
        mod.STRUCTURAL_REL,
        mod.AGENTS_REL,
    ):
        dest = tmp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    return tmp


class HermesFeedbackProbeTests(unittest.TestCase):
    def test_live_tree_has_three_loops(self) -> None:
        result, code = PROBE_MOD.measure(ROOT)
        self.assertEqual(code, 0)
        self.assertEqual(result["ported_loops"], 3)
        self.assertTrue(result["consistent"])
        self.assertTrue(result["guards"]["reflect_routes_skill"])
        self.assertTrue(result["guards"]["install_forbidden"])
        self.assertFalse(result["installed"])
        self.assertEqual(result["runs"], 0)

    def test_reflect_row_without_the_skill_fails(self) -> None:
        tmp = _stage(PROBE_MOD)
        self.addCleanup(shutil.rmtree, tmp)
        path = tmp / PROBE_MOD.AGENTS_REL
        text = path.read_text(encoding="utf-8")
        old = "| Reflect | **`/hermes-feedback`**"
        self.assertIn(old, text)
        text = text.replace(old, "| Reflect | **`/retro`**", 1)
        text = text.replace(
            "# AGENTS.md",
            "# AGENTS.md\n\nSee /hermes-feedback in the skills list.\n",
            1,
        )
        path.write_text(text, encoding="utf-8")
        result, code = PROBE_MOD.measure(tmp)
        self.assertEqual(code, 1)
        self.assertFalse(result["guards"]["reflect_routes_skill"])
        self.assertEqual(result["ported_loops"], 3)
        self.assertFalse(result["consistent"])

    def test_install_ban_must_stay_on_one_line(self) -> None:
        tmp = _stage(PROBE_MOD)
        self.addCleanup(shutil.rmtree, tmp)
        for rel in (PROBE_MOD.SKILL_REL, PROBE_MOD.MIRROR_SKILL_REL):
            path = tmp / rel
            text = path.read_text(encoding="utf-8")
            self.assertIn("Install or require", text)
            text = text.replace(" as runtime", "", 1)
            text += "\nUpstream is described as runtime in its own docs.\n"
            path.write_text(text, encoding="utf-8")
        result, code = PROBE_MOD.measure(tmp)
        self.assertEqual(code, 1)
        self.assertFalse(result["guards"]["install_forbidden"])
        self.assertEqual(result["ported_loops"], 3)

    def test_dropping_the_daemon_sentence_drops_a_loop(self) -> None:
        tmp = _stage(PROBE_MOD)
        self.addCleanup(shutil.rmtree, tmp)
        for rel in (PROBE_MOD.SKILL_REL, PROBE_MOD.MIRROR_SKILL_REL):
            path = tmp / rel
            text = path.read_text(encoding="utf-8")
            self.assertIn("no background daemon required", text)
            path.write_text(
                text.replace("no background daemon required", "maintenance is explicit", 1),
                encoding="utf-8",
            )
        result, code = PROBE_MOD.measure(tmp)
        self.assertEqual(code, 1)
        self.assertEqual(result["ported_loops"], 2)
        self.assertEqual(result["loops"][2]["missing"], ["no background daemon required"])

    def test_missing_skill_exits_2(self) -> None:
        tmp = _stage(PROBE_MOD)
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / PROBE_MOD.SKILL_REL).unlink()
        result, code = PROBE_MOD.measure(tmp)
        self.assertEqual(code, 2)
        self.assertEqual(result["ported_loops"], 0)
        self.assertEqual(result["error"], "missing")
        self.assertIn(PROBE_MOD.SKILL_REL, result["missing"])
