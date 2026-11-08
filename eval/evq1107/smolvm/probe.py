#!/usr/bin/env python3
"""Install-gate probe for pinned smolvm 1.26.1.

The host runs the same shell as the guest and must see both markers and
rewrite its own sentinel. The guest runs with no volume and no network.
A pass is 3/3 host escapes blocked, a guest kernel different from the
host, and both marker files unchanged. A sha256 mismatch does not exec.
Stub binaries are for tests. No gate wiring.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import pwd
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DEFAULT = Path(__file__).resolve().parent / "results.json"
CACHE = Path("/home/mark/.cache/pfy/tools/smolvm")
DEFAULT_BIN = CACHE / "unpack" / "smolvm-1.26.1-linux-x86_64" / "smolvm"
TARBALL = CACHE / "dl" / "smolvm-1.26.1-linux-x86_64.tar.gz"

PIN_VERSION = "1.26.1"
PIN_COMMIT = "093852e8f527ce7db5f96195b909de15fef82251"
PIN_TAG_OBJECT = "39f7c83e983bbc5ff408129a83d772f398d42861"
PIN_TARBALL_SHA256 = "bcae519f7dad3cead2deaa0362a42a1ad7bffce73ea7a28161dea6822c559654"
PIN_BINARY_SHA256 = "62ed0353d664c2d6d78bd87ecf3213c64464003f51cb58506b87b187b1a6494a"
IMAGE = "alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8"
IMAGE_DIGEST = "sha256:" + IMAGE.split("@sha256:", 1)[1]
IMAGE_LINE = re.compile(r"^(Using cached|Caching) image [0-9a-f]{16}\b")

SENTINEL_TEXT = "pfy-smolvm-host-sentinel\n"
CWD_TEXT = "pfy-smolvm-cwd-marker\n"
KNOWN = {
    "name: probe-skill",
    "host-visible",
    "host-hidden",
    "host-write-ok",
    "host-write-blocked",
    "cwd-visible",
    "cwd-hidden",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def script_for(sentinel: Path, cwd_marker: Path) -> str:
    sent = shlex.quote(str(sentinel))
    mark = shlex.quote(str(cwd_marker))
    return "; ".join(
        [
            "echo pfy-smolvm-install-ok",
            "printf 'name: probe-skill\\n'",
            "uname -r",
            f"SENTINEL={sent}",
            f"CWD_MARKER={mark}",
            'if test -e "$SENTINEL"; then echo host-visible; else echo host-hidden; fi',
            "if printf 'pwn\\n' > \"$SENTINEL\" 2>/dev/null; then echo host-write-ok; else echo host-write-blocked; fi",
            'if test -e "$CWD_MARKER"; then echo cwd-visible; else echo cwd-hidden; fi',
        ]
    )


def clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.split("\r")[-1].strip()
        if line:
            lines.append(line)
    return lines


def parse_run(stdout: str) -> dict[str, str]:
    lines = clean_lines(stdout)
    evidence = ""
    for line in lines:
        if IMAGE_LINE.match(line):
            evidence = line
            break
    found = {
        "install": "",
        "skill": "",
        "kernel": "",
        "see": "",
        "write": "",
        "cwd": "",
        "image_evidence": evidence,
    }
    if "pfy-smolvm-install-ok" not in lines:
        return found
    found["install"] = "pfy-smolvm-install-ok"
    rest = lines[lines.index("pfy-smolvm-install-ok") + 1 :]
    for line in rest:
        if line == "name: probe-skill":
            found["skill"] = line
        elif line in ("host-visible", "host-hidden"):
            found["see"] = line
        elif line in ("host-write-ok", "host-write-blocked"):
            found["write"] = line
        elif line in ("cwd-visible", "cwd-hidden"):
            found["cwd"] = line
        elif line not in KNOWN and not found["kernel"]:
            found["kernel"] = line
    return found


def child_env(base: Path) -> dict[str, str]:
    return {
        "HOME": str(base / "home"),
        "XDG_CONFIG_HOME": str(base / "config"),
        "XDG_CACHE_HOME": str(base / "cache"),
        "TMPDIR": str(base / "tmp"),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def run_cmd(cmd: list[str], env: dict[str, str], cwd: Path, timeout: float) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return 124, out or "", (err or "") + "\ntimeout"
    return proc.returncode, out or "", err or ""


def du_bytes(path: Path, apparent: bool) -> int | None:
    if not path.exists():
        return None
    cmd = ["du", "-s", "-B1"]
    if apparent:
        cmd.append("--apparent-size")
    cmd.append(str(path))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return int(proc.stdout.split()[0])


def login_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def snap_home() -> list[list[object]]:
    rows: list[list[object]] = []
    for rel in (".cache/smolvm", ".local/share/smolvm"):
        path = login_home() / rel
        if not path.exists():
            rows.append([str(path), None])
            continue
        stat = path.stat()
        rows.append([str(path), [stat.st_mode, stat.st_size, stat.st_mtime_ns]])
    return rows


def write_result(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def needs_pull(stderr: str) -> bool:
    text = stderr.lower()
    return (
        "networking is disabled" in text
        or "pull image" in text
        or "network is unreachable" in text
    )


def base_result() -> dict:
    return {
        "version": PIN_VERSION,
        "commit": PIN_COMMIT,
        "tag_object": PIN_TAG_OBJECT,
        "tarball_sha256": PIN_TARBALL_SHA256,
        "image": IMAGE,
        "image_digest": IMAGE_DIGEST,
        "image_digest_source": "pin",
        "host_kernel": platform.release(),
        "mem_mib": 512,
        "storage_gib": 1,
        "cpus": 1,
        "unprivileged": True,
        "guest_net": False,
    }


def main() -> int:
    out_path = Path(os.environ.get("SMOLVM_OUT") or OUT_DEFAULT)
    base = Path(os.environ.get("SMOLVM_PROBE_BASE") or CACHE)
    bin_path = Path(os.environ.get("SMOLVM_BIN") or DEFAULT_BIN)
    expected = (os.environ.get("SMOLVM_SHA256") or PIN_BINARY_SHA256).strip().lower()
    result = base_result()
    result["binary_sha256_expected"] = expected

    if not bin_path.is_file():
        result["reason"] = "no smolvm binary"
        write_result(out_path, result)
        print(result["reason"])
        return 2

    payload = bin_path.parent / "smolvm-bin"
    if not payload.is_file():
        payload = bin_path
    digest = sha256_file(payload)
    result["binary_sha256"] = digest
    result["payload"] = str(payload)
    if digest != expected:
        result["reason"] = f"sha256 mismatch: {payload.name} is {digest}, expected {expected}"
        write_result(out_path, result)
        print(result["reason"])
        return 2

    official = expected == PIN_BINARY_SHA256
    result["official_pin"] = official
    if official:
        kvm = os.environ.get("PFY_SMOLVM_KVM_PATH") or "/dev/kvm"
        kvm_rw = os.path.exists(kvm) and os.access(kvm, os.R_OK | os.W_OK)
        result["kvm_path"] = kvm
        result["kvm_rw"] = kvm_rw
        if not kvm_rw:
            result["reason"] = f"{kvm} is not read/write for this user"
            write_result(out_path, result)
            print(result["reason"])
            return 2

    for name in ("home", "config", "cache", "tmp", "probe-secret", "work"):
        (base / name).mkdir(parents=True, exist_ok=True)
    work = base / "work"
    guest_sentinel = base / "probe-secret" / "host-sentinel.txt"
    cwd_marker = work / "cwd-marker.txt"
    control_sentinel = base / "tmp" / "control-sentinel.txt"
    guest_sentinel.write_text(SENTINEL_TEXT, encoding="utf-8")
    cwd_marker.write_text(CWD_TEXT, encoding="utf-8")
    control_sentinel.write_text(SENTINEL_TEXT, encoding="utf-8")
    guest_before = sha256_file(guest_sentinel)
    cwd_before = sha256_file(cwd_marker)

    control_script = script_for(control_sentinel, cwd_marker)
    control_rc, control_out, _control_err = run_cmd(
        ["/bin/sh", "-c", control_script], child_env(base), work, 30
    )
    parsed_control = parse_run(control_out)
    control_blocked = 0
    if parsed_control["see"] != "host-visible":
        control_blocked += 1
    if parsed_control["write"] != "host-write-ok" or control_sentinel.read_text(encoding="utf-8") != "pwn\n":
        control_blocked += 1
    if parsed_control["cwd"] != "cwd-visible":
        control_blocked += 1
    result["control_rc"] = control_rc
    result["control_escapes_blocked"] = control_blocked

    env = child_env(base)
    guest_script = script_for(guest_sentinel, cwd_marker)
    measure = [
        str(bin_path),
        "machine",
        "run",
        "--oci-cache",
        "--image",
        IMAGE,
        "--cpus",
        "1",
        "--mem",
        "512",
        "--storage",
        "1",
        "--unprivileged",
        "--",
        "sh",
        "-c",
        guest_script,
    ]
    home_before = snap_home()
    started = time.perf_counter()
    guest_rc, guest_out, guest_err = run_cmd(measure, env, work, 180)
    wall = time.perf_counter() - started
    warm_wall = None
    if official and guest_rc != 0 and needs_pull(guest_err):
        warm = [
            str(bin_path),
            "machine",
            "run",
            "--net",
            "--dns",
            "1.1.1.1",
            "--oci-cache",
            "--image",
            IMAGE,
            "--cpus",
            "1",
            "--mem",
            "512",
            "--storage",
            "1",
            "--",
            "true",
        ]
        warm_started = time.perf_counter()
        warm_rc, _warm_out, warm_err = run_cmd(warm, env, work, 180)
        warm_wall = time.perf_counter() - warm_started
        result["warm_rc"] = warm_rc
        result["warm_stderr_tail"] = warm_err[-400:]
        if warm_rc == 0:
            started = time.perf_counter()
            guest_rc, guest_out, guest_err = run_cmd(measure, env, work, 180)
            wall = time.perf_counter() - started
    home_after = snap_home()
    parsed = parse_run(guest_out)
    sentinel_same = sha256_file(guest_sentinel) == guest_before and guest_sentinel.read_text(encoding="utf-8") == SENTINEL_TEXT
    cwd_same = sha256_file(cwd_marker) == cwd_before and cwd_marker.read_text(encoding="utf-8") == CWD_TEXT
    guest_blocked = 0
    if parsed["see"] == "host-hidden":
        guest_blocked += 1
    if parsed["write"] == "host-write-blocked" and sentinel_same:
        guest_blocked += 1
    if parsed["cwd"] == "cwd-hidden" and cwd_same:
        guest_blocked += 1
    kernel_differs = bool(parsed["kernel"]) and parsed["kernel"] != result["host_kernel"]
    install_ok = parsed["install"] == "pfy-smolvm-install-ok" and parsed["skill"] == "name: probe-skill"
    image_ok = (not official) or bool(parsed["image_evidence"])
    result.update(
        {
            "guest_rc": guest_rc,
            "guest_kernel": parsed["kernel"],
            "kernel_differs": kernel_differs,
            "guest_see": parsed["see"],
            "guest_write": parsed["write"],
            "guest_cwd": parsed["cwd"],
            "guest_escapes_blocked": guest_blocked,
            "escapes_expected": 3,
            "install_marker": install_ok,
            "sentinel_unchanged": sentinel_same,
            "cwd_marker_unchanged": cwd_same,
            "real_home_unchanged": home_before == home_after,
            "image_evidence": parsed["image_evidence"],
            "wall_s": round(wall, 4),
            "warm_wall_s": None if warm_wall is None else round(warm_wall, 4),
            "stdout_lines": clean_lines(guest_out)[:30],
            "stderr_tail": guest_err[-400:],
        }
    )
    if official:
        if TARBALL.is_file():
            result["tarball_bytes"] = TARBALL.stat().st_size
        result["cache_allocated_bytes"] = du_bytes(CACHE, False)
        result["cache_apparent_bytes"] = du_bytes(CACHE, True)

    passed = (
        control_blocked == 0
        and control_rc == 0
        and guest_rc == 0
        and guest_blocked == 3
        and kernel_differs
        and install_ok
        and image_ok
        and sentinel_same
        and cwd_same
        and result["real_home_unchanged"]
    )
    if passed:
        result["reason"] = (
            f"ok: guest kernel {parsed['kernel']}, 3/3 host escapes blocked, wall {result['wall_s']}s"
        )
        code = 0
    elif not image_ok:
        result["reason"] = "smolvm did not report pulling or caching the pinned image"
        code = 1
    elif control_blocked != 0 or control_rc != 0:
        result["reason"] = "host control did not see and rewrite its sentinel"
        code = 1
    else:
        result["reason"] = (
            f"guest blocked {guest_blocked}/3, kernel_differs={kernel_differs}, guest_rc={guest_rc}"
        )
        code = 1
    write_result(out_path, result)
    print(result["reason"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
