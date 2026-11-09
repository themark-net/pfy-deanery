#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 109-111 (smolvm, Brigade, runx). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_109_111.py --entry smolvm|brigade|runx

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs anything; every scratch file goes to a fresh tempfile directory that is removed. Tool subprocesses
get a fresh temp HOME and an env scrubbed of paid provider keys and token-like names. No smoke calls a model.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the per-command tool timeouts (default 120s; 300s for smolvm
commands that may pull an image); empty or invalid keeps the default.

When bubblewrap (`bwrap`) is on PATH and works, the brigade and runx commands run inside it with a read-only root,
only the temp HOME and the scratch dir writable, no network, and its own PID namespace, so a write anywhere else
or a network call fails the step. smolvm is never run under bwrap. Every tool command runs in its own session and
a timeout SIGKILLs its whole process group, so no forked child outlives the smoke. Without bwrap the smoke falls back to checking that the tool's real-HOME state dirs were not
created or modified. The receipt records which mode ran (`containment`).

  smolvm   $SMOLVM_BIN, then ~/DEVELOP/pfy-mentat/tmp/smolvm/smolvm (the wrapper script from the v1.26.1
           smolvm-1.26.1-linux-x86_64.tar.gz release, unpacked as-is), then PATH. The `smolvm-bin` next to the
           wrapper is pinned by sha256 ($SMOLVM_SHA256 overrides); a mismatch exits 2 without exec. Exits 2 if
           /dev/kvm is missing or not read/write for this user ($PFY_SMOLVM_KVM_PATH overrides that path).
           In a temp HOME: `machine run --image <digest-pinned ref>` (no --net, no mounts) must print a marker,
           report a guest kernel different from the host's, and not see a host sentinel file; the sentinel must
           be unchanged afterwards and the real HOME's ~/.cache/smolvm and ~/.local/share/smolvm must not be
           created or modified. The ref is SMOLVM_IMAGE_PIN unless $SMOLVM_IMAGE is itself digest-pinned
           (`name@sha256:<64 hex>`); anything else exits 2 before the KVM check. The receipt records `image`,
           `image_digest` (the sha256 part of that ref) and `image_digest_source` (`pin` or `env`). A digest is
           never taken from tool or guest output. After `machine run` succeeds, stderr must contain
           `Pulling image <ref>` or stdout must have a `Using cached image` / `Caching image` line; that line
           is `image_evidence`, and missing evidence FAILs. A passing run sets a short `reason`.
           SMOLVM_CHECKPOINT=1 adds checkpoint and
           rewind: write gen1 in a persistent machine, `machine checkpoint`, write gen2, `machine create --from`
           the checkpoint, and the restored machine must read gen1 while the source reads gen2; both machines
           are deleted afterwards. Never uses the curl | bash installer.
  brigade  $BRIGADE_BIN, then ~/DEVELOP/pfy-mentat/tmp/brigade/.venv/bin/brigade (a venv with
           `pip install brigade-cli==0.27.0`), then PATH; `brigade --version` must be 0.27.0 ($BRIGADE_VERSION
           overrides) or the smoke exits 2. Plus git. BRIGADE_NO_UPDATE_CHECK=1 is set (Brigade otherwise
           refreshes a version check against check.brigade.tools in a detached child). In a throwaway git repo:
           `init --depth repo --harnesses none --no-wire`, add a task, `work ready` lists it, one actor claims it
           and a second claim finds no ready work, a passing `work verify run` writes a completed receipt bound to
           HEAD, a failing one records the real exit code (3), `receipts verify` reports every digest OK, and a
           tampered log makes it report a mismatch and exit nonzero. FAILs if the temp HOME gains an update-check
           cache.
  runx     $RUNX_BIN, then ~/DEVELOP/pfy-mentat/tmp/runx/runx (from runx-0.9.1-x86_64-unknown-linux-musl.tar.gz),
           then PATH. The v0.9.1 binary is pinned by sha256 ($RUNX_SHA256 overrides); a mismatch exits 2 without
           exec. Plus the upstream example from $RUNX_SRC or ~/DEVELOP/pfy-mentat/tmp/runx/src (a clone at tag
           cli-v0.9.1; main has a different example layout) and Node from $RUNX_NODE, ~/DEVELOP/pfy-mentat/tmp/
           runx/node/bin/node, or PATH. A copy of examples/hello-world runs with a throwaway Ed25519 seed
           (issuer type `ci`), receipts go to the scratch dir, the run must be `sealed` with the input echoed,
           `runx verify` must find the receipt valid in production signature mode, and a different key or a
           tampered receipt must be reported invalid. Every RUNX_* variable from the parent env is dropped;
           no login, no registry, no hosted surface.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from smoke import TMP, find_bin, pinned, run, scrub_env, timeout_reason, write

