"""Cloud TypeSafe does not POST until a TypeSafe price is shown and accepted.

Fail: a key is set, the URL is https://api.typesafe.ai, and urlopen runs
with no price line. Recover: the record names CUA-S1-FORMS at $0 and
says no model was called. A fixture price (not the repo table) then
follows the same yes rules. A local laya-serve URL still posts.
No price is written into data/model-prices.json.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from scripts import pfy_jev_230 as jev

ROOT = Path(__file__).resolve().parents[1]


class _Body:
    def __init__(self, payload: dict):
        self.raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


class TypeSafeCostGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="typesafe-gate-"))
        self.calls: list[str] = []
        self.saved = {
            key: os.environ.get(key)
            for key in (
                "TYPESAFE_API_KEY",
                "TYPESAFE_KEY",
                "JEV_API_KEY",
                "PFY_JEV_TYPESAFE_URL",
                "PFY_JEV_OFFLINE",
                "PFY_JEV_MODEL",
                "PFY_MODEL_NO_PAID",
                "PFY_ROOT",
            )
        }
        os.environ.pop("PFY_JEV_TYPESAFE_URL", None)
        os.environ.pop("PFY_JEV_OFFLINE", None)
        os.environ.pop("PFY_JEV_MODEL", None)
        os.environ.pop("PFY_MODEL_NO_PAID", None)
        os.environ.pop("PFY_ROOT", None)
        os.environ["TYPESAFE_API_KEY"] = "test-not-a-real-key"
        os.environ.pop("TYPESAFE_KEY", None)
        os.environ.pop("JEV_API_KEY", None)
        self.patch = mock.patch.object(jev.urllib.request, "urlopen", side_effect=self._open)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _open(self, req, timeout=None):
        self.calls.append(getattr(req, "full_url", str(req)))
        return _Body(
            {
                "model": "jev-1.13.0",
                "answers": {"q": {"choice": "a", "confidence": 0.95}},
            }
        )

    def _price_root(self, *, provider: str = "TypeSafe", fetched: str = "2026-11-15", model: str = "jev-1.13.0") -> Path:
        root = self.tmp / provider / fetched
        path = root / "data"
        path.mkdir(parents=True, exist_ok=True)
        (path / "model-prices.json").write_text(
            json.dumps(
                {
                    "schema": "model-prices.v1",
                    "stale_after_days": 45,
                    "models": {
                        model: {
                            "provider": provider,
                            "source": "fixture",
                            "fetched": fetched,
                            "in": 1.0,
                            "out": 2.0,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return root

    def _eval(self, **kwargs):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rec = jev.typesafe_evaluate(
                {"task": "route"},
                {"q": {"type": "choice", "criteria": {"a": "one"}}},
                **kwargs,
            )
        return rec, buf.getvalue()

    def test_cloud_key_does_not_post_until_a_typesafe_price_is_accepted(self) -> None:
        rec, err = self._eval()
        self.assertEqual(self.calls, [], err)
        blob = (rec.get("error") or "") + "\n" + (rec.get("next_step") or "") + "\n" + err
        self.assertIn("No model was called", blob)
        self.assertIn("CUA-S1-FORMS", blob)
        self.assertIn("$0", blob)
        self.assertNotIn("test-not-a-real-key", blob)

        self.calls.clear()
        os.environ["PFY_JEV_MODEL"] = "grok-4.7"
        rec, err = self._eval(ROOT=ROOT, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, [], err)
        self.assertIn("no TypeSafe price", (rec.get("error") or "") + err)
        self.assertIn("No model was called", rec.get("error") or "")
        os.environ.pop("PFY_JEV_MODEL", None)

        priced = self._price_root()
        self.calls.clear()
        rec, err = self._eval(ROOT=priced, isatty=False)
        self.assertEqual(self.calls, [], err)
        blob = (rec.get("error") or "") + "\n" + err
        self.assertIn("cost estimate: $", blob)
        self.assertIn("no TTY", blob)
        self.assertIn("No model was called", blob)
        self.assertIn("CUA-S1-FORMS", blob)

        self.calls.clear()
        rec, err = self._eval(ROOT=priced, yes=True, isatty=False)
        self.assertEqual(self.calls, [], err)
        self.assertIn("--yes requires --max-usd", (rec.get("error") or "") + err)

        self.calls.clear()
        rec, err = self._eval(ROOT=priced, yes=True, max_usd=0, isatty=False)
        self.assertEqual(self.calls, [], err)
        self.assertIn("exceeds --max-usd", (rec.get("error") or "") + err)

        self.calls.clear()
        rec, err = self._eval(ROOT=priced, isatty=True, answer="n")
        self.assertEqual(self.calls, [], err)
        self.assertIn("declined", (rec.get("error") or "") + err)

        self.calls.clear()
        os.environ["PFY_MODEL_NO_PAID"] = "1"
        rec, err = self._eval(ROOT=priced, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, [], err)
        self.assertIn("paid cloud call blocked", (rec.get("error") or "") + err)
        os.environ.pop("PFY_MODEL_NO_PAID", None)

        stale = self._price_root(fetched="2020-01-01")
        self.calls.clear()
        rec, err = self._eval(ROOT=stale, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, [], err)
        self.assertIn("stale price", (rec.get("error") or "") + err)

        self.calls.clear()
        rec, err = self._eval(ROOT=priced, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, ["https://api.typesafe.ai/v1/systemone"])
        self.assertTrue(rec.get("ok"), rec)
        self.assertEqual((rec.get("answers") or {}).get("q", {}).get("choice"), "a")

    def test_local_laya_url_posts_without_a_price_or_a_yes(self) -> None:
        os.environ["PFY_JEV_TYPESAFE_URL"] = "http://127.0.0.1:8765/v1/systemone"
        os.environ["PFY_MODEL_NO_PAID"] = "1"
        rec, err = self._eval()
        self.assertEqual(self.calls, ["http://127.0.0.1:8765/v1/systemone"])
        self.assertNotIn("cost estimate:", err)
        self.assertTrue(rec.get("answers"), rec)


if __name__ == "__main__":
    unittest.main()
