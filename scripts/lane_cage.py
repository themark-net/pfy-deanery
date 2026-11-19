#!/usr/bin/env python3
"""Run one catalog or Build lane agent in a confined rootless podman container.

Outside code is data. A lane agent reads third-party READMEs, code and web
text, so it runs as if that text were hostile:

- Container: rootless podman, --network=none, cap-drop all, no-new-privileges,
  pids and memory caps. Only the lane worktree is writable. The git common dir
  is writable for objects and refs, but its config, hooks and info are
  read-only and other lanes' worktree metadata is read-only. The quarantine
  root (scripts/quarantine_clone.py) is mounted read-only.
- No ~/.ssh, no SSH agent, no other checkout, no real ~/.grok.
  A throwaway GROK_HOME per run has memory off and no MCP servers. The xAI
  credential is XAI_API_KEY passed by name, or the host auth.json mounted
  read-only. It is never copied, printed or logged.
- Egress: the only route out is a driver-side CONNECT proxy on a unix socket
  that allows TLS to PFY_LANE_EGRESS_ALLOW (default x.ai, grok.com). GitHub
  is not reachable, so the agent cannot push; only the driver pushes.
- Tools: --always-approve is gone. The lane gets a per-kind --tools allowlist
  with matching --allow rules, a denylist for everything else, web search off
  for eval, integrate and build lanes, no subagents, no plan mode.

  lane_cage.py grok --kind eval --wt WT --prompt FILE [--grok BIN] [--max-turns N]
  lane_cage.py exec --wt WT -- CMD...      # driver checks that run lane code: no network
  lane_cage.py grok ... --print            # print the podman argv as JSON, run nothing

Exit 2 when the cage cannot start (podman or image missing): the caller parks.
Env: PFY_PODMAN, PFY_LANE_IMAGE, PFY_LANE_EGRESS_ALLOW, PFY_LANE_PERMISSION_MODE,
PFY_LANE_GROK_AUTH, PFY_QUARANTINE_DIR, PFY_LANE_CAGE_DIR.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_IMAGE = "localhost/pfy-test:3.12"
DEFAULT_ALLOW = "x.ai,grok.com"
PROXY_PORT = 3128

EDIT_TOOLS = ("read_file", "grep", "list_dir", "search_replace", "write", "todo_write",
              "hashline_read", "hashline_grep", "hashline_edit")
SHELL_TOOLS = ("run_terminal_cmd", "run_terminal_command", "get_command_or_subagent_output",
               "kill_command_or_subagent")
READ_EDIT_TOOLS = ("read_file", "grep", "list_dir", "search_replace", "todo_write",
                   "hashline_read", "hashline_grep", "hashline_edit")
ALWAYS_DENY = ("task", "get_task_output", "kill_task", "enter_plan_mode", "exit_plan_mode", "monitor",
               "scheduler_create", "scheduler_delete", "scheduler_list", "image_gen", "image_edit",
               "image_to_video", "reference_to_video", "ask_user_question", "send_feedback",
               "search_tool", "use_tool", "Agent", "update_goal")
KIND_TOOLS = {
    "eval": EDIT_TOOLS + SHELL_TOOLS,
    "integrate": EDIT_TOOLS + SHELL_TOOLS,
    "build": EDIT_TOOLS + SHELL_TOOLS,
    # Supersede keeps web (served through x.ai) but gets no shell and no new files.
    "supersede": READ_EDIT_TOOLS,
}
WEB_KINDS = frozenset({"supersede"})

GROK_HOME_CONFIG = """# Throwaway GROK_HOME for one confined lane. Nothing persists.
[memory]
enabled = false

