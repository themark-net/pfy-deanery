"""Entries 106-108 smokes: cm sha pin/env, and har temp-HOME containment.

Parent HOME is a temp dir this test owns so a stub cannot touch the operator's real home.
Har is `node <realpath(HAR_BIN)>`; HAR_NODE is a stub that prints v22.0.0 and HAR_BIN is JavaScript.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "x-intake-local"))
from smoke import PAID_KEYS  # noqa: E402
from smoke_106_108 import CM_V050_SHA256  # noqa: E402

DUMMY_PAID = "pfy-test-dummy"

OTHER_SHA = "0123456789abcdef" * 4
REAL_NODE = shutil.which("node") or ""


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _node_stub(path: Path) -> None:
    _write_exe(path, f"""#!/bin/sh
if [ "$1" = "--version" ]; then
  echo v22.0.0
  exit 0
fi
exec {REAL_NODE} "$@"
""")


class XIntakeSmoke106108Tests(unittest.TestCase):
    def setUp(self) -> None:
        # Each test writes its smoke receipts to its own temp dir. A shared
        # pipelines/smoke/<entry>/latest.json raced with other modules that
        # run the same entry in parallel (modular CI: one state file per run).
        self._receipt_dir = tempfile.TemporaryDirectory(prefix="pfy-xintake-receipts-")
        self.receipts = Path(self._receipt_dir.name)

    def tearDown(self) -> None:
        self._receipt_dir.cleanup()

    def _base_env(self, home: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        for key in (
            "CM_BIN",
            "CM_SHA256",
            "HAR_BIN",
            "HAR_NODE",
            "PFY_XINTAKE_TIMEOUT",
            "PFY_PROBE_OUT",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
            "npm_config_cache",
        ):
            env.pop(key, None)
        env["PFY_SMOKE_RECEIPT_DIR"] = str(self.receipts)
        return env

    def _run(self, entry: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", "examples/x-intake-local/smoke_106_108.py", "--entry", entry],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def _receipt(self, entry: str) -> dict:
        path = self.receipts / entry / "latest.json"
        self.assertTrue(path.is_file(), f"missing receipt {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _cm_sha(self, override: str | None) -> None:
        # Fail: a mismatched pin still execs, or the receipt omits expected source/value,
        # or an override is silent. Recover: exit 2, no exec, source pin or env, WARN only for env.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-cm-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            marker = root / "executed-marker"
            stub = root / "cm"
            _write_exe(stub, "#!/bin/sh\ntouch %s\n" % marker)
            env = self._base_env(home)
            env["CM_BIN"] = str(stub)
            if override is not None:
                env["CM_SHA256"] = override
            proc = self._run("cassmemory", env)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 2, blob)
            self.assertFalse(marker.exists(), "cm stub was executed")
            self.assertNotIn("Traceback", proc.stderr)
            got = (self._receipt("cassmemory").get("expected") or {}).get("CM_SHA256") or {}
            self.assertEqual(got.get("pin"), CM_V050_SHA256, blob)
            if override is None:
                self.assertNotIn("WARN:", proc.stderr)
                self.assertEqual(got.get("source"), "pin", blob)
                self.assertEqual(got.get("value"), CM_V050_SHA256, blob)
            else:
                warn = f"WARN: $CM_SHA256={override} overrides the pinned {CM_V050_SHA256}"
                self.assertIn(warn, proc.stderr)
                self.assertEqual(got.get("source"), "env", blob)
                self.assertEqual(got.get("value"), override, blob)

    def test_cassmemory_sha_unset_records_pin_and_does_not_exec(self) -> None:
        self._cm_sha(None)

    def test_cassmemory_sha_env_warns_records_override_and_does_not_exec(self) -> None:
        self._cm_sha(OTHER_SHA)

    def test_cassmemory_sha_env_equal_to_pin_does_not_warn(self) -> None:
        # Fail: an env value equal to the pin (any hex case) still prints WARN.
        # Recover: exit 2, no exec, source env, value is the pin, stderr has no WARN.
        for override in (CM_V050_SHA256, CM_V050_SHA256.upper()):
            with self.subTest(override=override[:12]):
                with tempfile.TemporaryDirectory(prefix="pfy-xintake-cm-eq-") as td:
                    root = Path(td)
                    home = root / "home"
                    home.mkdir()
                    marker = root / "executed-marker"
                    stub = root / "cm"
                    _write_exe(stub, "#!/bin/sh\ntouch %s\n" % marker)
                    env = self._base_env(home)
                    env["CM_BIN"] = str(stub)
                    env["CM_SHA256"] = override
                    proc = self._run("cassmemory", env)
                    blob = proc.stdout + proc.stderr
                    self.assertEqual(proc.returncode, 2, blob)
                    self.assertFalse(marker.exists(), "cm stub was executed")
                    self.assertNotIn("WARN:", proc.stderr, blob)
                    got = (self._receipt("cassmemory").get("expected") or {}).get("CM_SHA256") or {}
                    self.assertEqual(got.get("source"), "env", blob)
                    self.assertEqual(got.get("value"), CM_V050_SHA256, blob)
                    self.assertEqual(got.get("pin"), CM_V050_SHA256, blob)

    def _har_bins(self, root: Path, js: str) -> dict[str, str]:
        node = root / "node-stub"
        har = root / "har.js"
        _node_stub(node)
        _write_exe(har, js)
        return {"HAR_NODE": str(node), "HAR_BIN": str(har)}

    def test_har_work_dir_outside_temp_home_fails(self) -> None:
        # Fail: launch's work dir outside the temp HOME is accepted (startswith false-friend).
        # Recover: exit 1 and the reason says the work dir is not under the temp HOME.
        js = r"""
