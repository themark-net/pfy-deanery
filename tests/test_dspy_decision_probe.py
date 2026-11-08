"""Behavior tests for the DSPy decision probe.

Drive eval/ev1107/dspy/probe.py, and the live proxy, as subprocesses.
No Ollama and no DSPy install. Loopback stubs only. A gain inside the
noise must not promote. A dead driver or a dead endpoint must not look
like a pass. An OpenAI chat body must go to native /api/chat with thinking
off and num_ctx 4096, and the chain of thought must stay out of the completion.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "ev1107" / "dspy" / "probe.py"
CASES = ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json"


def _scratch() -> Path:
    path = ROOT / "tmp" / "dspy-probe-tests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PROBE), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        },
    )


class SplitAndPayloadTests(unittest.TestCase):
    def test_seed_230_heldout_is_the_last_16_and_hides_the_note(self) -> None:
        bank = json.loads(CASES.read_text(encoding="utf-8"))
        ids = sorted(case["id"] for case in bank["cases"])
        order = ids[:]
        random.Random(230).shuffle(order)
        expected = {
            "train": order[:24],
            "dev": order[24:32],
            "heldout": order[32:48],
        }
        proc = _run(["split", "--cases", str(CASES)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        got = json.loads(proc.stdout)
        self.assertEqual(got["train"], expected["train"])
        self.assertEqual(got["dev"], expected["dev"])
        self.assertEqual(got["heldout"], expected["heldout"])
        self.assertEqual(len(set(got["train"] + got["dev"] + got["heldout"])), 48)

        sample = bank["cases"][0]
        self.assertTrue(sample.get("note"))
        payload = _run(["payload", "--cases", str(CASES), "--id", sample["id"]])
        self.assertEqual(payload.returncode, 0, payload.stderr)
        body = json.loads(payload.stdout)
        self.assertNotIn("label", body)
        self.assertNotIn("note", body)
        self.assertNotIn(sample["note"], payload.stdout)


class VerdictTests(unittest.TestCase):
    def test_gain_must_clear_noise_by_two_cases(self) -> None:
        inside = _run(["verdict", "--baseline", "10,12", "--optimized", "14,14"])
        self.assertEqual(inside.returncode, 0, inside.stderr)
        self.assertEqual(
            inside.stdout.strip(),
            "STAY I1 held-out mean gain 3 is under noise 2 plus 2",
        )

        exact = _run(["verdict", "--baseline", "10,10", "--optimized", "12,12"])
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertEqual(
            exact.stdout.strip(),
            "PROMOTE I2 held-out mean gain 2 clears noise 0 plus 2",
        )

        noisy = _run(["verdict", "--baseline", "10,10", "--optimized", "14,11"])
        self.assertEqual(noisy.returncode, 0, noisy.stderr)
        self.assertEqual(
            noisy.stdout.strip(),
            "STAY I1 held-out mean gain 2.5 is under noise 3 plus 2",
        )

        one_score = _run(["verdict", "--baseline", "10", "--optimized", "12,12"])
        self.assertEqual(one_score.returncode, 2, one_score.stdout)
        self.assertNotIn("PROMOTE", one_score.stdout)


class DriverAndPreflightTests(unittest.TestCase):
    def _bank(self, directory: Path) -> Path:
        path = directory / "cases.json"
        path.write_text(
            json.dumps(
                {
                    "conf_gate": 0.85,
                    "cases": [
                        {
                            "id": "c-match",
                            "instructions": "Pick.",
                            "state": {"ci": "green"},
                            "criteria": {"push": "go", "hold": "stop"},
                            "label": "push",
                            "note": "SECRET-NOTE",
                        },
                        {
                            "id": "c-miss",
                            "instructions": "Pick.",
                            "state": {"ci": "red"},
                            "criteria": {"push": "go", "hold": "stop"},
                            "label": "hold",
                            "note": "SECRET-NOTE",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def _driver(self, directory: Path) -> Path:
        path = directory / "driver.py"
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import sys
                from pathlib import Path
                raw = sys.stdin.read()
                Path(__file__).with_name("seen.jsonl").open("a", encoding="utf-8").write(raw + "\\n")
                if Path(__file__).with_name("crash.flag").exists():
                    sys.stderr.write("driver crashed\\n")
                    sys.exit(1)
                doc = json.loads(raw)
                if "label" in doc or "note" in doc:
                    sys.stderr.write("label leaked\\n")
                    sys.exit(3)
                key = next(iter(doc["criteria"]))
                print(json.dumps({"choice": key, "confidence": 0.91}))
                """
            ),
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def test_dead_driver_exits_2_and_a_restored_driver_scores(self) -> None:
        with tempfile.TemporaryDirectory(dir=_scratch()) as tmp:
            root = Path(tmp)
            cases = self._bank(root)
            driver = self._driver(root)
            out = root / "receipt.json"
            flag = root / "crash.flag"
            flag.write_text("1", encoding="utf-8")
            failed = _run(
                ["run", "--cases", str(cases), "--driver", str(driver), "--out", str(out)]
            )
            self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
            self.assertIn("driver-failed", failed.stderr)
            self.assertNotIn("PROMOTE", failed.stdout)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertIs(receipt["ok"], False)
            self.assertNotIn("n_correct", receipt)

            flag.unlink()
            restored = _run(
                ["run", "--cases", str(cases), "--driver", str(driver), "--out", str(out)]
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)
            scored = json.loads(out.read_text(encoding="utf-8"))
            self.assertIs(scored["ok"], True)
            self.assertEqual(scored["n_correct"], 1)
            self.assertEqual(scored["n"], 2)
            seen = (root / "seen.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("SECRET-NOTE", seen)
            self.assertNotIn('"label"', seen)

    def test_closed_port_fails_and_a_stub_version_endpoint_recovers(self) -> None:
        closed = _run(["preflight", "--base-url", "http://127.0.0.1:1", "--timeout", "1"])
        self.assertEqual(closed.returncode, 2, closed.stdout)
        self.assertIn("unreachable", closed.stderr)
        self.assertNotIn("PROMOTE", closed.stdout)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                body = b'{"version":"stub"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt: str, *args) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}"
            restored = _run(["preflight", "--base-url", url, "--timeout", "2"])
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(restored.stdout.strip(), "ok")


class ProxyTransportTests(unittest.TestCase):
    def test_openai_body_is_forced_onto_native_chat_without_the_chain(self) -> None:
        # The OpenAI-compatible route on this host ignores think and num_ctx.
        # A stub that answers /v1 with reasoning only must not be what the
        # proxy calls. /api/chat with think false and num_ctx 4096 returns
        # the answer, and the chain of thought stays out of the completion.
        driver = r"""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.request
sys.path.insert(0, str(Path("eval/ev1107/dspy").resolve()))
import live

class Stub(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"models":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        body = json.loads(raw.decode())
        path = self.path.split("?", 1)[0]
        self.server.seen = {"path": path, "body": body}
        if path == "/api/chat" and body.get("think") is False and (body.get("options") or {}).get("num_ctx") == 4096:
            payload = {
                "model": body.get("model"),
                "message": {
                    "role": "assistant",
                    "content": "{\"choice\":\"keep\",\"confidence\":0.91}",
                    "thinking": "CHAIN OF THOUGHT",
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 8,
            }
            status = 200
        else:
            payload = {"choices": [{"message": {"content": None, "reasoning_content": "CHAIN OF THOUGHT"}, "finish_reason": "length"}]}
            status = 200
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, fmt, *args):
        return

stub = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
stub.seen = {}
threading.Thread(target=stub.serve_forever, daemon=True).start()
proxy = None
try:
    proxy, port = live.start_proxy(None)
    proxy.upstream = "http://127.0.0.1:%d" % stub.server_address[1]
    req_body = {
        "model": "qwen3.6:35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        "temperature": 0.9,
        "think": True,
        "max_completion_tokens": 64,
        "options": {"num_ctx": 262144},
        "response_format": {"type": "json_object"},
        "stream": True,
    }
    raw = json.dumps(req_body).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d/v1/chat/completions" % port,
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        out = json.loads(resp.read().decode())
    print(json.dumps({"seen": stub.seen, "out": out}))
finally:
    if proxy is not None:
        proxy.shutdown()
        proxy.server_close()
    stub.shutdown()
    stub.server_close()
"""
        proc = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(driver)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        got = json.loads(proc.stdout)
        seen = got["seen"]
        body = seen["body"]
        self.assertEqual(seen["path"], "/api/chat")
        self.assertIs(body["think"], False)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"]["num_ctx"], 4096)
        self.assertEqual(body["options"]["num_predict"], 64)
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertEqual(body["options"]["seed"], 230)
        self.assertEqual(body["format"], "json")
        self.assertNotIn("keep_alive", body)
        self.assertEqual(body["messages"], [{"role": "user", "content": "hi"}])
        content = got["out"]["choices"][0]["message"]["content"]
        self.assertEqual(content, '{"choice":"keep","confidence":0.91}')
        self.assertNotIn("CHAIN", json.dumps(got["out"]))


if __name__ == "__main__":
    unittest.main()
