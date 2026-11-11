"""Behavior of the Agent Autoloop trial's stub lane (eval/integrate/agent-autoloop).

The trial's park and resume result depends on this lane: a park- slug must
ask on its first round and finish on the round that carries the answer, and
every lane must write only under lanes/<slug>/.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parents[1] / "eval" / "integrate" / "agent-autoloop" / "stub_lane.py"


def run_lane(cwd: Path, slug: str, answers=None):
    ctx = cwd / "ctx.json"
    ctx.write_text(json.dumps({"events": [{"subject": slug}], "answers": answers or []}))
    env = dict(os.environ, AGENT_AUTOLOOP_CONTEXT=str(ctx), AGENT_AUTOLOOP_RUN="7", STUB_SLEEP="0")
    return subprocess.run([sys.executable, str(LANE), "prompt"], cwd=cwd, env=env, capture_output=True, text=True)


class StubLaneTest(unittest.TestCase):
    def test_park_lane_asks_then_finishes_with_the_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            first = run_lane(cwd, "park-x")
            self.assertEqual(first.returncode, 0)
            block = first.stdout.split("```agent-autoloop\n", 1)[1].split("\n```", 1)[0]
            ask = json.loads(block)["ask"][0]
            self.assertEqual(ask["options"], ["approve", "park"])
            self.assertEqual(json.loads((cwd / "lanes/park-x/state.json").read_text())["state"], "parked")
            second = run_lane(cwd, "park-x", [{"chosen": "approve"}])
            self.assertNotIn("agent-autoloop", second.stdout)
            state = json.loads((cwd / "lanes/park-x/state.json").read_text())
            self.assertEqual((state["state"], state["answers"]), ("done", ["approve"]))

    def test_plain_lane_finishes_without_asking_and_stays_in_its_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            out = run_lane(cwd, "fake-a")
            self.assertEqual(out.returncode, 0)
            self.assertNotIn("agent-autoloop", out.stdout)
            written = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob("*") if p.is_file())
            self.assertEqual(written, ["conc.log", "ctx.json", "lanes/fake-a/context-run7.json", "lanes/fake-a/state.json"])

    def test_missing_context_still_ends_the_round(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, STUB_SLEEP="0")
            env.pop("AGENT_AUTOLOOP_CONTEXT", None)
            out = subprocess.run([sys.executable, str(LANE), "p"], cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0)
            self.assertIn("Lane unknown done", out.stdout)


if __name__ == "__main__":
    unittest.main()