[ui]
permission_mode = "default"
"""


class CageError(Exception):
    pass


def allowed_host(host: str, allow: list[str]) -> bool:
    host = host.strip().lower().rstrip(".")
    if not host or any(c in host for c in "/@ ") or host.replace(".", "").isdigit():
        return False
    return any(host == a or host.endswith("." + a) for a in allow)


class EgressProxy:
    """CONNECT-only proxy on a unix socket. TLS to allowlisted hosts on 443."""

    def __init__(self, sock_path: Path, allow: list[str], log: Path):
        self.sock_path = sock_path
        self.allow = allow
        self.log = log
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(str(sock_path))
        os.chmod(sock_path, 0o600)
        self.srv.listen(64)
        self.lock = threading.Lock()

    def note(self, line: str) -> None:
        with self.lock, self.log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(30)
            head = b""
            while b"\r\n\r\n" not in head and len(head) < 8192:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                head += chunk
            line = head.split(b"\r\n", 1)[0].decode("latin-1")
            parts = line.split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                self.note(f"deny non-connect {parts[0] if parts else '?'}")
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                return
            host, _, port = parts[1].rpartition(":")
            if port != "443" or not allowed_host(host, self.allow):
                self.note(f"deny {host}:{port}")
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                return
            up = socket.create_connection((host, 443), timeout=30)
            self.note(f"allow {host}:443")
            conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            rest = head.split(b"\r\n\r\n", 1)[1]
            if rest:
                up.sendall(rest)
            conn.settimeout(None)
            up.settimeout(None)
            t = threading.Thread(target=_pipe, args=(up, conn), daemon=True)
            t.start()
            _pipe(conn, up)
            t.join(timeout=5)
        except OSError:
            pass
        finally:
            conn.close()

    def close(self) -> None:
        try:
            self.srv.close()
        finally:
            try:
                self.sock_path.unlink()
            except OSError:
                pass


def _pipe(a: socket.socket, b: socket.socket) -> None:
    try:
        while True:
            data = a.recv(65536)
            if not data:
                break
            b.sendall(data)
    except OSError:
        pass
    finally:
        try:
            b.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def git_paths(wt: Path) -> tuple[Path | None, Path | None]:
    try:
        out = subprocess.run(["git", "-C", str(wt), "rev-parse", "--path-format=absolute",
                              "--git-common-dir", "--git-dir"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, None
    lines = out.split()
    if len(lines) < 2:
        return None, None
    return Path(lines[0]), Path(lines[1])


def git_mounts(wt: Path) -> list[str]:
    common, gitdir = git_paths(wt)
    if common is None:
        return []
    vols = [f"--volume={common}:{common}:rw"]
    for sub in ("config", "hooks", "info"):
        p = common / sub
        if p.exists():
            vols.append(f"--volume={p}:{p}:ro")
    wts = common / "worktrees"
    if wts.is_dir():
        vols.append(f"--volume={wts}:{wts}:ro")
    if gitdir is not None and gitdir != common:
        vols.append(f"--volume={gitdir}:{gitdir}:rw")
        cw = gitdir / "config.worktree"
        if cw.exists():
            vols.append(f"--volume={cw}:{cw}:ro")
    return vols


def grok_args(kind: str, grok: str, wt: Path, prompt: Path, max_turns: int) -> list[str]:
    tools = KIND_TOOLS[kind]
    deny = [t for t in ALWAYS_DENY if t not in tools]
    if kind == "supersede":
        deny += [t for t in SHELL_TOOLS + ("write",) if t not in tools]
    mode = os.environ.get("PFY_LANE_PERMISSION_MODE", "dontAsk")
    if mode in ("bypassPermissions",):
        raise CageError("PFY_LANE_PERMISSION_MODE=bypassPermissions is auto-approve; refused")
    argv = [grok, "--cwd", str(wt), "--output-format", "plain", "--prompt-file", str(prompt),
            "--max-turns", str(max_turns), "--permission-mode", mode,
            "--tools", ",".join(tools), "--disallowed-tools", ",".join(deny),
            "--no-subagents", "--no-plan"]
    for t in tools:
        argv += ["--allow", t]
    if kind not in WEB_KINDS:
        argv.append("--disable-web-search")
    return argv


def base_run(podman: str, image: str, wt: Path, cage: Path, network: str) -> list[str]:
    home = cage / "home"
    argv = [podman, "run", "--rm", "--pull=never", f"--network={network}", "--userns=keep-id",
            "--cap-drop=all", "--security-opt=no-new-privileges", "--pids-limit=2048", "--memory=16g",
            "--tmpfs=/tmp:rw,size=4g", f"--volume={wt}:{wt}:rw", f"--volume={home}:{home}:rw",
            f"--volume={SCRIPT_DIR / 'lane_cage_entry.sh'}:{SCRIPT_DIR / 'lane_cage_entry.sh'}:ro",
            f"--workdir={wt}", f"--env=HOME={home}", "--env=GIT_TERMINAL_PROMPT=0",
            "--env=PYTHONDONTWRITEBYTECODE=1"]
    argv += git_mounts(wt)
    # Commit identity for the agent's local commits (the cage has no ~/.gitconfig).
    for key, envs in (("user.name", ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME")),
                      ("user.email", ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"))):
        r = subprocess.run(["git", "-C", str(wt), "config", key], capture_output=True, text=True)
        val = r.stdout.strip() if r.returncode == 0 else ("Deanery lane" if key == "user.name" else "lane@localhost")
        for env in envs:
            argv.append(f"--env={env}={val}")
    qroot = os.environ.get("PFY_QUARANTINE_DIR") or str(
        Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "pfy" / "quarantine")
    if Path(qroot).is_dir():
        argv.append(f"--volume={qroot}:{qroot}:ro")
    if os.environ.get("PFY_CAGE_FAKE") == "1":
        argv.append("--env=PFY_CAGE_FAKE=1")
    return argv


def preflight(podman: str, image: str) -> None:
    if shutil.which(podman) is None:
        raise CageError(f"lane cage unavailable: {podman} not found (no unconfined fallback)")
    r = subprocess.run([podman, "image", "exists", image], capture_output=True)
    if r.returncode != 0:
        raise CageError(f"lane cage unavailable: image {image} missing (make test-image)")


def build_grok_argv(args, cage: Path) -> tuple[list[str], dict]:
    podman = os.environ.get("PFY_PODMAN", "podman")
    image = os.environ.get("PFY_LANE_IMAGE", DEFAULT_IMAGE)
    wt = Path(args.wt).resolve()
    prompt = Path(args.prompt).resolve()
    grok_real = Path(shutil.which(args.grok) or args.grok).resolve()
    if not grok_real.is_file():
        raise CageError(f"grok binary not found: {args.grok}")
    home = cage / "home"
    grok_home = home / ".grok"
    sock_dir = cage / "sock"
    argv = base_run(podman, image, wt, cage, "none")
    argv += [f"--volume={prompt}:{prompt}:ro", f"--volume={grok_real}:{grok_real}:ro",
             f"--volume={SCRIPT_DIR / 'lane_uds_forward.py'}:{SCRIPT_DIR / 'lane_uds_forward.py'}:ro",
             f"--volume={sock_dir}:{sock_dir}:rw",
             f"--env=GROK_HOME={grok_home}", f"--env=PFY_CAGE_PROXY_SOCK={sock_dir / 'egress.sock'}",
             f"--env=PFY_CAGE_FORWARDER={SCRIPT_DIR / 'lane_uds_forward.py'}",
             f"--env=PFY_CAGE_PROXY_PORT={PROXY_PORT}",
             f"--env=HTTPS_PROXY=http://127.0.0.1:{PROXY_PORT}", f"--env=HTTP_PROXY=http://127.0.0.1:{PROXY_PORT}",
             f"--env=https_proxy=http://127.0.0.1:{PROXY_PORT}", f"--env=http_proxy=http://127.0.0.1:{PROXY_PORT}",
             "--env=NO_PROXY=", "--env=no_proxy=", "--env=GROK_WORKFLOWS=0", "--env=GROK_SUBAGENTS=0"]
    cred = "none"
    if os.environ.get("XAI_API_KEY"):
        argv.append("--env=XAI_API_KEY")  # by name: the value is never on a command line or in a log
        cred = "env"
    else:
        auth = Path(os.environ.get("PFY_LANE_GROK_AUTH") or Path.home() / ".grok" / "auth.json")
        if auth.exists():
            argv.append(f"--volume={auth}:{grok_home / 'auth.json'}:ro")
            cred = "auth-file-ro"
    entry = str(SCRIPT_DIR / "lane_cage_entry.sh")
    argv += [image, entry] + grok_args(args.kind, str(grok_real), wt, prompt, args.max_turns)
    return argv, {"credential": cred, "image": image}


def prepare_cage(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    cage = Path(tempfile.mkdtemp(prefix="cage-", dir=root))
    (cage / "home" / ".grok").mkdir(parents=True)
    (cage / "home" / ".grok" / "config.toml").write_text(GROK_HOME_CONFIG, encoding="utf-8")
    (cage / "sock").mkdir()
    os.chmod(cage, 0o700)
    return cage


def cage_root(wt: Path) -> Path:
    if os.environ.get("PFY_LANE_CAGE_DIR"):
        return Path(os.environ["PFY_LANE_CAGE_DIR"])
    # Outside the worktree (the agent must not see its own cage) and short
    # enough for a unix socket path.
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / "pfy-lane-cages"


def cmd_grok(args) -> int:
    wt = Path(args.wt).resolve()
    cage = prepare_cage(cage_root(wt))
    try:
        argv, meta = build_grok_argv(args, cage)
        if args.print:
            print(json.dumps({"argv": argv, **meta}))
            return 0
        preflight(argv[0], meta["image"])
        allow = [a.strip().lower() for a in os.environ.get("PFY_LANE_EGRESS_ALLOW", DEFAULT_ALLOW).split(",") if a.strip()]
        egress_log = Path(args.egress_log) if args.egress_log else cage / "egress.log"
        proxy = EgressProxy(cage / "sock" / "egress.sock", allow, egress_log)
        proxy.start()
        print(f"lane-cage: kind={args.kind} image={meta['image']} network=none egress={','.join(allow)} "
              f"credential={meta['credential']} tools={','.join(KIND_TOOLS[args.kind])}", file=sys.stderr)
        try:
            return subprocess.run(argv, timeout=args.timeout).returncode
        except subprocess.TimeoutExpired:
            print("lane-cage: timeout", file=sys.stderr)
            return 124
        finally:
            proxy.close()
    except CageError as exc:
        print(f"lane-cage: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(cage, ignore_errors=True)


def cmd_exec(args) -> int:
    wt = Path(args.wt).resolve()
    cage = prepare_cage(cage_root(wt))
    try:
        podman = os.environ.get("PFY_PODMAN", "podman")
        image = os.environ.get("PFY_LANE_IMAGE", DEFAULT_IMAGE)
        argv = base_run(podman, image, wt, cage, "none")
        for ro in args.ro:
            p = Path(ro).resolve()
            argv.append(f"--volume={p}:{p}:ro")
        cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
        if not cmd:
            raise CageError("exec needs a command after --")
        argv += [image, str(SCRIPT_DIR / "lane_cage_entry.sh"), *cmd]
        if args.print:
            print(json.dumps({"argv": argv}))
            return 0
        preflight(podman, image)
        return subprocess.run(argv, timeout=args.timeout).returncode
    except CageError as exc:
        print(f"lane-cage: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(cage, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Confined lane runner (rootless podman).")
    sub = ap.add_subparsers(dest="cmd_name", required=True)
    g = sub.add_parser("grok")
    g.add_argument("--kind", required=True, choices=sorted(KIND_TOOLS))
    g.add_argument("--wt", required=True)
    g.add_argument("--prompt", required=True)
    g.add_argument("--grok", default=os.environ.get("PFY_GROK_BIN", "grok"))
    g.add_argument("--max-turns", type=int, default=250)
    g.add_argument("--timeout", type=int, default=7200)
    g.add_argument("--egress-log", default="")
    g.add_argument("--print", action="store_true")
    e = sub.add_parser("exec")
    e.add_argument("--wt", required=True)
    e.add_argument("--ro", action="append", default=[])
    e.add_argument("--timeout", type=int, default=3600)
    e.add_argument("--print", action="store_true")
    e.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    return cmd_grok(args) if args.cmd_name == "grok" else cmd_exec(args)


if __name__ == "__main__":
    raise SystemExit(main())
