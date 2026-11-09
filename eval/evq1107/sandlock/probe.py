#!/usr/bin/env python3
"""Install-gate probe for the pinned sandlock 0.8.9 binary.

A hostile installer writes one skill into a granted stage directory and
also tries to write a skills directory, write a sibling, read a canary,
and open a loopback TCP port. The unsandboxed run is the control. The
sandboxed run is the measurement. Nothing here is copied into a skills
tree, and the probe does not talk to a hosted service.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import statistics
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
CACHE = (Path.home() / ".cache/pfy/tools/sandlock")
BIN = Path(os.environ.get("SANDLOCK_BIN", str(CACHE / "unpack" / "sandlock")))
TARBALL = CACHE / "sandlock-x86_64-unknown-linux-gnu.tar.gz"
RUNTIME = ROOT / "tmp" / "sandlock-probe"

PIN_VERSION = "0.8.9"
PIN_COMMIT = "4a8c09fb537a152710cddfb1a4351d7e8a5af05f"
PIN_TARBALL_SHA256 = "2b6c3c4858177f0603c7c016dd2da854c09cc1dbce13682b8a627465c7842018"
PIN_BINARY_SHA256 = "79c8d72ddfef2c51fa7c598ef39c8ae746eafed76abd53a61d232ddee7e122b0"
CANARY = "PFY-SANDLOCK-CANARY\n"
SKILL_BODY = "name: probe-skill\n"
KEEP_BEFORE = "before\n"

# $0 is the shell name. Paths arrive as arguments so they are not interpolated.
INSTALLER = r"""
set +e
stage=$1
skills=$2
sibling=$3
canary=$4
host=$5
port=$6
printf 'name: probe-skill\n' > "$stage/SKILL.md"
printf 'pwn\n' > "$skills/SKILL.md"
printf 'escape\n' > "$sibling/escape.txt"
cat "$canary" > "$stage/stolen.txt"
/usr/bin/python3 -c 'import socket,sys; s=socket.create_connection((sys.argv[1], int(sys.argv[2])), 2); s.send(b"x"); s.close()' "$host" "$port"
echo $? > "$stage/net.rc"
"""

READ_PATHS = ("/usr", "/lib", "/lib64", "/bin", "/etc")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def child_env() -> dict[str, str]:
    # Minimal env so a host credential in the parent process is not passed through.
    return {
        "HOME": str(CACHE / "home"),
        "XDG_CONFIG_HOME": str(CACHE / "config"),
        "XDG_CACHE_HOME": str(CACHE / "cache"),
        "TMPDIR": str(CACHE / "tmp"),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
    }


def ascii_fold(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def pack_output(stdout: str, stderr: str) -> dict[str, object]:
    text = ascii_fold(stdout + "\n" + stderr)
    denied = [
        line.strip()
        for line in text.splitlines()
        if "Permission denied" in line or "PermissionError" in line
    ]
    return {
        "stdout": ascii_fold(stdout)[-800:],
        "stderr": ascii_fold(stderr)[-800:],
        "denied": denied,
    }


def run(argv: list[str], timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=child_env(),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        packed = pack_output(stdout, stderr)
        return {
            "rc": None,
            "timeout": True,
            "seconds": round(time.perf_counter() - started, 4),
            **packed,
        }
    packed = pack_output(proc.stdout, proc.stderr)
    return {
        "rc": proc.returncode,
        "timeout": False,
        "seconds": round(time.perf_counter() - started, 4),
        **packed,
    }


class Listener:
    """One loopback accept. Closed by the caller so a deny does not wait out the timeout."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.accepts = 0
        self.error = ""
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        self.ready.wait(timeout=2)

    def _serve(self) -> None:
        self.sock.settimeout(15)
        self.ready.set()
        try:
            conn, _addr = self.sock.accept()
        except Exception as exc:
            self.error = type(exc).__name__
            return
        self.accepts += 1
        conn.settimeout(2)
        try:
            conn.recv(16)
        except Exception:
            pass
        conn.close()

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass
        self.thread.join(timeout=2)


