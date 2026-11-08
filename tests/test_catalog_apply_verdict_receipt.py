import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_mod():
    path = ROOT / "scripts" / "catalog_apply_verdict.py"
    spec = importlib.util.spec_from_file_location("catalog_apply_verdict", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Grill",
            "GIT_AUTHOR_EMAIL": "grill@example.com",
            "GIT_COMMITTER_NAME": "Grill",
            "GIT_COMMITTER_EMAIL": "grill@example.com",
        }
    )
    subprocess.check_call(["git", *args], cwd=repo, env=env)


def make_repo(td):
    repo = td / "repo"
    bare = td / "origin.git"
    repo.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(repo)])
    (repo / "README").write_text("a\n")
    git(repo, "add", "README")
    git(repo, "commit", "-m", "init")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-u", "origin", "main")
    main_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    git(repo, "checkout", "-b", "side")
    (repo / "README").write_text("b\n")
    git(repo, "commit", "-am", "side")
    side_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    git(repo, "checkout", "main")
    return repo, main_sha, side_sha


def write_receipt(repo, slug, sha, run_kind="pipeline", raw=None):
    path = repo / "eval" / "integrate" / slug / "receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_text(raw)
        return path
    path.write_text(
        json.dumps(
            {
                "slug": slug,
                "run_kind": run_kind,
                "main_sha": sha,
                "run_id": "run-1",
                "started": "2026-11-08T00:00:00Z",
                "finished": "2026-11-08T00:01:00Z",
                "outcome": "ok",
                "tool_version": "0",
                "did": "ran in the pipeline",
            }
        )
    )
    return path


def write_card(td, slug, ceiling, evidence, stage="I2"):
    path = td / f"{slug}.json"
    path.write_text(
        json.dumps(
            {
                "slug": slug,
                "integration_stage": stage,
                "tier_ceiling": ceiling,
                "evidence": evidence,
            }
        )
    )
    return path


class ReceiptRuleTest(unittest.TestCase):
    def test_refusals_keep_bytes_and_valid_receipt_can_reach_i3(self):
        mod = load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo, main_sha, side_sha = make_repo(td)
            make_only = write_card(td, "makeonly", "I3", ["make:tool"])
            before = make_only.read_bytes()
            self.assertEqual(mod.apply_stage(make_only, "I3", repo), "missing-main-receipt")
            self.assertEqual(make_only.read_bytes(), before)
            path_only = write_card(td, "pathonly", "I3", ["path:tools/x"])
            before = path_only.read_bytes()
            self.assertEqual(mod.apply_stage(path_only, "I3", repo), "missing-main-receipt")
            self.assertEqual(path_only.read_bytes(), before)
            write_receipt(repo, "badjson", main_sha, raw="{")
            bad = write_card(td, "badjson", "I3", ["receipt:eval/integrate/badjson/receipt.json"])
            before = bad.read_bytes()
            self.assertEqual(mod.apply_stage(bad, "I3", repo), "receipt-malformed")
            self.assertEqual(bad.read_bytes(), before)
            write_receipt(repo, "badkind", main_sha, run_kind="branch")
            kind = write_card(td, "badkind", "I3", ["receipt:eval/integrate/badkind/receipt.json"])
            self.assertEqual(mod.apply_stage(kind, "I3", repo), "receipt-malformed")
            write_receipt(repo, "offmain", side_sha)
            off = write_card(td, "offmain", "I3", ["receipt:eval/integrate/offmain/receipt.json"])
            before = off.read_bytes()
            self.assertEqual(mod.apply_stage(off, "I3", repo), "receipt-sha-not-on-main")
            self.assertEqual(off.read_bytes(), before)
            empty = td / "nogit"
            empty.mkdir()
            write_receipt(empty, "nogit", main_sha)
            nogit = write_card(td, "nogit", "I3", ["receipt:eval/integrate/nogit/receipt.json"])
            self.assertEqual(mod.apply_stage(nogit, "I3", empty), "git-unavailable")
            write_receipt(repo, "lowceil", main_sha)
            low = write_card(td, "lowceil", "I1", ["receipt:eval/integrate/lowceil/receipt.json"])
            before = low.read_bytes()
            self.assertEqual(mod.apply_stage(low, "I3", repo), "tier_ceiling")
            self.assertEqual(low.read_bytes(), before)
            write_receipt(repo, "goodtool", main_sha)
            good = write_card(td, "goodtool", "I3", ["receipt:eval/integrate/goodtool/receipt.json"])
            self.assertIsNone(mod.apply_stage(good, "I3", repo))
            self.assertEqual(json.loads(good.read_text())["integration_stage"], "I3")

    def test_i4_without_embed_refuses_then_embed_applies(self):
        mod = load_mod()
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo, main_sha, _side = make_repo(td)
            write_receipt(repo, "embedtool", main_sha)
            card = write_card(
                td,
                "embedtool",
                "I4",
                ["receipt:eval/integrate/embedtool/receipt.json"],
            )
            before = card.read_bytes()
            self.assertEqual(mod.apply_stage(card, "I4", repo), "missing-embed")
            self.assertEqual(card.read_bytes(), before)
            body = json.loads(before)
            body["evidence"] = [
                "submodule:tools/embedtool",
                "receipt:eval/integrate/embedtool/receipt.json",
            ]
            card.write_text(json.dumps(body))
            self.assertIsNone(mod.apply_stage(card, "I4", repo))
            self.assertEqual(json.loads(card.read_text())["integration_stage"], "I4")
