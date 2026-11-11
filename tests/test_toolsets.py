"""pfylib.toolsets: matrix / plan / apply, Jev reference implementation (ADR-0017)."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import registry, toolsets  # noqa: E402
from tests._model_choice_isolation import begin as iso_begin, end as iso_end  # noqa: E402



class _TmpEnv(unittest.TestCase):
    """Isolated state dir + harness homes; no writes outside the tmp tree.

    plan() resolves decision-route, so model-choice paths stay off the real home.
    """

    KEYS = ("PFY_STATE_DIR", "GROK_HOME", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "TYPESAFE_API_KEY", "PFY_JEV_OFFLINE", "GAB_API_KEY")

    def setUp(self):
        self._iso, self._iso_saved = iso_begin(prefix="pfylib-toolset-")
        self._saved = {k: os.environ.get(k) for k in self.KEYS}
        self.tmp = self._iso
        self.state = self.tmp / "state"
        os.environ["PFY_STATE_DIR"] = str(self.state)
        os.environ["GROK_HOME"] = str(self.tmp / "grok-home")
        os.environ["CODEX_HOME"] = str(self.tmp / "codex-home")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmp / "claude-home")
        os.environ["PFY_JEV_OFFLINE"] = "1"
        os.environ.pop("TYPESAFE_API_KEY", None)
        os.environ.pop("GAB_API_KEY", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        iso_end(self._iso, self._iso_saved)


class MatrixTests(unittest.TestCase):
    def test_every_cell_present_with_valid_status(self):
        rows = toolsets.matrix(ROOT)
        tids, hids = registry.toolset_ids(ROOT), registry.harness_ids(ROOT)
        self.assertEqual(len(rows), len(tids) * len(hids))
        seen = {(r["toolset"], r["harness"]) for r in rows}
        self.assertEqual(seen, {(t, h) for t in tids for h in hids})
        for r in rows:
            self.assertIn(r["status"], toolsets.STATUSES, r)
            self.assertTrue(r["how"], "empty how for %s x %s" % (r["toolset"], r["harness"]))
            self.assertTrue(r["lanes"])

    def test_matrix_is_honest_not_all_implemented(self):
        statuses = {r["status"] for r in toolsets.matrix(ROOT)}
        self.assertIn("stub", statuses)
        self.assertIn("implemented", statuses)

    def test_matrix_text_has_header_and_counts(self):
        text = toolsets.matrix_text(ROOT)
        self.assertTrue(text.startswith("TOOLSET"))
        self.assertIn("cells: %d" % len(toolsets.matrix(ROOT)), text)
        header, grid = toolsets.matrix_grid(ROOT)
        self.assertEqual(header[1:], registry.harness_ids(ROOT))
        self.assertEqual(len(grid), len(registry.toolset_ids(ROOT)))


class PlanTests(_TmpEnv):
    def _jev_cells(self, status):
        jev = registry.toolset("jev", ROOT)
        return [h for h, c in jev["implementation"].items() if c["status"] == status]

    def test_jev_implemented_cells_produce_env_brief_files(self):
        impl = self._jev_cells("implemented")
        self.assertGreaterEqual(len(impl), 4, impl)
        for hid in impl:
            p = toolsets.plan("jev", hid, "local", root_dir=ROOT, state=self.state)
            self.assertTrue(p["ok"], p.get("copy"))
            self.assertEqual(p["live"], "READY")
            self.assertEqual(p["status"], "implemented")
            self.assertTrue(p["env"], hid)
            self.assertIn("PFY_DECISION_PATH", p["env"])
            self.assertEqual(p["env"]["PFY_DECISION_PATH"], "cua-s1-forms")
            self.assertTrue(p["brief"].startswith("# Toolset: jev"), hid)
            self.assertIn(hid, p["brief"])
            self.assertGreaterEqual(len(p["files"]), 2, hid)
            paths = [f["path"] for f in p["files"]]
            self.assertTrue(any(str(self.state) in x for x in paths), paths)
            # a harness-native surface, not only the state dir
            self.assertTrue(any(str(self.state) not in x for x in paths) or hid == "opencode", (hid, paths))

    def test_jev_partial_hermes_is_ready_but_flagged(self):
        p = toolsets.plan("jev", "hermes", root_dir=ROOT, state=self.state)
        self.assertEqual(p["status"], "partial")
        self.assertTrue(p["ok"])
        self.assertTrue(p["note"].startswith("partial"))
        self.assertTrue(p["next_step"])
        self.assertTrue(all(str(self.state) in f["path"] for f in p["files"]))

    def test_jev_stub_cells_are_stub_with_next_step(self):
        for hid in self._jev_cells("stub"):
            p = toolsets.plan("jev", hid, root_dir=ROOT, state=self.state)
            self.assertFalse(p["ok"])
            self.assertEqual(p["live"], "STUB")
            self.assertTrue(p["next_step"])
            self.assertIn("implemented today on", p["next_step"])
            self.assertEqual(p["files"], [])

    def test_jev_cloud_lane_fails_honestly_without_key(self):
        p = toolsets.plan("jev", "grok", "cloud", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("TypeSafe key", p["error"])
        self.assertIn("--lane local", p["next_step"])

    def test_jev_cloud_lane_with_key(self):
        os.environ["TYPESAFE_API_KEY"] = "test-not-a-real-key"
        p = toolsets.plan("jev", "grok", "cloud", root_dir=ROOT, state=self.state)
        self.assertTrue(p["ok"])
        self.assertEqual(p["env"]["PFY_DECISION_PATH"], "typesafe")
        self.assertIn("Lane **cloud**", p["brief"])

    def test_default_lane_is_local_when_offered(self):
        p = toolsets.plan("jev", "codex", root_dir=ROOT, state=self.state)
        self.assertEqual(p["lane"], "local")

    def test_lane_not_offered_fails(self):
        p = toolsets.plan("gab", "opencode", "local", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("no local lane", p["error"])

    def test_unknown_ids_fail_with_choices(self):
        p = toolsets.plan("nope", "grok", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("jev", p["next_step"])
        p = toolsets.plan("jev", "nope", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("grok", p["next_step"])

    def test_every_non_stub_cell_has_a_planner_never_stubs(self):
        """T-0121: implemented/partial cells plan() to READY (env/files/brief) or honest FAIL (missing dep), never STUB."""
        for r in toolsets.matrix(ROOT):
            if r["status"] == "stub":
                continue
            lanes = registry.toolset(r["toolset"], ROOT)["lanes"]
            p = toolsets.plan(r["toolset"], r["harness"], lanes[0], root_dir=ROOT, state=self.state)
            self.assertNotEqual(p["live"], "STUB", (r, p.get("copy"), p.get("next_step")))
            self.assertIn(p["live"], ("READY", "FAIL"), (r, p))
            if p["ok"]:
                self.assertTrue(p["env"] or p["files"] or p["brief"], r)
            else:
                self.assertTrue(p["next_step"], r)

    def test_stub_cells_are_stub_with_next_step(self):
        for r in toolsets.matrix(ROOT):
            if r["status"] != "stub":
                continue
            lanes = registry.toolset(r["toolset"], ROOT)["lanes"]
            p = toolsets.plan(r["toolset"], r["harness"], lanes[0], root_dir=ROOT, state=self.state)
            self.assertEqual(p["live"], "STUB", (r, p["copy"]))
            self.assertTrue(p["next_step"])
            self.assertEqual(p["files"], [])

    def test_gab_cloud_fails_without_key_and_redacts_key_when_present(self):
        p = toolsets.plan("gab", "opencode", "cloud", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("GAB_API_KEY", p["error"])
        os.environ["GAB_API_KEY"] = "gab_not-a-real-key"
        try:
            p = toolsets.plan("gab", "opencode", "cloud", root_dir=ROOT, state=self.state)
        finally:
            os.environ.pop("GAB_API_KEY", None)
        self.assertTrue(p["ok"], p)
        self.assertEqual(p["env"].get("OPENAI_BASE_URL"), "https://gab.ai/v1")
        self.assertEqual(p["env"].get("GAB_API_KEY"), toolsets.GAB_KEY_PLACEHOLDER)
        self.assertNotIn("gab_not-a-real-key", json.dumps(p["env"]))
        self.assertEqual(p["files"], [])

    def test_catalog_ask_fails_without_prompt_then_ready_with_artifact(self):
        p = toolsets.plan("catalog-ask", "grok", root_dir=ROOT, state=self.state)
        self.assertEqual(p["live"], "FAIL")
        self.assertIn("no pending catalog ask", p["error"])
        self.state.mkdir(parents=True)
        prompt = self.state / "catalog-ask-prompt.md"
        prompt.write_text("# implement foo\n", encoding="utf-8")
        p = toolsets.plan("catalog-ask", "grok", root_dir=ROOT, state=self.state)
        self.assertTrue(p["ok"], p)
        self.assertIn("PFY_CATALOG_ASK_PROMPT", p["env"])
        self.assertIn("implement foo", p["brief"])

    def test_orchestration_ready_when_agent_loops_skill_present(self):
        p = toolsets.plan("orchestration", "opencode", root_dir=ROOT, state=self.state)
        self.assertTrue(p["ok"], p)
        self.assertEqual(p["env"]["PFY_ATTACH_MODE"], "orchestration")
        self.assertTrue(any(f.get("mode") == "symlink" for f in p["files"]))
        self.assertTrue(any("opencode-skills" in f["path"] for f in p["files"]))
        grok_home = str(self.tmp / "grok-home")
        self.assertFalse(any(grok_home in f["path"] for f in p["files"]))
        grok = toolsets.plan("orchestration", "grok", root_dir=ROOT, state=self.state)
        self.assertTrue(any(grok_home in f["path"] and f.get("mode") == "symlink" for f in grok["files"]), grok["files"])


class ApplyTests(_TmpEnv):
    def test_dry_run_writes_nothing(self):
        p = toolsets.plan("jev", "codex", root_dir=ROOT, state=self.state)
        out = toolsets.apply(p, yes=False, state=self.state)
        self.assertTrue(out["dry_run"])
        self.assertEqual(out["applied"], [])
        self.assertIn("DRY-RUN", out["copy"])
        self.assertFalse(self.state.exists())

    def test_apply_codex_is_idempotent(self):
        p = toolsets.plan("jev", "codex", root_dir=ROOT, state=self.state)
        first = toolsets.apply(p, yes=True, state=self.state)
        self.assertTrue(first["ok"], first)
        self.assertEqual(first["failed"], [])
        agents = Path(os.environ["CODEX_HOME"]) / "AGENTS.md"
        self.assertTrue(agents.is_file())
        once = agents.read_text()
        second = toolsets.apply(p, yes=True, state=self.state)
        self.assertTrue(second["ok"])
        self.assertEqual(agents.read_text(), once)
        self.assertEqual(once.count(toolsets.MARK_BEGIN % "jev"), 1)
        self.assertIn("replaced", [a["result"] for a in second["applied"]])

    def test_apply_orchestration_symlinks_skill_under_state(self):
        p = toolsets.plan("orchestration", "opencode", root_dir=ROOT, state=self.state)
        self.assertTrue(p["ok"], p)
        out = toolsets.apply(p, yes=True, state=self.state, root_dir=ROOT)
        self.assertTrue(out["ok"], out)
        link = self.state / "opencode-skills" / "agent-loops"
        self.assertTrue(link.is_symlink() or link.is_dir(), link)
        self.assertTrue((link / "SKILL.md").is_file())

    def test_apply_opencode_merges_json_without_duplicates(self):
        cfg = self.state / "opencode.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"instructions": ["keep-me.md"], "model": "x"}))
        p = toolsets.plan("jev", "opencode", root_dir=ROOT, state=self.state)
        toolsets.apply(p, yes=True, state=self.state)
        toolsets.apply(p, yes=True, state=self.state)
        data = json.loads(cfg.read_text())
        self.assertEqual(data["model"], "x")
        self.assertEqual(data["instructions"][0], "keep-me.md")
        self.assertEqual(len(data["instructions"]), 2)

    def test_apply_grok_writes_skill_under_grok_home(self):
        p = toolsets.plan("jev", "grok", root_dir=ROOT, state=self.state)
        out = toolsets.apply(p, yes=True, state=self.state)
        self.assertTrue(out["ok"], out)
        skill = Path(os.environ["GROK_HOME"]) / "skills" / "pfy-jev-decision" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertTrue(skill.read_text().startswith("---\nname: pfy-jev-decision"))

    def test_apply_refuses_paths_outside_allowed_roots(self):
        p = toolsets.plan("jev", "codex", root_dir=ROOT, state=self.state)
        rogue = self.tmp / "elsewhere" / "AGENTS.md"
        p["files"].append({"path": str(rogue), "mode": "write", "content": "x"})
        out = toolsets.apply(p, yes=True, state=self.state)
        self.assertFalse(out["ok"])
        self.assertEqual(out["live"], "FAIL")
        self.assertFalse(rogue.exists())
        self.assertTrue(any("refused" in f["result"] for f in out["failed"]))

    def test_apply_of_stub_plan_writes_nothing(self):
        p = toolsets.plan("jev", "gemini", root_dir=ROOT, state=self.state)
        out = toolsets.apply(p, yes=True, state=self.state)
        self.assertEqual(out["live"], "STUB")
        self.assertEqual(out["applied"], [])
        self.assertFalse(self.state.exists())

    def test_export_env_lines_are_shell_safe(self):
        p = toolsets.plan("jev", "codex", root_dir=ROOT, state=self.state)
        lines = toolsets.export_env_lines(p)
        self.assertEqual(len(lines), len(p["env"]))
        for line in lines:
            self.assertRegex(line, r'^export [A-Z_]+="')


if __name__ == "__main__":
    unittest.main()
