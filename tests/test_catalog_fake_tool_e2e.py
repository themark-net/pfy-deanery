"""Fake local tool, temp catalog: intake, stubbed I1 apply, browse.

Fail: a new card stays invisible, or I1 is refused because evidence is empty,
or an I2 stub is written onto the card.
Recovery: intake records the fixture's real facts, apply refuses I2 and
leaves the bytes alone, the same script then writes I1, and ./pfy catalog
lists that one card. A second intake is a duplicate. The temp tree is
removed before the test returns. No network, no model, no GPU.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests._ledger import assert_only_ledger

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "scripts" / "catalog_intake_dedupe.py"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"
PFY = ROOT / "pfy"
SLUG = "pfy-e2e-fake-tool"


def git(path, *args, hooks):
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={hooks}", "-C", str(path), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def run(cmd, env, cwd):
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def write_verdict(path, stage):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "metric": "e2e_fake_tool",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": stage,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def catalog_rows(stdout):
    rows = {}
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 5 or parts[0] == "name":
            continue
        rows[parts[0]] = parts
    return rows


class FakeToolE2ETest(unittest.TestCase):
    def test_local_fixture_reaches_i1_and_browse_lists_it(self):
        real_card = ROOT / "data" / "stages" / f"{SLUG}.json"
        real_state = Path.home() / ".pfy-mentat" / "last-verb"
        self.assertFalse(real_card.exists())
        real_before = real_state.read_bytes() if real_state.is_file() else None
        with tempfile.TemporaryDirectory(prefix="pfy-e2e-fake-tool-") as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "catalog"
            (root / "data" / "stages").mkdir(parents=True)
            state = tmp_path / "state"
            state.mkdir()
            hooks = tmp_path / "hooks"
            hooks.mkdir()
            fixture = tmp_path / SLUG
            fixture.mkdir()
            (fixture / "README.md").write_text(
                "# Pfy e2e fake tool sorts nothing\n\nNot a real catalog row.\n",
                encoding="utf-8",
            )
            (fixture / "LICENSE").write_text(
                "MIT License\n\nPermission is hereby granted, free of charge.\n",
                encoding="utf-8",
            )
            self.assertEqual(git(fixture, "init", hooks=hooks).returncode, 0)
            self.assertEqual(
                git(fixture, "add", "README.md", "LICENSE", hooks=hooks).returncode, 0
            )
            committed = git(
                fixture,
                "-c",
                "user.email=e2e@example.com",
                "-c",
                "user.name=e2e",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "init",
                hooks=hooks,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            remote = git(
                fixture,
                "remote",
                "add",
                "origin",
                f"https://github.com/example/{SLUG}.git",
                hooks=hooks,
            )
            self.assertEqual(remote.returncode, 0, remote.stderr)
            sha = git(fixture, "rev-parse", "HEAD", hooks=hooks).stdout.strip()
            self.assertEqual(len(sha), 40)

            env = os.environ.copy()
            env["PFY_ROOT"] = str(root)
            env["PFY_STATE_DIR"] = str(state)
            env["GIT_TERMINAL_PROMPT"] = "0"
            env.pop("PFY_START_ENGINE_FLAG", None)

            empty = run([str(PFY), "catalog"], env, root)
            self.assertEqual(empty.returncode, 2, empty.stdout + empty.stderr)
            self.assertIn("no usable catalog subset", empty.stdout)
            self.assertEqual(catalog_rows(empty.stdout), {})

            intake = run(
                ["python3", str(INTAKE), str(fixture), "--root", str(root), "--write-card"],
                env,
                root,
            )
            self.assertEqual(intake.returncode, 0, intake.stderr)
            self.assertEqual(intake.stdout.strip(), f"new {SLUG}")
            card_path = root / "data" / "stages" / f"{SLUG}.json"
            card = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual(card["integration_stage"], "I0")
            self.assertEqual(card["tier_ceiling"], "I1")
            self.assertTrue(card["evidence"])
            self.assertIn(f"https://github.com/example/{SLUG}", card["evidence"])
            self.assertIn("license:MIT", card["evidence"])
            self.assertIn(f"pin:{sha}", card["evidence"])
            self.assertIn("readme: Pfy e2e fake tool sorts nothing", card["evidence"])
            self.assertNotIn("Not a real catalog row", json.dumps(card))

            listed = run([str(PFY), "catalog"], env, root)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("1 tools", listed.stdout)
            rows = catalog_rows(listed.stdout)
            self.assertEqual(set(rows), {SLUG})
            self.assertEqual(rows[SLUG][1], "I0")
            self.assertEqual(rows[SLUG][2], "incomplete")
            self.assertNotIn("adr-tools", listed.stdout)

            verdict = root / "eval" / "evals" / SLUG / "VERDICT.json"
            before = card_path.read_bytes()
            write_verdict(verdict, "I2")
            refused = run(
                ["python3", str(APPLY), "--card", str(card_path), "--verdict", str(verdict)],
                env,
                root,
            )
            self.assertEqual(refused.returncode, 1, refused.stdout)
            self.assertIn("above-ceiling", refused.stderr)
            self.assertIn("proposed I2", refused.stderr)
            assert_only_ledger(self, card_path, before)
            still = run([str(PFY), "catalog"], env, root)
            self.assertEqual(catalog_rows(still.stdout)[SLUG][1], "I0")

            write_verdict(verdict, "I1")
            allowed = run(
                ["python3", str(APPLY), "--card", str(card_path), "--verdict", str(verdict)],
                env,
                root,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertIn("PROMOTE I1", allowed.stdout)
            promoted = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["integration_stage"], "I1")
            self.assertEqual(promoted["tier_ceiling"], "I1")
            self.assertEqual(promoted["evidence"], card["evidence"])

            shown = run([str(PFY), "catalog"], env, root)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertIn("1 tools", shown.stdout)
            ready = catalog_rows(shown.stdout)
            self.assertEqual(set(ready), {SLUG})
            self.assertEqual(ready[SLUG][1], "I1")
            self.assertEqual(ready[SLUG][2], "ready")
            self.assertEqual(ready[SLUG][4], f"https://github.com/example/{SLUG}")
            self.assertTrue((state / "last-verb").is_file())
            self.assertIn("verb: catalog", (state / "last-verb").read_text(encoding="utf-8"))

            again = run(
                ["python3", str(INTAKE), str(fixture), "--root", str(root), "--write-card"],
                env,
                root,
            )
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(
                again.stdout.strip(),
                f"duplicate {SLUG} data/stages/{SLUG}.json",
            )
            self.assertEqual(json.loads(card_path.read_text(encoding="utf-8"))["integration_stage"], "I1")
            self.assertFalse(real_card.exists())
            if real_before is None:
                self.assertFalse(real_state.exists())
            else:
                self.assertEqual(real_state.read_bytes(), real_before)
        self.assertFalse(Path(tmp).exists())
        self.assertFalse(real_card.exists())
