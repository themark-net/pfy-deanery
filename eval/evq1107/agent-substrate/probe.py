#!/usr/bin/env python3
"""Measure one rootless runsc checkpoint/restore, then one userns cycle.

No model, no network, no Docker. A stub runsc is enough for the fail/recover
test. The live binary is passed with --runsc.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TICK_RE = re.compile(r"tick=(\d+) acc=(\d+)")
VMRSS_RE = re.compile(r"^VmRSS:\s+(\d+)\s+kB", re.M)

SUMMARY_KEYS = (
    "rootless_do_ok",
    "rootless_checkpoint_ok",
    "rootless_restore_ok",
    "userns_checkpoint_ok",
    "userns_restore_ok",
    "state_continued",
    "tick_before",
    "tick_after",
    "acc_same",
    "out2_nul_bytes",
    "rss_kb_running",
    "pid_alive_after_checkpoint",
    "image_bytes",
    "image_alloc_bytes",
    "image_nonzero_bytes",
    "pid_state_after_checkpoint",
    "stop_wait_s",
    "image_fsync_s",
    "image_account_s",
    "ckpt_s",
    "restore_s",
    "mem_available_delta_kb",
    "gap_b_timeout_changed",
    "host_build_sessions_shelved",
    "full_stack",
)


def parse_ticks(text: str) -> list[tuple[int, int]]:
    return [(int(n), int(acc)) for n, acc in TICK_RE.findall(text)]


def continuation(before: str, after: str) -> dict:
    """A later tick with the same acc byte is continued state. Same tick is not."""
    pre = parse_ticks(before)
    post = parse_ticks(after)
    out = {
        "state_continued": 0,
        "tick_before": pre[-1][0] if pre else None,
        "tick_after": post[-1][0] if post else None,
        "acc_same": 0,
    }
    if not pre or not post:
        return out
    last_n, last_acc = pre[-1]
    for n, acc in post:
        if n > last_n and acc == last_acc:
            out["state_continued"] = 1
            out["acc_same"] = 1
            out["tick_after"] = n
            break
    return out


def mem_available_kb() -> int | None:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None


def rss_kb(pid: int | None) -> int | None:
    if not pid:
        return None
    path = Path(f"/proc/{pid}/status")
    if not path.is_file():
        return None
    match = VMRSS_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return None
    return int(match.group(1))


def pid_alive(pid: int | None) -> int:
    if not pid:
        return 0
    return 1 if Path(f"/proc/{pid}").exists() else 0


def proc_state(pid: int | None) -> str:
    if not pid:
        return "gone"
    path = Path(f"/proc/{pid}/status")
    if not path.is_file():
        return "gone"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("State:"):
            return line.split(":", 1)[1].strip() or "unknown"
    return "unknown"


def image_stats(path: Path) -> dict:
    """Apparent size, allocated bytes after fsync, and non-zero byte count.

    A checkpoint can return before ZFS accounts the pages file. fsync then stat.
    """
    apparent = 0
    nonzero = 0
    files: list[Path] = []
    start = time.perf_counter()
    if path.is_dir():
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            data = item.read_bytes()
            apparent += len(data)
            nonzero += len(data) - data.count(b"\x00")
            fd = os.open(item, os.O_RDWR)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            files.append(item)
    fsync_s = round(time.perf_counter() - start, 4)
    # ZFS st_blocks stays near 0 until the txg commits. Poll briefly.
    deadline = time.perf_counter() + 6.0
    while True:
        alloc = 0
        for item in files:
            alloc += item.stat().st_blocks * 512
        if not files or alloc * 2 > apparent or time.perf_counter() >= deadline:
            break
        time.sleep(0.1)
    return {
        "image_bytes": apparent,
        "image_alloc_bytes": alloc,
        "image_nonzero_bytes": nonzero,
        "image_fsync_s": fsync_s,
        "image_account_s": round(time.perf_counter() - start, 4),
    }


def wait_reaped(
    pid: int | None,
    runsc: str,
    flags: list[str],
    env: dict[str, str],
    timeout_s: float = 3.0,
) -> dict:
    """Checkpoint returns before the sentry is reaped. Poll until it is gone."""
    start = time.perf_counter()
    state = "gone"
    rss = None
    listed = ""
    while True:
        state = proc_state(pid)
        rss = rss_kb(pid)
        proc = subprocess.run(
            [runsc, *flags, "list"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        listed = (proc.stdout or "").strip()
        reaped = state == "gone" or state.startswith("Z")
        if reaped or (time.perf_counter() - start) >= timeout_s:
            break
        time.sleep(0.05)
    return {
        "stop_wait_s": round(time.perf_counter() - start, 4),
        "pid_state_after_checkpoint": state,
        "rss_kb_after_checkpoint": rss,
        "list_after_checkpoint": listed,
    }


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def first_line(text: str, limit: int = 240) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line[:limit]


def clean_env(work: Path) -> dict[str, str]:
    home = work / "home"
    config = work / "config"
    cache = work / "cache"
    tmp = work / "tmp"
    for path in (home, config, cache, tmp):
        path.mkdir(parents=True, exist_ok=True)
    os.chmod(tmp, 0o700)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(cache),
        "XDG_RUNTIME_DIR": str(tmp),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }


def run_cmd(
    argv: list[str],
    env: dict[str, str],
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> tuple[int, float]:
    start = time.perf_counter()
    out_fh = stdout_path.open("w", encoding="utf-8") if stdout_path else subprocess.DEVNULL
    err_fh = stderr_path.open("w", encoding="utf-8") if stderr_path else subprocess.DEVNULL
    try:
        proc = subprocess.run(argv, env=env, stdout=out_fh, stderr=err_fh, check=False)
    finally:
        if stdout_path is not None and out_fh is not subprocess.DEVNULL:
            out_fh.close()
        if stderr_path is not None and err_fh is not subprocess.DEVNULL:
            err_fh.close()
    return proc.returncode, round(time.perf_counter() - start, 4)


def write_guest(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "import hashlib, os, sys, time",
                "n = int(sys.argv[1])",
                "blob = os.urandom(n)",
                "acc0 = 0",
                "for i in range(0, n, 4096):",
                "    acc0 = (acc0 + blob[i]) & 0xFFFFFFFF",
                "digest = hashlib.sha256(blob).hexdigest()",
                "print(f'digest={digest} bytes={n} acc0={acc0}', flush=True)",
                "mark = blob[0] ^ blob[n // 2] ^ blob[-1]",
                "tick = 0",
                "while True:",
                "    tick += 1",
                "    print(f'tick={tick} acc={mark}', flush=True)",
                "    time.sleep(0.25)",
                "",
            ]
        ),
        encoding="utf-8",
    )


def prepare_bundle(runsc: str, work: Path, guest: Path, env: dict[str, str]) -> None:
    bundle = work / "b"
    bundle.mkdir(parents=True, exist_ok=True)
    spec = bundle / "config.json"
    code, _ = run_cmd(
        [runsc, "spec", "-bundle", str(bundle), "--", "/usr/bin/python3", "-B", str(guest), "0"],
        env,
        stdout_path=work / "spec.out",
        stderr_path=work / "spec.err",
    )
    if code != 0 or not spec.is_file():
        raise SystemExit(f"runsc spec failed rc={code}")
    cfg = json.loads(spec.read_text(encoding="utf-8"))
    cfg.setdefault("root", {})
    cfg["root"]["path"] = "/"
    cfg["root"]["readonly"] = True
    cfg.setdefault("process", {})
    cfg["process"]["terminal"] = False
    cfg["process"]["args"] = ["/usr/bin/python3", "-B", str(guest), str(work.name)]
    # The byte count is passed on the command line below. Placeholder replaced by caller.
    env_list = [item for item in cfg["process"].get("env", []) if not item.startswith("HOME=")]
    env_list.extend(
        [
            "HOME=/tmp",
            "PATH=/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE=1",
            "PYTHONUNBUFFERED=1",
            "LANG=C.UTF-8",
        ]
    )
    cfg["process"]["env"] = env_list
    spec.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def set_guest_bytes(work: Path, guest: Path, nbytes: int) -> None:
    spec = work / "b" / "config.json"
    cfg = json.loads(spec.read_text(encoding="utf-8"))
    cfg["process"]["args"] = ["/usr/bin/python3", "-B", str(guest), str(nbytes)]
    spec.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def wait_for_tick(path: Path, timeout_s: float) -> str:
    deadline = time.perf_counter() + timeout_s
    text = ""
    while time.perf_counter() < deadline:
        text = read_text(path)
        if parse_ticks(text):
            return text
        time.sleep(0.1)
    return text


def global_flags(state: Path, rootless: bool) -> list[str]:
    flags = ["--network=none", "--ignore-cgroups", "--root", str(state)]
    if rootless:
        flags = ["--rootless", *flags]
    return flags


def cleanup_with_flags(runsc: str, flags: list[str], ids: list[str], env: dict[str, str]) -> None:
    for cid in ids:
        run_cmd([runsc, *flags, "kill", cid, "KILL"], env)
        run_cmd([runsc, *flags, "delete", "-force", cid], env)


def cycle(runsc: str, work: Path, label: str, rootless: bool, env: dict[str, str], tick_timeout: float) -> dict:
    """One run, checkpoint, restore. Restore refusal is a result, not a crash."""
    state = work / f"{label}-state"
    image = work / f"{label}-img"
    log = work / f"{label}-log"
    for path in (state, image, log):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    flags = global_flags(state, rootless)
    run_id = f"{label}1"
    restore_id = f"{label}2"
    result: dict = {
        "label": label,
        "rootless": 1 if rootless else 0,
        "run_ok": 0,
        "checkpoint_ok": 0,
        "restore_ok": 0,
        "restore_error": "",
        "rss_kb_running": None,
        "pid_alive_before": 0,
        "pid_alive_after_checkpoint": 0,
        "mem_available_running_kb": None,
        "mem_available_shelved_kb": None,
        "mem_available_delta_kb": None,
        "image_bytes": 0,
        "image_alloc_bytes": 0,
        "image_nonzero_bytes": 0,
        "pid_state_after_checkpoint": "gone",
        "rss_kb_after_checkpoint": None,
        "list_after_checkpoint": "",
        "ckpt_s": None,
        "restore_s": None,
        "state_continued": 0,
        "tick_before": None,
        "tick_after": None,
        "acc_same": 0,
    }
    try:
        if rootless:
            do_out = log / "do.out"
            do_err = log / "do.err"
            do_rc, _ = run_cmd(
                [runsc, *flags, "do", "echo", "rootless-ok"],
                env,
                stdout_path=do_out,
                stderr_path=do_err,
            )
            result["do_ok"] = 1 if do_rc == 0 and "rootless-ok" in read_text(do_out) else 0
        run_rc, _ = run_cmd(
            [runsc, *flags, "run", "-detach", "-bundle", str(work / "b"), "-pid-file", str(log / "pid"), run_id],
            env,
            stdout_path=log / "out1.log",
            stderr_path=log / "run.err",
        )
        before = wait_for_tick(log / "out1.log", tick_timeout)
        result["run_ok"] = 1 if run_rc == 0 and parse_ticks(before) else 0
        state_out = log / "state.json"
        run_cmd([runsc, *flags, "state", run_id], env, stdout_path=state_out, stderr_path=log / "state.err")
        pid = None
        try:
            pid = int(json.loads(read_text(state_out)).get("pid") or 0) or None
        except (json.JSONDecodeError, TypeError, ValueError):
            pid = None
        result["pid_alive_before"] = pid_alive(pid)
        result["rss_kb_running"] = rss_kb(pid)
        result["mem_available_running_kb"] = mem_available_kb()
        ckpt_rc, ckpt_s = run_cmd(
            [runsc, *flags, "checkpoint", "-image-path", str(image), run_id],
            env,
            stdout_path=log / "ckpt.out",
            stderr_path=log / "ckpt.err",
        )
        result["ckpt_s"] = ckpt_s
        result["checkpoint_ok"] = 1 if ckpt_rc == 0 else 0
        result.update(wait_reaped(pid, runsc, flags, env))
        result["pid_alive_after_checkpoint"] = pid_alive(pid)
        result["mem_available_shelved_kb"] = mem_available_kb()
        running = result["mem_available_running_kb"]
        shelved = result["mem_available_shelved_kb"]
        if running is not None and shelved is not None:
            result["mem_available_delta_kb"] = shelved - running
        result.update(image_stats(image))
        restore_rc, restore_s = run_cmd(
            [
                runsc,
                *flags,
                "restore",
                "-detach",
                "-image-path",
                str(image),
                "-bundle",
                str(work / "b"),
                restore_id,
            ],
            env,
            stdout_path=log / "out2.log",
            stderr_path=log / "restore.err",
        )
        result["restore_s"] = restore_s
        result["restore_ok"] = 1 if restore_rc == 0 else 0
        result["restore_error"] = first_line(read_text(log / "restore.err"))
        after = wait_for_tick(log / "out2.log", tick_timeout if restore_rc == 0 else 0.2)
        result.update(continuation(before, after))
        out2 = log / "out2.log"
        result["out2_nul_bytes"] = out2.read_bytes().count(b"\x00") if out2.is_file() else 0
    finally:
        cleanup_with_flags(runsc, flags, [run_id, restore_id], env)
        if image.exists():
            shutil.rmtree(image, ignore_errors=True)
    return result


def preflight() -> dict:
    cgroup = ""
    try:
        cgroup = subprocess.check_output(
            ["stat", "-fc", "%T", "/sys/fs/cgroup"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        cgroup = ""
    apparmor = None
    restrict = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
    if restrict.is_file():
        raw = restrict.read_text(encoding="utf-8", errors="replace").strip()
        apparmor = int(raw) if raw.isdigit() else raw
    return {
        "kernel": os.uname().release,
        "cgroup_fs": cgroup,
        "apparmor_restrict_unprivileged_userns": apparmor,
        "docker_on_path": 1 if shutil.which("docker") else 0,
        "podman_on_path": 1 if shutil.which("podman") else 0,
        "minikube_on_path": 1 if shutil.which("minikube") else 0,
        "kind_on_path": 1 if shutil.which("kind") else 0,
        "kubectl_on_path": 1 if shutil.which("kubectl") else 0,
        "go_on_path": 1 if shutil.which("go") else 0,
        "full_stack": "SKIPPED",
        "full_stack_reason": "rootless runsc only; kind kubectl and go are absent; docker and podman were not started",
    }


def version_line(runsc: str, env: dict[str, str], work: Path) -> str:
    out = work / "version.out"
    err = work / "version.err"
    run_cmd([runsc, "--version"], env, stdout_path=out, stderr_path=err)
    text = read_text(out).strip() or read_text(err).strip()
    return first_line(text, 200)


def print_summary(row: dict) -> None:
    for key in SUMMARY_KEYS:
        value = row.get(key)
        if value is None:
            value = "none"
        print(f"{key}={value}")


def build_row(rootless: dict, userns: dict, info: dict) -> dict:
    row = {
        "rootless_do_ok": int(rootless.get("do_ok") or 0),
        "rootless_checkpoint_ok": int(rootless.get("checkpoint_ok") or 0),
        "rootless_restore_ok": int(rootless.get("restore_ok") or 0),
        "rootless_restore_error": rootless.get("restore_error") or "",
        "userns_checkpoint_ok": int(userns.get("checkpoint_ok") or 0),
        "userns_restore_ok": int(userns.get("restore_ok") or 0),
        "state_continued": int(userns.get("state_continued") or 0),
        "tick_before": userns.get("tick_before"),
        "tick_after": userns.get("tick_after"),
        "acc_same": int(userns.get("acc_same") or 0),
        "out2_nul_bytes": int(userns.get("out2_nul_bytes") or 0),
        "rss_kb_running": userns.get("rss_kb_running"),
        "pid_alive_after_checkpoint": int(userns.get("pid_alive_after_checkpoint") or 0),
        "image_bytes": int(userns.get("image_bytes") or 0),
        "image_alloc_bytes": int(userns.get("image_alloc_bytes") or 0),
        "image_nonzero_bytes": int(userns.get("image_nonzero_bytes") or 0),
        "pid_state_after_checkpoint": userns.get("pid_state_after_checkpoint") or "gone",
        "rss_kb_after_checkpoint": userns.get("rss_kb_after_checkpoint"),
        "stop_wait_s": userns.get("stop_wait_s"),
        "image_fsync_s": userns.get("image_fsync_s"),
        "image_account_s": userns.get("image_account_s"),
        "ckpt_s": userns.get("ckpt_s"),
        "restore_s": userns.get("restore_s"),
        "mem_available_delta_kb": userns.get("mem_available_delta_kb"),
        "gap_b_timeout_changed": 0,
        "host_build_sessions_shelved": 0,
        "full_stack": "SKIPPED",
        "preflight": info,
        "rootless": rootless,
        "userns": userns,
    }
    return row


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe runsc checkpoint/restore")
    parser.add_argument("--runsc", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--results", default="")
    parser.add_argument("--bytes", type=int, default=33554432)
    parser.add_argument("--unshare", default="unshare")
    parser.add_argument("--phase", default="all", choices=("all", "userns"))
    parser.add_argument("--tick-timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.bytes < 1:
        print("bytes must be >= 1", file=sys.stderr)
        return 2
    runsc = str(Path(args.runsc).resolve())
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = clean_env(work)
    if args.phase == "userns":
        result = cycle(runsc, work, "userns", False, env, args.tick_timeout)
        (work / "userns-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 0
    guest = work / "guest.py"
    write_guest(guest)
    prepare_bundle(runsc, work, guest, env)
    set_guest_bytes(work, guest, args.bytes)
    info = preflight()
    info["runsc_version"] = version_line(runsc, env, work)
    info["runsc_bytes"] = Path(runsc).stat().st_size
    rootless = cycle(runsc, work, "rootless", True, env, args.tick_timeout)
    phase_cmd = [
        args.unshare,
        "-Urm",
        "--propagation",
        "private",
        "--",
        sys.executable,
        str(Path(__file__).resolve()),
        "--phase",
        "userns",
        "--runsc",
        runsc,
        "--work",
        str(work),
        "--bytes",
        str(args.bytes),
        "--tick-timeout",
        str(args.tick_timeout),
    ]
    phase_err = work / "userns-invoke.err"
    phase_rc, _ = run_cmd(phase_cmd, env, stdout_path=work / "userns-invoke.out", stderr_path=phase_err)
    userns_path = work / "userns-result.json"
    if userns_path.is_file():
        userns = json.loads(userns_path.read_text(encoding="utf-8"))
    else:
        userns = {
            "checkpoint_ok": 0,
            "restore_ok": 0,
            "state_continued": 0,
            "restore_error": first_line(read_text(phase_err)),
            "invoke_rc": phase_rc,
        }
    userns["invoke_rc"] = phase_rc
    row = build_row(rootless, userns, info)
    text = json.dumps(row, indent=2) + "\n"
    (work / "results.json").write_text(text, encoding="utf-8")
    if args.results:
        dest = Path(args.results)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    print_summary(row)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