# smolvm v1.26.1 smolvm-1.26.1-linux-x86_64.tar.gz: smolvm-bin (matches the tarball's own checksums.txt; the tarball
# itself is sha256 bcae519f7dad3cead2deaa0362a42a1ad7bffce73ea7a28161dea6822c559654 in the release checksums.sha256)
SMOLVM_V1261_BIN_SHA256 = "62ed0353d664c2d6d78bd87ecf3213c64464003f51cb58506b87b187b1a6494a"
# alpine 3.22 multi-arch index digest, resolved 2026-10-17 from registry-1.docker.io.
SMOLVM_IMAGE_PIN = "alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8"
_PINNED_IMAGE_REF = re.compile(r"@sha256:[0-9a-f]{64}$", re.IGNORECASE)
_IMAGE_CACHE_LINE = re.compile(r"^(Using cached|Caching) image [0-9a-f]{16}\b")
# runx cli-v0.9.1 runx-0.9.1-x86_64-unknown-linux-musl.tar.gz: the `runx` binary inside (the tarball itself is
# sha256 59eee2af81d24d0f8ba2416e2bac55d147ed93693e6a41ffe7c2cfd5cba98cc7, matching the upstream .sha256 asset)
RUNX_V091_SHA256 = "e0c0627882c2ce7a4e8cfb20cf4896a4aa371db0e13c95c8b86fa31276388b60"
BRIGADE_PIN = "0.27.0"
DROP_PREFIXES = ("XDG_", "RUNX_", "SMOLVM_", "BRIGADE_")


