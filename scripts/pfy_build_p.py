#!/usr/bin/env python3
"""pfy build -p: jev toolset (local) + decision shadow + grok -p (plain).

Dogfood D1 friction fix: wrap headless Grok Build so bots use --output-format plain (never text) and do not skip decision smoke.

Preamble (#263): default is trimmed — jev conf gate ~0.85 (no silent auto-act),
`./pfy decision route` exits (0=proceed/ready, 3=escalate, 1=broken), receipt
dir `pipelines/dogfood/build/`, and a skill path pointer. Full skill bodies
are not inlined.

Skills bundle (#265): the trimmed grok child gets a GROK_HOME with
`auth.json` copied as bytes (never a symlink; dest mode forced to ``0600``),
a real-file pointer at `skills/pfy-jev-decision/SKILL.md`, and `bundled/` as
a real directory tree of byte copies from the real home's `bundled/` (never
a file symlink, never one directory symlink, and never anything from
`real_home/skills`). File symlinks wrote through: grok opened the dest path
and changed the real file. Dest copies are chmod a-w after `shutil.copy2`.
The isolated home directory is ``0700`` (not world-readable). The real tree
is only read. Text size of that exposed tree is recorded apart from the
preamble and the task prompt. Receipt mode stays `bundled_link` (historical
name; the tree is copies).

The isolated home persists under
``pipelines/dogfood/build/<stamp>/grok-home/`` for receipt audit (operators
can inspect byte copies after a run). It is gitignored
(``pipelines/dogfood/build/**/grok-home/``) and is not auto-deleted after
``build_p`` returns — auth and bundled copies must never be committed.

`PFY_BUILD_FULL_PREAMBLE=1` restores a full preamble that inlines
`toolset-jev-brief.md` plus the `pfy-jev-decision` and `jev-decision`
SKILL.md bodies, and keeps the real GROK_HOME (`skills_bundle_mode`
`full_skills`).

`PFY_BUILD_FULL_SKILLS=1` (trimmed preamble only) restores the previous D3
child home: pointer skill + auth byte copy, no bundled expose, no user
skills, and it does not keep the real GROK_HOME (`skills_bundle_mode`
`pointer_only`). Default is `bundled_link`. Live/non-dry `bundled_link`
fails closed when `real_home/bundled` is missing or not a directory
(reason `bundled_missing`) and does not fall back to the real GROK_HOME.
Dry-run may still plan in that case (pointer-only home).

Receipt fields (method `chars/4`): `preamble_chars`, `preamble_tokens_est`
where `tokens_est = max(1, (chars + 3) // 4)`, plus `task_prompt_chars`,
`task_prompt_tokens_est`, and `preamble_mode` (`trimmed`|`full`). Sizes are
separate from the task prompt. Skills bundle (same method, separate fields):
`skills_bundle_chars`, `skills_bundle_tokens_est`, `skills_bundle_method`,
`skills_bundle_mode` (`bundled_link`|`pointer_only`|`full_skills`|`bundled_skipped`).
`bundled_skipped` is a dry-run plan when `bundled/` is missing: exit 0, pointer-only
home, real GROK_HOME left unused. Bundle chars are Unicode text of regular files
under the exposed `bundled/` and `skills/` trees (the dest copies, not a
follow-out). Symlinks are not followed. Bytes are decoded as UTF-8
(`errors="ignore"`). Files with a NUL in the first 8192 bytes are skipped
(binaries such as PDF).

Exit codes:
  0  READY (dry-run complete, or grok finished)
  1  FAIL (grok missing / unauthenticated / bundled missing / apply/smoke/grok hard fail)
  2  usage (blank prompt, or the cost estimate was declined before grok -p)
  3  reserved (decision escalate is logged; build still proceeds unless
     PFY_BUILD_ABORT_ON_ESCALATE=1)

Before grok -p, the run prints the cloud choice against local qwen3.6:35b at
$0, a low-high dollar range, and a wall-time range. On a TTY it asks. Off a
TTY it needs --yes, --approve-cost, or --max-cost at or above the estimate
(PFY_BUILD_YES=1 is the same approval). A lower cap exits 2 and does not
exec grok. Dry-run prints the choice and does not ask. The grok_p receipt
row stores choice, estimate, and actual.

Receipt: <cwd>/pipelines/dogfood/build/<timestamp>/receipt.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.review_chunks import (  # noqa: E402
    build_route_quotes,
    cost_block_reason,
    estimate_receipt,
    format_route_banner,
    load_price_table,
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

TOKEN_METHOD = "chars/4"
JEV_SOT_REL = "bootstrap/grok-cli/skills/jev-decision/SKILL.md"

# Shared by the trimmed prompt preamble and the isolated pointer skill.
# Stay short: trimmed preamble_tokens_est is bounded at 400 and at 1/4 of the full dump.
_LEAN_CONTRACT = (
    "Jev conf gate ~0.85 (PFY_JEV_CONF_GATE). No silent auto-act. "
    "./pfy decision route exits: 0=proceed/ready, 3=escalate (conf low, valid), 1=broken. "
    "Receipt: pipelines/dogfood/build/. "
    "Toolset: local jev applied. Skill pointer: GROK_HOME/skills/pfy-jev-decision. "
    "SoT: bootstrap/grok-cli/skills/jev-decision/SKILL.md."
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _append_receipt(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(row)
    row.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _encode_cwd(cwd: Path) -> str:
    # grok sessions dir uses percent-encoded absolute path
    return urllib.parse.quote(str(cwd.resolve()), safe="")


def find_latest_session(cwd: Path, grok_home: Path | None = None) -> str | None:
    home = Path(grok_home or os.environ.get("GROK_HOME") or (Path.home() / ".grok"))
    sess_root = home / "sessions" / _encode_cwd(cwd)
    if not sess_root.is_dir():
        return None
    newest = None
    newest_mtime = -1.0
    for child in sess_root.iterdir():
        if not child.is_dir():
            continue
        usage = child / "usage.json"
        m = usage.stat().st_mtime if usage.is_file() else child.stat().st_mtime
        if m > newest_mtime:
            newest_mtime = m
            newest = child.name
    return newest


def read_usage(cwd: Path, session_id: str, grok_home: Path | None = None) -> dict:
    home = Path(grok_home or os.environ.get("GROK_HOME") or (Path.home() / ".grok"))
    usage_path = home / "sessions" / _encode_cwd(cwd) / session_id / "usage.json"
    if not usage_path.is_file():
        return {}
    try:
        return json.loads(usage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def tokens_est(text: str) -> int:
    """chars/4 estimate: max(1, (len(chars) + 3) // 4)."""
    return max(1, (len(text) + 3) // 4)


def tokens_from_chars(chars: int) -> int:
    """Same chars/4 estimate for a counted tree. Empty text is 0, not 1."""
    if chars <= 0:
        return 0
    return max(1, (int(chars) + 3) // 4)


def _env_flag(src: dict, name: str) -> bool:
    return str(src.get(name) or "").strip().lower() in ("1", "true", "yes")


def preamble_mode_from_env(env: dict | None = None) -> str:
    src = env if env is not None else os.environ
    if _env_flag(src, "PFY_BUILD_FULL_PREAMBLE"):
        return "full"
    return "trimmed"


def skills_mode_from_env(env: dict | None = None) -> str:
    """Default ``bundled_link`` (byte copies of ``bundled/``, not file symlinks).

    ``PFY_BUILD_FULL_SKILLS=1`` selects ``pointer_only``: the D3 trimmed home
    (pointer skill + auth.json byte copy). It does not expose ``bundled/``,
    does not copy ``real_home/skills``, and does not keep the real GROK_HOME.
    """
    src = env if env is not None else os.environ
    if _env_flag(src, "PFY_BUILD_FULL_SKILLS"):
        return "pointer_only"
    return "bundled_link"


def _read_text(path: Path) -> str | None:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        return None
    return None


def _first_text(paths: list[Path]) -> str | None:
    for path in paths:
        text = _read_text(path)
        if text:
            return text
    return None


def _brief_candidates() -> list[Path]:
    found: list[Path] = []
    raw = os.environ.get("PFY_TOOLSET_BRIEF")
    if raw:
        found.append(Path(raw))
    state = Path(os.environ.get("PFY_STATE_DIR") or (Path.home() / ".pfy-mentat"))
    found.append(state / "toolset-jev-brief.md")
    return found


def _jev_skill_candidates(repo: Path, grok_home: Path | None) -> list[Path]:
    paths = [
        repo / JEV_SOT_REL,
        repo / ".grok" / "skills" / "jev-decision" / "SKILL.md",
    ]
    if grok_home is not None:
        paths.append(Path(grok_home) / "skills" / "jev-decision" / "SKILL.md")
    return paths


def _pfy_skill_candidates(repo: Path, grok_home: Path | None) -> list[Path]:
    paths: list[Path] = []
    if grok_home is not None:
        paths.append(Path(grok_home) / "skills" / "pfy-jev-decision" / "SKILL.md")
    default_home = Path(os.environ.get("GROK_HOME") or (Path.home() / ".grok"))
    paths.append(default_home / "skills" / "pfy-jev-decision" / "SKILL.md")
    paths.append(repo / ".grok" / "skills" / "pfy-jev-decision" / "SKILL.md")
    return paths


def build_preamble(
    repo: Path | None = None,
    *,
    mode: str | None = None,
    grok_home: Path | None = None,
) -> str:
    """Return the headless Build preamble. Default mode is trimmed.

    ``mode="full"`` (or ``PFY_BUILD_FULL_PREAMBLE=1`` when mode is omitted)
    inlines toolset-jev-brief.md and the pfy-jev-decision / jev-decision
    SKILL.md bodies. Trimmed text is a pointer, not those bodies.
    """
    repo = Path(repo or ROOT)
    if mode is None:
        mode = preamble_mode_from_env()
    if mode != "full":
        return "pfy build -p preamble (trimmed). " + _LEAN_CONTRACT + "\n"
    brief = _first_text(_brief_candidates())
    pfy_body = _first_text(_pfy_skill_candidates(repo, grok_home))
    jev_body = _first_text(_jev_skill_candidates(repo, grok_home))
    parts = [
        "pfy build -p preamble (full). PFY_BUILD_FULL_PREAMBLE=1 inlines "
        "toolset-jev-brief.md and pfy-jev-decision / jev-decision SKILL.md bodies.",
        "## toolset-jev-brief.md",
        (brief.rstrip("\n") if brief else "(missing)"),
        "## pfy-jev-decision/SKILL.md",
        (pfy_body.rstrip("\n") if pfy_body else "(missing)"),
        "## jev-decision/SKILL.md",
        (jev_body.rstrip("\n") if jev_body else "(missing)"),
        "",
    ]
    return "\n".join(parts)


def pointer_skill_md() -> str:
    """Minimal skill the trimmed grok child can see. Not the full SKILL.md body."""
    return (
        "---\n"
        "name: pfy-jev-decision\n"
        "description: Pointer only. Local jev is applied. Full skill body is not inlined.\n"
        "---\n\n"
        + _LEAN_CONTRACT
        + "\n"
    )


class BundledMissingError(Exception):
    """real_home/bundled is missing or not a directory. Do not fall back."""

    reason = "bundled_missing"


class BundledLinkError(Exception):
    """Safe bundled link could not be built. Do not fall back to the real home."""

    reason = "bundled_link_unsafe"


def bundled_missing_message(real_home: Path) -> str:
    bundled = Path(real_home) / "bundled"
    return (
        "FAIL: bundled skills missing or not a directory: %s. "
        "Refusing to fall back to the real GROK_HOME or the user skills tree. "
        "Next: restore that bundled/ directory, or set PFY_BUILD_FULL_SKILLS=1 "
        "for D3 pointer-only isolation (no bundled expose; real GROK_HOME is not kept)."
        % bundled
    )


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except (ValueError, OSError):
        return False
    return True


def _unlink_or_rmtree(path: Path) -> None:
    """Remove path. A symlink is unlinked and its target is left alone."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _deny_write_dest_copy(path: Path) -> None:
    """Clear write bits on a regular dest file. Never follow a symlink."""
    if path.is_symlink():
        raise BundledLinkError(
            "FAIL: refusing to chmod a symlink (would change the real tree): %s" % path
        )
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise BundledLinkError("FAIL: cannot stat dest copy %s: %s" % (path, exc)) from exc
    if not stat.S_ISREG(mode):
        raise BundledLinkError("FAIL: dest bundled copy is not a regular file: %s" % path)
    cleared = mode & ~0o222
    try:
        os.chmod(path, cleared, follow_symlinks=False)
    except NotImplementedError:
        os.chmod(path, cleared)
    except OSError as exc:
        raise BundledLinkError(
            "FAIL: cannot drop write bits on dest copy %s: %s" % (path, exc)
        ) from exc


def link_bundled_skills(real_home: Path, dest: Path) -> dict:
    """Mirror ``real_home/bundled`` under ``dest/bundled`` as byte copies.

    ``dest/bundled`` is a real directory. Each file is a regular file written
    with ``shutil.copy2`` (the dest path only). Write bits are then cleared
    on that copy. The real tree is only read. Directory symlinks and file
    symlinks are not created: a dest symlink is how grok wrote through into
    the real file. Entries whose ``Path.resolve()`` leaves ``bundled/`` are
    skipped. Nothing under ``real_home/skills`` is read or copied.

    Receipt mode stays ``bundled_link`` (the value predates the copy).

    Raises ``BundledMissingError`` when ``bundled`` is missing or not a directory.
    Raises ``BundledLinkError`` when a copy would escape or land as a symlink.
    """
    real_home = Path(real_home)
    bundled = real_home / "bundled"
    try:
        bundled_is_dir = bundled.is_dir()
    except OSError as exc:
        raise BundledMissingError(bundled_missing_message(real_home)) from exc
    if not bundled_is_dir:
        raise BundledMissingError(bundled_missing_message(real_home))

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    real_root = bundled.resolve()
    if _is_within(dest, real_root):
        raise BundledLinkError(
            "FAIL: refusing to copy bundled skills into a dest inside bundled/: %s" % dest
        )

    dest_bundled = dest / "bundled"
    # A directory symlink here would let later writes land in the real tree.
    _unlink_or_rmtree(dest_bundled)
    dest_bundled.mkdir(parents=True)
    if dest_bundled.is_symlink():
        raise BundledLinkError("FAIL: dest/bundled must be a real directory, not a symlink")

    copied = 0
    skipped = 0
    seen_dirs: set[tuple[int, int]] = set()

    def walk(src_dir: Path, out_dir: Path) -> None:
        nonlocal copied, skipped
        try:
            resolved_dir = src_dir.resolve()
            st = resolved_dir.stat()
        except OSError:
            skipped += 1
            return
        if not _is_within(resolved_dir, real_root):
            skipped += 1
            return
        key = (st.st_dev, st.st_ino)
        if key in seen_dirs:
            return
        seen_dirs.add(key)
        out_dir.mkdir(parents=True, exist_ok=True)
        if out_dir.is_symlink():
            raise BundledLinkError(
                "FAIL: refusing to copy into a symlink directory: %s" % out_dir
            )
        try:
            entries = list(src_dir.iterdir())
        except OSError as exc:
            raise BundledLinkError(
                "FAIL: cannot read bundled directory %s: %s" % (src_dir, exc)
            ) from exc
        for src in entries:
            try:
                resolved = src.resolve()
            except OSError:
                skipped += 1
                continue
            if not _is_within(resolved, real_root):
                skipped += 1
                continue
            if resolved.is_dir():
                walk(src, out_dir / src.name)
                continue
            if not resolved.is_file():
                skipped += 1
                continue
            # Byte copy of the resolved file (an in-tree symlink becomes a
            # regular file). Never symlink, never open the real path for write.
            out_path = out_dir / src.name
            if _is_within(out_path, real_root):
                raise BundledLinkError(
                    "FAIL: refusing to write a bundled copy inside the real tree: %s" % out_path
                )
            if out_path.is_symlink() or out_path.exists():
                _unlink_or_rmtree(out_path)
            try:
                shutil.copy2(resolved, out_path, follow_symlinks=True)
            except OSError as exc:
                raise BundledLinkError(
                    "FAIL: cannot copy bundled file %s -> %s: %s" % (resolved, out_path, exc)
                ) from exc
            if out_path.is_symlink() or not out_path.is_file():
                raise BundledLinkError(
                    "FAIL: bundled dest entry must be a regular file, not a symlink: %s" % out_path
                )
            try:
                if out_path.stat().st_size != resolved.stat().st_size:
                    raise BundledLinkError("FAIL: bundled copy size mismatch: %s" % out_path)
            except BundledLinkError:
                raise
            except OSError as exc:
                raise BundledLinkError(
                    "FAIL: cannot stat bundled copy %s: %s" % (out_path, exc)
                ) from exc
            _deny_write_dest_copy(out_path)
            copied += 1

    walk(bundled, dest_bundled)
    _assert_bundled_copies(dest_bundled)
    return {
        "copied_files": copied,
        "linked_files": copied,
        "skipped": skipped,
        "bundled_root": str(real_root),
        "mode": "bundled_link",
    }


def _assert_bundled_copies(dest_bundled: Path) -> None:
    if dest_bundled.is_symlink() or not dest_bundled.is_dir():
        raise BundledLinkError(
            "FAIL: dest/bundled must be a real directory under the isolated home"
        )
    for dirpath, dirnames, filenames in os.walk(dest_bundled, followlinks=False):
        for name in dirnames:
            child = Path(dirpath) / name
            if child.is_symlink():
                raise BundledLinkError(
                    "FAIL: directory symlink in dest/bundled is forbidden: %s" % child
                )
        for name in filenames:
            child = Path(dirpath) / name
            if child.is_symlink() or not child.is_file():
                raise BundledLinkError(
                    "FAIL: dest/bundled file must be a byte copy, not a symlink: %s" % child
                )
            if child.stat().st_mode & 0o222:
                raise BundledLinkError("FAIL: dest bundled copy is still writable: %s" % child)


def _read_nofollow(path: Path) -> bytes | None:
    """Read a regular file. Symlinks and unreadable paths return None."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        chunks: list[bytes] = []
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
        return b"".join(chunks)
    except OSError:
        return None
    finally:
        os.close(fd)


def _text_char_len(path: Path) -> int:
    """Unicode length of a dest text file. NUL in the first 8192 bytes → skip (binary).

    Does not follow symlinks, so a link out of dest contributes nothing.
    """
    if path.is_symlink():
        return 0
    blob = _read_nofollow(path)
    if not blob:
        return 0
    if b"\0" in blob[:8192]:
        return 0
    return len(blob.decode("utf-8", errors="ignore"))


def _tree_text_chars(base: Path) -> int:
    """Sum text chars of regular files under base. Do not follow symlinks out."""
    try:
        if base.is_symlink() or not base.is_dir():
            return 0
    except OSError:
        return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [d for d in dirnames if not (Path(dirpath) / d).is_symlink()]
        for name in filenames:
            total += _text_char_len(Path(dirpath) / name)
    return total


def measure_skills_bundle(dest: Path) -> tuple[int, int]:
    """``(chars, tokens_est)`` of text in regular files under ``dest/bundled`` and ``dest/skills``.

    Counts each dest copy's own bytes. Symlinks are not followed (a follow-out
    would recount the real tree, which is what the symlink bug exposed).
    Method name for receipts: ``chars/4``.
    ``tokens_est`` is 0 when no text is exposed, otherwise ``max(1, (chars + 3) // 4)``.
    """
    dest = Path(dest)
    chars = 0
    for name in ("bundled", "skills"):
        base = dest / name
        try:
            present = base.exists() or base.is_symlink()
        except OSError:
            continue
        if not present:
            continue
        chars += _tree_text_chars(base)
    return chars, tokens_from_chars(chars)


def isolate_trimmed_grok_home(
    real_home: Path,
    dest: Path,
    *,
    link_bundled: bool = True,
) -> Path:
    """Isolated grok home: pointer skill, auth byte copy, optional bundled byte copies.

    Does not copy or symlink ``real_home/skills``. The pointer skill is always
    a regular file. ``auth.json`` is a byte copy when the real file exists,
    then forced to mode ``0600`` (``copy2`` would otherwise preserve a broader
    source mode). The isolated home directory is ``0700`` so it is not
    world-readable. ``link_bundled=False`` is the D3 pointer-only home
    (``PFY_BUILD_FULL_SKILLS=1``). ``link_bundled=True`` mirrors
    ``real_home/bundled`` as dest byte copies (never file symlinks). The real
    tree is not written.

    Persistence: callers typically place ``dest`` under
    ``pipelines/dogfood/build/<stamp>/grok-home/``. That tree is kept after
    the run for receipt audit (gitignored); ``build_p`` does not delete it.
    Never commit auth or grok-home contents.
    """
    dest = Path(dest)
    if dest.exists() or dest.is_symlink():
        _unlink_or_rmtree(dest)
    skill_dir = dest / "skills" / "pfy-jev-decision"
    skill_dir.mkdir(parents=True)
    # Owner-only home: auth.json lives here; do not leave the dir world-readable.
    os.chmod(dest, 0o700)
    pointer = skill_dir / "SKILL.md"
    pointer.write_text(pointer_skill_md(), encoding="utf-8")
    if pointer.is_symlink():
        raise BundledLinkError("FAIL: pointer skill must be a real file, not a symlink")
    auth = Path(real_home) / "auth.json"
    try:
        auth_ok = auth.is_file()
    except OSError:
        auth_ok = False
    if auth_ok:
        # Byte copy (not a symlink). copy2 follows a symlink source; do not keep
        # a broader source mode — force 0600 on the dest copy.
        shutil.copy2(auth, dest / "auth.json", follow_symlinks=True)
        dest_auth = dest / "auth.json"
        if dest_auth.is_symlink():
            raise BundledLinkError("FAIL: auth.json must be a byte copy, not a symlink")
        os.chmod(dest_auth, 0o600)
    if link_bundled:
        link_bundled_skills(real_home, dest)
    return dest


def compose_grok_prompt(preamble: str, task: str) -> str:
    body = preamble if preamble.endswith("\n") else preamble + "\n"
    return body + "--- task ---\n" + task


def grok_bin(path_env: str | None = None) -> str | None:
    return shutil.which("grok", path=path_env if path_env is not None else os.environ.get("PATH"))


def grok_authenticated(grok_home: Path | None = None) -> bool:
    home = Path(grok_home or os.environ.get("GROK_HOME") or (Path.home() / ".grok"))
    auth = home / "auth.json"
    try:
        return auth.is_file() and auth.stat().st_size > 20
    except OSError:
        return False


def run_cmd(argv: list[str], *, cwd: Path, env: dict | None = None, dry_run: bool = False) -> dict:
    if dry_run:
        return {"ok": True, "dry_run": True, "argv": argv, "rc": 0, "stdout": "", "stderr": ""}
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "argv": argv,
    }


def apply_jev_local(repo: Path, *, dry_run: bool, env: dict) -> dict:
    argv = [str(repo / "pfy"), "toolset", "apply", "jev", "--harness", "grok", "--lane", "local"]
    if not dry_run:
        argv.append("--yes")
    return run_cmd(argv, cwd=repo, env=env, dry_run=dry_run)


def decision_smoke(repo: Path, *, dry_run: bool, env: dict) -> dict:
    argv = [str(repo / "pfy"), "decision", "smoke"]
    return run_cmd(argv, cwd=repo, env=env, dry_run=dry_run)


def decision_route_shadow(repo: Path, *, dry_run: bool, env: dict) -> dict:
    """Run route; escalate (rc 3) is a valid shadow verdict — not a build abort."""
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rc": 3,
            "verdict": "escalate",
            "stdout": "ESCALATE decision · (dry-run shadow)\n  verdict: escalate\n",
            "stderr": "",
            "argv": [str(repo / "pfy"), "decision", "route"],
        }
    argv = [str(repo / "pfy"), "decision", "route"]
    proc = subprocess.run(argv, cwd=str(repo), env=env, text=True, capture_output=True)
    out = proc.stdout or ""
    verdict = "ready"
    if proc.returncode == 3 or "verdict: escalate" in out or out.startswith("ESCALATE"):
        verdict = "escalate"
    elif proc.returncode != 0:
        verdict = "fail"
    return {
        "ok": proc.returncode in (0, 3),
        "rc": proc.returncode,
        "verdict": verdict,
        "stdout": out,
        "stderr": proc.stderr or "",
        "argv": argv,
    }


def run_grok_p(
    *,
    prompt: str,
    cwd: Path,
    grok: str,
    dry_run: bool,
    env: dict,
) -> dict:
    argv = [
        grok,
        "-p",
        prompt,
        "--cwd",
        str(cwd),
        "--always-approve",
        "--output-format",
        "plain",
    ]
    home = Path(env["GROK_HOME"]) if env.get("GROK_HOME") else None
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "rc": 0,
            "argv": argv,
            "stdout": "(dry-run: grok not executed)",
            "stderr": "",
            "session_id": None,
            "usage": {},
            "grok_home": str(home) if home else None,
        }
    before = time.time()
    proc = subprocess.run(argv, cwd=str(cwd), env=env, text=True, capture_output=True)
    session_id = find_latest_session(cwd, home)
    usage = read_usage(cwd, session_id, home) if session_id else {}
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "argv": argv,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "elapsed_s": round(time.time() - before, 3),
        "session_id": session_id,
        "usage": usage,
        "grok_home": str(home) if home else None,
    }


