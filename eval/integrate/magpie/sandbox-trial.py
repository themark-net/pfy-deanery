#!/usr/bin/env python3
"""Sandbox eval body for magpie: what it touches in a throwaway HOME.

Usage (run by scripts/integrations/sandlock/trial.py inside sandlock):
  sandbox-trial.py MAGPIE_BIN STAGE_DIR

HOME, XDG dirs and PATH point into STAGE_DIR. Fake agent configs and fake
agent CLIs (claude, codex, opencode, gemini) are seeded there with
placeholder values; no real agent config and no real key is read. Each
magpie command runs under strace when ptrace works inside the sandbox
(sandlock denies it, so the operator traces the whole trial from outside);
the trace lists the programs it ran, the signals it sent, the sockets it
opened, and every write it attempted, allowed or denied. Writes STAGE_DIR/scan.json:
  verdict OBSERVED (the eval ran), findings = one item per HOME change and
  per takeover action seen. Exit 0 when every command finished (any exit
  code), 1 when the harness itself failed.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

binary, stage = sys.argv[1], Path(sys.argv[2])
home = stage / "home"
fakebin = stage / "bin"
traces = stage / "traces"
for d in (home, fakebin, traces):
    d.mkdir(parents=True, exist_ok=True)

SEED = {
    ".claude/settings.json": '{\n  "model": "placeholder-model"\n}\n',
    ".claude.json": '{\n  "numStartups": 1\n}\n',
    ".codex/config.toml": 'model = "placeholder-model"\n',
    ".config/opencode/opencode.json": '{\n  "model": "placeholder/model"\n}\n',
    ".gemini/settings.json": '{\n  "model": {"name": "placeholder"}\n}\n',
    ".bashrc": "# placeholder bashrc\n",
    ".profile": "# placeholder profile\n",
}
for rel, text in SEED.items():
    path = home / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
for name in ("claude", "codex", "opencode", "gemini"):
    shim = fakebin / name
    shim.write_text("#!/bin/sh\necho \"%s 1.0.0 (placeholder)\"\n" % name, encoding="utf-8")
    shim.chmod(0o755)

env = {
    "HOME": str(home),
    "XDG_CONFIG_HOME": str(home / ".config"),
    "XDG_DATA_HOME": str(home / ".local/share"),
    "XDG_CACHE_HOME": str(home / ".cache"),
    "XDG_STATE_HOME": str(home / ".local/state"),
    "PATH": "%s:/usr/bin:/bin" % fakebin,
    "LANG": "C.UTF-8",
    "TMPDIR": str(stage / "tmp"),
    "NO_COLOR": "1",
}
(stage / "tmp").mkdir(exist_ok=True)

STEPS = [
    ["--version"],
    ["ls"],
    ["provider", "add", "Local", "url=http://127.0.0.1:11434/v1", "key=placeholder-not-a-key", "models=local-model"],
    ["providers"],
    ["claude", "local/local-model"],
    ["codex", "local/local-model"],
    ["opencode", "local/local-model"],
    ["gemini", "local/local-model"],
    ["ls"],
    ["accounts", "--json"],
    ["autostart", "on"],
    ["autostart", "off"],
    ["daemon", "install"],
    ["library", "sync"],
    ["web", "--no-open", "--addr", "127.0.0.1:34250"],
    ["claude", "default"],
    ["codex", "default"],
    ["uninstall", "--yes"],
]


def snapshot() -> dict:
    out = {}
    for path in sorted(home.rglob("*")):
        if path.is_symlink():
            out[str(path.relative_to(home))] = "link:" + os.readlink(path)
        elif path.is_file():
            out[str(path.relative_to(home))] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return out


def label(text: str) -> str:
    text = re.sub(r"([?&]k=)[0-9A-Za-z._~-]+", r"\1<redacted>", text)
    return text.replace(str(home), "~").replace(str(stage), "{stage}")


strace = shutil.which("strace")
if strace and subprocess.run([strace, "-o", os.devnull, "true"], capture_output=True).returncode != 0:
    strace = None  # sandlock denies ptrace; trace the whole trial from outside instead
WRITE_FLAGS = re.compile(r"O_WRONLY|O_RDWR|O_CREAT|O_TRUNC")
steps = []
execs, signals, sockets, writes_denied, writes_outside = set(), set(), set(), set(), set()
before_all = snapshot()
for n, args in enumerate(STEPS):
    before = snapshot()
    trace = traces / ("step%02d.log" % n)
    cmd = [binary, *args]
    if strace:
        cmd = [strace, "-f", "-qq", "-s", "200", "-o", str(trace), "-e",
               "trace=execve,kill,tgkill,ptrace,connect,bind,openat,mkdirat,renameat,renameat2,unlinkat,symlinkat,linkat", *cmd]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=8 if args[0] == "web" else 30, stdin=subprocess.DEVNULL)
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = "timeout", (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""), ""
    after = snapshot()
    changed = sorted(k for k in after if before.get(k) != after[k])
    removed = sorted(k for k in before if k not in after)
    if trace.is_file():
        for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r'execve\("([^"]+)"', line)
            if m and "= 0" in line and m.group(1) != binary:
                execs.add(label(m.group(1)))
            if re.search(r"\b(kill|tgkill)\(", line) and "SIGURG" not in line:
                signals.add(label(line.split(" ", 1)[1][:160]))
            if re.search(r"\b(connect|bind)\(", line) and "AF_UNIX" not in line or ("connect(" in line and "sun_path" in line):
                sockets.add(label(re.sub(r"^\d+\s+", "", line)[:200]))
            m = re.search(r'(openat|mkdirat|renameat2?|unlinkat|symlinkat|linkat)\([^"]*"([^"]+)"(.*)', line)
            if m:
                path, rest = m.group(2), m.group(3)
                is_write = m.group(1) != "openat" or WRITE_FLAGS.search(rest)
                if is_write and path.startswith("/") and not path.startswith((str(stage), "/dev/null", "/proc/self")):
                    if "EACCES" in line or "EPERM" in line or "EROFS" in line:
                        writes_denied.add(label(path))
                    elif "= -1" not in line:
                        writes_outside.add(label(path))
    steps.append({
        "args": ["magpie", *[("key=<placeholder>" if a.startswith("key=") else a) for a in args]],
        "exit": code,
        "home_changed": changed,
        "home_removed": removed,
        "stdout_head": label(out)[:400],
        "stderr_head": label(err)[:400],
    })

after_all = snapshot()
configs = {}
for rel in SEED:
    path = home / rel
    configs[rel] = path.read_text(encoding="utf-8", errors="replace")[:600] if path.is_file() else None
findings = []
for rel in sorted(set(after_all) | set(before_all)):
    if before_all.get(rel) != after_all.get(rel):
        findings.append({"kind": "home-file", "path": "~/" + rel,
                         "change": "added" if rel not in before_all else "removed" if rel not in after_all else "modified"})
for item in sorted(execs):
    findings.append({"kind": "exec", "program": item})
for item in sorted(signals):
    findings.append({"kind": "signal", "call": item})
for item in sorted(sockets):
    findings.append({"kind": "socket", "call": item})
for item in sorted(writes_denied):
    findings.append({"kind": "write-denied-outside-stage", "path": item})
for item in sorted(writes_outside):
    findings.append({"kind": "write-outside-stage", "path": item})
doc = {
    "verdict": "OBSERVED",
    "strace": bool(strace),
    "steps": steps,
    "home_touched_during_run": sorted({f["path"] for f in findings if f["kind"] == "home-file"}),
    "seeded_configs_after_uninstall": configs,
    "findings": findings,
}
(stage / "scan.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
print("steps=%d findings=%d strace=%s" % (len(steps), len(findings), bool(strace)))
