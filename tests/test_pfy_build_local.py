#!/usr/bin/env python3
"""Behavior tests for ./pfy build --local. Stub Ollama and stub opencode only."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "local-build-tests"


def _direct_socket_dir() -> Path:
    """A directory whose ollama.sock path is shorter than sun_path.

    Repo tmp is used when that string fits. A deep checkout uses another
    short writable directory that is not /tmp, because bwrap hides /tmp.
    """
    preferred = ROOT / "tmp" / "s" / "w"
    if len(str(preferred / "tmp" / "ollama.sock")) < 108:
        return preferred
    parents = [Path("/run/user") / str(os.getuid()), Path("/dev/shm")]
    for parent in parents:
        if not parent.is_dir() or not os.access(parent, os.W_OK):
            continue
        dest = parent / ("pfy-w-%d" % os.getpid())
        if len(str(dest / "tmp" / "ollama.sock")) < 108:
            return dest
    raise AssertionError("no short writable directory outside /tmp for the direct socket")


def _load_build():
    path = ROOT / "scripts" / "pfy_build_local.py"
    spec = importlib.util.spec_from_file_location("pfy_build_local_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pfy_build_local")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD = _load_build()

STUB = r"""#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

argv = sys.argv[1:]
if "--version" in argv:
    print("stub-opencode 0")
    raise SystemExit(0)
if not argv or argv[0] in ("-h", "--help"):
    print("usage: opencode run --pure --model --variant")
    raise SystemExit(0)
if argv[0] != "run":
    print("stub-opencode")
    raise SystemExit(0)

def _mark(path, text):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True

def _wait_ready(path, seconds=5):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if path.is_file():
            return True
        time.sleep(0.05)
    return False

root = Path.cwd()
_mark(root / "tmp" / "pfy-agent-started", "started\n")
marker = os.environ.get("PFY_STUB_MARKER")
if marker:
    _mark(Path(marker), "started\n")
payload = {
    "home": os.environ.get("HOME"),
    "tmpdir": os.environ.get("TMPDIR"),
    "xdg": {k: os.environ[k] for k in sorted(os.environ) if k.startswith("XDG_")},
    "keys": sorted(os.environ),
    "cwd": os.getcwd(),
}
print("PFY_STUB_REPORT " + json.dumps(payload), flush=True)
report = os.environ.get("PFY_STUB_REPORT")
if report:
    _mark(Path(report), json.dumps(payload))

def _pid(name, pid):
    _mark(root / "tmp" / name, str(pid))
    external = os.environ.get("PFY_STUB_CHILD_PID") or ""
    if not external:
        return
    target = external if name == "orphan-child.pid" else external + ".parent"
    _mark(Path(target), str(pid))

def _beat(name):
    _mark(root / "tmp" / name, str(time.time()))

def _loop(name):
    while True:
        _beat(name)
        time.sleep(0.2)

scenario = os.environ.get("PFY_LOCAL_BUILD_SCENARIO", "noop")
if scenario == "hang":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    pid = os.fork()
    if pid == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        _pid("orphan-child.pid", os.getpid())
        _loop("orphan-child.heartbeat")
    _pid("orphan-parent.pid", os.getpid())
    _loop("orphan-parent.heartbeat")
if scenario == "orphan-ignore-child":
    pid = os.fork()
    if pid == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        _pid("orphan.pid", os.getpid())
        _mark(root / "tmp" / "orphan.ready", "1\n")
        _loop("orphan.heartbeat")
    _wait_ready(root / "tmp" / "orphan.ready")
    raise SystemExit(0)
if scenario == "orphan-background":
    pid = os.fork()
    if pid == 0:
        _pid("orphan.pid", os.getpid())
        _mark(root / "tmp" / "orphan.ready", "1\n")
        _loop("orphan.heartbeat")
    _wait_ready(root / "tmp" / "orphan.ready")
    raise SystemExit(0)
if scenario == "orphan-grandchild":
    pid = os.fork()
    if pid == 0:
        grand = os.fork()
        if grand == 0:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            _pid("orphan.pid", os.getpid())
            _mark(root / "tmp" / "orphan.ready", "1\n")
            _loop("orphan.heartbeat")
        os._exit(0)
    _wait_ready(root / "tmp" / "orphan.ready")
    raise SystemExit(0)
if scenario == "slow-fix":
    time.sleep(float(os.environ.get("PFY_STUB_SLEEP") or "2"))
    scenario = "fix"

calc = root / "src" / "calc.py"
test_calc = root / "tests" / "test_calc.py"
ci = root / ".github" / "workflows" / "ci.yml"
if scenario == "fix" and calc.exists():
    calc.write_text(calc.read_text(encoding="utf-8").replace("return a + b + 1", "return a + b"), encoding="utf-8")
elif scenario == "protect" and test_calc.exists():
    test_calc.write_text(test_calc.read_text(encoding="utf-8") + "\n# touched by stub\n", encoding="utf-8")
elif scenario == "worse" and calc.exists():
    calc.write_text("def add(a, b):\n    return a + b + 5\n", encoding="utf-8")
elif scenario == "delete-test" and test_calc.exists():
    test_calc.unlink()
elif scenario == "cheat-asserts" and test_calc.exists():
    text = test_calc.read_text(encoding="utf-8")
    text = text.replace("self.assertEqual(add(1, 1), 2)", "self.assertTrue(True)")
    test_calc.write_text(text, encoding="utf-8")
elif scenario == "skip-test" and test_calc.exists():
    text = test_calc.read_text(encoding="utf-8")
    text = text.replace(
        "    def test_add(self):",
        "    @unittest.skip('cheat')\n    def test_add(self):",
        1,
    )
    test_calc.write_text(text, encoding="utf-8")
elif scenario == "dotfile":
    if calc.exists():
        calc.write_text(calc.read_text(encoding="utf-8").replace("return a + b + 1", "return a + b"), encoding="utf-8")
    if ci.exists():
        ci.write_text(ci.read_text(encoding="utf-8") + "# touched\n", encoding="utf-8")
elif scenario == "exit-zero" and calc.exists():
    calc.write_text("import os\nos._exit(0)\n", encoding="utf-8")
elif scenario == "conftest-exit" and calc.exists():
    calc.write_text(calc.read_text(encoding="utf-8").replace("return a + b + 1", "return a + b"), encoding="utf-8")
    (root / "conftest.py").write_text("import os\nos._exit(0)\n", encoding="utf-8")
elif scenario == "pytest-deselect":
    (root / "pytest.ini").write_text("[pytest]\naddopts = --deselect tests/test_calc.py\n", encoding="utf-8")
elif scenario == "ignore-star" and calc.exists():
    calc.write_text("from src.helper import add_impl\ndef add(a, b):\n    return add_impl(a, b)\n", encoding="utf-8")
    (root / "src" / "helper.py").write_text("def add_impl(a, b):\n    return a + b\n", encoding="utf-8")
    (root / ".gitignore").write_text("*\n", encoding="utf-8")
elif scenario == "ignored-helper" and calc.exists():
    calc.write_text("from src.helper import add_impl\ndef add(a, b):\n    return add_impl(a, b)\n", encoding="utf-8")
    (root / "src" / "helper.py").write_text("def add_impl(a, b):\n    return a + b\n", encoding="utf-8")
