"""The shared driver runs a slug receipt script after land.

destructive-command-guard already added that hook. This test pins the
contract sandlock uses: the script runs, apply refusal still lands, and
the receipt file stays in the worktree.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.test_integrate_lane_land import git, make_fixture

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "integrate_lane.sh"


class SandlockLaneHookTest(unittest.TestCase):
    def test_receipt_stays_in_worktree_and_apply_refusal_still_lands(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            clone, bare = make_fixture(td)
            script = clone / "eval" / "integrate" / "hookslug" / "run-on-main.sh"
            script.parent.mkdir(parents=True)
            script.write_text(textwrap.dedent("""\
                #!/bin/bash
                set -euo pipefail
                python3 - "$1" <<'PY'
                import json, sys
                from pathlib import Path
                Path(sys.argv[1]).write_text(json.dumps({
                    "slug": "hookslug",
                    "run_kind": "pipeline",
                    "main_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "run_id": "hook-1",
                    "started": "2026-11-08T00:00:00Z",
                    "finished": "2026-11-08T00:00:01Z",
                    "outcome": "ok",
                    "tool_version": "fixture",
                    "did": "wrote a receipt",
                    "log_path": "eval/integrate/hookslug/notes.md",
                }) + "\\n")
                PY
            """))
            verdict = script.parent / "VERDICT.json"
            verdict.write_text('{"proposed_stage": "I3"}\n')
            card = clone / "data" / "stages" / "hookslug.json"
            card.parent.mkdir(parents=True, exist_ok=True)
            card.write_text('{"name": "hookslug", "integration_stage": "I2", "tier_ceiling": "I1"}\n')
            apply_py = clone / "scripts" / "catalog_apply_verdict.py"
            apply_py.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                from pathlib import Path
                Path("apply-refused.txt").write_text("refused\\n")
                raise SystemExit(1)
            """))
            git(clone, "add", "-A")
            git(clone, "commit", "-m", "hook seed")
            git(clone, "push", "origin", "main")

            bindir = td / "bin"
            bindir.mkdir()
            grok = bindir / "grok"
            grok.write_text(textwrap.dedent("""\
                #!/bin/sh
                set -e
                prompt=""
                prev=""
                for arg in "$@"; do
                  if [ "$prev" = "--prompt-file" ]; then
                    prompt=$arg
                  fi
                  prev=$arg
                done
                if grep -q "Self-review" "$prompt"; then
                  exit 0
                fi
                printf '%s\\n' 'print("hook")' > hook.py
                git add hook.py
                git commit -m "land hook"
                exit 0
            """))
            grok.chmod(grok.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PFY_DCG_DISABLE"] = "1"
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            (clone / "tmp").mkdir(exist_ok=True)
            (clone / "tmp" / "TICKET-hookslug.md").write_text("hook ticket\n")
            result = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "hookslug", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            progress = (clone / "tmp" / "integrate" / "progress.md").read_text(encoding="utf-8")
            self.assertIn("hookslug receipt wrote", progress)
            self.assertIn("hookslug apply refused", progress)
            self.assertIn("hookslug landed", progress)
            sha = (clone / "tmp" / "integrate" / "LANDED_hookslug").read_text(encoding="utf-8").strip()
            remote = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(remote, sha)
            showed = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:hook.py"], text=True
            )
            self.assertIn("hook", showed)
            missing = subprocess.run(
                ["git", "--git-dir", str(bare), "cat-file", "-e", "main:eval/integrate/hookslug/receipt.json"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            wt = clone / "tmp" / "integrate" / "wt" / "hookslug"
            body = json.loads((wt / "eval" / "integrate" / "hookslug" / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(body["slug"], "hookslug")
            self.assertEqual(body["outcome"], "ok")
            card_remote = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:data/stages/hookslug.json"],
                text=True,
            )
            self.assertEqual(json.loads(card_remote)["integration_stage"], "I2")
            self.assertEqual((clone / "apply-refused.txt").read_text(encoding="utf-8"), "refused\n")


if __name__ == "__main__":
    unittest.main()