def make_tree(name: str) -> dict[str, Path]:
    root = RUNTIME / name
    if root.exists():
        for child in sorted(root.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                child.rmdir()
        root.rmdir()
    stage = root / "stage"
    skills = root / "skills"
    sibling = root / "sibling"
    stage.mkdir(parents=True)
    skills.mkdir(parents=True)
    sibling.mkdir(parents=True)
    (skills / "existing.txt").write_text("keep\n", encoding="utf-8")
    return {"root": root, "stage": stage, "skills": skills, "sibling": sibling}


def fs_args(extra_read: list[Path], write: Path | None) -> list[str]:
    argv: list[str] = []
    for path in READ_PATHS:
        if Path(path).exists():
            argv.extend(["-r", path])
    for path in extra_read:
        argv.extend(["-r", str(path)])
    if write is not None:
        argv.extend(["-w", str(write)])
    return argv


def score(tree: dict[str, Path], accepts: int) -> dict:
    stage = tree["stage"]
    skill = (stage / "SKILL.md").read_text(encoding="utf-8") if (stage / "SKILL.md").exists() else ""
    stolen = (stage / "stolen.txt").read_text(encoding="utf-8") if (stage / "stolen.txt").exists() else ""
    net_rc = (stage / "net.rc").read_text(encoding="utf-8").strip() if (stage / "net.rc").exists() else ""
    skills_write = (tree["skills"] / "SKILL.md").exists()
    sibling_write = (tree["sibling"] / "escape.txt").exists()
    canary_leaked = stolen == CANARY
    net_connect = accepts >= 1
    escapes = {
        "skills_write": skills_write,
        "sibling_write": sibling_write,
        "canary_leaked": canary_leaked,
        "net_connect": net_connect,
    }
    blocked = sum(1 for value in escapes.values() if not value)
    return {
        "install_landed": skill == SKILL_BODY,
        "skills_dir_untouched": (tree["skills"] / "existing.txt").read_text(encoding="utf-8") == "keep\n",
        "stolen_bytes": len(stolen.encode()),
        "net_rc": net_rc,
        "accepts": accepts,
        "escapes": escapes,
        "escapes_blocked": blocked,
        "escapes_total": 4,
    }


def installer_argv(tree: dict[str, Path], port: int, sandboxed: bool, net_allow: bool) -> list[str]:
    tail = [
        "/bin/sh",
        "-c",
        INSTALLER,
        "sh",
        str(tree["stage"]),
        str(tree["skills"]),
        str(tree["sibling"]),
        str(CACHE / "probe-secret" / "canary.txt"),
        "127.0.0.1",
        str(port),
    ]
    if not sandboxed:
        return tail
    argv = [str(BIN), "run", "--clean-env"]
    argv.extend(fs_args([tree["skills"]], tree["stage"]))
    if net_allow:
        argv.extend(["--net-allow", "127.0.0.1:%d" % port])
    argv.append("--")
    argv.extend(tail)
    return argv


def scenario(name: str, sandboxed: bool, net_allow: bool) -> dict:
    tree = make_tree(name)
    listener = Listener()
    try:
        outcome = run(installer_argv(tree, listener.port, sandboxed, net_allow), timeout=30)
    finally:
        listener.close()
    body = score(tree, listener.accepts)
    body["name"] = name
    body["sandboxed"] = sandboxed
    body["net_allow"] = net_allow
    body["port"] = listener.port
    body["listener_error"] = listener.error
    body["rc"] = outcome["rc"]
    body["timeout"] = outcome["timeout"]
    body["seconds"] = outcome["seconds"]
    body["permission_denied_lines"] = outcome["denied"]
    return body


def dry_run() -> dict:
    root = RUNTIME / "dry"
    if root.exists():
        for child in sorted(root.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                child.rmdir()
        root.rmdir()
    root.mkdir(parents=True)
    (root / "keep.txt").write_text(KEEP_BEFORE, encoding="utf-8")
    before = {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file()}
    argv = [str(BIN), "run", "--dry-run", "--workdir", str(root), "--clean-env"]
    argv.extend(fs_args([], None))
    argv.extend(
        [
            "--",
            "/bin/sh",
            "-c",
            "printf 'name: probe-skill\\n' > SKILL.md; printf 'after\\n' > keep.txt",
        ]
    )
    outcome = run(argv, timeout=30)
    after = {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file()}
    text = outcome["stdout"] + "\n" + outcome["stderr"]
    listed = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"A", "M", "D"} and not parts[1].startswith("sandlock"):
            listed.append({"op": parts[0], "path": parts[1]})
    return {
        "rc": outcome["rc"],
        "timeout": outcome["timeout"],
        "seconds": outcome["seconds"],
        "listed": listed,
        "listed_count": len(listed),
        "before": before,
        "after": after,
        "discarded": before == after and len(listed) > 0,
        "output_tail": text[-800:],
    }


def startup(samples: int = 21) -> dict:
    argv = [str(BIN), "run", "--clean-env"]
    argv.extend(fs_args([], None))
    argv.extend(["--", "/bin/true"])
    times = []
    rcs = []
    for _ in range(samples):
        outcome = run(argv, timeout=15)
        times.append(outcome["seconds"] * 1000.0)
        rcs.append(outcome["rc"])
    warm = times[1:]
    return {
        "samples_including_warmup": samples,
        "reported_n": len(warm),
        "median_ms": round(statistics.median(warm), 2),
        "min_ms": round(min(warm), 2),
        "max_ms": round(max(warm), 2),
        "all_rc_zero": all(rc == 0 for rc in rcs),
        "times_ms": [round(item, 2) for item in times],
    }


def check_kernel() -> dict:
    outcome = run([str(BIN), "check"], timeout=20)
    text = ascii_fold(outcome["stdout"] + "\n" + outcome["stderr"])
    abi = ""
    for line in text.splitlines():
        if "Landlock:" in line and "ABI" in line:
            abi = line.strip()
    return {
        "rc": outcome["rc"],
        "timeout": outcome["timeout"],
        "abi_line": abi,
        "text": text.strip(),
    }


def pin_record() -> dict:
    binary_sha = sha256_file(BIN) if BIN.is_file() else ""
    tarball_sha = sha256_file(TARBALL) if TARBALL.is_file() else ""
    version = ""
    if BIN.is_file():
        outcome = run([str(BIN), "--version"], timeout=15)
        version = (outcome["stdout"] + outcome["stderr"]).strip()
    return {
        "version_text": version,
        "version_ok": version == "sandlock %s" % PIN_VERSION,
        "tag": "v%s" % PIN_VERSION,
        "tag_commit": PIN_COMMIT,
        "tarball": TARBALL.name,
        "tarball_sha256": tarball_sha,
        "tarball_sha_ok": tarball_sha == PIN_TARBALL_SHA256,
        "binary": str(BIN),
        "binary_sha256": binary_sha,
        "binary_sha_ok": binary_sha == PIN_BINARY_SHA256,
        "binary_bytes": BIN.stat().st_size if BIN.is_file() else 0,
        "kernel": platform.release(),
    }


def summarize(control: dict, enforce: dict, allowed: dict, dry: dict, times: dict) -> dict:
    enforce_ok = (
        enforce["install_landed"]
        and enforce["skills_dir_untouched"]
        and enforce["escapes_blocked"] == 4
        and enforce["net_rc"] not in {"", "0"}
        and not enforce["timeout"]
    )
    control_ok = (
        control["install_landed"]
        and all(control["escapes"].values())
        and control["net_rc"] == "0"
        and not control["timeout"]
    )
    allow_ok = (
        allowed["install_landed"]
        and allowed["escapes"]["net_connect"]
        and allowed["net_rc"] == "0"
        and allowed["escapes_blocked"] == 3
        and not allowed["escapes"]["skills_write"]
        and not allowed["escapes"]["sibling_write"]
        and not allowed["escapes"]["canary_leaked"]
        and not allowed["timeout"]
    )
    dry_ok = (
        dry["discarded"]
        and dry["after"].get("keep.txt") == KEEP_BEFORE
        and "SKILL.md" not in dry["after"]
        and {item["path"] for item in dry["listed"]} >= {"SKILL.md", "keep.txt"}
    )
    startup_ok = bool(times.get("all_rc_zero")) and times.get("reported_n") == 20
    return {
        "control_ok": control_ok,
        "enforce_ok": enforce_ok,
        "net_allow_ok": allow_ok,
        "dry_run_ok": dry_ok,
        "startup_ok": startup_ok,
        "headline": "%d/%d escapes blocked" % (enforce["escapes_blocked"], enforce["escapes_total"]),
        "install_landed": enforce["install_landed"],
    }


def main() -> int:
    for path in (CACHE / "home", CACHE / "config", CACHE / "cache", CACHE / "tmp", CACHE / "probe-secret"):
        path.mkdir(parents=True, exist_ok=True)
    (CACHE / "probe-secret" / "canary.txt").write_text(CANARY, encoding="utf-8")
    RUNTIME.mkdir(parents=True, exist_ok=True)

    pins = pin_record()
    kernel = check_kernel() if BIN.is_file() else {"rc": None, "text": "binary missing", "abi_line": ""}
    if not pins["version_ok"] or not pins["binary_sha_ok"] or not pins["tarball_sha_ok"]:
        payload = {"pins": pins, "kernel": kernel, "error": "pin mismatch or missing binary"}
        (OUT_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(payload["error"])
        return 2

    control = scenario("control", sandboxed=False, net_allow=False)
    enforce = scenario("enforce", sandboxed=True, net_allow=False)
    allowed = scenario("net-allow", sandboxed=True, net_allow=True)
    dry = dry_run()
    times = startup()
    summary = summarize(control, enforce, allowed, dry, times)
    payload = {
        "pins": pins,
        "kernel": kernel,
        "control": control,
        "enforce": enforce,
        "net_allow": allowed,
        "dry_run": dry,
        "startup": times,
        "summary": summary,
    }
    (OUT_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(summary["headline"])
    print(
        "control_ok=%s enforce_ok=%s net_allow_ok=%s dry_run_ok=%s startup_ok=%s startup_median_ms=%s"
        % (
            summary["control_ok"],
            summary["enforce_ok"],
            summary["net_allow_ok"],
            summary["dry_run_ok"],
            summary["startup_ok"],
            times["median_ms"],
        )
    )
    keys = ("control_ok", "enforce_ok", "net_allow_ok", "dry_run_ok", "startup_ok")
    return 0 if all(summary[key] for key in keys) else 1


if __name__ == "__main__":
    raise SystemExit(main())
