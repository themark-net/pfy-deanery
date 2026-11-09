#!/usr/bin/env python3
"""The integrate lane must not push when dcg denies that push."""
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "integrate_lane.sh"

STUBS = {
    "scripts/catalog_check.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/grill_ticket.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/check_no_encoded_payloads.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/test_select.py": (
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'mode': 'none', 'reason': 'fixture', 'modules': [], "
        "'changed': [], 'source': 'ast'}))\n"
    ),
    "scripts/run_tests.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "README": "fixture\n",
    "data/stages/dcghook.json": '{"name": "dcghook", "integration_stage": "I2"}\n',
}


def git(repo, *args, env=None):
    run_env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}  # never the real ops checkout
    run_env.update(
        {
            "GIT_AUTHOR_NAME": "Lane",
            "GIT_AUTHOR_EMAIL": "lane@example.com",
            "GIT_COMMITTER_NAME": "Lane",
            "GIT_COMMITTER_EMAIL": "lane@example.com",
        }
    )
    if env:
        run_env.update(env)
    subprocess.check_call(["git", *args], cwd=repo, env=run_env)


def make_fixture(td: Path) -> tuple[Path, Path]:
    seed = td / "seed"
    bare = td / "origin.git"
    clone = td / "clone"
    seed.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(seed)])
    git(seed, "config", "user.email", "lane@example.com")
    git(seed, "config", "user.name", "Lane")
    for rel, text in STUBS.items():
        path = seed / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    subprocess.check_call(
        ["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"]
    )
    subprocess.check_call(["git", "clone", str(bare), str(clone)])
    git(clone, "config", "user.email", "lane@example.com")
    git(clone, "config", "user.name", "Lane")
    return clone, bare


class LaneHookTest(unittest.TestCase):
    def test_denied_push_does_not_move_origin_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_fixture(td)
            log = td / "dcg.log"
            binary = td / "dcg"
            binary.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/bash
                    cmd=$(cat)
                    printf '%s\\n' "$cmd" >> {log}
                    case "$cmd" in
                      *push*)
                        printf '%s\\n' '{{"decision":"deny","rule_id":"test"}}'
                        exit 1
                        ;;
                    esac
                    printf '%s\\n' '{{"decision":"allow"}}'
                    exit 0
                    """
                )
            )
            binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
            bindir = td / "bin"
            bindir.mkdir()
            grok = bindir / "grok"
            grok.write_text(
                textwrap.dedent(
                    """\
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
                    printf '%s\\n' 'print("landed")' > landed.py
                    git add landed.py
                    git commit -m "land widget"
                    exit 0
                    """
                )
            )
            grok.chmod(grok.stat().st_mode | stat.S_IEXEC)
            before = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            (clone / "tmp").mkdir()
            (clone / "tmp" / "TICKET-dcghook.md").write_text("dcg hook ticket\n")
            env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}  # never the real ops checkout
            env.pop("PFY_DCG_DISABLE", None)
            env["PFY_DCG_BIN"] = str(binary)
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "dcghook", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(result.returncode, 0, result.stderr + result.stdout)
            parked = (clone / "tmp" / "integrate" / "dcghook.parked").read_text()
            self.assertIn("land failed", parked)
            self.assertFalse((clone / "tmp" / "integrate" / "LANDED_dcghook").exists())
            after = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(after, before, "denied push moved origin/main")
            seen = log.read_text(encoding="utf-8")
            self.assertIn("push", seen)


if __name__ == "__main__":
    unittest.main()
