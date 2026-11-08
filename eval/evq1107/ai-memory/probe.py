#!/usr/bin/env python3
"""Offline probe: pasted-note recall and claim-once handoffs.

Runs the pinned ai-memory binary against a loopback server. Embeddings stay
off. HOME and the data dir stay under the cache or a temp dir. Never calls
setup, install, run, or hook registration. Never reads token files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = Path(__file__).resolve().parent / "results.json"
EXPECT_VERSION = "3.1.1"
TAG = "v3.1.1"
COMMIT = "52020da90131a5afea70a114a01e44a8e67b44f3"
TARBALL_SHA256 = "d055aef2989eeceb08da7a2db3533d9389a689058c57b5f8a03d5f4439225a2d"
BINARY_SHA256 = "be9f539cbaaa8c583dd94a58c3817c35321f3d887e8195df91bf74f9c5eefa4b"
N = 8
HEALTH_TIMEOUT = 20.0
CLI_TIMEOUT = 30.0

REPO_NEEDLES = (
    "second_pop_empty",
    "catalog_hold_70_75",
    "52020da90131",
    "be9f539cbaaa8c583dd94a58c3817c35321f3d887e8195df91bf74f9c5eefa4b",
    "d055aef2989eeceb08da7a2db3533d9389a689058c57b5f8a03d5f4439225a2d",
    "AI_MEMORY_EMBEDDING_PROVIDER",
    "OPENCONTEXT_CONTEXTS_ROOT",
    "integration_stage",
)
OVERLAP_WORDS = ("memory", "handoff", "handoffs", "context", "wiki", "claim", "rag")
NAMED_CARDS = (
    "skill-up.json",
    "harness2.json",
    "harness-score.json",
    "eval-harness-pfy.json",
    "neatroots.json",
    "codebase-memory-mcp.json",
    "opencode-mem.json",
    "mempalace.json",
    "memvid.json",
    "opencontext.json",
    "leann.json",
    "hermes-agent-feedback-loops.json",
    "robrain.json",
    "agent-beacon.json",
    "repowise.json",
    "graphify.json",
    "chroma-or-lancedb.json",
)
FORBIDDEN = {
    "setup",
    "run",
    "bootstrap",
    "embed",
    "llm-test",
    "install-hooks",
    "install-mcp",
    "install-skills",
    "install-instructions",
    "generate-auth-token",
    "setup-agent",
    "uninstall",
}
SENSITIVE_NAME = re.compile(r"(?i)token|secret|credential|auth")
LONG_HEX = re.compile(r"\b[a-fA-F0-9]{32,}\b")
BEARER = re.compile(r"(?i)bearer|api[_-]?key")
WORD = re.compile(r"[a-z0-9]+")
WATCH_DIRS = (
    ".local/share/ai-memory",
    ".config/ai-memory",
    ".local/bin/ai-memory",
)


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def cache_base() -> Path:
    return real_home() / ".cache" / "pfy" / "tools" / "ai-memory"


def novel_tokens() -> list[str]:
    return ["AIM1107_HANDOFF_%02d" % i for i in range(1, N + 1)]


def nonsense_tokens() -> list[str]:
    return ["AIM1107_NO_SUCH_%02d" % i for i in range(1, N + 1)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def allowed_path(path: Path, tmp: Path) -> bool:
    resolved = path.resolve()
    if under(resolved, cache_base()):
        return True
    if under(resolved, tmp.resolve()):
        return True
    if under(resolved, (ROOT / "tmp").resolve()):
        return True
    try:
        system_tmp = Path(os.environ.get("TMPDIR", "/tmp")).resolve()
    except OSError:
        system_tmp = Path("/tmp")
    return under(resolved, system_tmp)


def ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 1)


def fingerprint(root: Path) -> list[dict]:
    rows = []
    for rel in WATCH_DIRS:
        path = root / rel
        if not path.exists() and not path.is_symlink():
            rows.append({"rel": rel, "exists": False})
            continue
        stat = path.lstat()
        rows.append(
            {
                "rel": rel,
                "exists": True,
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "mode": stat.st_mode,
            }
        )
    return rows


def parse_json(text: str):
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def command_name(args: list[str]) -> str:
    if not args:
        return ""
    if args[0] == "message" and len(args) > 1:
        return "message " + args[1]
    return args[0]


def sensitive_files(root: Path) -> list[str]:
    found = []
    if not root.exists():
        return found
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(SENSITIVE_NAME.search(part) for part in rel.parts):
            found.append(rel.as_posix())
    return sorted(found)


def file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def tree_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def wiki_mark_count(wiki: Path, marks: list[str]) -> int:
    if not wiki.is_dir():
        return 0
    count = 0
    for path in wiki.rglob("*.md"):
        rel = path.relative_to(wiki)
        if ".git" in rel.parts or any(SENSITIVE_NAME.search(part) for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(mark in text for mark in marks):
            count += 1
    return count


def git_stats(wiki: Path) -> dict:
    if not (wiki / ".git").exists():
        return {"commits": None, "tracked": 0, "sensitive_tracked": 0}
    try:
        commits = subprocess.run(
            ["git", "-C", str(wiki), "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        listed = subprocess.run(
            ["git", "-C", str(wiki), "ls-files"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"commits": None, "tracked": 0, "sensitive_tracked": 0}
    names = [line for line in listed.stdout.splitlines() if line]
    sensitive = [
        name for name in names if any(SENSITIVE_NAME.search(part) for part in Path(name).parts)
    ]
    count = None
    if commits.returncode == 0 and commits.stdout.strip().isdigit():
        count = int(commits.stdout.strip())
    return {
        "commits": count,
        "tracked": len(names),
        "sensitive_tracked": len(sensitive),
    }


def catalog_view(stages: Path) -> dict:
    words_hit = []
    named = []
    if stages.is_dir():
        for path in sorted(stages.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                card = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            parts: list[str] = []
            for key in ("uses", "features", "tags", "catalog_tags"):
                value = card.get(key)
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, list):
                    parts.extend(str(item) for item in value)
            blob = " ".join(parts).lower()
            found = []
            tokens = set(WORD.findall(blob))
            for word in OVERLAP_WORDS:
                if word in tokens:
                    found.append(word)
            if found:
                words_hit.append(
                    {
                        "name": card.get("name") or path.stem,
                        "stage": card.get("integration_stage"),
                        "file": path.name,
                        "words": found,
                    }
                )
        for name in NAMED_CARDS:
            path = stages / name
            if not path.is_file():
                named.append({"file": name, "present": False})
                continue
            try:
                card = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                named.append({"file": name, "present": False})
                continue
            uses = card.get("uses")
            named.append(
                {
                    "file": name,
                    "present": True,
                    "name": card.get("name"),
                    "stage": card.get("integration_stage"),
                    "uses": uses if isinstance(uses, str) else "",
                }
            )
    return {
        "word_matches": words_hit,
        "named": named,
        "cass_memory_card": (stages / "cass-memory.json").is_file(),
        "cass_memory_entry": (ROOT / "sources" / "entries" / "108-cass-memory.md").is_file(),
    }


def scrub(value, allow: set[str]):
    if isinstance(value, str):
        if BEARER.search(value):
            return "[redacted]"

        def repl(match: re.Match) -> str:
            token = match.group(0)
            if token.lower() in allow or token in allow:
                return token
            return "[hex]"

        return LONG_HEX.sub(repl, value)
    if isinstance(value, list):
        return [scrub(item, allow) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item, allow) for key, item in value.items()}
    return value


def rg_hit(rg: str, repo: Path, needle: str) -> bool:
    proc = subprocess.run(
        [
            rg,
            "-l",
            "-F",
            "--glob",
            "!.git/**",
            "--glob",
            "!eval/evq1107/ai-memory/**",
            needle,
            str(repo),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.home = Path(args.home)
        self.tmp = Path(args.tmp)
        self.data = Path(args.data_dir)
        self.work = Path(args.work)
        self.bin = Path(args.bin)
        self.env = self._env()
        self.commands: list[str] = []
        self.servers: list[subprocess.Popen] = []
        self.timings: dict[str, float] = {}

    def _env(self) -> dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(Path(self.args.xdg_config)),
            "XDG_CACHE_HOME": str(Path(self.args.xdg_cache)),
            "XDG_DATA_HOME": str(Path(self.args.xdg_data)),
            "TMPDIR": str(self.tmp),
            "NO_COLOR": "1",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "AI_MEMORY_EMBEDDING_PROVIDER": "none",
            "GIT_AUTHOR_NAME": "evq-probe",
            "GIT_AUTHOR_EMAIL": "evq-probe@localhost",
            "GIT_COMMITTER_NAME": "evq-probe",
            "GIT_COMMITTER_EMAIL": "evq-probe@localhost",
        }
        for key in ("AIM_MODE", "AIM_LOG"):
            if os.environ.get(key):
                env[key] = os.environ[key]
        return env

    def prepare_dirs(self) -> None:
        for path in (
            self.home,
            self.tmp,
            Path(self.args.xdg_config),
            Path(self.args.xdg_cache),
            Path(self.args.xdg_data),
        ):
            path.mkdir(parents=True, exist_ok=True)
        for path in (self.data, self.work):
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
        (self.work / "srcproj").mkdir()
        (self.work / "inboxproj").mkdir()

    def stop_servers(self) -> None:
        for proc in self.servers:
            if proc.poll() is not None:
                continue
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(5)

    def cli(self, args: list[str], cwd: Path) -> dict:
        name = command_name(args)
        self.commands.append(name)
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(self.bin), "--data-dir", str(self.data), *args],
                cwd=cwd,
                env=self.env,
                text=True,
                capture_output=True,
                timeout=CLI_TIMEOUT,
            )
            return {
                "rc": proc.returncode,
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "ms": ms(start),
            }
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            err = exc.stderr or ""
            if isinstance(out, bytes):
                out = out.decode("utf-8", "replace")
            if isinstance(err, bytes):
                err = err.decode("utf-8", "replace")
            return {"rc": 124, "stdout": out, "stderr": err, "ms": ms(start)}

    def start_server(self) -> tuple[bool, float]:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        url = "http://127.0.0.1:%d" % port
        self.env["AI_MEMORY_SERVER_URL"] = url
        log_path = self.work / "serve.log"
        log = log_path.open("a", encoding="utf-8")
        start = time.perf_counter()
        proc = subprocess.Popen(
            [
                str(self.bin),
                "--data-dir",
                str(self.data),
                "serve",
                "--transport",
                "http",
                "--bind",
                "127.0.0.1:%d" % port,
                "--no-watcher",
            ],
            cwd=self.work,
            env=self.env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.commands.append("serve")
        self.servers.append(proc)
        healthy = False
        deadline = time.monotonic() + float(self.args.health_timeout)
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(url + "/healthz", timeout=0.5) as resp:
                    if resp.status == 200:
                        healthy = True
                        break
            except Exception:
                time.sleep(0.05)
        log.close()
        return healthy, ms(start)

    def search(self, query: str, cwd: Path, global_search: bool = False) -> dict:
        args = ["search", "--json"]
        if global_search:
            args.append("--global")
        args.append(query)
        result = self.cli(args, cwd)
        parsed = parse_json(result["stdout"])
        hit = False
        error = True
        if isinstance(parsed, list):
            hit = len(parsed) > 0
            error = False
        elif isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
            hit = len(parsed["results"]) > 0
            error = False
        result["hit"] = hit
        result["error"] = error
        return result

    def send(self, body: str) -> dict:
        return self.cli(
            [
                "message",
                "send",
                "--to-workspace",
                "default",
                "--to-project",
                "inboxproj",
                "--subject",
                "handoff",
                "--json",
                body,
            ],
            self.work / "srcproj",
        )

    def pop(self) -> dict:
        result = self.cli(["message", "pop", "--json"], self.work / "inboxproj")
        parsed, error = None, True
        data = parse_json(result["stdout"])
        if isinstance(data, dict) and "message" in data:
            parsed = data
            error = False
        result["parsed"] = parsed
        result["error"] = error
        return result


def empty_counts() -> dict:
    return {
        "novel_hits": 0,
        "novel_n": N,
        "nonsense_misses": 0,
        "nonsense_n": N,
        "search_miss_ok": False,
        "search_errors": 0,
        "repo_search_hits": 0,
        "repo_n": N,
        "read_back_ok": False,
        "rg_repo_hits": None,
        "rg_novel_hits": None,
        "rg_skipped": True,
        "unseen_send_rc": None,
        "unseen_send_said_404": False,
        "send_recovered": False,
        "sends_ok": 0,
        "claims": 0,
        "unique_claims": 0,
        "duplicate_claims": 0,
        "states_claimed": 0,
        "ninth_empty": False,
        "notices": 0,
        "notices_say_untrusted": 0,
        "untrusted_ok": False,
        "claim_once_ok": False,
        "restart_hits": 0,
        "restart_agreement": 0,
        "scoped_cross_hits": 0,
        "global_cross_hits": 0,
        "wiki_files_with_mark": 0,
        "write_ok": 0,
        "h1_graded_cases": 0,
        "score_delta": None,
    }


def run_probe(args: argparse.Namespace) -> dict:
    runner = Runner(args)
    home_before = None if args.skip_home else fingerprint(real_home())
    runner.prepare_dirs()
    pin = pin_block(args, runner.bin)
    started = time.perf_counter()
    try:
        init = runner.cli(["init"], runner.work)
        runner.timings["init_ms"] = init["ms"]
        healthy, health_ms = runner.start_server()
        runner.timings["health_ms"] = health_ms
        doc = {
            "pin": pin,
            "embedding_provider": "none",
            "server_healthy": healthy,
            "skipped": not healthy,
            "skip_reason": "" if healthy else "healthz not ready",
            "init_rc": init["rc"],
            "commands": runner.commands,
            "forbidden_commands_called": sorted(
                name for name in runner.commands if name in FORBIDDEN or name.split()[0] in FORBIDDEN
            ),
            "sensitive_filenames": sensitive_files(runner.data),
            "home_before": home_before,
            "timings_ms": runner.timings,
        }
        doc.update(empty_counts())
        if not healthy:
            return finish(runner, doc, started, args)
        return finish(runner, live(runner, doc, args), started, args)
    finally:
        runner.stop_servers()


def pin_block(args: argparse.Namespace, binary: Path) -> dict:
    digest = None
    match = None
    size = None
    if binary.is_file() and not args.skip_sha:
        digest = sha256_file(binary)
        match = digest == BINARY_SHA256
        size = binary.stat().st_size
    version = ""
    if binary.is_file():
        proc = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(args.home),
                "TMPDIR": str(args.tmp),
                "NO_COLOR": "1",
                "AI_MEMORY_EMBEDDING_PROVIDER": "none",
            },
        )
        version = (proc.stdout or proc.stderr or "").strip().splitlines()[:1]
        version = version[0] if version else ""
    text_ok = version == "ai-memory " + EXPECT_VERSION or version == EXPECT_VERSION
    return {
        "version_text": version,
        "version_ok": text_ok,
        "expect_version": EXPECT_VERSION,
        "tag": TAG,
        "commit": COMMIT,
        "tarball_sha256": TARBALL_SHA256,
        "binary_sha256": BINARY_SHA256,
        "binary_sha256_computed": digest,
        "binary_sha256_match": match,
        "binary_bytes": size,
        "tarball_uncompressed_bytes": 48284491,
    }


def live(runner: Runner, doc: dict, args: argparse.Namespace) -> dict:
    tokens = novel_tokens()
    src = runner.work / "srcproj"
    inbox = runner.work / "inboxproj"
    write_ok = 0
    write_started = time.perf_counter()
    for index, token in enumerate(tokens, start=1):
        body = "# Note %d\n\n%s\n" % (index, token)
        result = runner.cli(
            [
                "write-page",
                "--path",
                "notes/h%02d.md" % index,
                "--kind",
                "gotcha",
                "--body",
                body,
            ],
            src,
        )
        if result["rc"] == 0:
            write_ok += 1
    runner.timings["write_ms"] = ms(write_started)
    doc["write_ok"] = write_ok

    search_started = time.perf_counter()
    novel_hits = 0
    errors = 0
    for token in tokens:
        found = runner.search(token, src)
        errors += int(found["error"])
        novel_hits += int(found["hit"] and not found["error"])
    runner.timings["search_novel_ms"] = ms(search_started)

    miss_started = time.perf_counter()
    nonsense_misses = 0
    miss_errors = 0
    for token in nonsense_tokens():
        found = runner.search(token, src)
        errors += int(found["error"])
        miss_errors += int(found["error"])
        if not found["error"] and not found["hit"]:
            nonsense_misses += 1
    runner.timings["search_miss_ms"] = ms(miss_started)
    search_miss_ok = nonsense_misses == N and miss_errors == 0

    repo_started = time.perf_counter()
    repo_hits = 0
    for needle in REPO_NEEDLES:
        found = runner.search(needle, src)
        errors += int(found["error"])
        repo_hits += int(found["hit"] and not found["error"])
    runner.timings["search_repo_ms"] = ms(repo_started)

    read = runner.cli(["read-page", "--path", "notes/h01.md", "--json"], src)
    read_body = parse_json(read["stdout"])
    read_ok = (
        read["rc"] == 0
        and isinstance(read_body, dict)
        and tokens[0] in str(read_body.get("body") or "")
    )

    if args.skip_rg:
        rg_repo = None
        rg_novel = None
        rg_skipped = True
        runner.timings["rg_ms"] = 0.0
    else:
        rg_started = time.perf_counter()
        rg_bin = args.rg_bin
        rg_repo = sum(1 for needle in REPO_NEEDLES if rg_hit(rg_bin, Path(args.repo), needle))
        rg_novel = sum(1 for token in tokens if rg_hit(rg_bin, Path(args.repo), token))
        rg_skipped = False
        runner.timings["rg_ms"] = ms(rg_started)

    send_started = time.perf_counter()
    unseen = runner.send(tokens[0])
    unseen_404 = "404" in (unseen["stdout"] + unseen["stderr"])
    sends_ok = 0
    if unseen["rc"] == 0:
        sends_ok += 1
        recovered = False
    seed = runner.cli(
        ["write-page", "--path", "notes/inbox.md", "--body", "# Inbox\n"],
        inbox,
    )
    if unseen["rc"] != 0 and seed["rc"] == 0:
        retried = runner.send(tokens[0])
        if retried["rc"] == 0:
            sends_ok += 1
        recovered = sends_ok == 1
    else:
        recovered = False
    for token in tokens[1:]:
        result = runner.send(token)
        if result["rc"] == 0:
            sends_ok += 1
    runner.timings["send_ms"] = ms(send_started)

    pop_started = time.perf_counter()
    pops = [runner.pop() for _ in range(N + 1)]
    runner.timings["pop_ms"] = ms(pop_started)
    bodies = []
    notices = 0
    notices_untrusted = 0
    states = 0
    pop_errors = 0
    for item in pops[:N]:
        pop_errors += int(item["error"])
        parsed = item["parsed"] or {}
        message = parsed.get("message") if isinstance(parsed, dict) else None
        if not isinstance(message, dict):
            continue
        body = message.get("body")
        if isinstance(body, str):
            bodies.append(body)
        if message.get("state") == "claimed":
            states += 1
        notice = parsed.get("security_notice") if isinstance(parsed, dict) else None
        if isinstance(notice, str) and notice.strip():
            notices += 1
            if "untrusted" in notice.lower():
                notices_untrusted += 1
    ninth = pops[-1]["parsed"] if not pops[-1]["error"] else None
    ninth_empty = isinstance(ninth, dict) and ninth.get("message") is None
    unique = len(set(bodies))
    claim_once = (
        len(bodies) == N
        and unique == N
        and set(bodies) == set(tokens)
        and ninth_empty
        and states == N
        and pop_errors == 0
    )

    cross_scoped = 0
    cross_global = 0
    for token in tokens:
        scoped = runner.search(token, inbox)
        errors += int(scoped["error"])
        cross_scoped += int(scoped["hit"] and not scoped["error"])
        broad = runner.search(token, inbox, global_search=True)
        errors += int(broad["error"])
        cross_global += int(broad["hit"] and not broad["error"])

    commit = runner.cli(["commit", "-m", "evq probe"], runner.work)
    git = git_stats(runner.data / "wiki")
    marks = wiki_mark_count(runner.data / "wiki", tokens)

    runner.stop_servers()
    restart_ok, restart_ms = runner.start_server()
    runner.timings["restart_health_ms"] = restart_ms
    restart_hits = 0
    if restart_ok:
        for token in tokens:
            found = runner.search(token, src)
            errors += int(found["error"])
            restart_hits += int(found["hit"] and not found["error"])

    doc.update(
        {
            "novel_hits": novel_hits,
            "nonsense_misses": nonsense_misses,
            "search_miss_ok": search_miss_ok,
            "search_errors": errors,
            "repo_search_hits": repo_hits,
            "read_back_ok": read_ok,
            "rg_repo_hits": rg_repo,
            "rg_novel_hits": rg_novel,
            "rg_skipped": rg_skipped,
            "unseen_send_rc": unseen["rc"],
            "unseen_send_said_404": unseen_404,
            "send_recovered": recovered and sends_ok == N,
            "sends_ok": sends_ok,
            "claims": len(bodies),
            "unique_claims": unique,
            "duplicate_claims": len(bodies) - unique,
            "states_claimed": states,
            "ninth_empty": ninth_empty,
            "notices": notices,
            "notices_say_untrusted": notices_untrusted,
            "untrusted_ok": notices == N,
            "claim_once_ok": claim_once,
            "restart_healthy": restart_ok,
            "restart_hits": restart_hits,
            "restart_agreement": restart_hits if restart_ok else 0,
            "scoped_cross_hits": cross_scoped,
            "global_cross_hits": cross_global,
            "wiki_files_with_mark": marks,
            "git": git,
            "commit_rc": commit["rc"],
            "pop_errors": pop_errors,
            "seed_rc": seed["rc"],
        }
    )
    return doc


def finish(runner: Runner, doc: dict, started: float, args: argparse.Namespace) -> dict:
    runner.timings["total_ms"] = ms(started)
    doc["timings_ms"] = dict(runner.timings)
    doc["commands"] = list(runner.commands)
    doc["forbidden_commands_called"] = sorted(
        {name for name in runner.commands if name in FORBIDDEN or name.split()[0] in FORBIDDEN}
    )
    doc["sensitive_filenames"] = sensitive_files(runner.data)
    if args.skip_home:
        doc["home_unchanged"] = None
    else:
        after = fingerprint(real_home())
        doc["home_after"] = after
        doc["home_unchanged"] = after == doc.get("home_before")
    if args.skip_catalog:
        doc["catalog"] = None
    else:
        doc["catalog"] = catalog_view(Path(args.stages))
    doc["h1_graded_cases"] = 0
    doc["score_delta"] = None
    doc["models_files"] = file_count(runner.data / "models")
    doc["data_bytes"] = tree_bytes(runner.data)
    return doc


def guard(args: argparse.Namespace) -> str | None:
    home = Path(args.home).resolve()
    data = Path(args.data_dir).resolve()
    work = Path(args.work).resolve()
    tmp = Path(args.tmp).resolve()
    real = real_home().resolve()
    cache = cache_base().resolve()
    if home == real:
        return "refusing to use the real HOME"
    for path in (data, work):
        if path == cache or path == cache / "bin":
            return "refusing to wipe the cache root"
    for path in (home, data, work, tmp):
        if not allowed_path(path, tmp) and not under(path, cache_base()):
            return "path is outside the cache and temp dirs: %s" % path
        if under(path, ROOT.resolve()) and not under(path, (ROOT / "tmp").resolve()):
            return "refusing to write inside the worktree: %s" % path
    return None


def build_parser() -> argparse.ArgumentParser:
    base = cache_base()
    parser = argparse.ArgumentParser(description="Probe ai-memory recall and claim-once handoffs.")
    parser.add_argument("--bin", default=str(base / "bin" / "ai-memory"))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--data-dir", default=str(base / "probe" / "data"))
    parser.add_argument("--work", default=str(base / "probe" / "work"))
    parser.add_argument("--home", default=str(base / "home"))
    parser.add_argument("--tmp", default=str(base / "tmp"))
    parser.add_argument("--xdg-config", default=str(base / "xdg-config"))
    parser.add_argument("--xdg-cache", default=str(base / "xdg-cache"))
    parser.add_argument("--xdg-data", default=str(base / "xdg-data"))
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--rg-bin", default="rg")
    parser.add_argument("--stages", default=str(ROOT / "data" / "stages"))
    parser.add_argument("--health-timeout", type=float, default=HEALTH_TIMEOUT)
    parser.add_argument("--skip-sha", action="store_true")
    parser.add_argument("--skip-rg", action="store_true")
    parser.add_argument("--skip-catalog", action="store_true")
    parser.add_argument("--skip-home", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    problem = guard(args)
    out_path = Path(args.out)
    if problem:
        payload = {"skipped": True, "skip_reason": problem, "h1_graded_cases": 0}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(problem)
        return 2
    doc = run_probe(args)
    allow = {
        TARBALL_SHA256,
        BINARY_SHA256,
        COMMIT,
        "52020da90131",
    }
    computed = (doc.get("pin") or {}).get("binary_sha256_computed")
    if isinstance(computed, str):
        allow.add(computed)
    for needle in REPO_NEEDLES:
        if LONG_HEX.fullmatch(needle):
            allow.add(needle)
    doc = scrub(doc, allow)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(
        "healthy=%s novel=%s/%s misses=%s/%s repo_search=%s claims=%s unique=%s ninth_empty=%s notices=%s graded=%s"
        % (
            doc.get("server_healthy"),
            doc.get("novel_hits"),
            doc.get("novel_n"),
            doc.get("nonsense_misses"),
            doc.get("nonsense_n"),
            doc.get("repo_search_hits"),
            doc.get("claims"),
            doc.get("unique_claims"),
            doc.get("ninth_empty"),
            doc.get("notices"),
            doc.get("h1_graded_cases"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
