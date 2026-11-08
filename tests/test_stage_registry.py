"""Stage cards are one file per tool. The assembled document matches those files.

Fail: the assembler drops a field, a missing git history shrinks the check
to a few sample stages, two lanes edit the same stage file, a slug clash is
silent, or the monolith returns.
Recovery: compare every card, including integration_stage and tier_ceiling,
with no git lookup. Each new tool is its own path, a clash names both tools,
and catalog validation rejects the monolith.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pfylib.stage_registry import (
    MONOLITH_MESSAGE,
    load_stages,
    slug_for,
    validate_stage_files,
    write_registry,
    write_tool,
)

ROOT = Path(__file__).resolve().parents[1]
LEGACY = "data/tool_integration_stages.json"


def _card_bodies(root: Path) -> dict:
    """Card objects as JSON on disk. Independent of load_stages."""
    directory = root / "data" / "stages"
    tools: dict = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "_registry.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data["name"]
        tools[name] = {key: value for key, value in data.items() if key != "name"}
    return tools


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "stage-test"
    env["GIT_AUTHOR_EMAIL"] = "stage-test@example.com"
    env["GIT_COMMITTER_NAME"] = "stage-test"
    env["GIT_COMMITTER_EMAIL"] = "stage-test@example.com"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(cwd: Path, args: list[str], env: dict[str, str]) -> None:
    hooks = cwd / ".empty-hooks"
    hooks.mkdir(exist_ok=True)
    subprocess.check_call(
        ["git", "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={hooks}", *args],
        cwd=cwd,
        env=env,
    )


class StageRegistryTests(unittest.TestCase):
    def test_assembled_document_matches_card_files(self):
        doc = load_stages(ROOT)
        registry_path = ROOT / "data" / "stages" / "_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertNotIn("last_updated", registry)
        self.assertFalse((ROOT / LEGACY).exists())
        cards = _card_bodies(ROOT)
        self.assertEqual(set(doc["tools"]), set(cards))
        for name, body in cards.items():
            self.assertEqual(doc["tools"][name], body)
        for key, value in registry.items():
            self.assertEqual(doc.get(key), value)
        if "last_updated" in doc:
            self.assertRegex(str(doc["last_updated"]), r"^\d{4}-\d{2}-\d{2}$")

    def test_card_edit_is_visible_without_git_history(self):
        # A depth-1 checkout cannot see the retired monolith. The check still
        # has to read every card. A stage or ceiling edit on a copy must show
        # up, and the repo cards must stay as they are.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "data" / "stages"
            shutil.copytree(ROOT / "data" / "stages", dest)
            self.assertFalse((root / ".git").exists())
            repo_before = {
                path.name: path.read_bytes()
                for path in (ROOT / "data" / "stages").glob("*.json")
            }
            self.assertEqual(load_stages(root)["tools"], _card_bodies(root))
            paths = sorted(p for p in dest.glob("*.json") if p.name != "_registry.json")
            target = paths[0]
            sibling = paths[1]
            target_data = json.loads(target.read_text(encoding="utf-8"))
            sibling_data = json.loads(sibling.read_text(encoding="utf-8"))
            original_stage = target_data.get("integration_stage")
            flipped = "I0" if original_stage != "I0" else "I1"
            original_ceiling = target_data.get("tier_ceiling")
            flipped_ceiling = "I4" if original_ceiling != "I4" else "I3"
            target_data["integration_stage"] = flipped
            target_data["tier_ceiling"] = flipped_ceiling
            target.write_text(
                json.dumps(target_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            changed = load_stages(root)
            edited = {key: value for key, value in target_data.items() if key != "name"}
            self.assertEqual(changed["tools"][target_data["name"]], edited)
            self.assertEqual(
                changed["tools"][sibling_data["name"]].get("integration_stage"),
                sibling_data.get("integration_stage"),
            )
            self.assertEqual(
                changed["tools"][sibling_data["name"]].get("tier_ceiling"),
                sibling_data.get("tier_ceiling"),
            )
            repo_after = {
                path.name: path.read_bytes()
                for path in (ROOT / "data" / "stages").glob("*.json")
            }
            self.assertEqual(repo_after, repo_before)

    def test_dump_prints_the_assembled_document(self):
        proc = subprocess.run(
            [sys.executable, "-m", "pfylib.stage_registry", "--dump"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), load_stages(ROOT))

    def test_slug_collision_names_both_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tool(root, "Foo Bar", {"integration_stage": "I1"})
            with self.assertRaises(Exception) as caught:
                write_tool(root, "foo-bar", {"integration_stage": "I0"})
            message = str(caught.exception)
            self.assertIn("Foo Bar", message)
            self.assertIn("foo-bar", message)
            self.assertEqual(slug_for("Foo Bar"), slug_for("foo-bar"))

    def test_write_tool_touches_exactly_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root, {"version": "1.3", "default_stage": "I1"})
            write_tool(root, "Alpha", {"integration_stage": "I1", "note": "a"})
            write_tool(root, "Beta", {"integration_stage": "I0", "note": "b"})
            directory = root / "data" / "stages"
            before = {path: path.read_bytes() for path in directory.glob("*.json")}
            write_tool(root, "Alpha", {"integration_stage": "I2", "note": "changed"})
            after = list(directory.glob("*.json"))
            changed = [path.name for path in after if path.read_bytes() != before.get(path)]
            extra = [path.name for path in after if path not in before]
            self.assertEqual(changed, ["alpha.json"])
            self.assertEqual(extra, [])
            self.assertEqual((directory / "_registry.json").read_bytes(), before[directory / "_registry.json"])
            self.assertEqual((directory / "beta.json").read_bytes(), before[directory / "beta.json"])

    def test_two_branches_add_tools_without_overlapping_paths(self):
        env = _git_env()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(root, {"version": "1.3", "default_stage": "I1"})
            write_tool(root, "Shared Tool", {"integration_stage": "I1"})
            _git(root, ["init", "-q", "-b", "main"], env)
            _git(root, ["add", "data/stages"], env)
            _git(root, ["commit", "-q", "-m", "base"], env)
            _git(root, ["checkout", "-q", "-b", "lane-a"], env)
            write_tool(root, "Tool A", {"integration_stage": "I0"})
            _git(root, ["add", "data/stages/tool-a.json"], env)
            _git(root, ["commit", "-q", "-m", "add a"], env)
            _git(root, ["checkout", "-q", "main"], env)
            _git(root, ["checkout", "-q", "-b", "lane-b"], env)
            write_tool(root, "Tool B", {"integration_stage": "I2"})
            _git(root, ["add", "data/stages/tool-b.json"], env)
            _git(root, ["commit", "-q", "-m", "add b"], env)

            def added(rev: str) -> set[str]:
                out = subprocess.check_output(
                    ["git", "diff", "--name-only", "main", rev],
                    cwd=root,
                    text=True,
                    env=env,
                )
                return {line for line in out.splitlines() if line}

            paths_a = added("lane-a")
            paths_b = added("lane-b")
            self.assertEqual(paths_a, {"data/stages/tool-a.json"})
            self.assertEqual(paths_b, {"data/stages/tool-b.json"})
            self.assertTrue(paths_a.isdisjoint(paths_b))
            _git(root, ["merge", "-q", "--no-edit", "lane-a"], env)
            doc = load_stages(root)
            self.assertEqual(doc["tools"]["Tool A"]["integration_stage"], "I0")
            self.assertEqual(doc["tools"]["Tool B"]["integration_stage"], "I2")
            self.assertEqual(doc["tools"]["Shared Tool"]["integration_stage"], "I1")

    def test_validate_rejects_monolith_and_bad_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_registry(
                root,
                {
                    "version": "1.3",
                    "policy": "docs/ops/integration-stages.md",
                    "default_stage": "I1",
                },
            )
            write_tool(root, "Widget", {"integration_stage": "I1"})
            self.assertEqual(validate_stage_files(root), [])
            legacy = root / LEGACY
            legacy.write_text("{}\n", encoding="utf-8")
            problems = validate_stage_files(root)
            self.assertIn(MONOLITH_MESSAGE, problems)
            legacy.unlink()
            directory = root / "data" / "stages"
            (directory / "broken.json").write_text("{", encoding="utf-8")
            (directory / "no-name.json").write_text(
                json.dumps({"integration_stage": "I1"}) + "\n",
                encoding="utf-8",
            )
            (directory / "bad-stage.json").write_text(
                json.dumps({"name": "Bad Stage", "integration_stage": "I9"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (directory / "wrong.json").write_text(
                json.dumps({"name": "Wrong Name", "integration_stage": "I0"}, indent=2) + "\n",
                encoding="utf-8",
            )
            text = "\n".join(validate_stage_files(root))
            self.assertIn("broken.json: invalid JSON", text)
            self.assertIn("no-name.json: missing name", text)
            self.assertIn("integration_stage 'I9'", text)
            self.assertIn("does not match name 'Wrong Name'", text)
            self.assertNotIn("tool_integration_stages.json must not exist", text)


if __name__ == "__main__":
    unittest.main()