const fs = require('fs');
const args = process.argv.slice(2);
if (args[0] === 'telemetry') process.exit(0);
if (args[0] === 'env' && args[1] === 'init') {
  fs.mkdirSync('.har', {recursive: true});
  fs.writeFileSync('.har/stages.json', '{}\n');
  process.exit(0);
}
if (args[0] === 'env' && args[1] === 'launch') {
  console.log('make ALL file edits under: /tmp/outside-the-temp-home/work');
  process.exit(0);
}
if (args[0] === 'env' && args[1] === 'teardown') process.exit(0);
process.exit(3);
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-har-out-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            env = self._base_env(home)
            env.update(self._har_bins(root, js))
            proc = self._run("har", env)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 1, blob)
            self.assertNotIn("Traceback", proc.stderr)
            reason = self._receipt("har").get("reason") or ""
            self.assertIn("not under the temp HOME", reason, blob)

    def test_har_work_dir_sibling_prefix_fails(self) -> None:
        # Fail: startswith treats /tmp/foo-evil as inside /tmp/foo, so a sibling work dir is accepted.
        # Recover: is_relative_to rejects it; the smoke exits 1 with the temp-HOME reason.
        js = r"""
const fs = require('fs');
const args = process.argv.slice(2);
if (args[0] === 'telemetry') process.exit(0);
if (args[0] === 'env' && args[1] === 'init') {
  fs.mkdirSync('.har', {recursive: true});
  fs.writeFileSync('.har/stages.json', '{}\n');
  process.exit(0);
}
if (args[0] === 'env' && args[1] === 'launch') {
  const home = process.env.HOME;
  const work = home + '-evil';
  fs.writeFileSync(process.env.PFY_PROBE_OUT, JSON.stringify({home: home, work: work}));
  console.log('make ALL file edits under: ' + work);
  process.exit(0);
}
if (args[0] === 'env' && args[1] === 'teardown') process.exit(0);
process.exit(3);
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-har-sib-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            probe = root / "probe.json"
            env = self._base_env(home)
            env["PFY_PROBE_OUT"] = str(probe)
            env.update(self._har_bins(root, js))
            proc = self._run("har", env)
            blob = proc.stdout + proc.stderr
            self.assertTrue(probe.is_file(), blob)
            seen = json.loads(probe.read_text(encoding="utf-8"))
            work = seen["work"]
            got_home = seen["home"]
            self.assertEqual(work, got_home + "-evil", seen)
            self.assertTrue(work.startswith(got_home), seen)
            self.assertFalse(Path(work).resolve().is_relative_to(Path(got_home).resolve()), seen)
            self.assertTrue("/tmp/foo-evil".startswith("/tmp/foo"))
            self.assertFalse(Path("/tmp/foo-evil").is_relative_to(Path("/tmp/foo")))
            receipt = self._receipt("har")
            self.assertEqual(proc.returncode, 1, blob + "\n" + json.dumps(receipt))
            self.assertNotIn("Traceback", proc.stderr)
            self.assertFalse(receipt.get("work_dir_under_temp_home"), receipt)
            self.assertIn("not under the temp HOME", receipt.get("reason") or "", blob)

    def test_har_env_dirs_are_under_temp_home(self) -> None:
        # Fail: the har process inherits the parent HOME or XDG/npm cache paths outside its HOME.
        # Recover: HOME is a fresh temp dir and the four dirs sit under that HOME.
        js = r"""