def _p_cost_args(yes: bool, approve_cost: bool, max_cost: float | None):
    return argparse.Namespace(yes=bool(yes), approve_cost=bool(approve_cost), max_cost=max_cost)


def _p_quotes():
    why = (
        "pfy build -p runs one grok -p turn on Grok Build; "
        "pfy build --local uses Ollama qwen3.6:35b at $0"
    )
    return build_route_quotes("cloud", "grok-4.7", why, 1, 0, load_price_table())


def _p_actual(usage: dict, *, ran: bool) -> dict:
    if not ran:
        return {"usd": 0.0, "source": "not-run"}
    session = usage.get("session") if isinstance(usage, dict) else None
    ticks = session.get("costUsdTicks") if isinstance(session, dict) else None
    if ticks is None:
        return {"usd": 0.0, "source": "not-recorded"}
    try:
        return {"usd": float(ticks) / 1e10, "source": "usage.json"}
    except (TypeError, ValueError):
        return {"usd": 0.0, "source": "not-recorded"}


def build_p(
    prompt: str,
    *,
    cwd: Path | None = None,
    repo: Path | None = None,
    dry_run: bool = False,
    path_env: str | None = None,
    grok_home: Path | None = None,
    abort_on_escalate: bool | None = None,
    yes: bool = False,
    approve_cost: bool = False,
    max_cost: float | None = None,
) -> int:
    repo = Path(repo or ROOT).resolve()
    cwd = Path(cwd or repo).resolve()
    stamp = _now()
    receipt_dir = cwd / "pipelines" / "dogfood" / "build" / stamp
    receipt = receipt_dir / "receipt.jsonl"
    env = os.environ.copy()
    env.setdefault("PFY_DECISION_PATH", "cua-s1-forms")
    env.setdefault("PFY_JEV_OFFLINE", "1")
    env.pop("TYPESAFE_API_KEY", None)
    if grok_home is not None:
        env["GROK_HOME"] = str(grok_home)

    if abort_on_escalate is None:
        abort_on_escalate = os.environ.get("PFY_BUILD_ABORT_ON_ESCALATE", "").strip() in (
            "1",
            "true",
            "yes",
        )

    mode = preamble_mode_from_env(env)
    real_home = Path(env["GROK_HOME"]) if env.get("GROK_HOME") else Path(
        os.environ.get("GROK_HOME") or (Path.home() / ".grok")
    )
    preamble = build_preamble(repo, mode=mode, grok_home=real_home)
    composed = compose_grok_prompt(preamble, prompt)
    skills_request = skills_mode_from_env(env)

    def _start_row(bundle_mode: str, chars, tokens) -> dict:
        return {
            "event": "start",
            "prompt_head": prompt[:240],
            "cwd": str(cwd),
            "repo": str(repo),
            "dry_run": dry_run,
            "typesafe_tokens": 0,
            "preamble_chars": len(preamble),
            "preamble_tokens_est": tokens_est(preamble),
            "preamble_tokens_method": TOKEN_METHOD,
            "task_prompt_chars": len(prompt),
            "task_prompt_tokens_est": tokens_est(prompt),
            "preamble_mode": mode,
            "skills_bundle_chars": chars,
            "skills_bundle_tokens_est": tokens,
            "skills_bundle_method": TOKEN_METHOD,
            "skills_bundle_mode": bundle_mode,
        }

    def _fail(reason: str, msg: str, bundle_mode: str, chars=None, tokens=None) -> int:
        print(msg, file=sys.stderr)
        _append_receipt(receipt, _start_row(bundle_mode, chars, tokens))
        _append_receipt(receipt, {"event": "fail", "reason": reason, "copy": msg})
        return EXIT_FAIL

    print(
        "pfy build -p · preamble %s · %s tokens_est (%s) · task %s tokens_est"
        % (mode, tokens_est(preamble), TOKEN_METHOD, tokens_est(prompt))
    )

    grok = grok_bin(path_env)
    if not grok:
        msg = "FAIL: grok not on PATH — install Grok Build CLI or fix PATH; next: ~/.local/bin/grok"
        planned = skills_request if mode == "trimmed" else "full_skills"
        return _fail("grok_missing", msg, planned)

    child_env = dict(env)
    child_home = real_home
    link_bundled = False
    bundle_mode = "full_skills"
    if mode == "trimmed":
        if skills_request == "pointer_only":
            bundle_mode = "pointer_only"
        else:
            try:
                bundled_ok = (real_home / "bundled").is_dir()
            except OSError:
                bundled_ok = False
            if not bundled_ok and not dry_run:
                return _fail(
                    "bundled_missing",
                    bundled_missing_message(real_home),
                    "bundled_missing",
                )
            # Dry-run with no bundled still plans a pointer-only home.
            # It does not keep the real GROK_HOME or the user skills tree.
            link_bundled = bundled_ok
            bundle_mode = "bundled_link" if bundled_ok else "bundled_skipped"
        try:
            child_home = isolate_trimmed_grok_home(
                real_home,
                receipt_dir / "grok-home",
                link_bundled=link_bundled,
            )
        except BundledMissingError as exc:
            return _fail("bundled_missing", str(exc), "bundled_missing")
        except BundledLinkError as exc:
            return _fail("bundled_link_unsafe", str(exc), "bundled_link_unsafe")
        child_env["GROK_HOME"] = str(child_home)
        bundle_chars, bundle_tokens = measure_skills_bundle(child_home)
    else:
        bundle_chars, bundle_tokens = measure_skills_bundle(real_home)

    _append_receipt(receipt, _start_row(bundle_mode, bundle_chars, bundle_tokens))
    skipped = ""
    if bundle_mode == "bundled_skipped":
        skipped = " · dry-run, bundled not copied"
    print(
        "pfy build -p · skills_bundle %s · %s tokens_est (%s)%s"
        % (bundle_mode, bundle_tokens, TOKEN_METHOD, skipped)
    )

    if not grok_authenticated(child_home):
        # In dry-run allow missing auth so CI can exercise the path
        if not dry_run:
            msg = (
                "FAIL: grok unauthenticated — missing/empty ~/.grok/auth.json "
                "(or $GROK_HOME/auth.json); next: run `grok` once to log in"
            )
            print(msg, file=sys.stderr)
            _append_receipt(receipt, {"event": "fail", "reason": "grok_unauthenticated", "copy": msg})
            return EXIT_FAIL

    print("pfy build -p · toolset apply jev --lane local%s" % (" · dry-run" if dry_run else ""))
    apply = apply_jev_local(repo, dry_run=dry_run, env=env)
    _append_receipt(receipt, {"event": "toolset_apply", **{k: apply[k] for k in apply if k != "stdout"}})
    if not apply.get("ok") and not dry_run:
        print(apply.get("stderr") or apply.get("stdout") or "FAIL toolset apply", file=sys.stderr)
        _append_receipt(receipt, {"event": "fail", "reason": "toolset_apply", "rc": apply.get("rc")})
        return EXIT_FAIL
    if apply.get("stdout"):
        print(apply["stdout"].rstrip())

    print("pfy build -p · decision smoke")
    smoke = decision_smoke(repo, dry_run=dry_run, env=env)
    _append_receipt(
        receipt,
        {
            "event": "decision_smoke",
            "rc": smoke.get("rc"),
            "ok": smoke.get("ok"),
            "stdout_head": (smoke.get("stdout") or "")[:500],
        },
    )
    if not smoke.get("ok") and not dry_run:
        print(smoke.get("stderr") or smoke.get("stdout") or "FAIL decision smoke", file=sys.stderr)
        _append_receipt(receipt, {"event": "fail", "reason": "decision_smoke", "rc": smoke.get("rc")})
        return EXIT_FAIL
    if smoke.get("stdout"):
        print(smoke["stdout"].rstrip())

    print("pfy build -p · decision route (shadow)")
    route = decision_route_shadow(repo, dry_run=dry_run, env=env)
    _append_receipt(
        receipt,
        {
            "event": "decision_route_shadow",
            "rc": route.get("rc"),
            "verdict": route.get("verdict"),
            "ok": route.get("ok"),
            "stdout_head": (route.get("stdout") or "")[:500],
            "note": "escalate is valid; no silent auto-act",
        },
    )
    if route.get("stdout"):
        print(route["stdout"].rstrip())
    if route.get("verdict") == "fail" and not dry_run:
        print("FAIL: decision route broken (not escalate)", file=sys.stderr)
        _append_receipt(receipt, {"event": "fail", "reason": "decision_route_broken", "rc": route.get("rc")})
        return EXIT_FAIL
    if route.get("verdict") == "escalate" and abort_on_escalate and not dry_run:
        print("FAIL: PFY_BUILD_ABORT_ON_ESCALATE=1 and route escalated", file=sys.stderr)
        _append_receipt(receipt, {"event": "fail", "reason": "abort_on_escalate"})
        return EXIT_FAIL

    choice, estimate, alternative = _p_quotes()
    print(format_route_banner(choice, estimate, alternative, 1), file=sys.stderr, flush=True)
    cost_fields = {
        "choice": choice,
        "estimate": estimate_receipt(estimate, alternative),
    }
    if not dry_run:
        blocked = cost_block_reason(_p_cost_args(yes, approve_cost, max_cost), estimate)
        if blocked:
            print(blocked, file=sys.stderr)
            _append_receipt(
                receipt,
                {
                    "event": "fail",
                    "reason": "estimate-declined",
                    "copy": blocked,
                    "actual": {"usd": 0.0, "source": "not-run"},
                    **cost_fields,
                },
            )
            return EXIT_USAGE

    print("pfy build -p · grok -p --output-format plain --always-approve")
    grok_rec = run_grok_p(prompt=composed, cwd=cwd, grok=grok, dry_run=dry_run, env=child_env)
    # Persist grok streams for operators
    (receipt_dir / "grok-stdout.log").write_text(grok_rec.get("stdout") or "", encoding="utf-8")
    (receipt_dir / "grok-stderr.log").write_text(grok_rec.get("stderr") or "", encoding="utf-8")
    usage = grok_rec.get("usage") or {}
    sess = usage.get("session") or {}
    summary = {
        "event": "grok_p",
        "rc": grok_rec.get("rc"),
        "ok": grok_rec.get("ok"),
        "dry_run": dry_run,
        "session_id": grok_rec.get("session_id"),
        "elapsed_s": grok_rec.get("elapsed_s"),
        "turnCount": sess.get("turnCount"),
        "modelCalls": sess.get("modelCalls"),
        "totalTokens": sess.get("totalTokens"),
        "primaryModelId": sess.get("primaryModelId"),
        "typesafe_tokens": 0,
        "argv": grok_rec.get("argv"),
        "grok_home": str(child_home),
        "preamble_mode": mode,
        "preamble_tokens_est": tokens_est(preamble),
        "task_prompt_tokens_est": tokens_est(prompt),
        "skills_bundle_chars": bundle_chars,
        "skills_bundle_tokens_est": bundle_tokens,
        "skills_bundle_method": TOKEN_METHOD,
        "skills_bundle_mode": bundle_mode,
        **cost_fields,
        "actual": _p_actual(usage, ran=not dry_run),
    }
    _append_receipt(receipt, summary)

    sid = grok_rec.get("session_id") or "(none)"
    print("session_id: %s" % sid)
    print(
        "usage: turns=%s model_calls=%s total_tokens=%s model=%s"
        % (
            sess.get("turnCount", "(n/a)" if dry_run else "?"),
            sess.get("modelCalls", "(n/a)" if dry_run else "?"),
            sess.get("totalTokens", "(n/a)" if dry_run else "?"),
            sess.get("primaryModelId", "(n/a)" if dry_run else "?"),
        )
    )
    print("receipt: %s" % receipt)

    if not grok_rec.get("ok") and not dry_run:
        err = (grok_rec.get("stderr") or grok_rec.get("stdout") or "").strip()
        print(err or "FAIL: grok -p exited non-zero", file=sys.stderr)
        _append_receipt(receipt, {"event": "fail", "reason": "grok_p", "rc": grok_rec.get("rc")})
        return EXIT_FAIL

    _append_receipt(receipt, {"event": "done", "ok": True, "dry_run": dry_run, "typesafe_tokens": 0})
    print("READY pfy build -p%s" % (" · dry-run" if dry_run else ""))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="pfy build",
        description="Apply local jev toolset, shadow decision, run grok -p (plain).",
    )
    p.add_argument("-p", "--prompt", dest="prompt", help="single-turn prompt for grok -p")
    p.add_argument("--prompt-file", help="read prompt from file")
    p.add_argument("--cwd", help="worktree / working directory for grok and receipt")
    p.add_argument("--dry-run", action="store_true", help="plan + shadow only; do not write toolset or exec grok")
    p.add_argument("--yes", action="store_true", help="accept the printed estimate off a TTY")
    p.add_argument("--approve-cost", action="store_true", help="same as --yes")
    p.add_argument("--max-cost", type=float, default=None, help="USD cap; at or above the estimate is approval")
    p.add_argument("--path-env", default=None, help=argparse.SUPPRESS)  # tests: override PATH for which()
    args = p.parse_args(argv)

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt or not str(prompt).strip():
        p.print_help()
        print("\nFAIL: need -p \"<prompt>\" or --prompt-file", file=sys.stderr)
        return EXIT_USAGE

    return build_p(
        str(prompt),
        cwd=Path(args.cwd).resolve() if args.cwd else None,
        dry_run=bool(args.dry_run),
        path_env=args.path_env,
        yes=bool(args.yes),
        approve_cost=bool(args.approve_cost),
        max_cost=args.max_cost,
    )


if __name__ == "__main__":
    sys.exit(main())
