import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/litellm/run-on-main.sh"


class TestLitellmFailClosed(unittest.TestCase):
    def test_failures_do_not_write_a_receipt(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        self.assertIn("receipt.json", text)
        self.assertNotIn("timeout is a pass", lowered)
        self.assertIn("exit", lowered)

    def test_marker_and_non_ancestor_write_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "receipt.json"
            marker = Path(tmp) / "marker"
            marker.write_text("pid 1\n", encoding="utf-8")
            env = os.environ.copy()
            env["PFY_LITELLM_LANE_MARKER"] = str(marker)
            held = subprocess.run(
                ["bash", str(SCRIPT), str(dest)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(held.returncode, 2, held.stderr)
            self.assertFalse(dest.exists())

            bindir = Path(tmp) / "bin"
            bindir.mkdir()
            self._write_exec(bindir / "git", _GIT_STUB_NOT_ANCESTOR)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_LITELLM_LANE_MARKER"] = str(Path(tmp) / "absent-marker")
            blocked = subprocess.run(
                ["bash", str(SCRIPT), str(dest)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0, blocked.stderr)
            self.assertIn("not an ancestor", blocked.stderr)
            self.assertFalse(dest.exists())
            self.assertFalse((ROOT / "eval/integrate/litellm/receipt.json").exists())

    def test_probe_stays_off_ollama_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "bin"
            bindir.mkdir()
            log = Path(tmp) / "curl.log"
            log.write_text("", encoding="utf-8")
            self._write_exec(bindir / "git", _GIT_STUB)
            self._write_exec(bindir / "ss", _SS_STUB)
            self._write_exec(bindir / "curl", _CURL_STUB)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_LITELLM_LANE_MARKER"] = str(Path(tmp) / "absent-marker")
            env["CURL_LOG"] = str(log)
            env.pop("SS_LISTEN", None)
            env.pop("CURL_MODE", None)

            missing = Path(tmp) / "missing.json"
            quiet = self._run(env, missing)
            self.assertEqual(quiet.returncode, 1, quiet.stderr)
            self.assertIn("proxy missing", quiet.stderr)
            self.assertEqual(log.read_text(encoding="utf-8"), "")
            self.assertFalse(missing.exists())

            env["SS_LISTEN"] = "11435"
            env["CURL_MODE"] = "timeout"
            timed = Path(tmp) / "timed.json"
            hung = self._run(env, timed)
            self.assertEqual(hung.returncode, 124, hung.stderr)
            self.assertFalse(timed.exists())
            self.assertNotIn("11434", log.read_text(encoding="utf-8"))

            env["CURL_MODE"] = "down"
            log.write_text("", encoding="utf-8")
            refused = Path(tmp) / "refused.json"
            bad = self._run(env, refused)
            self.assertNotEqual(bad.returncode, 0, bad.stderr)
            self.assertFalse(refused.exists())

            env["CURL_MODE"] = "ok"
            env["CURL_CODE"] = "500"
            log.write_text("", encoding="utf-8")
            http = Path(tmp) / "http.json"
            erred = self._run(env, http)
            self.assertNotEqual(erred.returncode, 0, erred.stderr)
            self.assertFalse(http.exists())

            caller = ROOT / "tests"
            dest = Path(tmp) / "out" / "receipt.json"
            rel = os.path.relpath(dest, caller)
            env["CURL_CODE"] = "200"
            log.write_text("", encoding="utf-8")
            ok = subprocess.run(
                ["bash", str(SCRIPT), rel],
                cwd=caller,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(dest.is_file(), ok.stderr)
            wrong = (ROOT / rel).resolve()
            if wrong != dest.resolve():
                self.assertFalse(wrong.exists(), wrong)
            doc = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(doc["slug"], "litellm")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(len(doc["main_sha"]), 40)
            self.assertNotIn("11434", doc["did"])
            self.assertNotIn("\n", doc["tool_version"])
            self.assertNotIn("11434", log.read_text(encoding="utf-8"))
            self.assertIn("127.0.0.1:11435/v1/models", log.read_text(encoding="utf-8"))
            self.assertFalse((ROOT / "eval/integrate/litellm/receipt.json").exists())

    def _run(self, env, dest):
        return subprocess.run(
            ["bash", str(SCRIPT), str(dest)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def _write_exec(self, path, text):
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)


_GIT_STUB = """#!/bin/bash
if [ "$1" = "merge-base" ] && [ "$2" = "--is-ancestor" ]; then
  exit 0
fi
exec /usr/bin/git "$@"
"""

_GIT_STUB_NOT_ANCESTOR = """#!/bin/bash
if [ "$1" = "merge-base" ] && [ "$2" = "--is-ancestor" ]; then
  exit 1
fi
exec /usr/bin/git "$@"
"""

_SS_STUB = """#!/bin/bash
port=${SS_LISTEN:-}
case " $* " in
  *"sport = :${port}"*)
    if [ -n "$port" ]; then
      printf '%s\\n' "LISTEN 0 128 127.0.0.1:${port} 0.0.0.0:*"
    fi
    ;;
esac
exit 0
"""

_CURL_STUB = """#!/bin/bash
out=
url=
prev=
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then
    out=$arg
  fi
  url=$arg
  prev=$arg
done
printf '%s\\n' "$url" >> "${CURL_LOG:?}"
case "$url" in
  *11434*) exit 7 ;;
esac
mode=${CURL_MODE:-ok}
if [ "$mode" = "timeout" ]; then
  exit 124
fi
if [ "$mode" = "down" ]; then
  exit 7
fi
code=${CURL_CODE:-200}
if [ -n "$out" ] && [ "$code" = "200" ]; then
  printf '%s\\n' '{"object":"list","data":[{"id":"local-coder"}]}' > "$out"
fi
printf '%s' "$code"
exit 0
"""


if __name__ == "__main__":
    unittest.main()