elif scenario == "sandbox-attack" and calc.exists():
    target = os.environ.get("PFY_STUB_ATTACK_FILE") or ""
    port = os.environ.get("PFY_STUB_ATTACK_PORT") or "9"
    bare = os.environ.get("PFY_STUB_ATTACK_BARE") or ""
    repo_path = os.environ.get("PFY_STUB_ATTACK_REPO") or ""
    (root / "src" / "__init__.py").write_text(
        "import socket, subprocess\n"
        "notes = []\n"
        "try:\n"
        "    s = socket.create_connection(('127.0.0.1', %s), 2)\n"
        "    s.close()\n"
        "    notes.append('tcp=ok')\n"
        "except Exception:\n"
        "    notes.append('tcp=fail')\n"
        "try:\n"
        "    s = socket.create_connection(('1.1.1.1', 53), 2)\n"
        "    s.close()\n"
        "    notes.append('ext=ok')\n"
        "except Exception:\n"
        "    notes.append('ext=fail')\n"
        "try:\n"
        "    open(%r, 'w').write('PWNED\\n')\n"
        "    notes.append('write=ok')\n"
        "except Exception:\n"
        "    notes.append('write=fail')\n"
        "try:\n"
        "    proc = subprocess.run(['git','-c','remote.origin.url=%s','-c','remote.origin.pushurl=%s','push','origin','HEAD'], timeout=5)\n"
        "    notes.append('push=ok' if proc.returncode == 0 else 'push=fail')\n"
        "except Exception:\n"
        "    notes.append('push=fail')\n"
        "try:\n"
        "    proc = subprocess.run(['git','-C',%r,'branch','pwned'], timeout=5)\n"
        "    notes.append('branch=ok' if proc.returncode == 0 else 'branch=fail')\n"
        "except Exception:\n"
        "    notes.append('branch=fail')\n"
        "try:\n"
        "    open('tmp/attack-result.txt','w').write('\\n'.join(notes) + '\\n')\n"
        "except Exception:\n"
        "    pass\n" % (port, target, bare, bare, repo_path),
        encoding="utf-8",
    )
    calc.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
elif scenario == "late-rewrite" and calc.exists():
    calc.write_text(calc.read_text(encoding="utf-8").replace("return a + b + 1", "return a + b"), encoding="utf-8")
    pid = os.fork()
    if pid == 0:
        os.setsid()
        grand = os.fork()
        if grand == 0:
            started = time.time()
            while True:
                _beat("daemon.heartbeat")
                if time.time() - started >= 24:
                    calc.write_text("def add(a, b):\n    return 0\n", encoding="utf-8")
                    _mark(root / "tmp" / "daemon-rewrote", "1\n")
                    os._exit(0)
                time.sleep(0.2)
        os._exit(0)
    _wait_ready(root / "tmp" / "daemon.heartbeat")
elif scenario == "plan":
    plan_path = os.environ.get("PFY_STUB_PLAN") or ""
    count_path = os.environ.get("PFY_STUB_COUNT") or ""
    prompts_path = os.environ.get("PFY_STUB_PROMPTS") or ""
    n = 0
    if count_path:
        try:
            n = int(Path(count_path).read_text(encoding="utf-8").strip() or "0")
        except (OSError, ValueError):
            n = 0
        _mark(Path(count_path), str(n + 1))
    prompt = argv[-1] if argv else ""
    if prompts_path:
        line = json.dumps({"attempt": n + 1, "prompt": prompt}) + "\n"
        try:
            with open(prompts_path, "a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass
    steps = []
    if plan_path:
        try:
            steps = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            steps = []
    step = steps[n] if n < len(steps) else (steps[-1] if steps else {"mode": "fix"})
    mode = step.get("mode") or "noop"
    if mode == "fix" and calc.exists():
        calc.write_text(calc.read_text(encoding="utf-8").replace("return a + b + 1", "return a + b"), encoding="utf-8")
    elif mode == "worse" and calc.exists():
        calc.write_text("def add(a, b):\n    return a + b + 5\n", encoding="utf-8")
    for rel, content in (step.get("write") or {}).items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    for rel, extra in (step.get("append") or {}).items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        prev = dest.read_text(encoding="utf-8") if dest.is_file() else ""
        dest.write_text(prev + extra, encoding="utf-8")
raise SystemExit(0)
"""

TEST_CALC = """\
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.calc import add


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 1), 2)
"""

TEST_OTHER = """\
import unittest


class OtherTests(unittest.TestCase):
    def test_true(self):
        self.assertTrue(True)
