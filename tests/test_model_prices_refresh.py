"""Price refresh parses saved pages. No network.

Fail: a bad parse or a second run inside 7 days rewrites data/model-prices.json,
or an offline tick writes the refresh stamp.
Recovery: the price file bytes stay as they were, and the stamp records the
failed attempt so the next tick does not fetch again.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIX = ROOT / "tests" / "fixtures" / "model-prices"


def _load():
    spec = importlib.util.spec_from_file_location(
        "model_prices_refresh", ROOT / "scripts" / "model_prices_refresh.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


refresh_mod = _load()


class PriceRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-prices-"))
        self.root = self.tmp / "repo"
        (self.root / "data").mkdir(parents=True)
        self.prices = self.root / "data" / "model-prices.json"
        shutil.copy(ROOT / "data" / "model-prices.json", self.prices)
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.original = self.prices.read_text(encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, xai: Path, openai: Path | None, today: str, fetch=None) -> str:
        buf = io.StringIO()
        kwargs = dict(
            root=self.root,
            state_dir=self.state,
            today=date.fromisoformat(today),
            xai_text=xai.read_text(encoding="utf-8"),
            openai_text=None if openai is None else openai.read_text(encoding="utf-8"),
        )
        if fetch is not None:
            kwargs["fetch"] = fetch
        with redirect_stdout(buf):
            code = refresh_mod.refresh(**kwargs)
        self.assertEqual(code, 0)
        return buf.getvalue()

    def test_confident_markdown_and_html_update_only_known_fields(self) -> None:
        def boom(url):
            raise AssertionError("network %s" % url)

        text = self._run(FIX / "xai-ok.md", FIX / "openai-ok.md", "2026-11-18", fetch=boom)
        self.assertIn("updated", text)
        data = json.loads(self.prices.read_text(encoding="utf-8"))
        names = list(data["models"])
        self.assertEqual(names, list(json.loads(self.original)["models"]))
        grok = data["models"]["grok-4.7"]
        self.assertEqual(grok["in"], 3.0)
        self.assertEqual(grok["out"], 7.0)
        self.assertEqual(grok["cached_in"], 0.6)
        self.assertEqual(grok["long_context"]["in"], 5.0)
        self.assertEqual(grok["long_context"]["out"], 13.0)
        self.assertEqual(grok["long_context"]["min_prompt_tokens"], 200000)
        self.assertEqual(grok["fetched"], "2026-11-18")
        self.assertNotIn("cached_in", data["models"]["grok-4.3"])
        self.assertEqual(data["models"]["grok-4.3"]["in"], 1.5)
        self.assertEqual(data["models"]["grok-4.3"]["out"], 3.0)
        sol = data["models"]["gpt-6.1-sol"]
        self.assertEqual(sol["in"], 2.5)
        self.assertEqual(sol["out"], 11.0)
        self.assertNotIn("cached_in", sol)
        self.assertEqual(data["models"]["gpt-5.4-mini"]["short_context_max_input_tokens"], 272000)
        local = data["models"]["ollama:*"]
        self.assertEqual(local["in"], 0.0)
        self.assertEqual(local["fetched"], "2026-11-11")
        self.assertEqual(set(grok), set(json.loads(self.original)["models"]["grok-4.7"]))

        self.prices.write_text(self.original, encoding="utf-8")
        (self.state / "model-prices-refresh.json").unlink()
        html_out = self._run(FIX / "xai-ok.html", FIX / "openai-ok.md", "2026-11-18", fetch=boom)
        self.assertIn("updated", html_out)
        again = json.loads(self.prices.read_text(encoding="utf-8"))
        self.assertEqual(again["models"]["grok-4.7"]["in"], 3.0)
        self.assertEqual(again["models"]["grok-4.7"]["long_context"]["out"], 13.0)

    def test_missing_model_or_garbage_leaves_the_file_and_stamps(self) -> None:
        missing = self._run(FIX / "xai-missing.md", FIX / "openai-ok.md", "2026-11-18")
        self.assertIn("xAI", missing)
        self.assertIn("grok-4.3", missing)
        self.assertEqual(self.prices.read_text(encoding="utf-8"), self.original)
        stamp = json.loads((self.state / "model-prices-refresh.json").read_text(encoding="utf-8"))
        self.assertEqual(stamp["attempted"], "2026-11-18")

        (self.state / "model-prices-refresh.json").unlink()
        garbage = self._run(FIX / "xai-garbage.md", FIX / "openai-ok.md", "2026-11-18")
        self.assertIn("xAI", garbage)
        self.assertIn("bad price", garbage)
        self.assertEqual(self.prices.read_text(encoding="utf-8"), self.original)

    def test_once_per_seven_days_ignores_a_later_fixture(self) -> None:
        self._run(FIX / "xai-ok.md", FIX / "openai-ok.md", "2026-11-12")
        first = self.prices.read_text(encoding="utf-8")
        skipped = self._run(FIX / "xai-next.md", FIX / "openai-ok.md", "2026-11-18")
        self.assertIn("skipped", skipped)
        self.assertEqual(self.prices.read_text(encoding="utf-8"), first)
        stamp = (self.state / "model-prices-refresh.json").read_text(encoding="utf-8")
        self.assertIn("2026-11-12", stamp)
        opened = self._run(FIX / "xai-next.md", FIX / "openai-ok.md", "2026-11-19")
        self.assertIn("updated", opened)
        data = json.loads(self.prices.read_text(encoding="utf-8"))
        self.assertEqual(data["models"]["grok-4.7"]["in"], 3.5)
        self.assertEqual(data["models"]["grok-4.7"]["fetched"], "2026-11-19")

    def test_fetch_failure_is_fail_open_and_offline_skips(self) -> None:
        def boom(url):
            raise OSError("down")

        text = self._run(FIX / "xai-ok.md", None, "2026-11-18", fetch=boom)
        self.assertIn("OpenAI: fetch failed", text)
        self.assertEqual(self.prices.read_text(encoding="utf-8"), self.original)
        self.assertTrue((self.state / "model-prices-refresh.json").is_file())

        fresh = self.tmp / "offline-state"
        fresh.mkdir()
        env = os.environ.copy()
        env["PFY_CATALOG_OFFLINE"] = "1"
        env["PFY_MODEL_NO_PAID"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "model_prices_refresh.py"),
                "--state", str(fresh),
                "--root", str(self.root),
                "--xai-fixture", str(FIX / "xai-ok.md"),
                "--openai-fixture", str(FIX / "openai-ok.md"),
                "--today", "2026-11-18",
            ],
            cwd=self.tmp,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertFalse((fresh / "model-prices-refresh.json").exists())
        self.assertEqual(self.prices.read_text(encoding="utf-8"), self.original)

    def test_request_has_no_auth_and_usage_exits_2(self) -> None:
        request = refresh_mod.build_request("https://docs.x.ai/docs/models")
        self.assertEqual(request.get_header("User-agent"), refresh_mod.USER_AGENT)
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(refresh_mod.main(["--not-a-flag"]), 2)
        loop = (ROOT / "scripts" / "catalog_loop.sh").read_text(encoding="utf-8")
        self.assertIn("data/model-prices.json", loop)
        hook = loop.split("model_prices_refresh.py", 1)[1][:120]
        self.assertIn("|| true", hook)
        self.assertLess(loop.index("model_prices_refresh.py"), loop.index("fi # online regeneration"))


if __name__ == "__main__":
    unittest.main()