const fs = require('fs');
const keys = ['HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'npm_config_cache'];
const out = {};
for (const k of keys) out[k] = process.env[k] || '';
fs.writeFileSync(process.env.PFY_PROBE_OUT, JSON.stringify(out));
process.exit(0);
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-har-env-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            probe = root / "probe.json"
            env = self._base_env(home)
            env["PFY_PROBE_OUT"] = str(probe)
            env["XDG_CONFIG_HOME"] = str(home / ".config")
            env["XDG_CACHE_HOME"] = str(home / ".cache")
            env["XDG_DATA_HOME"] = str(home / ".local" / "share")
            env["npm_config_cache"] = str(home / ".npm")
            env.update(self._har_bins(root, js))
            proc = self._run("har", env)
            blob = proc.stdout + proc.stderr
            self.assertTrue(probe.is_file(), blob)
            data = json.loads(probe.read_text(encoding="utf-8"))
            seen = Path(data["HOME"]).resolve()
            self.assertNotEqual(seen, home.resolve(), data)
            for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "npm_config_cache"):
                got = Path(data[key]).resolve()
                self.assertTrue(got.is_relative_to(seen), f"{key}={data[key]} HOME={data['HOME']}")

    def test_har_otel_hooks_in_temp_home_fails(self) -> None:
        # Fail: $HOME/.har/otel-hooks written with telemetry off is ignored, so the smoke passes.
        # Recover: exit 1 and the reason names .har/otel-hooks, same as the other hook files.
        js = r"""
const fs = require('fs');
const path = require('path');
const args = process.argv.slice(2);
const home = process.env.HOME;
function done(code, text) {
  if (text) process.stdout.write(text.endsWith('\n') ? text : text + '\n');
  process.exit(code);
}
if (args[0] === 'telemetry') {
  fs.mkdirSync(path.join(home, '.har'), {recursive: true});
  fs.writeFileSync(path.join(home, '.har', 'otel-hooks'), '');
  done(0);
}
if (args[0] === 'env' && args[1] === 'init') {
  fs.mkdirSync('.har', {recursive: true});
  fs.writeFileSync('.har/stages.json', '{}\n');
  done(0);
}
if (args[0] === 'env' && args[1] === 'launch') {
  const work = path.join(home, 'slot-1');
  fs.mkdirSync(work, {recursive: true});
  fs.writeFileSync(path.join(home, 'work-path'), work);
  done(0, 'make ALL file edits under: ' + work);
}
if (args[0] === 'env' && args[1] === 'verify') {
  const marker = path.join(home, 'verify-seen');
  const seen = fs.existsSync(marker);
  fs.writeFileSync(marker, '1');
  if (!seen) done(0, JSON.stringify({status: 'pass', stages: [{name: 'unit-tests', pass: true}]}));
  done(1, JSON.stringify({status: 'fail', stages: [{name: 'unit-tests', pass: false}]}));
}
if (args[0] === 'env' && args[1] === 'teardown') {
  const work = fs.readFileSync(path.join(home, 'work-path'), 'utf8').trim();
  fs.rmSync(work, {recursive: true, force: true});
  done(0);
}
done(3, 'unexpected ' + args.join(' '));
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-har-otel-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            env = self._base_env(home)
            env.update(self._har_bins(root, js))
            proc = self._run("har", env)
            blob = proc.stdout + proc.stderr
            receipt = self._receipt("har")
            self.assertEqual(proc.returncode, 1, blob + "\n" + json.dumps(receipt))
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn(".har/otel-hooks", receipt.get("reason") or "", blob)

    def _assert_child_dirs_under_its_home(self, text: str, parent_home: Path) -> None:
        env = {}
        cwd = ""
        for line in text.splitlines():
            if line.startswith("cwd="):
                cwd = line.split("=", 1)[1]
            elif "=" in line:
                key, value = line.split("=", 1)
                env[key] = value
        seen = Path(env["HOME"]).resolve()
        self.assertNotEqual(seen, parent_home.resolve(), env)
        self.assertTrue(cwd, text)
        self.assertTrue(Path(cwd).is_absolute(), cwd)
        for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "npm_config_cache"):
            got = Path(env[key]).resolve()
            self.assertTrue(got.is_relative_to(seen), f"{key}={env[key]} HOME={env['HOME']}")

    def test_rulora_child_env_dirs_are_under_temp_home(self) -> None:
        # Fail: the rulora node probe inherits the parent HOME or XDG/npm paths outside its HOME.
        # Recover: HOME is a fresh temp dir and the four dirs sit under that HOME.
        stub = """#!/bin/sh
