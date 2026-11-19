#!/usr/bin/env python3
"""Run one catalog or Build lane agent in a confined rootless podman container.

Outside code is data. A lane agent reads third-party READMEs, code and web
text, so it runs as if that text were hostile:

- Container: rootless podman, --network=none, cap-drop all, no-new-privileges,
  pids and memory caps. Only the lane worktree is writable. The git common
  dir is mounted read-only. Commits go to a private object store; after the
  cage exits the driver copies new objects and only the result ref back onto
  the host. Other lanes' worktree metadata stays read-only. The quarantine
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
from dataclasses import dataclass
import hashlib
import json
import os
import shutil
import stat
import socket
import subprocess
import sys
import tempfile
import threading
import zlib
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


class GitStoreError(CageError):
    """Copy-back of the private git store was refused. The shared store is unchanged."""


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


@dataclass
class GitStore:
    """Private git state for one cage run. The shared common dir stays read-only."""

    wt: Path
    common: Path
    gitdir: Path
    objects: Path
    overlay: Path
    kind: str
    start_ref: str
    start_sha: str
    gitfile_orig: str | None = None


def _head_info(wt: Path) -> tuple[str, str]:
    ref_p = subprocess.run(["git", "-C", str(wt), "symbolic-ref", "-q", "HEAD"],
                           capture_output=True, text=True)
    ref = ref_p.stdout.strip() if ref_p.returncode == 0 else ""
    sha_p = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                           capture_output=True, text=True)
    sha = sha_p.stdout.strip() if sha_p.returncode == 0 else ""
    return ref, sha


def prepare_git_store(wt: Path, cage: Path) -> GitStore | None:
    common, gitdir = git_paths(wt)
    if common is None or gitdir is None:
        return None
    common = common.resolve()
    gitdir = gitdir.resolve()
    root = cage / "git"
    objects = root / "objects"
    (objects / "info").mkdir(parents=True, exist_ok=True)
    (objects / "pack").mkdir(parents=True, exist_ok=True)
    (objects / "info" / "alternates").write_text(str(common / "objects") + "\n", encoding="utf-8")
    start_ref, start_sha = _head_info(wt)
    kind = "plain" if gitdir == common else "worktree"
    overlay = root / "overlay"
    if overlay.exists():
        shutil.rmtree(overlay)
    if kind == "worktree":
        shutil.copytree(gitdir, overlay, symlinks=True, ignore=shutil.ignore_patterns("*.lock"))
        (overlay / "commondir").write_text(str(common) + "\n", encoding="utf-8")
    else:
        overlay.mkdir(parents=True)
        (overlay / "commondir").write_text(str(common) + "\n", encoding="utf-8")
        for name in ("HEAD", "index", "COMMIT_EDITMSG", "ORIG_HEAD"):
            src = gitdir / name
            dst = overlay / name
            if src.is_file():
                shutil.copy2(src, dst)
            else:
                dst.write_bytes(b"")
        logs_src = gitdir / "logs"
        logs_dst = overlay / "logs"
        if logs_src.is_dir():
            shutil.copytree(logs_src, logs_dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.lock"))
        else:
            logs_dst.mkdir()
            (logs_dst / "HEAD").write_bytes(b"")
    if start_sha:
        (overlay / "HEAD").write_text(start_sha + "\n", encoding="utf-8")
    return GitStore(wt=wt, common=common, gitdir=gitdir, objects=objects, overlay=overlay,
                    kind=kind, start_ref=start_ref, start_sha=start_sha)


def git_mounts(wt: Path, store: GitStore | None = None) -> list[str]:
    if store is None:
        return []
    common, gitdir = store.common, store.gitdir
    vols = [f"--volume={common}:{common}:ro"]
    for sub in ("config", "hooks", "info"):
        p = common / sub
        if p.exists():
            vols.append(f"--volume={p}:{p}:ro")
    wts = common / "worktrees"
    if wts.is_dir():
        vols.append(f"--volume={wts}:{wts}:ro")
    # Overlay is always mounted at its own path so GIT_DIR works. For a
    # worktree, also remount it over the real gitdir so tools that ignore
    # GIT_DIR still cannot write the host metadata.
    vols.append(f"--volume={store.overlay}:{store.overlay}:rw")
    if store.kind == "worktree":
        vols.append(f"--volume={store.overlay}:{gitdir}:rw")
    vols.append(f"--volume={store.objects}:{store.objects}:rw")
    return vols


def git_store_envs(store: GitStore | None) -> list[str]:
    if store is None:
        return []
    # GIT_DIR is only for a plain repo. It would leak into `git -C other`
    # inside the lane, which the card-guard stubs (and real lane scripts)
    # rely on. Worktrees instead retarget wt/.git at the overlay for the
    # run (see activate_git_store), which fake_podman honors.
    envs = [
        f"--env=GIT_OBJECT_DIRECTORY={store.objects}",
        f"--env=GIT_ALTERNATE_OBJECT_DIRECTORIES={store.common / 'objects'}",
    ]
    if store.kind == "plain":
        envs += [
            f"--env=GIT_DIR={store.overlay}",
            f"--env=GIT_WORK_TREE={store.wt}",
        ]
    return envs


def _hex_name(name: str, n: int) -> bool:
    return len(name) == n and all(c in "0123456789abcdef" for c in name)


def _object_format(wt: Path) -> tuple[int, object]:
    r = subprocess.run(["git", "-C", str(wt), "rev-parse", "--show-object-format"],
                       capture_output=True, text=True)
    kind = (r.stdout or "sha1").strip() or "sha1"
    if kind == "sha256":
        return 64, hashlib.sha256
    return 40, hashlib.sha1


def _verify_loose_file(path: Path, expected_sha: str, hasher) -> bytes:
    """Read a loose object with O_NOFOLLOW and require hash(header+content) == name.

    A hardlink to an outside path would share bytes with that path. Acceptance
    is still bound to the decompressed hash, so a host secret cannot land
    unless those bytes already hash to this object name.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise GitStoreError(f"cannot open object {path}: {exc}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise GitStoreError(f"object is not a regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(fd)
    data = b"".join(chunks)
    try:
        dec = zlib.decompressobj()
        raw = dec.decompress(data)
        raw += dec.flush()
    except zlib.error as exc:
        raise GitStoreError(f"loose object is not zlib data: {path}") from exc
    if dec.unconsumed_tail or dec.unused_data:
        raise GitStoreError(f"loose object has trailing data: {path}")
    digest = hasher(raw).hexdigest()
    if digest != expected_sha:
        raise GitStoreError(f"loose object hash mismatch: {path}")
    return zlib.compress(raw)


def _pack_object_ids(idx: Path, hexlen: int) -> set[str]:
    r = subprocess.run(["git", "verify-pack", "-v", str(idx)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise GitStoreError(f"git verify-pack failed for {idx.name}: {r.stderr.strip()}")
    shas: set[str] = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if parts and _hex_name(parts[0], hexlen):
            shas.add(parts[0])
    return shas


def _verify_packs(packdir: Path, hexlen: int) -> set[str]:
    packs: dict[str, Path] = {}
    idxs: dict[str, Path] = {}
    for sub in packdir.iterdir():
        try:
            st = os.lstat(sub)
        except OSError as exc:
            raise GitStoreError(f"cannot lstat pack entry {sub}: {exc}") from exc
        if not stat.S_ISREG(st.st_mode):
            raise GitStoreError(f"non-regular pack entry: {sub}")
        name = sub.name
        if name.startswith("pack-") and name.endswith(".pack"):
            hid = name[len("pack-"):-len(".pack")]
            if not _hex_name(hid, hexlen):
                raise GitStoreError(f"unexpected pack name: {name}")
            packs[hid] = sub
        elif name.startswith("pack-") and name.endswith(".idx"):
            hid = name[len("pack-"):-len(".idx")]
            if not _hex_name(hid, hexlen):
                raise GitStoreError(f"unexpected pack idx name: {name}")
            idxs[hid] = sub
        else:
            raise GitStoreError(f"unexpected pack entry: {name}")
    if set(packs) != set(idxs):
        raise GitStoreError("pack and idx names do not match")
    all_ids: set[str] = set()
    for hid, pack in packs.items():
        idx = idxs[hid]
        all_ids |= _pack_object_ids(idx, hexlen)
        r = subprocess.run(["git", "index-pack", "--verify", "--strict", str(pack)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise GitStoreError(f"git index-pack --verify failed for {pack.name}: {r.stderr.strip()}")
    return all_ids


def _scan_private_objects(store: GitStore) -> tuple[dict[str, Path], set[str], int, object]:
    """Validate every private-store entry. objects/info is skipped, never copied.

    Returns (loose sha->path, shas present in verified packs, hexlen, hasher).
    Any non-regular entry or unexpected name refuses the whole copy-back.
    """
    hexlen, hasher = _object_format(store.wt)
    src = store.objects
    loose: dict[str, Path] = {}
    pack_ids: set[str] = set()
    if not src.is_dir():
        return loose, pack_ids, hexlen, hasher
    for item in src.iterdir():
        try:
            st = os.lstat(item)
        except OSError as exc:
            raise GitStoreError(f"cannot lstat {item}: {exc}") from exc
        if item.name == "info":
            continue
        if item.name == "pack":
            if not stat.S_ISDIR(st.st_mode):
                raise GitStoreError("objects/pack is not a directory")
            pack_ids = _verify_packs(item, hexlen)
            continue
        if not stat.S_ISDIR(st.st_mode):
            raise GitStoreError(f"unexpected object store entry: {item.name}")
        if not _hex_name(item.name, 2):
            raise GitStoreError(f"unexpected object store entry: {item.name}")
        for sub in item.iterdir():
            try:
                sst = os.lstat(sub)
            except OSError as exc:
                raise GitStoreError(f"cannot lstat {sub}: {exc}") from exc
            if not stat.S_ISREG(sst.st_mode):
                raise GitStoreError(f"non-regular object: {sub}")
            if not _hex_name(sub.name, hexlen - 2):
                raise GitStoreError(f"unexpected loose object name: {sub}")
            sha = item.name + sub.name
            _verify_loose_file(sub, sha, hasher)
            loose[sha] = sub
    return loose, pack_ids, hexlen, hasher


def _private_has(sha: str, loose: dict[str, Path], pack_ids: set[str]) -> bool:
    return sha in loose or sha in pack_ids


def _raw_object(store: GitStore, sha: str) -> bytes:
    env = dict(os.environ,
               GIT_OBJECT_DIRECTORY=str(store.objects),
               GIT_ALTERNATE_OBJECT_DIRECTORIES=str(store.common / "objects"))
    typ = subprocess.run(["git", "--git-dir", str(store.overlay), "cat-file", "-t", sha],
                         capture_output=True, text=True, env=env)
    if typ.returncode != 0:
        raise GitStoreError(f"missing object {sha}: {typ.stderr.strip()}")
    kind = typ.stdout.strip()
    body = subprocess.run(["git", "--git-dir", str(store.overlay), "cat-file", kind, sha],
                          capture_output=True, env=env)
    if body.returncode != 0:
        raise GitStoreError(f"cannot read object {sha}")
    return f"{kind} {len(body.stdout)}".encode() + b"\0" + body.stdout


def _dest_status(dest: Path, sha: str, hasher) -> str:
    """Return 'missing' or 'skip'. Refuse if dest exists and does not hash to sha."""
    try:
        st = os.lstat(dest)
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        raise GitStoreError(f"cannot lstat shared object {dest}: {exc}") from exc
    if not stat.S_ISREG(st.st_mode):
        raise GitStoreError(f"shared object is not a regular file: {dest}")
    try:
        _verify_loose_file(dest, sha, hasher)
    except GitStoreError as exc:
        raise GitStoreError(f"refusing to overwrite existing object {sha}") from exc
    return "skip"


def _install_loose(dest: Path, compressed: bytes, installed: list[Path]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.pfy-cage-tmp-{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(tmp, flags, 0o644)
        try:
            view = memoryview(compressed)
            while view:
                n = os.write(fd, view)
                view = view[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.lstat(dest)
        except FileNotFoundError:
            os.rename(tmp, dest)
            installed.append(dest)
            return
        raise GitStoreError(f"shared object appeared during copy: {dest}")
    except GitStoreError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise GitStoreError(f"failed to copy object to {dest}: {exc}") from exc


def _rollback(installed: list[Path]) -> None:
    for path in reversed(installed):
        try:
            path.unlink()
        except OSError:
            pass


def _accept_result_commit(store: GitStore, new: str, loose: dict[str, Path],
                          pack_ids: set[str], hexlen: int) -> None:
    if not _hex_name(new, hexlen):
        raise GitStoreError(f"overlay HEAD is not an object name: {new!r}")
    env = dict(os.environ,
               GIT_OBJECT_DIRECTORY=str(store.objects),
               GIT_ALTERNATE_OBJECT_DIRECTORIES=str(store.common / "objects"))
    typ = subprocess.run(["git", "--git-dir", str(store.overlay), "cat-file", "-t", new],
                         capture_output=True, text=True, env=env)
    if typ.returncode != 0 or typ.stdout.strip() != "commit":
        raise GitStoreError(f"result {new} is not a commit")
    if new == store.start_sha:
        return
    if not _private_has(new, loose, pack_ids):
        raise GitStoreError("result commit was not created in the private store")
    if store.start_sha:
        anc = subprocess.run(
            ["git", "--git-dir", str(store.overlay), "merge-base", "--is-ancestor",
             store.start_sha, new],
            capture_output=True, text=True, env=env,
        )
        if anc.returncode != 0:
            raise GitStoreError("result commit does not descend from the lane start")


def _copy_new_objects(store: GitStore, new: str) -> None:
    """Copy verified, reachable objects into common. No partial merge on failure."""
    loose, pack_ids, hexlen, hasher = _scan_private_objects(store)
    if new and new != store.start_sha:
        _accept_result_commit(store, new, loose, pack_ids, hexlen)
    # Copy every verified private object, not only those reachable from the
    # result commit. GIT_OBJECT_DIRECTORY applies to `git -C` inside the
    # cage, so a driver-side second repo may have written valid objects
    # that the result ref does not name.
    dest_root = store.common / "objects"
    planned: list[tuple[str, bytes]] = []
    for sha in sorted(set(loose) | pack_ids):
        dest = dest_root / sha[:2] / sha[2:]
        status = _dest_status(dest, sha, hasher)
        if status == "skip":
            continue
        if sha in loose:
            compressed = _verify_loose_file(loose[sha], sha, hasher)
        else:
            raw = _raw_object(store, sha)
            if hasher(raw).hexdigest() != sha:
                raise GitStoreError(f"pack object hash mismatch: {sha}")
            compressed = zlib.compress(raw)
        planned.append((sha, compressed))
    installed: list[Path] = []
    try:
        for sha, compressed in planned:
            dest = dest_root / sha[:2] / sha[2:]
            if _dest_status(dest, sha, hasher) == "skip":
                continue
            _install_loose(dest, compressed, installed)
    except GitStoreError:
        _rollback(installed)
        raise


def _overlay_head_sha(store: GitStore) -> str:
    head = store.overlay / "HEAD"
    if head.is_file():
        text = head.read_text(encoding="utf-8").strip()
        if text and not text.startswith("ref:"):
            return text
    env = dict(os.environ, GIT_OBJECT_DIRECTORY=str(store.objects))
    r = subprocess.run(["git", "--git-dir", str(store.overlay), "rev-parse", "HEAD"],
                       capture_output=True, text=True, env=env)
    return r.stdout.strip() if r.returncode == 0 else ""


def activate_git_store(store: GitStore) -> None:
    """Point the worktree at the overlay so host-side git (fake_podman) uses it.

    A worktree's .git file is rewritten to `gitdir: <overlay>`. The original
    text is restored in finalize_git_store before the result ref is copied
    back. --print does not call this, so a dry argv print cannot leave the
    worktree pointing at a cage directory that is about to be deleted.
    """
    if store.kind != "worktree":
        return
    gitfile = store.wt / ".git"
    if gitfile.is_file():
        store.gitfile_orig = gitfile.read_text(encoding="utf-8")
        gitfile.write_text(f"gitdir: {store.overlay}\n", encoding="utf-8")


def restore_git_pointer(store: GitStore) -> None:
    if store.gitfile_orig is None:
        return
    gitfile = store.wt / ".git"
    gitfile.write_text(store.gitfile_orig, encoding="utf-8")
    store.gitfile_orig = None


def _install_host_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        return
    try:
        if dest.exists() and src.resolve() == dest.resolve():
            return
    except OSError:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".pfy-cage-tmp")
    shutil.copy2(src, tmp)
    try:
        os.replace(tmp, dest)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        print(f"lane-cage: failed to copy back {dest}: {exc}", file=sys.stderr)


def finalize_git_store(store: GitStore, *, cage_ok: bool = True) -> None:
    """Copy verified objects and only the result ref into the shared store.

    On any copy-back error the shared objects and refs are left unchanged
    and GitStoreError is raised so the cage result is marked failed.
    A failed cage run (cage_ok=False) copies nothing.
    """
    restore_git_pointer(store)
    if not cage_ok:
        return
    new = _overlay_head_sha(store)
    _copy_new_objects(store, new)
    if new and new != store.start_sha:
        if store.start_ref:
            r = subprocess.run(["git", "-C", str(store.wt), "update-ref", store.start_ref, new],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise GitStoreError(
                    f"failed to copy back result ref {store.start_ref}: {r.stderr.strip()}")
        else:
            (store.gitdir / "HEAD").write_text(new + "\n", encoding="utf-8")
    _install_host_file(store.overlay / "index", store.gitdir / "index")
    logs_head = store.overlay / "logs" / "HEAD"
    if logs_head.is_file():
        (store.gitdir / "logs").mkdir(parents=True, exist_ok=True)
        _install_host_file(logs_head, store.gitdir / "logs" / "HEAD")


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


def base_run(podman: str, image: str, wt: Path, cage: Path, network: str,
             store: GitStore | None = None) -> list[str]:
    home = cage / "home"
    argv = [podman, "run", "--rm", "--pull=never", f"--network={network}", "--userns=keep-id",
            "--cap-drop=all", "--security-opt=no-new-privileges", "--pids-limit=2048", "--memory=16g",
            "--tmpfs=/tmp:rw,size=4g", f"--volume={wt}:{wt}:rw", f"--volume={home}:{home}:rw",
            f"--volume={SCRIPT_DIR / 'lane_cage_entry.sh'}:{SCRIPT_DIR / 'lane_cage_entry.sh'}:ro",
            f"--workdir={wt}", f"--env=HOME={home}", "--env=GIT_TERMINAL_PROMPT=0",
            "--env=PYTHONDONTWRITEBYTECODE=1"]
    argv += git_mounts(wt, store)
    argv += git_store_envs(store)
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


def build_grok_argv(args, cage: Path, store: GitStore | None = None) -> tuple[list[str], dict]:
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
    argv = base_run(podman, image, wt, cage, "none", store)
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
    store = None
    rc = 0
    printed = False
    try:
        store = prepare_git_store(wt, cage)
        argv, meta = build_grok_argv(args, cage, store)
        if args.print:
            print(json.dumps({"argv": argv, **meta}))
            printed = True
        else:
            if store is not None:
                activate_git_store(store)
            preflight(argv[0], meta["image"])
            allow = [a.strip().lower() for a in os.environ.get("PFY_LANE_EGRESS_ALLOW", DEFAULT_ALLOW).split(",") if a.strip()]
            egress_log = Path(args.egress_log) if args.egress_log else cage / "egress.log"
            proxy = EgressProxy(cage / "sock" / "egress.sock", allow, egress_log)
            proxy.start()
            print(f"lane-cage: kind={args.kind} image={meta['image']} network=none egress={','.join(allow)} "
                  f"credential={meta['credential']} tools={','.join(KIND_TOOLS[args.kind])}", file=sys.stderr)
            try:
                rc = subprocess.run(argv, timeout=args.timeout).returncode
            except subprocess.TimeoutExpired:
                print("lane-cage: timeout", file=sys.stderr)
                rc = 124
            finally:
                proxy.close()
    except CageError as exc:
        print(f"lane-cage: {exc}", file=sys.stderr)
        rc = 2
    finally:
        try:
            if store is not None and not printed:
                try:
                    finalize_git_store(store, cage_ok=(rc == 0))
                except GitStoreError as exc:
                    print(f"lane-cage: {exc}", file=sys.stderr)
                    if rc == 0:
                        rc = 2
        finally:
            shutil.rmtree(cage, ignore_errors=True)
    return rc


def cmd_exec(args) -> int:
    wt = Path(args.wt).resolve()
    cage = prepare_cage(cage_root(wt))
    store = None
    rc = 0
    printed = False
    try:
        podman = os.environ.get("PFY_PODMAN", "podman")
        image = os.environ.get("PFY_LANE_IMAGE", DEFAULT_IMAGE)
        store = prepare_git_store(wt, cage)
        argv = base_run(podman, image, wt, cage, "none", store)
        for ro in args.ro:
            p = Path(ro).resolve()
            argv.append(f"--volume={p}:{p}:ro")
        cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
        if not cmd:
            raise CageError("exec needs a command after --")
        argv += [image, str(SCRIPT_DIR / "lane_cage_entry.sh"), *cmd]
        if args.print:
            print(json.dumps({"argv": argv}))
            printed = True
        else:
            if store is not None:
                activate_git_store(store)
            preflight(podman, image)
            rc = subprocess.run(argv, timeout=args.timeout).returncode
    except CageError as exc:
        print(f"lane-cage: {exc}", file=sys.stderr)
        rc = 2
    finally:
        try:
            if store is not None and not printed:
                try:
                    finalize_git_store(store, cage_ok=(rc == 0))
                except GitStoreError as exc:
                    print(f"lane-cage: {exc}", file=sys.stderr)
                    if rc == 0:
                        rc = 2
        finally:
            shutil.rmtree(cage, ignore_errors=True)
    return rc


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
