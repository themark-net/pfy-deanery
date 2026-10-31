"""pfylib.registry: loaders + validate() (ADR-0017)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import registry  # noqa: E402


class RegistryLoadTests(unittest.TestCase):
    def test_root_and_state_dir(self):
        self.assertEqual(registry.root(ROOT), ROOT)
        self.assertTrue((registry.root() / "data" / "toolsets.json").is_file())
        self.assertEqual(registry.state_dir("/tmp/x"), registry.state_dir("/tmp/x"))

    def test_harness_axis_is_role_harness_only(self):
        hids = registry.harness_ids(ROOT)
        self.assertGreaterEqual(len(hids), 5)
        for expected in ("grok", "opencode", "claude-code", "codex", "hermes"):
            self.assertIn(expected, hids)
        for not_a_harness in ("ollama", "freetoken", "agent-cage"):
            self.assertNotIn(not_a_harness, hids)

    def test_toolsets_seeded(self):
        tids = registry.toolset_ids(ROOT)
        self.assertEqual(
            set(tids),
            {
                "jev",
                "gab",
                "opencontext",
                "code-graph",
                "orchestration",
                "catalog-ask",
                "core-skills",
                "rea",
            },
        )
        self.assertEqual(len(tids), len(set(tids)))
        jev = registry.toolset("jev", ROOT)
        self.assertIsNotNone(jev)
        self.assertIn("local", jev["lanes"])
        self.assertIsNone(registry.toolset("nope", ROOT))
        self.assertIsNone(registry.harness("nope", ROOT))

    def test_repo_data_validates(self):
        self.assertEqual(registry.validate(root_dir=ROOT), [])


class RegistryValidateTests(unittest.TestCase):
    def setUp(self):
        self.ts = registry.load_toolsets(ROOT)
        self.hs = registry.load_harnesses(ROOT)

    def _problems(self, ts):
        return registry.validate(ts, self.hs)

    def test_missing_cell_reported(self):
        ts = copy.deepcopy(self.ts)
        del ts["toolsets"][0]["implementation"]["grok"]
        probs = self._problems(ts)
        self.assertTrue(any("x grok: missing cell" in p for p in probs), probs)

    def test_bad_status_reported(self):
        ts = copy.deepcopy(self.ts)
        ts["toolsets"][0]["implementation"]["grok"]["status"] = "ready"
        self.assertTrue(any("status 'ready' not in" in p for p in self._problems(ts)))

    def test_unknown_harness_and_bad_lane(self):
        ts = copy.deepcopy(self.ts)
        ts["toolsets"][0]["implementation"]["vscode"] = {"status": "stub", "how": "x"}
        ts["toolsets"][1]["lanes"] = ["edge"]
        probs = self._problems(ts)
        self.assertTrue(any("unknown harness 'vscode'" in p for p in probs))
        self.assertTrue(any("lanes must be non-empty subset" in p for p in probs))

    def test_catalog_tool_must_be_present_string_or_null(self):
        ts = copy.deepcopy(self.ts)
        del ts["toolsets"][0]["catalog_tool"]
        ts["toolsets"][1]["catalog_tool"] = 7
        probs = self._problems(ts)
        self.assertTrue(any("missing catalog_tool" in p for p in probs))
        self.assertTrue(any("catalog_tool must be string or null" in p for p in probs))

    def test_duplicate_id_and_empty_rows(self):
        ts = copy.deepcopy(self.ts)
        ts["toolsets"].append(copy.deepcopy(ts["toolsets"][0]))
        self.assertTrue(any("duplicate id" in p for p in self._problems(ts)))
        self.assertTrue(any("empty or missing" in p for p in self._problems({"toolsets": []})))

    def _harness(self, hs, hid):
        return next(h for h in hs["harnesses"] if h.get("id") == hid)

    def test_attach_profile_shape_is_validated(self):
        hs = copy.deepcopy(self.hs)
        codex = self._harness(hs, "codex")
        del codex["attach"]["next_install"]
        codex["attach"]["config_dir"] = {"env": "CODEX_HOME"}
        codex["attach"]["bin_fallbacks"] = "~/.local/bin/codex"
        self._harness(hs, "grok")["attach"]["session_id"] = ""
        self._harness(hs, "hermes")["detect"] = []
        self._harness(hs, "ollama")["attach"] = dict(self._harness(hs, "grok")["attach"], session_id="ollama")
        probs = registry.validate(self.ts, hs)
        self.assertTrue(any("codex: attach.next_install missing" in p for p in probs), probs)
        self.assertTrue(any("codex: attach.config_dir must be null or {env, default}" in p for p in probs), probs)
        self.assertTrue(any("codex: attach.bin_fallbacks must be a list" in p for p in probs), probs)
        self.assertTrue(any("grok: attach.session_id must be a non-empty string" in p for p in probs), probs)
        self.assertTrue(any("hermes: attach requires non-empty detect[]" in p for p in probs), probs)
        self.assertTrue(any("ollama: attach only allowed on role=harness" in p for p in probs), probs)

    def test_attach_profile_and_harness_home(self):
        import os

        prof = registry.attach_profile("claude-code", ROOT)
        self.assertEqual(prof["session_id"], "claude")
        self.assertEqual(prof["binaries"], ("claude",))
        self.assertEqual(prof["config_dir_env"], "CLAUDE_CONFIG_DIR")
        oc = registry.attach_profile("opencode", ROOT)
        self.assertEqual(oc["script"], "pfy_enterable_162")
        self.assertEqual(oc["session_id"], "opencode")
        self.assertIsNone(oc["config_dir_env"])
        self.assertIsNone(registry.harness_home("opencode", ROOT))
        self.assertIsNone(registry.harness_home("hermes", ROOT))
        saved = os.environ.get("CODEX_HOME")
        try:
            os.environ["CODEX_HOME"] = "/tmp/pfylib-codex-home"
            self.assertEqual(registry.harness_home("codex", ROOT), Path("/tmp/pfylib-codex-home"))
            os.environ.pop("CODEX_HOME")
            self.assertEqual(registry.harness_home("codex", ROOT), Path("~/.codex").expanduser())
        finally:
            if saved is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = saved


if __name__ == "__main__":
    unittest.main()