if [ "$1" = --version ]; then echo v22.0.0; exit 0; fi
{ env; echo "cwd=$(pwd)"; } > "$PFY_PROBE_OUT"
exit 0
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-rulora-env-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            pkg = root / "rulora" / "node_modules" / "@rulora" / "core"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text('{"version": "0.1.0-alpha.4"}\n', encoding="utf-8")
            node = root / "node"
            _write_exe(node, stub)
            probe = root / "probe.txt"
            env = self._base_env(home)
            env["PFY_PROBE_OUT"] = str(probe)
            env["RULORA_DIR"] = str(root / "rulora")
            env["RULORA_NODE"] = str(node)
            proc = self._run("rulora", env)
            blob = proc.stdout + proc.stderr
            self.assertTrue(probe.is_file(), blob)
            self.assertNotIn("Traceback", proc.stderr, blob)
            self._assert_child_dirs_under_its_home(probe.read_text(encoding="utf-8"), home)

    def test_cassmemory_child_env_dirs_are_under_temp_home(self) -> None:
        # Fail: the cm child inherits the parent HOME or XDG/npm paths outside its HOME.
        # Recover: HOME is a fresh temp dir and the four dirs sit under that HOME.
        stub = """#!/bin/sh
{ env; echo "cwd=$(pwd)"; } > "$PFY_PROBE_OUT"
echo '{"success": false}'
exit 1
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-cm-env-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            binary = root / "cm"
            _write_exe(binary, stub)
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            probe = root / "probe.txt"
            env = self._base_env(home)
            env["PFY_PROBE_OUT"] = str(probe)
            env["CM_BIN"] = str(binary)
            env["CM_SHA256"] = digest
            proc = self._run("cassmemory", env)
            blob = proc.stdout + proc.stderr
            self.assertTrue(probe.is_file(), blob)
            self.assertNotIn("Traceback", proc.stderr, blob)
            self._assert_child_dirs_under_its_home(probe.read_text(encoding="utf-8"), home)

    def test_node_version_uses_clean_env(self) -> None:
        # Fail: `node --version` inherits PAID_KEYS or the parent HOME.
        # Recover: the version probe runs, its HOME is a fresh temp dir, and no paid name or dummy value is present.
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-nodever-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            pkg = root / "rulora" / "node_modules" / "@rulora" / "core"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text('{"version": "0.1.0-alpha.4"}\n', encoding="utf-8")
            probe = root / "node.env"
            node = root / "node"
            _write_exe(node, "#!/bin/sh\nif [ \"$1\" = --version ]; then env > %s; echo v22.0.0; exit 0; fi\nexit 0\n" % shlex.quote(str(probe)))
            env = self._base_env(home)
            for key in PAID_KEYS:
                env[key] = DUMMY_PAID
            for key in ("GH_TOKEN", "GITHUB_TOKEN", "NPM_TOKEN", "FOO_API_KEY"):
                env[key] = DUMMY_PAID
            env["PFY_SMOKE_RECEIPT_DIR"] = str(root / "receipts")
            env["RULORA_DIR"] = str(root / "rulora")
            env["RULORA_NODE"] = str(node)
            proc = self._run("rulora", env)
            self.assertTrue(probe.is_file(), proc.stdout + proc.stderr)
            dump = probe.read_text(encoding="utf-8")
            leaked = sorted(
                {line.split("=", 1)[0] for line in dump.splitlines() if line.split("=", 1)[0] in PAID_KEYS}
            )
            self.assertEqual(leaked, [], f"node --version received paid keys {leaked}")
            self.assertFalse(DUMMY_PAID in dump, "node --version received the dummy paid value")
            names = {line.split("=", 1)[0] for line in dump.splitlines()}
            secret_names = [key for key in ("GH_TOKEN", "GITHUB_TOKEN", "NPM_TOKEN", "FOO_API_KEY") if key in names]
            self.assertEqual(secret_names, [], f"node --version received secret names {secret_names}")
            self.assertIn("PATH", names)
            self.assertTrue(any(line.startswith("PATH=") and line.split("=", 1)[1] for line in dump.splitlines()))
            homes = [line.split("=", 1)[1] for line in dump.splitlines() if line.startswith("HOME=")]
            self.assertEqual(len(homes), 1, "node --version env dump has no HOME")
            self.assertNotEqual(os.path.normpath(homes[0]), os.path.normpath(str(home)))
            self.assertTrue(homes[0].startswith(os.path.normpath(tempfile.gettempdir()) + os.sep), homes[0])
            self.assertNotIn("Traceback", proc.stderr)

    def test_cassmemory_child_drops_secret_shaped_env(self) -> None:
        # Fail: the cm child keeps secret-shaped names (M26) or GITHUB_PAT (M28).
        # Recover: those names are absent, PATH is present, and HOME is a fresh temp dir.
        secret_names = (
            "NPM_TOKEN", "GITHUB_PAT", "GH_ENTERPRISE_TOKEN", "HF_TOKEN",
            "FOO_API_KEY", "DB_PASSWORD", "MY_SECRET", "AWS_CREDENTIALS",
        )
        stub_body = """#!/usr/bin/env python3
