"""pfy catalog validate rejects manifest args/env values that look like a key.

Offline fakes only. Never prints the secret. provides.env name lists and
env-ref values are allowed. The repo catalog must still PASS.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "scripts" / "pfy"
VALIDATE = ROOT / "scripts" / "catalog_item_validate.py"

# Obviously fake tokens for fixtures. Validate output must not echo them.
FAKE_SK = "sk-abcdefghijklmnopqrstuvwxyz012345"
FAKE_XAI = "xai-abcdefghijklmnopqrstuvwxyz012345"


def _catalog_mod():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "catalog_item_validate", VALIDATE
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class LooksLikeKeyTests(unittest.TestCase):
    def test_token_values_and_allowed_refs(self):
        from pfylib.redact import looks_like_key

        self.assertTrue(looks_like_key(FAKE_SK))
        self.assertTrue(looks_like_key(FAKE_XAI))
        self.assertTrue(looks_like_key("ghp_abcdefghijklmnopqrstuv"))
        self.assertFalse(looks_like_key("OPENAI_API_KEY"))
        self.assertFalse(looks_like_key("$OPENAI_API_KEY"))
        self.assertFalse(looks_like_key("${OPENAI_API_KEY}"))
        self.assertFalse(looks_like_key(""))
        self.assertFalse(looks_like_key("codebase-memory-mcp"))


class SecretFieldTests(unittest.TestCase):
    def setUp(self):
        self.mod = _catalog_mod()

    def _item(self, **over):
        item = {
            "id": "sample",
            "title": "Sample",
            "kind": "mcp",
            "provides": {
                "brief": None,
                "env": ["OPENAI_API_KEY", "GAB_API_KEY"],
                "mcp_servers": [],
                "commands": [],
                "mcp": [
                    {
                        "name": "sample",
                        "command": "sample-mcp",
                        "args": [],
                        "env": {},
                    }
                ],
            },
            "install": {"strategy": "native"},
            "presets": [],
            "secrets": [],
        }
        item.update(over)
        return {"toolsets": [item]}

    def test_env_name_list_is_not_a_key(self):
        problems = self.mod.secret_looking_problems(self._item())
        self.assertEqual(problems, [])

    def test_env_ref_value_is_allowed(self):
        data = self._item()
        data["toolsets"][0]["provides"]["mcp"][0]["env"] = {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
        self.assertEqual(self.mod.secret_looking_problems(data), [])

    def test_args_key_fails(self):
        data = self._item()
        data["toolsets"][0]["provides"]["mcp"][0]["args"] = ["--token", FAKE_SK]
        problems = self.mod.secret_looking_problems(data)
        self.assertEqual(len(problems), 1)
        self.assertIn("sample: provides.mcp[0].args[1] looks like a key", problems[0])
        self.assertNotIn(FAKE_SK, "".join(problems))

    def test_env_map_value_fails(self):
        data = self._item()
        data["toolsets"][0]["provides"]["mcp"][0]["env"] = {"TOKEN": FAKE_XAI}
        problems = self.mod.secret_looking_problems(data)
        self.assertEqual(len(problems), 1)
        self.assertIn("sample: provides.mcp[0].env.TOKEN looks like a key", problems[0])
        self.assertNotIn(FAKE_XAI, "".join(problems))


class CliTests(unittest.TestCase):
    def test_repo_catalog_passes(self):
        proc = subprocess.run(
            ["bash", str(PFY), "catalog", "validate"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("PASS catalog-item-v2", blob)

    def test_fail_then_recover_without_echoing_the_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "data").mkdir()
            shutil.copy(ROOT / "data" / "toolsets.json", dest / "data" / "toolsets.json")
            shutil.copy(ROOT / "data" / "harnesses.json", dest / "data" / "harnesses.json")
            path = dest / "data" / "toolsets.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            leaked = False
            for row in data["toolsets"]:
                mcp = (row.get("provides") or {}).get("mcp")
                if isinstance(mcp, list) and mcp and isinstance(mcp[0], dict):
                    mcp[0]["args"] = [FAKE_SK]
                    leaked = True
                    tid = row["id"]
                    break
            self.assertTrue(leaked, "need a provides.mcp row to inject a fake key")
            path.write_text(json.dumps(data), encoding="utf-8")

            bad = subprocess.run(
                ["python3", str(VALIDATE), "--root", str(dest)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            blob = bad.stdout + bad.stderr
            self.assertEqual(bad.returncode, 1, blob)
            self.assertIn("FAIL", blob)
            self.assertIn("%s: provides.mcp[0].args[0] looks like a key" % tid, blob)
            self.assertNotIn(FAKE_SK, blob)

            mcp[0]["args"] = []
            path.write_text(json.dumps(data), encoding="utf-8")
            good = subprocess.run(
                ["python3", str(VALIDATE), "--root", str(dest)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            gblob = good.stdout + good.stderr
            self.assertEqual(good.returncode, 0, gblob)
            self.assertIn("PASS catalog-item-v2", gblob)


if __name__ == "__main__":
    unittest.main()
