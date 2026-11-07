"""Stage cards are one file per tool. The assembled document matches the old monolith.

Fail: two lanes edit the same stage file, a slug clash is silent, or the
monolith returns.
Recovery: each new tool is its own path, a clash names both tools, and
catalog validation rejects the monolith.
"""
from __future__ import annotations

import json
import os
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


def _legacy_monolith() -> dict | None:
    try:
        rev = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", LEGACY],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if not rev:
        return None
    for spec in (f"{rev}:{LEGACY}", f"{rev}^:{LEGACY}"):
        try:
            blob = subprocess.check_output(
                ["git", "-C", str(ROOT), "show", spec],
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("tools"), dict):
            return data
    return None


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
    def test_assembled_document_matches_legacy_monolith(self):
        got = load_stages(ROOT)
        registry = json.loads((ROOT / "data" / "stages" / "_registry.json").read_text(encoding="utf-8"))
        self.assertNotIn("last_updated", registry)
        expected = _legacy_monolith()
        if expected is None:
            self.assertGreaterEqual(len(got["tools"]), 85)
            self.assertEqual(got.get("version"), "1.3")
            self.assertEqual(got["tools"]["Kolibri-1"]["integration_stage"], "I0")
            self.assertEqual(got["tools"]["Atomic Task Graph (ATG)"]["integration_stage"], "I2")
            self.assertEqual(got["tools"]["Pipecat"]["integration_stage"], "I0")
            self.assertIn("last_updated", got)
            return
        self.assertEqual(got["tools"], expected["tools"])
        rest_got = {key: value for key, value in got.items() if key != "tools"}
        rest_expected = {key: value for key, value in expected.items() if key != "tools"}
        self.assertEqual(rest_got, rest_expected)

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