"""

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _send(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/tags"):
            self._send(200, {"models": self.server.tags})
        elif self.path.startswith("/api/ps"):
            code = getattr(self.server, "ps_status", 200)
            if code != 200:
                self._send(code, {"error": "ps-unavailable"})
                return
            self._send(200, {"models": self.server.ps})
        elif self.path.startswith("/v1/models"):
            data = [{"id": item.get("name")} for item in self.server.tags if isinstance(item, dict)]
            self._send(200, {"object": "list", "data": data})
        else:
            self._send(200, {})

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            payload = {}
        self.server.posts.append((self.path, payload))
        if "/chat/completions" in self.path:
            blob = json.dumps(payload)
            content = "ok"
            if "pfy-review-v1" in blob:
                started = getattr(self.server, "review_started", None)
                if started is not None:
                    started.set()
                blocker = getattr(self.server, "review_block", None)
                if blocker is not None:
                    blocker.wait()
                queue = getattr(self.server, "review_queue", None)
                if queue:
                    content = queue.pop(0)
                else:
                    content = json.dumps({"verdict": "accept", "reasons": []})
            self._send(200, {"id": "c", "choices": [{"message": {"role": "assistant", "content": content}}]})
            return
        self._send(200, {"ok": True})


def _serve(tags=None, ps=None):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.tags = list(tags or [{"name": "fixture:small", "size": 1024 ** 3}])
    httpd.ps = list(ps or [])
    httpd.posts = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def _unloads(httpd) -> int:
    count = 0
    for _path, payload in httpd.posts:
        if isinstance(payload, dict) and payload.get("keep_alive") in (0, 0.0):
            count += 1
    return count


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def _init_repo(repo: Path, bare: Path) -> None:
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "src" / "calc.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "tests" / "test_calc.py").write_text(TEST_CALC, encoding="utf-8")
    (repo / "tests" / "test_other.py").write_text(TEST_OTHER, encoding="utf-8")
    (repo / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    subprocess.check_call(["git", "-C", str(repo), "init", "-b", "main"], stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "-C", str(repo), "config", "user.email", "test@example.com"])
    subprocess.check_call(["git", "-C", str(repo), "config", "user.name", "test"])
    subprocess.check_call(["git", "-C", str(repo), "add", "-A"])
    subprocess.check_call(["git", "-C", str(repo), "commit", "-m", "base"], stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "init", "--bare", "-b", "main", str(bare)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "-C", str(repo), "remote", "add", "origin", str(bare)])
    subprocess.check_call(["git", "-C", str(repo), "push", "-u", "origin", "main"], stdout=subprocess.DEVNULL)


def _kb(gib: float) -> int:
    return int(round(gib * 1024 * 1024))


def _dead(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _under_repo_tmp(path: Path, repo: Path) -> bool:
    resolved = path.resolve()
    base = (repo / "tmp").resolve()
    return resolved == base or base in resolved.parents


def _is_system_tmp(path: Path) -> bool:
    resolved = path.resolve()
    system_tmp = Path("/tmp").resolve()
    return resolved == system_tmp or system_tmp in resolved.parents


def _branches(repo: Path) -> list[str]:
    text = _git(repo, "branch", "--list", "local/*")
    return [line.strip().lstrip("* ").strip() for line in text.splitlines() if line.strip()]


class LocalBuildTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix="case-", dir=SCRATCH))
        self.repo = self.tmp / "repo"
        self.bare = self.tmp / "origin.git"
        self.mem = self.tmp / "meminfo"
        self.marker = self.tmp / "marker"
        self.report = self.tmp / "report.json"
        self.child_pid = self.tmp / "child.pid"
        self.stub = self.tmp / "opencode"
        self.stub.write_text(STUB, encoding="utf-8")
        self.stub.chmod(0o755)
        self.write_mem(40, 8, 8)
        _init_repo(self.repo, self.bare)
        self.httpd = _serve()
        self.port = self.httpd.server_address[1]
        self.head0 = _git(self.repo, "rev-parse", "HEAD").strip()
        self.status0 = _git(self.repo, "status", "--porcelain")
        self.refs0 = subprocess.check_output(["git", "ls-remote", str(self.bare)], text=True)
        self._seq = 0

    def tearDown(self):
        self._kill_noted_orphans()
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _kill_noted_orphans(self):
        # A pid written inside the sandbox is a namespace pid. Signalling that
        # number on the host can hit an unrelated process. Match the cmdline.
        if not self.tmp.exists():
            return
        needle = str(self.tmp).encode()
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid <= 1 or pid == os.getpid():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes()
            except OSError:
                continue
            if needle in cmd:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

    def write_mem(self, available_gib, swap_free_gib, swap_total_gib):
        text = (
            "MemTotal: %d kB\nMemAvailable: %d kB\nSwapTotal: %d kB\nSwapFree: %d kB\n"
            % (_kb(128), _kb(available_gib), _kb(swap_total_gib), _kb(swap_free_gib))
        )
        self.mem.write_text(text, encoding="utf-8")

    def env(self, scenario="fix", **extra):
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("PFY_LOCAL_BUILD_") or key.startswith("PFY_STUB_") or key in (
                "PFY_BOT_OPENCODE",
                "PFY_MEMINFO_FILE",
                "LOCAL_OPENAI_BASE_URL",
                "PFY_LOCAL_BUILD_INJECT_CRASH",
            ):
                env.pop(key, None)
        env.update(
            {
                "PFY_MEMINFO_FILE": str(self.mem),
                "PFY_BOT_OPENCODE": str(self.stub),
                "PFY_LOCAL_BUILD_SCENARIO": scenario,
                "PFY_STUB_MARKER": str(self.marker),
                "PFY_STUB_REPORT": str(self.report),
                "PFY_STUB_CHILD_PID": str(self.child_pid),
                "GITHUB_TOKEN": "ghp_supersecretvalue",
                "AWS_SECRET_ACCESS_KEY": "AKIASECRETVALUE",
                "MY_KEY": "abcdkeyvalue",
                "TMPDIR": str(ROOT / "tmp" / "scratch"),
                "PFY_LOCAL_BUILD_MODEL": "not-the-flag-model:latest",
            }
        )
        env.update(extra)
        return env

    def command(self, scenario, extra=None, auto_unsafe=True, task=None):
        self._seq += 1
        receipt = self.repo / "tmp" / "receipts" / ("%s-%s" % (scenario, self._seq))
        cmd = [
            str(ROOT / "pfy"),
            "build",
            "--repo",
            str(self.repo),
            "--local",
            task or "fix add so one plus one is two",
            "--model",
            "fixture:small",
            "--endpoint",
            "http://127.0.0.1:%d/v1" % self.port,
            "--test-cmd",
            "python3 -m unittest discover -s tests -t .",
            "--timeout",
            "30",
            "--test-timeout",
            "30",
            "--min-free-gb",
            "32",
            "--receipt-dir",
            str(receipt),
        ]
        if extra:
            cmd.extend(extra)
        if auto_unsafe and not BUILD.bwrap_works() and "--unsafe-no-sandbox" not in cmd:
            cmd.append("--unsafe-no-sandbox")
        return cmd, receipt

    def run_build(self, scenario="fix", extra=None, env_extra=None, timeout=60, auto_unsafe=True, task=None):
        if self.marker.exists():
            self.marker.unlink()
        cmd, receipt = self.command(scenario, extra, auto_unsafe=auto_unsafe, task=task)
        proc = subprocess.run(
            cmd,
            cwd=self.repo,
            env=self.env(scenario, **(env_extra or {})),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return proc, receipt

    def receipt(self, proc, receipt_dir):
        path = receipt_dir / "receipt.json"
        self.assertTrue(path.is_file(), proc.stdout + "\n" + proc.stderr)
        return json.loads(path.read_text(encoding="utf-8"))

    def started_files(self):
        return list(self.repo.glob("tmp/local-build-*/tmp/pfy-agent-started"))

    def wait_started(self, proc, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.started_files() or self.marker.exists():
                return True
            if proc.poll() is not None:
                return bool(self.started_files() or self.marker.exists())
            time.sleep(0.05)
        return False

    def assert_agent_did_not_start(self):
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.started_files(), [])

    def worktree_pid(self, name):
        found = list(self.repo.glob("tmp/local-build-*/tmp/%s" % name))
        self.assertTrue(found, name)
        return int(found[0].read_text(encoding="utf-8").strip())

    def wait_worktree_file(self, name, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            found = list(self.repo.glob("tmp/local-build-*/tmp/%s" % name))
            if found and found[0].is_file() and found[0].stat().st_size > 0:
                return found[0]
            time.sleep(0.05)
        return None

    def assert_quiet(self, path, pause=0.8):
        self.assertIsNotNone(path)
        first = path.read_text(encoding="utf-8")
        time.sleep(pause)
        second = path.read_text(encoding="utf-8")
        self.assertEqual(first, second, path)

    def commit_base(self, message="base update"):
        subprocess.check_call(["git", "-C", str(self.repo), "add", "-A"], stdout=subprocess.DEVNULL)
        subprocess.check_call(
            ["git", "-C", str(self.repo), "commit", "-m", message],
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["git", "-C", str(self.repo), "push", "origin", "HEAD:main"],
            stdout=subprocess.DEVNULL,
        )
        self.head0 = _git(self.repo, "rev-parse", "HEAD").strip()
        self.status0 = _git(self.repo, "status", "--porcelain")
        self.refs0 = subprocess.check_output(["git", "ls-remote", str(self.bare)], text=True)

    def stub_report(self, receipt_dir):
        log = (receipt_dir / "agent.log").read_text(encoding="utf-8")
        for line in log.splitlines():
            if line.startswith("PFY_STUB_REPORT "):
                return json.loads(line.split(" ", 1)[1])
        self.fail("no stub report in agent.log\n" + log)

    def assert_clean_origin(self):
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.head0)
        self.assertEqual(_git(self.repo, "status", "--porcelain"), self.status0)
        self.assertEqual(subprocess.check_output(["git", "ls-remote", str(self.bare)], text=True), self.refs0)
        self.assertIn("+ 1", (self.repo / "src" / "calc.py").read_text(encoding="utf-8"))

    def assert_no_commit(self, proc, receipt_dir):
        data = self.receipt(proc, receipt_dir)
        self.assertIsNone(data["branch"])
        self.assertIsNone(data["commit"])
        self.assertEqual(_branches(self.repo), [])
        self.assert_clean_origin()
        return data

    def test_fix_creates_one_commit_and_leaves_the_checkout_alone(self):
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["schema"], "pfy-local-build/1")
        self.assertEqual(data["status"], "PASS")
        self.assertNotEqual(data["tests_before"]["exit"], 0)
        self.assertEqual(data["tests_after"]["exit"], 0)
        self.assertTrue(str(data["worktree"]).startswith(str(self.repo / "tmp") + os.sep))
        self.assertEqual(_unloads(self.httpd), 1)
        self.assertFalse(data["model_was_loaded"])
        self.assertTrue(data["unloaded"])
        self.assertEqual(len(_branches(self.repo)), 1)
        self.assertEqual(data["branch"], _branches(self.repo)[0])
        ahead = _git(self.repo, "rev-list", "--count", "%s..%s" % (self.head0, data["branch"])).strip()
        self.assertEqual(ahead, "1")
        shown = _git(self.repo, "show", "%s:src/calc.py" % data["branch"])
        self.assertIn("return a + b\n", shown)
        self.assertNotIn("+ 1", shown)
        names = _git(self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", data["commit"]).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])
        author = _git(self.repo, "log", "-1", "--format=%an", data["branch"]).strip()
        self.assertEqual(author, "pfy-local-build")
        message = _git(self.repo, "log", "-1", "--format=%B", data["branch"])
        self.assertIn(data["id"], message)
        self.assertIn("fix add", message)
        self.assert_clean_origin()
        self.assertIn("PASS", proc.stdout)
        self.assertTrue(str(data.get("sandbox") or "").startswith("bwrap") or data.get("sandbox") == "unsafe-no-sandbox")
        self.assertFalse((self.repo / "tmp" / "local-build.lock").exists())
        self.assertFalse((self.repo / "tmp" / "local-build.pids.json").exists())
        self.assertEqual(list(self.repo.glob("tmp/**/opencode.home")), [])

    def test_no_change_does_not_commit(self):
        proc, receipt = self.run_build("noop")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "no-change")

    def test_protected_test_edit_does_not_commit(self):
        proc, receipt = self.run_build("protect", extra=["--protect", "tests/*"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "protected-path-changed")
        self.assertIn("tests/test_calc.py", data["files_changed"])

    def test_worse_tests_do_not_commit(self):
        proc, receipt = self.run_build("worse")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-failed")

    def test_deleting_a_test_is_a_regression(self):
        proc, receipt = self.run_build("delete-test")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-regressed")
        self.assertEqual(data["tests_after"]["exit"], 0)
        self.assertLess(
            (data["tests_after"]["passed"] or 0) + (data["tests_after"]["failed"] or 0) + (data["tests_after"]["errors"] or 0),
            (data["tests_before"]["passed"] or 0) + (data["tests_before"]["failed"] or 0) + (data["tests_before"]["errors"] or 0),
        )

    def test_missing_test_command_does_not_start_the_agent(self):
        proc, receipt = self.run_build("fix", extra=["--test-cmd", "/no/such/pfy-test-cmd"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "test-cmd-failed-to-start")
        self.assert_agent_did_not_start()

    def test_hang_is_timeout_and_the_group_is_gone(self):
        started = time.monotonic()
        proc, receipt = self.run_build("hang", extra=["--timeout", "2"], timeout=20)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertLess(elapsed, 12)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["status"], "TIMEOUT")
        self.assertEqual(data["reason"], "timeout")
        self.assertEqual(_unloads(self.httpd), 1)
        child = self.wait_worktree_file("orphan-child.heartbeat", seconds=2)
        parent = self.wait_worktree_file("orphan-parent.heartbeat", seconds=2)
        self.assert_quiet(child)
        self.assert_quiet(parent)

    def test_sigterm_interrupts_and_releases_the_lock(self):
        cmd, receipt = self.command("hang", extra=["--timeout", "30"])
        proc = subprocess.Popen(
            cmd,
            cwd=self.repo,
            env=self.env("hang"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.assertTrue(self.wait_started(proc), "agent did not start")
        # The started marker is written before the child pid file. Wait for
        # the pid file itself so SIGTERM cannot land in that gap.
        self.assertIsNotNone(self.wait_worktree_file("orphan-child.pid"), "orphan-child.pid")
        self.assertIsNotNone(self.wait_worktree_file("orphan-parent.pid"), "orphan-parent.pid")
        child_beat = self.wait_worktree_file("orphan-child.heartbeat")
        parent_beat = self.wait_worktree_file("orphan-parent.heartbeat")
        self.assertIsNotNone(child_beat, "orphan-child.heartbeat")
        self.assertIsNotNone(parent_beat, "orphan-parent.heartbeat")
        os.kill(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.kill(proc.pid, signal.SIGKILL)
            out, err = proc.communicate(timeout=5)
            self.fail("runner did not exit after SIGTERM\n%s\n%s" % (out, err))
        self.assertEqual(proc.returncode, 1, (out or "") + (err or ""))
        data = self.receipt(subprocess.CompletedProcess(cmd, proc.returncode, out, err), receipt)
        self.assertEqual(data["reason"], "interrupted")
        self.assertIsNone(data["commit"])
        self.assert_quiet(child_beat)
        self.assert_quiet(parent_beat)
        lock = open(self.repo / "tmp" / "local-build.lock", "a+", encoding="utf-8")
        try:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        finally:
            lock.close()

    def test_low_memory_blocks_and_full_swap_is_not_free(self):
        self.write_mem(10, 0, 64)
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "BLOCKED")
        self.assertEqual(data["reason"], "mem")
        self.assertIsNone(data["worktree"])
        self.assert_agent_did_not_start()
        self.assertEqual(_unloads(self.httpd), 0)

    def test_plenty_of_ram_passes_when_swap_is_full(self):
        self.write_mem(40, 0, 64)
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["mem"]["swap_free_gb"], 0)

    def test_busy_host_does_not_unload_and_recovers(self):
        self.httpd.ps = [{"name": "other:7b"}]
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "busy-host")
        self.assert_agent_did_not_start()
        self.assertEqual(_unloads(self.httpd), 0)
        self.httpd.ps = []
        self.httpd.posts.clear()
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(_unloads(self.httpd), 1)

    def test_model_over_30_gib_is_blocked(self):
        self.httpd.tags = [{"name": "fixture:small", "size": 40 * 1024 ** 3}]
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "model-too-big")
        self.assert_agent_did_not_start()

    def test_cloud_tag_is_blocked(self):
        self.httpd.tags = [{"name": "deepseek-v4-flash:cloud", "size": 1024}]
        proc, receipt = self.run_build("fix", extra=["--model", "deepseek-v4-flash:cloud"])
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "cloud-tag")
        self.assert_agent_did_not_start()

    def test_missing_opencode_names_the_next_step_and_recovers(self):
        proc, receipt = self.run_build("fix", env_extra={"PFY_BOT_OPENCODE": str(self.tmp / "missing-opencode")})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        blob = proc.stdout + proc.stderr
        self.assertIn("./pfy attach opencode", blob)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "no-opencode")
        self.assert_agent_did_not_start()
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_ollama_down_is_no_model_and_recovers(self):
        proc, receipt = self.run_build("fix", extra=["--endpoint", "http://127.0.0.1:9/v1"])
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "no-model")
        self.assertEqual(data["status"], "BLOCKED")
        self.assert_agent_did_not_start()
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_second_run_blocks_and_the_first_still_passes(self):
        cmd, receipt = self.command("slow-fix", extra=["--timeout", "30"])
        first = subprocess.Popen(
            cmd,
            cwd=self.repo,
            env=self.env("slow-fix", PFY_STUB_SLEEP="2"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertTrue(self.wait_started(first), "first run did not start")
        other_marker = self.tmp / "marker-second"
        proc2, receipt2 = self.run_build(
            "fix",
            env_extra={"PFY_STUB_MARKER": str(other_marker)},
            timeout=15,
        )
        self.assertEqual(proc2.returncode, 4, proc2.stdout + proc2.stderr)
        data2 = self.receipt(proc2, receipt2)
        self.assertEqual(data2["reason"], "another run")
        self.assertFalse(other_marker.exists())
        out, err = first.communicate(timeout=30)
        self.assertEqual(first.returncode, 0, (out or "") + (err or ""))
        data = self.receipt(subprocess.CompletedProcess(cmd, first.returncode, out, err), receipt)
        self.assertEqual(data["status"], "PASS")

    def test_stale_lock_from_a_dead_pid_does_not_block(self):
        lock = self.repo / "tmp" / "local-build.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("42424242\n", encoding="utf-8")
        self.assertTrue(_dead(42424242))
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_model_already_loaded_is_not_unloaded(self):
        self.httpd.ps = [{"name": "fixture:small"}]
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertTrue(data["model_was_loaded"])
        self.assertFalse(data["unloaded"])
        self.assertEqual(_unloads(self.httpd), 0)

    def test_crash_after_the_agent_still_unloads(self):
        proc, receipt = self.run_build("fix", env_extra={"PFY_LOCAL_BUILD_INJECT_CRASH": "post"})
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "runner-crash")
        self.assertEqual(_unloads(self.httpd), 1)

    def test_timeout_unloads_when_this_run_loaded_the_model(self):
        proc, receipt = self.run_build("hang", extra=["--timeout", "2"], timeout=20)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(_unloads(self.httpd), 1)
        data = self.receipt(proc, receipt)
        self.assertTrue(data["unloaded"])

    def test_child_env_stays_inside_repo_tmp_and_has_no_secrets(self):
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = self.stub_report(receipt)
        real_home = Path.home().resolve()
        home = Path(report["home"]).resolve()
        tmpdir = Path(report["tmpdir"]).resolve()
        # The repo itself lives under the user home, so "not the real HOME"
        # means the child HOME is not that directory. Ancestors are expected.
        self.assertNotEqual(home, real_home)
        self.assertTrue(home.parent.name.endswith(".home"), str(home))
        self.assertNotEqual(home, self.repo.resolve())
        # HOME must not be an ancestor of the checkout. The repo lives under
        # the user home on this machine, so the user home is an ancestor of
        # the isolated directory and that is expected.
        self.assertNotIn(home, self.repo.resolve().parents)
        for label, path in (("home", home), ("tmpdir", tmpdir)):
            self.assertTrue(_under_repo_tmp(path, self.repo), label)
            self.assertFalse(_is_system_tmp(path), label)
        isolated = home.parent
        for value in report["xdg"].values():
            path = Path(value).resolve()
            self.assertTrue(_under_repo_tmp(path, self.repo))
            self.assertFalse(_is_system_tmp(path))
            self.assertTrue(path == isolated or isolated in path.parents, str(path))
        for key in report["keys"]:
            if key.startswith("GIT_CONFIG_"):
                continue
            upper = key.upper()
            self.assertNotIn("TOKEN", upper, key)
            self.assertNotIn("KEY", upper, key)
            self.assertNotIn("SECRET", upper, key)
        blob = json.dumps(report)
        self.assertNotIn("ghp_", blob)
        self.assertNotIn("AKIA", blob)
        cwd = Path(report["cwd"])
        self.assertTrue(_under_repo_tmp(cwd, self.repo))
        self.assertNotEqual(cwd.resolve(), self.repo.resolve())
        data = self.receipt(proc, receipt)
        self.assertNotIn("ghp_", json.dumps(data))
        self.assertNotIn("AKIA", json.dumps(data))

    def test_dry_run_loads_nothing_and_starts_nothing(self):
        proc, receipt = self.run_build("fix", extra=["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assert_agent_did_not_start()
        self.assertEqual(_unloads(self.httpd), 0)
        for path, payload in self.httpd.posts:
            self.assertNotIn("generate", path)
            self.assertNotIn("chat", path)
            if isinstance(payload, dict):
                self.assertNotIn("keep_alive", payload)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "dry-run")
        self.assertIsNone(data["worktree"])
        self.assertEqual(_branches(self.repo), [])

    def test_env_model_is_used_when_the_flag_is_absent(self):
        cmd, receipt = self.command("fix")
        # Drop the flag so the env value has to win over the default tag.
        cleaned = []
        skip = False
        for part in cmd:
            if skip:
                skip = False
                continue
            if part == "--model":
                skip = True
                continue
            cleaned.append(part)
        proc = subprocess.run(
            cleaned,
            cwd=self.repo,
            env=self.env("fix", PFY_LOCAL_BUILD_MODEL="fixture:small"),
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["model"], "fixture:small")

    def test_rewriting_asserts_to_true_does_not_commit(self):
        proc, receipt = self.run_build("cheat-asserts")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-tampered")

    def test_skipping_a_failing_test_does_not_commit(self):
        proc, receipt = self.run_build("skip-test", extra=["--writable-test", "tests/*"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-failed")
        self.assertEqual(data["tests_after"]["exit"], 0)

    def test_dotfile_protect_matches_github_workflows(self):
        proc, receipt = self.run_build("dotfile", extra=["--protect", ".github/*"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "protected-path-changed")
        self.assertTrue(any(path.startswith(".github/") for path in data["files_changed"]))

    def test_ps_error_blocks_closed(self):
        self.httpd.ps_status = 500
        proc, receipt = self.run_build("fix")
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "BLOCKED")
        self.assertEqual(data["reason"], "busy-host")
        self.assert_agent_did_not_start()
        self.assertEqual(_unloads(self.httpd), 0)

    def test_exclude_is_the_worktree_git_dir_only(self):
        info = self.repo / ".git" / "info"
        info.mkdir(parents=True, exist_ok=True)
        exclude = info / "exclude"
        exclude.write_text("# origin-marker\n", encoding="utf-8")
        proc, receipt = self.run_build("noop")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(exclude.read_text(encoding="utf-8"), "# origin-marker\n")
        data = self.receipt(proc, receipt)
        worktree = Path(data["worktree"])
        git_dir = subprocess.check_output(
            ["git", "-C", str(worktree), "rev-parse", "--path-format=absolute", "--git-dir"],
            text=True,
        ).strip()
        text = (Path(git_dir) / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn("tmp/", text)

    def test_permission_config_is_kept_and_sandbox_is_recorded(self):
        proc, receipt = self.run_build("noop")
        data = self.receipt(proc, receipt)
        self.assertTrue(str(data.get("sandbox") or "").startswith("bwrap") or data.get("sandbox") == "unsafe-no-sandbox")
        cfg = json.loads((receipt / "opencode.json").read_text(encoding="utf-8"))
        bash = cfg["permission"]["bash"]
        self.assertEqual(bash.get("git push*"), "deny")
        self.assertEqual(cfg["permission"].get("external_directory"), "deny")

    def test_memory_watchdog_stops_a_hang(self):
        cmd, receipt = self.command("hang", extra=["--timeout", "60"])
        proc = subprocess.Popen(
            cmd,
            cwd=self.repo,
            env=self.env("hang"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            self.assertTrue(self.wait_started(proc), "agent did not start")
            self.write_mem(1, 0, 0)
            try:
                out, err = proc.communicate(timeout=40)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                out, err = proc.communicate(timeout=5)
                self.fail("watchdog did not stop the run\n%s\n%s" % (out, err))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 1, (out or "") + (err or ""))
        data = self.receipt(subprocess.CompletedProcess(cmd, proc.returncode, out, err), receipt)
        self.assertEqual(data["reason"], "mem-edge")
        self.assertIsNone(data["commit"])

    def _orphan(self, scenario, limit):
        started = time.monotonic()
        proc, receipt = self.run_build(scenario, extra=["--timeout", "60"], timeout=25)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertLess(elapsed, limit, scenario)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "no-change")
        self.assertLess(data["agent_seconds"], limit)
        beat = self.wait_worktree_file("orphan.heartbeat", seconds=2)
        self.assert_quiet(beat)
        return data

    def test_orphan_ignore_child_is_reaped(self):
        self._orphan("orphan-ignore-child", 20)

    def test_orphan_background_does_not_block(self):
        self._orphan("orphan-background", 12)

    def test_orphan_grandchild_is_reaped(self):
        self._orphan("orphan-grandchild", 20)

    def test_leader_dead_orphan_does_not_sit_out_the_timeout(self):
        data = self._orphan("orphan-ignore-child", 20)
        self.assertLess(data["agent_seconds"], 20)

    def test_reap_writes_aborted_and_leaves_a_live_pid(self):
        stale = self.repo / "pipelines" / "dogfood" / "build-local" / "killed-run"
        stale.mkdir(parents=True)
        sleeper = subprocess.Popen(["sleep", "30"], start_new_session=True)
        self.addCleanup(lambda: sleeper.poll() is not None or sleeper.kill())
        pid_path = self.repo / "tmp" / "local-build.pids.json"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(
            json.dumps(
                {
                    "pid": sleeper.pid,
                    "pgid": os.getpgid(sleeper.pid),
                    "agent_pgid": os.getpgid(sleeper.pid),
                    "model": "fixture:small",
                    "ollama_root": "http://127.0.0.1:9",
                    "loaded_by_run": False,
                    "receipt_dir": str(stale),
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [str(ROOT / "pfy"), "build", "--local", "--reap", "--repo", str(self.repo)],
            cwd=self.repo,
            env=self.env("noop"),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("reaped:", proc.stdout)
        self.assertTrue(sleeper.poll() is None, "a live recorded pid was killed")
        aborted = json.loads((stale / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")
        sleeper.kill()
        sleeper.wait(timeout=5)

    def test_reap_kills_a_dead_runners_group(self):
        stale = self.repo / "pipelines" / "dogfood" / "build-local" / "dead-run"
        stale.mkdir(parents=True)
        inner_path = self.tmp / "inner.pid"
        leader = subprocess.Popen(
            ["bash", "-c", 'sleep 60 & echo $! > "%s"; wait' % inner_path],
            start_new_session=True,
        )

        def _stop_inner():
            if not inner_path.exists():
                return
            try:
                pid = int(inner_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return
            if pid > 1 and not _dead(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

        self.addCleanup(_stop_inner)
        self.addCleanup(lambda: leader.poll() is not None or leader.kill())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not inner_path.exists():
            time.sleep(0.05)
        self.assertTrue(inner_path.exists(), "inner child did not start")
        inner = int(inner_path.read_text(encoding="utf-8").strip())
        os.kill(leader.pid, signal.SIGKILL)
        leader.wait(timeout=5)
        self.assertTrue(_dead(leader.pid))
        self.assertFalse(_dead(inner))
        pid_path = self.repo / "tmp" / "local-build.pids.json"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(
            json.dumps(
                {
                    "pid": leader.pid,
                    "pgid": os.getpgid(inner),
                    "agent_pgid": os.getpgid(inner),
                    "loaded_by_run": False,
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [str(ROOT / "pfy"), "build", "--local", "--reap", "--repo", str(self.repo)],
            cwd=self.repo,
            env=self.env("noop"),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(_dead(inner), "dead runner's group was left alive")
        aborted = json.loads((stale / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")

    def test_missing_bwrap_blocks_unless_the_flag_is_set(self):
        bindir = self.tmp / "bin"
        bindir.mkdir()
        fake = bindir / "bwrap"
        fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        fake.chmod(0o755)
        hidden = str(bindir) + os.pathsep + os.environ.get("PATH", "")
        cmd, receipt = self.command("noop")
        cmd = [part for part in cmd if part != "--unsafe-no-sandbox"]
        proc = subprocess.run(
            cmd,
            cwd=self.repo,
            env=self.env("noop", PATH=hidden),
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "no-sandbox")
        self.assert_agent_did_not_start()
        cmd2, receipt2 = self.command("noop", extra=["--unsafe-no-sandbox"])
        proc2 = subprocess.run(
            cmd2,
            cwd=self.repo,
            env=self.env("noop", PATH=hidden),
            text=True,
            capture_output=True,
            timeout=40,
        )
        self.assertEqual(proc2.returncode, 1, proc2.stdout + proc2.stderr)
        data2 = self.receipt(proc2, receipt2)
        self.assertEqual(data2["sandbox"], "unsafe-no-sandbox")
        self.assertEqual(data2["reason"], "no-change")
        self.assertIn("not sandboxed", proc2.stderr or "")

    def test_unsafe_flag_does_not_disable_a_working_bwrap(self):
        if not BUILD.bwrap_works():
            self.skipTest("SKIP: bwrap-missing; confinement was not demonstrated")
        proc, receipt = self.run_build("noop", extra=["--unsafe-no-sandbox"])
        data = self.receipt(proc, receipt)
        self.assertTrue(str(data["sandbox"]).startswith("bwrap"), data["sandbox"])

    def test_os_exit_in_src_is_not_a_pass(self):
        proc, receipt = self.run_build("exit-zero")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-failed")

    def test_new_conftest_does_not_commit(self):
        proc, receipt = self.run_build("conftest-exit")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-tampered")

    def test_pytest_deselect_is_not_a_pass(self):
        tools = self.repo / "tools"
        tools.mkdir()
        (tools / "fake_pytest.py").write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "root = Path(__file__).resolve().parents[1]\n"
            "sys.path.insert(0, str(root))\n"
            "ini = root / 'pytest.ini'\n"
            "text = ini.read_text(encoding='utf-8') if ini.is_file() else ''\n"
            "if '--deselect' in text:\n"
            "    print('1 deselected, 1 passed in 0.01s')\n"
            "    raise SystemExit(0)\n"
            "from src.calc import add\n"
            "failed = 1 if add(1, 1) != 2 else 0\n"
            "if failed:\n"
            "    print('1 failed, 1 passed in 0.01s')\n"
            "    raise SystemExit(1)\n"
            "print('2 passed in 0.01s')\n",
            encoding="utf-8",
        )
        self.commit_base("add a pytest-summary command")
        proc, receipt = self.run_build(
            "pytest-deselect",
            extra=["--test-cmd", "python3 tools/fake_pytest.py"],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-failed")

    def test_gitignore_star_does_not_commit(self):
        proc, receipt = self.run_build("ignore-star")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "tests-tampered")

    def test_ignored_helper_is_in_the_commit(self):
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "helper.py\n", encoding="utf-8")
        self.commit_base("ignore helper.py")
        proc, receipt = self.run_build("ignored-helper")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        shown = _git(self.repo, "show", "%s:src/helper.py" % data["commit"])
        self.assertIn("def add_impl", shown)
        calc = _git(self.repo, "show", "%s:src/calc.py" % data["commit"])
        self.assertIn("add_impl", calc)

    def test_sandboxed_tests_block_push_write_and_tcp(self):
        if not BUILD.bwrap_works():
            self.skipTest("SKIP: bwrap-missing; confinement was not demonstrated")
        main = self.tmp / "main-checkout"
        main.mkdir()
        secret = main / "secret.txt"
        secret.write_text("SECRET\n", encoding="utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        accepted = []

        def _accept():
            sock.settimeout(1)
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                try:
                    conn, _addr = sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return
                accepted.append(1)
                conn.close()

        thread = threading.Thread(target=_accept, daemon=True)
        thread.start()
        self.addCleanup(sock.close)
        proc, receipt = self.run_build(
            "sandbox-attack",
            extra=["--keep-worktree"],
            env_extra={
                "PFY_STUB_ATTACK_FILE": str(secret),
                "PFY_STUB_ATTACK_PORT": str(port),
                "PFY_STUB_ATTACK_BARE": str(self.bare),
                "PFY_STUB_ATTACK_REPO": str(self.repo),
            },
            timeout=90,
        )
        sock.close()
        thread.join(timeout=2)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["tests_after"]["exit"], 0)
        self.assertEqual(secret.read_text(encoding="utf-8"), "SECRET\n")
        self.assertEqual(accepted, [])
        bare = subprocess.check_output(
            ["git", "--git-dir", str(self.bare), "rev-parse", "refs/heads/main"],
            text=True,
        ).strip()
        self.assertEqual(bare, self.refs0.split()[0] if self.refs0.strip() else bare)
        self.assertEqual(
            subprocess.check_output(["git", "ls-remote", str(self.bare)], text=True),
            self.refs0,
        )
        self.assertNotIn("pwned", _git(self.repo, "branch", "--list"))
        result = (Path(data["worktree"]) / "tmp" / "attack-result.txt").read_text(encoding="utf-8")
        self.assertIn("tcp=fail", result)
        self.assertIn("ext=fail", result)
        self.assertIn("write=fail", result)
        self.assertIn("push=fail", result)
        self.assertIn("branch=fail", result)

    def test_setsid_daemon_cannot_rewrite_after_the_gate(self):
        if not BUILD.bwrap_works():
            self.skipTest("SKIP: bwrap-missing; confinement was not demonstrated")
        started = time.monotonic()
        proc, receipt = self.run_build("late-rewrite", extra=["--keep-worktree"], timeout=40)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertLess(elapsed, 20, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        shown = _git(self.repo, "show", "%s:src/calc.py" % data["commit"])
        self.assertIn("return a + b\n", shown)
        self.assertNotIn("return 0", shown)
        work = Path(data["worktree"])
        beat = work / "tmp" / "daemon.heartbeat"
        self.assertTrue(beat.is_file(), proc.stdout + proc.stderr)
        self.assert_quiet(beat)
        self.assertFalse((work / "tmp" / "daemon-rewrote").exists())
        self.assertIn("return a + b", (work / "src" / "calc.py").read_text(encoding="utf-8"))

    def test_sigkill_of_pfy_kills_the_sandbox_and_reap_writes_aborted(self):
        if not BUILD.bwrap_works():
            self.skipTest("SKIP: bwrap-missing; confinement was not demonstrated")
        receipt = self.tmp / "custom-receipt"
        cmd, _ignored = self.command("hang", extra=["--timeout", "60", "--receipt-dir", str(receipt)])
        proc = subprocess.Popen(
            cmd,
            cwd=self.repo,
            env=self.env("hang"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        beat = None
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline and beat is None:
                if proc.poll() is not None:
                    break
                beat = self.wait_worktree_file("orphan-child.heartbeat", seconds=0.3)
            out = err = ""
            self.assertIsNotNone(beat, "sandbox child did not heartbeat")
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
            self.assert_quiet(beat)
        finally:
            if proc.poll() is None:
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        reap = subprocess.run(
            [str(ROOT / "pfy"), "build", "--local", "--reap", "--repo", str(self.repo)],
            cwd=self.repo,
            env=self.env("noop"),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(reap.returncode, 0, reap.stdout + reap.stderr)
        aborted = json.loads((receipt / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")

    def test_missing_runtime_dir_is_not_reported_as_missing_bwrap(self):
        # Do not add --unsafe-no-sandbox. That flag skips the bridge, so the
        # runtime-dir guard would never run on a host without bwrap.
        missing = self.tmp / "no-such-runtime"
        proc, receipt = self.run_build(
            "fix",
            env_extra={"XDG_RUNTIME_DIR": str(missing)},
            auto_unsafe=False,
        )
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "no-runtime-dir")
        self.assertNotIn("no-sandbox", data["reason"])
        self.assert_agent_did_not_start()
        self.assertIn("runtime dir", (proc.stderr or "").lower())

    def test_runtime_dir_under_system_tmp_is_blocked(self):
        proc, receipt = self.run_build(
            "fix",
            env_extra={"XDG_RUNTIME_DIR": "/tmp"},
            auto_unsafe=False,
        )
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        data = self.receipt(proc, receipt)
        self.assertEqual(data["reason"], "runtime-dir-in-tmp")
        self.assert_agent_did_not_start()
        self.assertIn("/tmp", proc.stderr or "")


class CloudBuildUnchangedTests(unittest.TestCase):
    def test_help_and_dry_run_stay_the_same(self):
        if shutil.which("grok") is None:
            self.skipTest("SKIP: grok-missing")
        env = os.environ.copy()
        env["TMPDIR"] = str(ROOT / "tmp" / "scratch")
        receipt_root = ROOT / "pipelines" / "dogfood" / "build"
        before = {path.name for path in receipt_root.iterdir()} if receipt_root.is_dir() else set()
        try:
            help_proc = subprocess.run(
                [str(ROOT / "pfy"), "build", "--help"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(help_proc.returncode, 0, help_proc.stderr)
            help_text = help_proc.stdout or ""
            self.assertIn("usage: pfy build", help_text)
            self.assertIn("--dry-run", help_text)
            self.assertIn("--prompt-file", help_text)
            self.assertIn("-p, --prompt", help_text)
            dry = subprocess.run(
                [str(ROOT / "pfy"), "build", "-p", "x", "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
            self.assertIn("dry-run", dry.stdout)
            self.assertIn("READY", dry.stdout)
            self.assertIn("receipt:", dry.stdout)
        finally:
            if receipt_root.is_dir():
                for child in list(receipt_root.iterdir()):
                    if child.name not in before:
                        if child.is_dir():
                            shutil.rmtree(child, ignore_errors=True)
                        else:
                            child.unlink(missing_ok=True)
        after = {path.name for path in receipt_root.iterdir()} if receipt_root.is_dir() else set()
        self.assertEqual(after, before)

    def test_real_opencode_accepts_the_flags_we_pass(self):
        binary = shutil.which("opencode")
        if not binary:
            self.skipTest("SKIP: opencode-missing")
        version = subprocess.run([binary, "--version"], text=True, capture_output=True, timeout=20)
        self.assertEqual(version.returncode, 0)
        self.assertTrue((version.stdout or version.stderr).strip())
        help_proc = subprocess.run([binary, "run", "--help"], text=True, capture_output=True, timeout=20)
        text = (help_proc.stdout or "") + (help_proc.stderr or "")
        self.assertIn("--pure", text)
        self.assertIn("--model", text)
        self.assertIn("--variant", text)


class GateTests(unittest.TestCase):
    def test_password_colon_is_redacted(self):
        masked = BUILD.redact("password: x")
        self.assertEqual(masked, "password:***")
        self.assertNotIn("x", masked.split(":", 1)[-1])
        passwd = BUILD.redact("passwd=hunter2")
        self.assertNotIn("hunter2", passwd)
        basic = BUILD.redact("Authorization: Basic dXNlcjpwYXNzMTIz")
        self.assertNotIn("dXNlcjpwYXNzMTIz", basic)
        self.assertIn("Basic", basic)
        akia = BUILD.redact("key AKIAIOSFODNN7EXAMPLE end")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", akia)
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJB\n-----END RSA PRIVATE KEY-----"
        hidden = BUILD.redact(pem)
        self.assertNotIn("MIIBogIBAAJB", hidden)
        self.assertIn("redacted-private-key", hidden)

    def test_protected_matches_dot_directories_and_dot_slash(self):
        self.assertTrue(BUILD._protected(".github/workflows/ci.yml", [".github/*"]))
        self.assertTrue(BUILD._protected("./tests/test_calc.py", ["./tests/*"]))
        self.assertTrue(BUILD._protected("./tests/test_calc.py", ["tests/*"]))
        self.assertFalse(BUILD._protected("src/calc.py", [".github/*"]))

    def test_a_new_skip_or_xfail_is_not_a_pass(self):
        before = {
            "started": True,
            "exit": 1,
            "counts": {"ran": 2, "failed": 1, "errors": 0, "skipped": 0, "xfailed": 0, "passed": 1},
        }
        skipped = {
            "started": True,
            "exit": 0,
            "counts": {"ran": 2, "failed": 0, "errors": 0, "skipped": 1, "xfailed": 0, "passed": 1},
        }
        self.assertEqual(BUILD.judge_tests(before, skipped), "tests-failed")
        xfailed = {
            "started": True,
            "exit": 0,
            "counts": {"ran": 2, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 1, "passed": 1},
        }
        self.assertEqual(BUILD.judge_tests(before, xfailed), "tests-failed")

    def test_exit_without_a_summary_and_pytest_counts_fail_closed(self):
        before = {
            "started": True,
            "exit": 1,
            "counts": {
                "ran": 2,
                "passed": 1,
                "failed": 1,
                "errors": 0,
                "skipped": 0,
                "xfailed": 0,
                "deselected": 0,
            },
        }
        quiet = {"started": True, "exit": 0, "counts": None}
        self.assertEqual(BUILD.judge_tests(before, quiet), "tests-failed")
        deselected = {
            "started": True,
            "exit": 0,
            "counts": {
                "ran": 1,
                "passed": 1,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "xfailed": 0,
                "deselected": 1,
            },
        }
        self.assertEqual(BUILD.judge_tests(before, deselected), "tests-failed")
        failed = BUILD.parse_test_counts("1 failed, 1 passed in 0.02s\n")
        self.assertEqual(failed["failed"], 1)
        self.assertEqual(failed["passed"], 1)
        summary = BUILD.parse_test_counts("===== 1 deselected, 1 passed in 0.01s =====\n")
        self.assertEqual(summary["deselected"], 1)
        self.assertEqual(summary["passed"], 1)
        xml = BUILD.parse_test_counts(
            '<testsuite name="pytest" tests="2" failures="0" errors="0" skipped="1"></testsuite>\n'
        )
        self.assertEqual(xml["skipped"], 1)
        self.assertEqual(xml["passed"], 1)
        uni = BUILD.parse_test_counts("Ran 2 tests in 0.01s\nOK\n")
        self.assertEqual(uni["ran"], 2)
        self.assertEqual(uni["passed"], 2)
        self.assertEqual(uni["deselected"], 0)

    def test_new_gate_files_anywhere_are_tampered(self):
        root = SCRATCH / "gate-files"
        if root.exists():
            shutil.rmtree(root)
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_calc.py").write_text("x\n", encoding="utf-8")
        (root / ".gitignore").write_text("tmp/\n", encoding="utf-8")
        snap = BUILD.snapshot_tests(root, "python3 -m pytest -q")
        self.assertIn(".gitignore", snap)
        names = [
            "conftest.py",
            "pytest.ini",
            "tox.ini",
            "setup.cfg",
            "pyproject.toml",
            "sitecustomize.py",
            "usercustomize.py",
            ".gitattributes",
        ]
        for name in names:
            path = root / "pkg" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("cheat\n", encoding="utf-8")
            bad = BUILD.tests_tampered(root, snap, [])
            self.assertIn("pkg/" + name, [item.replace("\\", "/") for item in bad], name)
            path.unlink()
        (root / ".gitignore").write_text("*\n", encoding="utf-8")
        bad = BUILD.tests_tampered(root, snap, [])
        self.assertIn(".gitignore", bad)
        shutil.rmtree(root, ignore_errors=True)


class SandboxEscapeTests(unittest.TestCase):
    def setUp(self):
        if not BUILD.bwrap_works():
            self.skipTest("SKIP: bwrap-missing; confinement was not demonstrated on this box")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix="sandbox-", dir=SCRATCH))
        self.main = self.base / "main"
        self.main.mkdir()
        self.secret = self.main / "secret.txt"
        self.secret.write_text("SECRET\n", encoding="utf-8")
        self.bare = self.base / "origin.git"
        self.work = self.base / "work"
        self.work.mkdir()
        subprocess.check_call(["git", "init", "--bare", "-b", "main", str(self.bare)], stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "-C", str(self.work), "init", "-b", "main"], stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "-C", str(self.work), "config", "user.email", "test@example.com"])
        subprocess.check_call(["git", "-C", str(self.work), "config", "user.name", "test"])
        (self.work / "README").write_text("one\n", encoding="utf-8")
        subprocess.check_call(["git", "-C", str(self.work), "add", "README"])
        subprocess.check_call(["git", "-C", str(self.work), "commit", "-m", "one"], stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "-C", str(self.work), "remote", "add", "origin", str(self.bare)])
        subprocess.check_call(["git", "-C", str(self.work), "push", "origin", "HEAD:main"], stdout=subprocess.DEVNULL)
        (self.work / "README").write_text("two\n", encoding="utf-8")
        subprocess.check_call(["git", "-C", str(self.work), "add", "README"])
        subprocess.check_call(["git", "-C", str(self.work), "commit", "-m", "two"], stdout=subprocess.DEVNULL)
        self.bare_sha = subprocess.check_output(
            ["git", "--git-dir", str(self.bare), "rev-parse", "refs/heads/main"],
            text=True,
        ).strip()
        self.hide = [str(self.base)]
        self.addCleanup(shutil.rmtree, self.base, True)

    def _bare_sha(self):
        return subprocess.check_output(
            ["git", "--git-dir", str(self.bare), "rev-parse", "refs/heads/main"],
            text=True,
        ).strip()

    def test_push_forms_and_secret_write_do_not_leak(self):
        bare = str(self.bare)
        forms = [
            ["git", "-c", "remote.origin.url=" + bare, "-c", "remote.origin.pushurl=" + bare, "push", "origin", "HEAD"],
            ["/usr/bin/git", "-c", "remote.origin.url=" + bare, "push", "origin", "HEAD"],
            ["sh", "-c", "git -c remote.origin.url=%s push origin HEAD" % bare],
            ["env", "git", "-c", "remote.origin.url=" + bare, "push", "origin", "HEAD"],
            [
                "python3",
                "-c",
                "import subprocess,sys; r=subprocess.run(['git','-c','remote.origin.url=%s','push','origin','HEAD']); sys.exit(r.returncode)"
                % bare,
            ],
        ]
        for form in forms:
            BUILD.run_sandboxed(form, self.work, hide=self.hide, timeout=30)
            self.assertEqual(self._bare_sha(), self.bare_sha, form)
            self.assertEqual(self.secret.read_text(encoding="utf-8"), "SECRET\n")
        writer = [
            "python3",
            "-c",
            "p=%r\nopen(p,'w').write('PWNED\\n')\nprint('WROTE')" % str(self.secret),
        ]
        BUILD.run_sandboxed(writer, self.work, hide=self.hide, timeout=20)
        self.assertEqual(self.secret.read_text(encoding="utf-8"), "SECRET\n")

    def test_unshare_net_cannot_reach_a_host_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        accepted = []

        def _accept():
            try:
                sock.settimeout(3)
                conn, _addr = sock.accept()
                accepted.append(1)
                conn.close()
            except OSError:
                pass

        thread = threading.Thread(target=_accept)
        thread.start()
        self.addCleanup(sock.close)
        proc = BUILD.run_sandboxed(
            [
                "python3",
                "-c",
                "import socket,sys; s=socket.create_connection(('127.0.0.1', %d), 2); sys.exit(0)" % port,
            ],
            self.work,
            hide=self.hide,
            timeout=20,
        )
        thread.join(timeout=5)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(accepted, [])

    def test_loopback_bridge_reaches_the_local_endpoint(self):
        httpd = _serve(tags=[{"name": "fixture:small", "size": 10}])
        self.addCleanup(httpd.shutdown)
        self.addCleanup(httpd.server_close)
        port = httpd.server_address[1]
        proc = BUILD.run_sandboxed(
            [
                "python3",
                "-c",
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:%d/api/tags', timeout=5).read().decode())"
                % port,
            ],
            self.work,
            hide=self.hide,
            endpoint="http://127.0.0.1:%d/v1" % port,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("fixture:small", proc.stdout)

    def test_worktree_socket_is_used_when_the_runtime_dir_is_missing(self):
        real = BUILD._runtime_dir

        def missing():
            raise BUILD.SandboxUnavailable("runtime dir is missing", reason="no-runtime-dir")

        BUILD._runtime_dir = missing
        saved = os.environ.pop("XDG_RUNTIME_DIR", None)
        short = _direct_socket_dir()
        try:
            # Longer than sun_path no matter how short the checkout is.
            long = Path("/" + ("n" * 120) + "/work")
            with self.assertRaises(BUILD.SandboxUnavailable) as raised:
                BUILD._socket_link(long)
            self.assertEqual(raised.exception.reason, "no-runtime-dir")
            self.assertLess(len(str(short / "tmp" / "ollama.sock")), 108)
            if short.exists():
                shutil.rmtree(short)
            short.mkdir(parents=True)
            httpd = _serve(tags=[{"name": "fixture:small", "size": 10}])
            self.addCleanup(httpd.shutdown)
            self.addCleanup(httpd.server_close)
            port = httpd.server_address[1]
            proc = BUILD.run_sandboxed(
                [
                    "python3",
                    "-c",
                    "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:%d/api/tags', timeout=5).read().decode())"
                    % port,
                ],
                short,
                hide=self.hide,
                endpoint="http://127.0.0.1:%d/v1" % port,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("fixture:small", proc.stdout)
        finally:
            BUILD._runtime_dir = real
            if saved is not None:
                os.environ["XDG_RUNTIME_DIR"] = saved
            shutil.rmtree(short, ignore_errors=True)
            if short.parent == ROOT / "tmp" / "s":
                shutil.rmtree(short.parent, ignore_errors=True)

    def test_loopback_bridge_waits_for_a_slow_upstream(self):
        # The connect timeout must not abort a response that has not started.
        # A model load is quiet for longer than that handshake.
        port_box = []

        def serve():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 0))
            srv.listen(1)
            port_box.append(srv.getsockname()[1])
            srv.settimeout(15)
            try:
                conn, _addr = srv.accept()
            except OSError:
                srv.close()
                return
            time.sleep(4)
            try:
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\nConnection: close\r\n\r\nSLOWOK"
                )
            except OSError:
                pass
            conn.close()
            srv.close()

        thread = threading.Thread(target=serve)
        thread.start()
        self.addCleanup(lambda: thread.join(timeout=2))
        deadline = time.monotonic() + 5
        while not port_box and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(port_box, "slow upstream did not bind")
        port = port_box[0]
        proc = BUILD.run_sandboxed(
            [
                "python3",
                "-c",
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:%d/slow', timeout=12).read().decode())"
                % port,
            ],
            self.work,
            hide=self.hide,
            endpoint="http://127.0.0.1:%d/v1" % port,
            timeout=20,
        )
        thread.join(timeout=16)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SLOWOK", proc.stdout)

    def test_host_pid_is_not_killed_from_inside(self):
        sleeper = subprocess.Popen(["sleep", "30"], start_new_session=True)
        self.addCleanup(lambda: sleeper.poll() is not None or sleeper.kill())
        proc = BUILD.run_sandboxed(
            [
                "python3",
                "-c",
                "import os,sys\n"
                "pid=int(sys.argv[1])\n"
                "visible=os.path.exists('/proc/%d' % pid)\n"
                "err=''\n"
                "try:\n"
                "    os.kill(pid, 9)\n"
                "except OSError as exc:\n"
                "    err=type(exc).__name__\n"
                "print('visible', int(visible))\n"
                "print('err', err)\n",
                str(sleeper.pid),
            ],
            self.work,
            hide=self.hide,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIsNone(sleeper.poll(), "host sleep was killed")
        self.assertIn("visible 0", proc.stdout)
        self.assertIn("ProcessLookupError", proc.stdout)
        sleeper.kill()
        sleeper.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