import os
from pathlib import Path
here = Path(__file__).resolve().parent
(here / "cm-env-names").write_text("\\n".join(sorted(os.environ)) + "\\n")
(here / "cm-home-value").write_text(os.environ.get("HOME", ""))
raise SystemExit(1)
"""
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-cm-envscrub-") as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            stub = root / "cm"
            _write_exe(stub, stub_body)
            env = self._base_env(home)
            env["CM_BIN"] = str(stub)
            env["CM_SHA256"] = hashlib.sha256(stub.read_bytes()).hexdigest()
            env["PFY_SMOKE_RECEIPT_DIR"] = str(root / "receipts")
            for key in secret_names:
                env[key] = DUMMY_PAID
            proc = self._run("cassmemory", env)
            blob = proc.stdout + proc.stderr
            names_path = root / "cm-env-names"
            self.assertTrue(names_path.is_file(), blob)
            seen = names_path.read_text(encoding="utf-8").splitlines()
            self.assertFalse(any("=" in line for line in seen), "env dump included values")
            leaked = [key for key in secret_names if key in seen]
            self.assertEqual(leaked, [], f"cm child saw secret names {leaked}")
            self.assertIn("PATH", seen)
            home_value = (root / "cm-home-value").read_text(encoding="utf-8").strip()
            self.assertNotEqual(os.path.normpath(home_value), os.path.normpath(str(home)))
            self.assertTrue(home_value.startswith(os.path.normpath(tempfile.gettempdir()) + os.sep), home_value)
            self.assertNotIn("Traceback", proc.stderr)


    def test_cassmemory_receipt_stays_in_this_tests_dir(self) -> None:
        # Fail: the smoke writes the shared repo receipt, so a parallel module
        # reading pipelines/smoke/cassmemory/latest.json sees this test's run.
        # Recover: the receipt lands under PFY_SMOKE_RECEIPT_DIR and the repo
        # file keeps its bytes.
        shared = ROOT / "pipelines" / "smoke" / "cassmemory" / "latest.json"
        before = shared.read_bytes() if shared.exists() else None
        with tempfile.TemporaryDirectory(prefix="pfy-xintake-cm-") as td:
            home = Path(td) / "home"
            home.mkdir()
            env = self._base_env(home)
            env["CM_BIN"] = str(Path(td) / "missing-cm")
            self._run("cassmemory", env)
        self.assertTrue((self.receipts / "cassmemory" / "latest.json").is_file())
        after = shared.read_bytes() if shared.exists() else None
        self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()