def xintake_timeout(default: float) -> float:
    """Seconds from PFY_XINTAKE_TIMEOUT when that value is a float > 0; otherwise default."""
    raw = (os.environ.get("PFY_XINTAKE_TIMEOUT") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_env(home: str, **extra: str) -> dict:
    env = {k: v for k, v in scrub_env(os.environ).items() if not k.startswith(DROP_PREFIXES)}
    env.update(HOME=home, NO_COLOR="1", **extra)
    return env


def call(cmd: list[str], cwd: str, env: dict, r: dict, tag: str, timeout: float = 120) -> subprocess.CompletedProcess | None:
    """Run cmd in its own session; on timeout SIGKILL the whole process group, not just the direct child."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                            start_new_session=True)
    limit = xintake_timeout(timeout)
    try:
        out, err = proc.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:  # a descendant that left the group still holds the pipes
            proc.kill()
            proc.wait()
        r["reason"] = timeout_reason(tag, limit)
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def last_json(text: str) -> dict | None:
    """The JSON object a CLI printed with --json (whole stdout, else from the first '{')."""
    for chunk in (text, text[text.find("{"):] if "{" in text else ""):
        try:
            o = json.loads(chunk)
            return o if isinstance(o, dict) else None
        except ValueError:
            continue
    return None


def state_snapshot(paths: list[Path]) -> dict:
    """One value per path: streamed bytes, lstat mode, and symlink text. None if missing.

    mtime is not part of the value. Symlinks are not followed. An unreadable file is recorded.
    """
    import stat

    def add(h, node: Path) -> None:
        try:
            st = os.lstat(node)
        except OSError:
            h.update(f"{node}:unreadable\n".encode())
            return
        mode = stat.S_IMODE(st.st_mode)
        if stat.S_ISLNK(st.st_mode):
            try:
                link = os.readlink(node)
            except OSError:
                h.update(f"{node}:{mode:o}:unreadable\n".encode())
                return
            h.update(f"{node}:{mode:o}:link:{link}\n".encode())
            return
        if stat.S_ISREG(st.st_mode):
            try:
                fh = hashlib.sha256()
                with open(node, "rb") as fp:  # 1 MiB chunks; a large file stays out of RAM
                    for chunk in iter(lambda: fp.read(1 << 20), b""):
                        fh.update(chunk)
                digest = fh.hexdigest()
            except OSError:
                h.update(f"{node}:{mode:o}:unreadable\n".encode())
                return
            h.update(f"{node}:{mode:o}:{digest}\n".encode())
            return
        if stat.S_ISDIR(st.st_mode):
            h.update(f"{node}:{mode:o}:dir\n".encode())
            try:
                names = sorted(os.listdir(node))
            except OSError:
                h.update(f"{node}:{mode:o}:unreadable\n".encode())
                return
            for name in names:
                add(h, node / name)
            return
        h.update(f"{node}:{mode:o}:other\n".encode())

    out = {}
    for p in paths:
        try:
            os.lstat(p)
        except FileNotFoundError:
            out[str(p)] = None
            continue
        except OSError:
            out[str(p)] = hashlib.sha256(f"{p}:unreadable\n".encode()).hexdigest()
            continue
        h = hashlib.sha256()
        add(h, p)
        out[str(p)] = h.hexdigest()
    return out


def bwrap_prefix(writable: list[str]) -> list[str] | None:
    """A bubblewrap prefix with a read-only root, only `writable` binds writable, and no network; None if unusable."""
    bw = shutil.which("bwrap")
    if not bw:
        return None
    base = [bw, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-net", "--unshare-pid",
            "--die-with-parent"]
    try:
        if subprocess.run(base + ["true"], capture_output=True, timeout=30).returncode != 0:
            return None
    except (OSError, subprocess.TimeoutExpired):
        return None
    for w in writable:
        base += ["--bind", w, w]
    return base


def smolvm_image(r: dict) -> str | None:
    """Digest-pinned ref. Records image, image_digest, image_digest_source. None means exit 2."""
    raw = (os.environ.get("SMOLVM_IMAGE") or "").strip()
    if raw:
        if not _PINNED_IMAGE_REF.search(raw):
            r["reason"] = "SMOLVM_IMAGE must be digest-pinned (name@sha256:<64 hex>)"
            return None
        image, source = raw.lower(), "env"
    else:
        image, source = SMOLVM_IMAGE_PIN, "pin"
    r["image"] = image
    r["image_digest"] = image.split("@", 1)[1]
    r["image_digest_source"] = source
    return image


def smolvm_image_evidence(stdout: str, stderr: str, image: str) -> str | None:
    """Cache line from stdout, else the pull line from stderr. Not a digest from the output."""
    for raw_line in stdout.splitlines():
        line = raw_line.split("\r")[-1].strip()
        if _IMAGE_CACHE_LINE.match(line):
            return line
    needle = "Pulling image " + image
    for raw_line in stderr.splitlines():
        line = raw_line.split("\r")[-1].strip()
        if needle in line:
            return line
    return None


# ---------------------------------------------------------------- smolvm

def smoke_smolvm(r: dict) -> int:
    image = smolvm_image(r)
    if image is None:
        return 2
    b = find_bin("SMOLVM_BIN", "smolvm/smolvm", "smolvm")
    r["bin"] = b
    if not b:
        r["reason"] = ("no smolvm. Operator: download smolvm-1.26.1-linux-x86_64.tar.gz and checksums.sha256 from "
                       "https://github.com/smol-machines/smolvm/releases/tag/v1.26.1, check the tarball sha256 "
                       "(bcae519f7dad3cead2deaa0362a42a1ad7bffce73ea7a28161dea6822c559654), and unpack it as "
                       "~/DEVELOP/pfy-mentat/tmp/smolvm/ (wrapper `smolvm`, `smolvm-bin`, lib/, agent-rootfs/). Not "
                       "the curl | bash installer (installs outside ~/DEVELOP), not brew")
        return 2
    real = os.path.realpath(b)
    payload = os.path.join(os.path.dirname(real), "smolvm-bin")
    if not os.path.isfile(payload):
        payload = real
    expect = pinned(r, "SMOLVM_SHA256", SMOLVM_V1261_BIN_SHA256, lower=True)
    digest = sha256_file(payload)
    r["pinned_file"], r["sha256"] = payload, digest
    if digest != expect:
        r["reason"] = f"sha256 mismatch: {os.path.basename(payload)} is {digest}, expected {expect}"
        return 2
    kvm = os.environ.get("PFY_SMOLVM_KVM_PATH") or "/dev/kvm"
    r["kvm_path"] = kvm
    r["kvm_present"] = os.path.exists(kvm)
    r["kvm_rw"] = r["kvm_present"] and os.access(kvm, os.R_OK | os.W_OK)
    if not r["kvm_rw"]:
        r["reason"] = ("no " + kvm if not r["kvm_present"] else
                       kvm + " is not read/write for this user (smolvm needs KVM; on Linux that is usually the "
                       "`kvm` group, a system change that needs the operator's approval on nimo)")
        return 2
    real_home = Path.home()
    watched = [real_home / ".cache/smolvm", real_home / ".local/share/smolvm"]
    before = state_snapshot(watched)
    with tempfile.TemporaryDirectory(prefix="pfy-smolvm-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-smolvm-home-") as home:
        env = clean_env(home)
        sentinel = Path(d, "host-sentinel.txt")
        sentinel.write_text("pfy host sentinel\n")
        sent_sha = sha256_file(str(sentinel))
        sv = lambda tag, *a, t=300: call([b, *a], d, env, r, f"smolvm {tag}", timeout=t)
        script = f"echo pfy-smolvm-ok; uname -r; test ! -e {sentinel} && echo host-hidden; rm -f {sentinel}; true"
        p = sv("run", "machine", "run", "--image", image, "--", "sh", "-c", script)
        if p is None:
            return 1
        lines = p.stdout.splitlines()
        r["run_rc"], r["run_stdout"] = p.returncode, lines[-10:]
        if p.returncode != 0 or "pfy-smolvm-ok" not in lines:
            r["reason"] = f"`machine run` failed (exit {p.returncode}): {(p.stdout + p.stderr)[-400:]}"
            return 1
        evidence = smolvm_image_evidence(p.stdout or "", p.stderr or "", image)
        if not evidence:
            r["reason"] = "smolvm did not report pulling or caching the pinned image"
            return 1
        r["image_evidence"] = evidence
        guest_kernel = lines[lines.index("pfy-smolvm-ok") + 1] if lines.index("pfy-smolvm-ok") + 1 < len(lines) else ""
        r["guest_kernel"], r["host_kernel"] = guest_kernel, platform.release()
        if not guest_kernel or guest_kernel == platform.release():
            r["reason"] = "guest reported the host kernel (no separate VM kernel?)"
            return 1
        if "host-hidden" not in lines:
            r["reason"] = "the guest could see a host file it was not given"
            return 1
        if not sentinel.is_file() or sha256_file(str(sentinel)) != sent_sha:
            r["reason"] = "host sentinel changed or removed by the guest"
            return 1
        if os.environ.get("SMOLVM_CHECKPOINT") == "1":
            code = smolvm_checkpoint(sv, d, image, r)
            if code:
                return code
        r["temp_home_used"] = Path(home, ".cache/smolvm").exists() or Path(home, ".local/share/smolvm").exists()
    after = state_snapshot(watched)
    r["real_home_state_unchanged"] = before == after
    if before != after:
        r["reason"] = f"smolvm state written into the real HOME: {after}"
        return 1
    r["reason"] = f"ok: guest kernel {guest_kernel}, host file hidden"
    return 0


def smolvm_checkpoint(sv, d: str, image: str, r: dict) -> int:
    tag = uuid.uuid4().hex[:8]
    src, restored = f"pfy-smoke-src-{tag}", f"pfy-smoke-rst-{tag}"
    ck = os.path.join(d, "src.checkpoint")
    created = []
    try:
        steps = [("create", ["machine", "create", "--name", src, "--image", image, "--", "sh", "-c", "exec sleep 86400"]),
                 ("start", ["machine", "start", "--name", src, "--branchable"]),
                 ("write gen1", ["machine", "exec", "--name", src, "--", "sh", "-c", "echo gen1 > /root/marker"]),
                 ("checkpoint", ["machine", "checkpoint", "--name", src, "-o", ck]),
                 ("write gen2", ["machine", "exec", "--name", src, "--", "sh", "-c", "echo gen2 > /root/marker"]),
                 ("restore", ["machine", "create", "--name", restored, "--from", ck]),
                 ("start restored", ["machine", "start", "--name", restored, "--branchable"])]
        for name, args in steps:
            p = sv(name, *args)
            if p is None:
                return 1
            if name == "create":
                created.append(src)
            if name == "restore" and p.returncode == 0:
                created.append(restored)
            if p.returncode != 0:
                r["reason"] = f"checkpoint step `{name}` exited {p.returncode}: {(p.stdout + p.stderr)[-300:]}"
                return 1
        got = {}
        for m in (restored, src):
            p = sv(f"read {m}", "machine", "exec", "--name", m, "--", "cat", "/root/marker")
            if p is None:
                return 1
            got[m] = p.stdout.strip()
        r["checkpoint"] = {"restored_reads": got[restored], "source_reads": got[src]}
        if got[restored] != "gen1" or got[src] != "gen2":
            r["reason"] = f"rewind did not restore the checkpointed disk state: {r['checkpoint']}"
            return 1
        return 0
    finally:
        for m in created:
            sv(f"stop {m}", "machine", "stop", "--name", m, t=120)
            sv(f"delete {m}", "machine", "delete", "--name", m, t=120)


# ---------------------------------------------------------------- brigade

def smoke_brigade(r: dict) -> int:
    b = find_bin("BRIGADE_BIN", "brigade/.venv/bin/brigade", "brigade")
    r["bin"] = b
    op = ("Operator: python3 -m venv ~/DEVELOP/pfy-mentat/tmp/brigade/.venv && ~/DEVELOP/pfy-mentat/tmp/brigade/.venv/"
          f"bin/pip install brigade-cli=={BRIGADE_PIN} (MIT, Python 3.10+, no runtime deps). Not pipx/uv tool install "
          "into the real HOME, no `brigade setup`, no `brigade operator quickstart` in a product checkout")
    if not b:
        r["reason"] = f"no brigade. {op}"
        return 2
    if not shutil.which("git"):
        r["reason"] = "git not on PATH"
        return 2
    want = pinned(r, "BRIGADE_VERSION", BRIGADE_PIN)
    with tempfile.TemporaryDirectory(prefix="pfy-brigade-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-brigade-home-") as home:
        env = clean_env(home, BRIGADE_NO_UPDATE_CHECK="1",
                        GIT_AUTHOR_NAME="smoke", GIT_AUTHOR_EMAIL="smoke@localhost",
                        GIT_COMMITTER_NAME="smoke", GIT_COMMITTER_EMAIL="smoke@localhost",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        p = call([b, "--version"], d, env, r, "brigade --version", timeout=60)
        if p is None:
            return 1
        r["version"] = p.stdout.strip()
        if p.returncode != 0 or r["version"].split()[-1:] != [want]:
            r["reason"] = f"brigade --version is {r['version']!r}, expected {want}. {op}"
            return 2
        repo = os.path.join(d, "repo")
        os.mkdir(repo)
        prefix = bwrap_prefix([d, home])
        r["containment"] = "bwrap-ro-root-no-net" if prefix else "real-home-snapshot"
        real_home = Path.home()
        watched = [real_home / n for n in (".brigade", ".config/brigade", ".cache/brigade", ".local/share/brigade",
                                           ".local/state/brigade")]
        before = state_snapshot(watched)
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env=env, timeout=60)
        g("init", "-q", "-b", "main")
        g("commit", "-q", "--allow-empty", "-m", "init")

        def br(tag: str, *a: str) -> subprocess.CompletedProcess | None:
            return call((prefix or []) + [b, *a], repo, env, r, f"brigade {tag}")

        p = br("init", "init", "--target", ".", "--depth", "repo", "--harnesses", "none", "--no-wire")
        if p is None:
            return 1
        if p.returncode != 0 or not os.path.isfile(os.path.join(repo, ".brigade/config.json")):
            r["reason"] = f"`brigade init` failed or wrote no .brigade/config.json (exit {p.returncode}): " \
                          f"{(p.stdout + p.stderr)[-300:]}"
            return 1
        g("add", "-A")
        g("commit", "-q", "-m", "brigade scaffold")
        p = br("task add", "work", "task", "add", "--target", ".", "--acceptance", "smoke passes", "Add a smoke script")
        if p is None:
            return 1
        if p.returncode != 0:
            r["reason"] = f"`work task add` exited {p.returncode}: {(p.stdout + p.stderr)[-300:]}"
            return 1
        p = br("ready", "work", "ready", "--target", ".", "--json")
        ready = last_json(p.stdout) if p else None
        if not ready or ready.get("ready_count") != 1:
            r["reason"] = f"`work ready` did not list the one task: {(p.stdout + p.stderr)[-300:] if p else ''}"
            return 1
        task_id = ready["ready"][0].get("id")
        p = br("claim a", "work", "claim", "--target", ".", "--actor", "smoke-a", "--next", "--json")
        ca = last_json(p.stdout) if p else None
        p2 = br("claim b", "work", "claim", "--target", ".", "--actor", "smoke-b", "--next", "--json")
        cb = last_json(p2.stdout) if p2 else None
        r["claims"] = {"a": ca and {k: ca.get(k) for k in ("task_id", "status", "assignee")},
                       "b": cb and {k: cb.get(k) for k in ("reason", "exit_code")}, "b_rc": p2 and p2.returncode}
        if not ca or ca.get("task_id") != task_id or ca.get("status") != "in_progress" or ca.get("assignee") != "smoke-a":
            r["reason"] = "first claim did not take the ready task"
            return 1
        if not p2 or p2.returncode == 0 or not cb or cb.get("reason") != "no_ready":
            r["reason"] = "a second actor could claim already-claimed work"
            return 1
        head = g("rev-parse", "HEAD").stdout.strip()
        p = br("verify pass", "work", "verify", "run", "--target", ".", "--no-reuse",
               "--argv-json", json.dumps(["python3", "-c", "print('pfy-ok')"]), "--json")
        vp = last_json(p.stdout) if p else None
        if not vp or p.returncode != 0 or vp.get("status") != "completed" \
                or (vp.get("git") or {}).get("head") != head or [c.get("exit_code") for c in vp.get("commands", [])] != [0]:
            r["reason"] = f"passing verify did not write a completed receipt at HEAD: {(p.stdout + p.stderr)[-300:] if p else ''}"
            return 1
        p = br("verify fail", "work", "verify", "run", "--target", ".", "--no-reuse",
               "--argv-json", json.dumps(["python3", "-c", "import sys; sys.exit(3)"]), "--json")
        vf = last_json(p.stdout) if p else None
        r["verify"] = {"pass_status": vp.get("status"), "fail_status": vf and vf.get("status"),
                       "fail_exit_codes": vf and [c.get("exit_code") for c in vf.get("commands", [])],
                       "fail_rc": p and p.returncode}
        if not vf or p.returncode == 0 or vf.get("status") != "failed" or r["verify"]["fail_exit_codes"] != [3]:
            r["reason"] = "failing verify did not record the real exit code"
            return 1
        p = br("receipts verify", "receipts", "verify", "--target", ".", "--json")
        rv = last_json(p.stdout) if p else None
        s = (rv or {}).get("summary") or {}
        r["receipts_clean"] = s
        if not p or p.returncode != 0 or not s.get("ok") or s.get("mismatch") or s.get("missing") \
                or s.get("ok") != s.get("total"):
            r["reason"] = f"`receipts verify` not clean on untouched receipts: {s}"
            return 1
        log = Path(vp.get("commands")[0].get("stdout_log_path") or "")
        if not log.is_file():
            r["reason"] = "passing receipt names no stdout log (receipt shape changed?)"
            return 1
        with open(log, "a") as fh:
            fh.write("tampered\n")
        p = br("receipts verify tampered", "receipts", "verify", "--target", ".", "--json")
        rt = last_json(p.stdout) if p else None
        s2 = (rt or {}).get("summary") or {}
        r["receipts_tampered"], r["tampered_rc"] = s2, p and p.returncode
        if not p or p.returncode == 0 or s2.get("mismatch") != 1:
            r["reason"] = f"a tampered log was not reported as a digest mismatch: {s2}"
            return 1
        home_files = sorted(str(Path(root, f).relative_to(home)) for root, _, fs in os.walk(home) for f in fs)
        r["temp_home_files"] = home_files[:20]
        if any("update-notify" in f for f in home_files):
            r["reason"] = "update check ran despite BRIGADE_NO_UPDATE_CHECK"
            return 1
    after = state_snapshot(watched)
    r["real_home_state_unchanged"] = before == after
    if before != after:
        r["reason"] = f"brigade state written into the real HOME: {after}"
        return 1
    return 0


# ---------------------------------------------------------------- runx

def smoke_runx(r: dict) -> int:
    b = find_bin("RUNX_BIN", "runx/runx", "runx")
    r["bin"] = b
    if not b:
        r["reason"] = ("no runx. Operator: download runx-0.9.1-x86_64-unknown-linux-musl.tar.gz and its .sha256 from "
                       "https://github.com/runxhq/runx/releases/tag/cli-v0.9.1, check it (sha256 59eee2af81d24d0f8b"
                       "a2416e2bac55d147ed93693e6a41ffe7c2cfd5cba98cc7), and unpack runx + runx-js-worker into "
                       "~/DEVELOP/pfy-mentat/tmp/runx/. Not the curl | sh installer, not npm i -g, no `runx login`")
        return 2
    expect = pinned(r, "RUNX_SHA256", RUNX_V091_SHA256, lower=True)
    digest = sha256_file(b)
    r["sha256"] = digest
    if digest != expect:
        r["reason"] = f"sha256 mismatch: runx binary is {digest}, expected {expect}"
        return 2
    src = None
    for c in (os.environ.get("RUNX_SRC"), str(TMP / "runx/src")):
        if c and os.path.isfile(os.path.join(c, "examples/hello-world/X.yaml")):
            src = c
            break
    r["src"] = src
    if not src:
        r["reason"] = ("no runx example. Operator: git clone --depth 1 --branch cli-v0.9.1 https://github.com/runxhq/"
                       "runx.git ~/DEVELOP/pfy-mentat/tmp/runx/src (main uses a different example layout)")
        return 2
    node = None
    for c in (os.environ.get("RUNX_NODE"), str(TMP / "runx/node/bin/node"), shutil.which("node")):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            node = c
            break
    r["node"] = node
    if not node:
        r["reason"] = "no node (the hello-world runner runs `node run.mjs`); set $RUNX_NODE"
        return 2
    with tempfile.TemporaryDirectory(prefix="pfy-runx-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-runx-home-") as home:
        shutil.copytree(os.path.join(src, "examples/hello-world"), os.path.join(d, "hello-world"))
        receipts = os.path.join(d, "receipts")
        seed = lambda: base64.b64encode(os.urandom(32)).decode()
        env = clean_env(home, PATH=os.path.dirname(node) + os.pathsep + os.environ.get("PATH", ""),
                        RUNX_RECEIPT_SIGN_KID="pfy-smoke", RUNX_RECEIPT_SIGN_ISSUER_TYPE="ci",
                        RUNX_RECEIPT_SIGN_ED25519_SEED_BASE64=seed())
        prefix = bwrap_prefix([d, home])
        r["containment"] = "bwrap-ro-root-no-net" if prefix else "real-home-snapshot"
        watched = [Path.home() / ".runx", Path.home() / ".config/runx", Path.home() / ".cache/runx"]
        before = state_snapshot(watched)
        rx = lambda tag, e, *a: call((prefix or []) + [b, *a], d, e, r, f"runx {tag}")
        msg = "hello from pfy smoke"
        p = rx("skill", env, "skill", "./hello-world", "-i", f"message={msg}", "-R", receipts, "--json")
        if p is None:
            return 1
        o = last_json(p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
        r["run_rc"] = p.returncode
        r["run"] = o and {k: o.get(k) for k in ("schema", "status", "outcome", "receipt_id", "result")}
        if p.returncode != 0 or not o or o.get("status") != "sealed" or (o.get("result") or {}).get("message") != msg:
            r["reason"] = f"hello-world did not seal with the input echoed (exit {p.returncode}): {(p.stdout + p.stderr)[-300:]}"
            return 1
        rid = o["receipt_id"]
        rfile = Path(receipts, rid.replace(":", "-") + ".json")
        if not rfile.is_file():
            r["reason"] = f"no receipt file {rfile.name} in the receipt dir"
            return 1

        def verify(tag: str, e: dict) -> tuple[int, dict]:
            q = rx(tag, e, "verify", rid, "--receipt-dir", receipts, "--json")
            return (-1, {}) if q is None else (q.returncode, last_json(q.stdout) or {})

        rc, v = verify("verify", env)
        r["verify"] = {"rc": rc, "valid": v.get("valid"), "signature_mode": v.get("signature_mode")}
        if rc != 0 or v.get("valid") is not True or v.get("signature_mode") != "production":
            r["reason"] = f"fresh receipt did not verify in production mode: {json.dumps(v)[:300]}"
            return 1
        rc, v = verify("verify other key", dict(env, RUNX_RECEIPT_SIGN_ED25519_SEED_BASE64=seed()))
        codes = [f.get("code") for t in v.get("trees", []) for f in t.get("findings", [])]
        r["other_key"] = {"rc": rc, "valid": v.get("valid"), "findings": codes}
        if rc == 0 or v.get("valid") is not False:
            r["reason"] = "receipt verified against a different key"
            return 1
        body = json.loads(rfile.read_text())
        body["created_at"] = "2020-01-01T00:00:00.000Z"
        rfile.write_text(json.dumps(body))
        rc, v = verify("verify tampered", env)
        codes = [f.get("code") for t in v.get("trees", []) for f in t.get("findings", [])]
        r["tampered"] = {"rc": rc, "valid": v.get("valid"), "findings": codes}
        if rc == 0 or v.get("valid") is not False:
            r["reason"] = "a tampered receipt still verified"
            return 1
        if os.path.exists(os.path.join(src, "examples/hello-world/.runx")):
            r["reason"] = "runx wrote into the source clone"
            return 1
    after = state_snapshot(watched)
    r["real_home_state_unchanged"] = before == after
    if before != after:
        r["reason"] = f"runx state written into the real HOME: {after}"
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["smolvm", "brigade", "runx"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename}
    code = {"smolvm": smoke_smolvm, "brigade": smoke_brigade, "runx": smoke_runx}[a.entry](receipt)
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
