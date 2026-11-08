"""Eval lane against a local bare remote and a stub grok. No model."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_lane.sh"

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
    "scripts/run_tests.py": "#!/usr/bin/env python3\nraise SystemExit(3)\n",
    "README": "fixture\n",
    ".gitignore": "tmp/\n",
}


def git(repo, *args):
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Lane",
        "GIT_AUTHOR_EMAIL": "lane@example.com",
        "GIT_COMMITTER_NAME": "Lane",
        "GIT_COMMITTER_EMAIL": "lane@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    })
    subprocess.check_call(["git", *args], cwd=repo, env=env)


def card(slug, **extra):
    body = {
        "name": slug,
        "integration_stage": "I1",
        "intent": "staged_evaluation",
        "next_gate": "eval",
        "uses": "format logs",
        "features": [],
        "potential": "ambiguous",
        "non_goals": ["no install"],
        "evidence": ["notes:local"],
        "tier_ceiling": "I1",
        "risk_class": "none",
    }
    body.update(extra)
    return body


def make_fixture(td: Path, cards: dict) -> tuple[Path, Path]:
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
        path.write_text(text, encoding="utf-8")
    stages = seed / "data" / "stages"
    stages.mkdir(parents=True)
    (stages / "_registry.json").write_text("{}\n", encoding="utf-8")
    for slug, body in cards.items():
        (stages / f"{slug}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    subprocess.check_call(["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
    subprocess.check_call(["git", "clone", str(bare), str(clone)])
    git(clone, "config", "user.email", "lane@example.com")
    git(clone, "config", "user.name", "Lane")
    return clone, bare


def write_grok(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def lane_env(td: Path, grok: Path) -> dict:
    env = os.environ.copy()
    env.update({
        "PFY_GROK_BIN": str(grok),
        "PFY_MODEL_LOCK": str(td / "model.lock"),
        "PFY_LOOP_STATE": str(td / "loopstate"),
        "PFY_DCG_DISABLE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    return env


class EvalLaneTest(unittest.TestCase):
    def test_refusal_leaves_the_card_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            body = card("widget", integration_stage="I0", tier_ceiling="I0", evidence=[])
            clone, bare = make_fixture(td, {"widget": body})
            original = (clone / "data" / "stages" / "widget.json").read_bytes()
            grok = td / "bin" / "grok"
            write_grok(grok, textwrap.dedent("""\
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
                mkdir -p eval/evals/widget
                cat > eval/evals/widget/VERDICT.json <<'EOF'
                {
                  "metric": "probe_score",
                  "threshold": 1,
                  "value_gate": "pass",
                  "modularity_gate": "pass",
                  "proposed_stage": "I3"
                }
                EOF
                printf '%s\\n' "report" > eval/evals/widget/REPORT.md
                git add eval/evals/widget
                git commit -m "eval verdict"
                exit 0
            """))
            state = td / "evalstate"
            proc = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--state", str(state), "--slug", "widget", "--date", "1108"],
                cwd=clone,
                env=lane_env(td, grok),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            remote = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:data/stages/widget.json"]
            )
            self.assertEqual(remote, original)
            refused = (state / "widget.refused").read_text(encoding="utf-8")
            self.assertIn("refused:", refused)
            progress = (state / "progress.md").read_text(encoding="utf-8")
            self.assertIn("skill=catalog-eval-lane sha=", progress)
            self.assertIn("apply refused", progress)
            self.assertIn("test_select mode=none", progress)
            self.assertIn("landed", progress)
            prompt = (state / "widget-implement.prompt").read_text(encoding="utf-8")
            self.assertIn("bootstrap/grok-cli/skills/catalog-eval-lane/SKILL.md", prompt)
            self.assertIn("tmp/TICKET-widget.md", prompt)

    def test_guard_keeps_another_lanes_card_after_rebase(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_fixture(td, {
                "widget": card("widget"),
                "other": card("other"),
            })
            grok = td / "bin" / "grok"
            write_grok(grok, textwrap.dedent("""\
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
                python3 - <<'PY'
                import json
                from pathlib import Path
                path = Path("data/stages/widget.json")
                card = json.loads(path.read_text(encoding="utf-8"))
                card["tier_ceiling"] = "I4"
                path.write_text(json.dumps(card, indent=2) + "\\n", encoding="utf-8")
                PY
                git add data/stages/widget.json
                git commit -m "lane ceiling"
                common=$(git rev-parse --path-format=absolute --git-common-dir)
                root=$(dirname "$common")
                python3 - "$root" <<'PY'
                import json, sys
                from pathlib import Path
                root = Path(sys.argv[1])
                path = root / "data" / "stages" / "other.json"
                card = json.loads(path.read_text(encoding="utf-8"))
                card["integration_stage"] = "I3"
                path.write_text(json.dumps(card, indent=2) + "\\n", encoding="utf-8")
                PY
                git -C "$root" add data/stages/other.json
                git -C "$root" commit -m "other lane"
                git -C "$root" push origin HEAD:refs/heads/main
                exit 0
            """))
            state = td / "evalstate"
            proc = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--state", str(state), "--slug", "widget", "--date", "1108"],
                cwd=clone,
                env=lane_env(td, grok),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            progress = (state / "progress.md").read_text(encoding="utf-8")
            self.assertIn("card guard ok", progress)
            self.assertIn("rebase attempt", progress)
            self.assertIn("missing verdict", (state / "widget.parked").read_text(encoding="utf-8"))
            wt = state / "wt" / "widget"
            widget = json.loads((wt / "data" / "stages" / "widget.json").read_text(encoding="utf-8"))
            other = json.loads((wt / "data" / "stages" / "other.json").read_text(encoding="utf-8"))
            self.assertEqual(widget["tier_ceiling"], "I1")
            self.assertEqual(other["integration_stage"], "I3")
            remote_other = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:data/stages/other.json"],
                text=True,
            )
            self.assertIn('"integration_stage": "I3"', remote_other)
            remote_widget = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:data/stages/widget.json"],
                text=True,
            )
            self.assertIn('"tier_ceiling": "I1"', remote_widget)
            self.assertNotIn('"I4"', remote_widget)
