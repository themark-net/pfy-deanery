#!/usr/bin/env python3
"""Score opencode-mem recall on this repo.

Eight salts are not in the product tree. The driver stores them, a second
process searches them, then a third process opens a damaged shard. A salt
that appears only in an error string is not a hit. No hosted model and no
API key. The live driver uses the local ONNX embedder already under the
cache home.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
DRIVER = Path(__file__).resolve().parent / "driver.mjs"
PIN = "6c5828f3e49f962385aeb3ad033ecac5adc22878"
NPM_VERSION = "2.41.1"
TARBALL_SHA256 = "142d404aea2add4ffbe1742862e912ddfd109e8b0e7533b73de8adf132ecf883"
TARBALL_SHA1 = "5e285c025f956c0c2036aac16de3986d38dc309a"

SALTS = tuple("OCM1107_SALT_%02d" % i for i in range(1, 9))
KNOWN = (
    "smoke-codebase-memory",
    "PFY_OPENCONTEXT_205_HELLO",
    "prefer-behavior-and-fail-recover-tests",
    "ADR-0011",
    "write-guard-mcp",
    "LOCAL_CODER_MODEL",
    "make smoke-codebase-memory",
    "codebase-memory-mcp",
)
OVERLAP_TOKENS = ("memory", "vector", "rag", "recall", "context")
REAL_HOME_DIRS = (
    ".config/opencode",
    ".opencode-mem",
    ".opencode",
    ".local/share/opencode",
    ".cache/opencode",
)


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def cache_base() -> Path:
    return real_home() / ".cache" / "pfy" / "tools" / "opencode-mem"


def ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dir_mtime(path: Path) -> int | None:
    if not path.exists():
        return None
    return path.stat().st_mtime_ns


def sentence(salt: str) -> str:
    return "pfy opencode-mem lane salt %s is private to this probe." % salt


def run_cmd(cmd: list[str], cwd: Path, env: dict[str, str] | None, timeout: int) -> dict:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "timeout")[:500],
            "ms": ms(start),
        }
    except OSError as exc:
        return {"exit": 127, "stdout": "", "stderr": str(exc)[:240], "ms": ms(start)}
    return {
        "exit": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": (proc.stderr or "")[:500],
        "ms": ms(start),
    }


def rg_hit(rg: str, needle: str, search: Path, globs: tuple[str, ...]) -> bool:
    cmd = [rg, "-F", "-l"]
    for pattern in globs:
        cmd.extend(["--glob", pattern])
    cmd.extend([needle, str(search)])
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def load_arm(proc: dict, out_path: Path) -> dict:
    payload = None
    if out_path.is_file():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        for line in reversed((proc.get("stdout") or "").splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            break
    if not isinstance(payload, dict):
        payload = {"ok": False, "error": "no json", "rows": []}
    else:
        payload = dict(payload)
    if proc.get("exit") != 0:
        payload["ok"] = False
        payload["exit"] = proc.get("exit")
        if not payload.get("error"):
            payload["error"] = "exit %s" % proc.get("exit")
    payload["ms"] = proc.get("ms")
    return payload


def arm_hits(payload: dict, field: str) -> int:
    if payload.get("ok") is not True:
        return 0
    found = set()
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        salt = row.get("salt")
        if salt in SALTS and row.get(field) is True:
            found.add(salt)
    return len(found)


def overlap_cards() -> list[dict]:
    rows = []
    stages = ROOT / "data" / "stages"
    for path in sorted(stages.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(card, dict):
            continue
        parts = [str(card.get("uses") or "")]
        for key in ("features", "catalog_tags", "tags"):
            value = card.get(key) or []
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
        blob = " ".join(parts).lower()
        words = set(re.findall(r"[a-z0-9]+", blob))
        hits = [token for token in OVERLAP_TOKENS if token in words]
        if not hits:
            continue
        rows.append(
            {
                "file": path.name,
                "name": card.get("name"),
                "stage": card.get("integration_stage"),
                "uses": card.get("uses"),
                "hits": hits,
            }
        )
    return rows


def pin_report() -> dict:
    base = cache_base()
    checkout = base / "src" / "opencode-mem"
    tarball = base / "npm" / ("opencode-mem-%s.tgz" % NPM_VERSION)
    pkg = base / "prefix" / "node_modules" / "opencode-mem" / "package.json"
    report: dict = {
        "pin": PIN,
        "npm_version": NPM_VERSION,
        "tarball_sha256": TARBALL_SHA256,
        "tarball_sha1": TARBALL_SHA1,
        "checkout": str(checkout),
        "tarball": str(tarball),
    }
    if checkout.joinpath(".git").exists():
        proc = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
        )
        head = (proc.stdout or "").strip()
        report["checkout_head"] = head
        report["checkout_matches"] = head == PIN
    else:
        report["checkout_matches"] = False
    if tarball.is_file():
        report["tarball_bytes"] = tarball.stat().st_size
        report["tarball_sha256_ok"] = sha256_file(tarball) == TARBALL_SHA256
        report["tarball_sha1_ok"] = sha1_file(tarball) == TARBALL_SHA1
    else:
        report["tarball_sha256_ok"] = False
        report["tarball_sha1_ok"] = False
    if pkg.is_file():
        meta = json.loads(pkg.read_text(encoding="utf-8"))
        report["installed_version"] = meta.get("version")
        report["installed_version_ok"] = meta.get("version") == NPM_VERSION
    else:
        report["installed_version_ok"] = False
    report["ok"] = bool(
        report.get("checkout_matches")
        and report.get("tarball_sha256_ok")
        and report.get("tarball_sha1_ok")
        and report.get("installed_version_ok")
    )
    return report


def reset_storage(storage: Path) -> None:
    """Drop shard files and metadata. Keep the ONNX cache link.

    Deleting a shard while metadata.db still names it blocks the next write.
    A second probe run has to start from an empty registry.
    """
    storage.mkdir(parents=True, exist_ok=True)
    for child in storage.iterdir():
        if child.name == ".cache":
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)


def write_config(home: Path, storage: Path) -> None:
    cfg_dir = home / ".config" / "opencode"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "storagePath": str(storage),
        "embeddingModel": "Xenova/nomic-embed-text-v1",
        "embeddingDimensions": 768,
        "autoCaptureEnabled": False,
        "webServerEnabled": False,
        "autoUpdate": False,
        "showAutoCaptureToasts": False,
        "showUserProfileToasts": False,
        "showErrorToasts": False,
    }
    (cfg_dir / "opencode-mem.jsonc").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    leftover = cfg_dir / "opencode-mem.json"
    if leftover.exists():
        leftover.unlink()


def driver_env(home: Path, scratch: Path, pkg: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "TMPDIR": str(scratch),
        "npm_config_cache": str(home / "npm-cache"),
        "OCM_PKG": str(pkg),
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--node", default="/usr/bin/node")
    parser.add_argument("--driver", type=Path, default=DRIVER)
    parser.add_argument("--rg-bin", default="rg")
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--tmp", type=Path, default=None)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--pkg", type=Path, default=None)
    parser.add_argument("--storage", type=Path, default=None)
    parser.add_argument("--skip-pins", action="store_true")
    parser.add_argument("--skip-config", action="store_true")
    args = parser.parse_args()

    home = args.home or (cache_base() / "home")
    scratch = args.tmp or (cache_base() / "tmp")
    scratch.mkdir(parents=True, exist_ok=True)
    pkg = args.pkg or (cache_base() / "prefix" / "node_modules" / "opencode-mem")
    # A new directory. Deleting a shard file while metadata.db still names it
    # blocks writes ("incompatible or corrupt") and does not rebuild the shard.
    storage = args.storage or (cache_base() / "run" / "data")
    if not args.skip_config:
        reset_storage(storage)
        model_src = cache_base() / "home" / ".opencode-mem" / "data" / ".cache"
        model_link = storage / ".cache"
        if model_src.is_dir() and not model_link.exists():
            model_link.symlink_to(model_src, target_is_directory=True)
        write_config(home, storage)

    before = {name: dir_mtime(real_home() / name) for name in REAL_HOME_DIRS}
    globs = ("!eval/evq1107/opencode-mem/**", "!tests/test_opencode_mem_probe.py")
    start = time.perf_counter()
    repo_novel = sum(1 for salt in SALTS if rg_hit(args.rg_bin, salt, args.repo, globs))
    repo_known = sum(1 for needle in KNOWN if rg_hit(args.rg_bin, needle, args.repo, globs))
    repo_ms = ms(start)

    notes = scratch / "notes.md"
    notes.write_text("\n".join(sentence(salt) for salt in SALTS) + "\n", encoding="utf-8")
    start = time.perf_counter()
    file_hits = sum(1 for salt in SALTS if rg_hit(args.rg_bin, salt, notes, ()))
    file_ms = ms(start)

    env = driver_env(home, scratch, pkg)
    arms = {}
    for command, extra in (
        ("store", ["--fresh"]),
        ("recall", []),
        ("corrupt", []),
    ):
        arm_out = scratch / ("%s.json" % command)
        proc = run_cmd(
            [args.node, str(args.driver), command, "--dir", str(args.repo), "--out", str(arm_out)]
            + extra,
            args.repo,
            env,
            180,
        )
        arms[command] = load_arm(proc, arm_out)

    after = {name: dir_mtime(real_home() / name) for name in REAL_HOME_DIRS}
    changed = [name for name in REAL_HOME_DIRS if before[name] != after[name]]
    recall = arms["recall"]
    corrupt = arms["corrupt"]
    doc = {
        "results_written": True,
        "pins": None if args.skip_pins else pin_report(),
        "repo_novel_hits": repo_novel,
        "repo_known_hits": repo_known,
        "repo_known_asked": len(KNOWN),
        "repo_scan_ms": repo_ms,
        "file_baseline_hits": file_hits,
        "file_baseline_ms": file_ms,
        "store_ok": arms["store"].get("ok") is True,
        "stored": arms["store"].get("stored"),
        "store_ms": arms["store"].get("ms"),
        "recall_ok": recall.get("ok") is True,
        "recall_search_hits": arm_hits(recall, "searched"),
        "recall_list_hits": arm_hits(recall, "listed"),
        "recall_ms": recall.get("ms"),
        "decoy_hit": recall.get("decoy_hit"),
        "corrupt_ok": corrupt.get("ok") is True,
        "corrupt_search_hits": arm_hits(corrupt, "searched"),
        "corrupt_list_hits": arm_hits(corrupt, "listed"),
        "corrupt_ms": corrupt.get("ms"),
        "corrupt": {
            "ok": corrupt.get("ok") is True,
            "error": corrupt.get("error"),
            "damaged": corrupt.get("damaged"),
        },
        "real_home_changed": changed,
        "overlap": overlap_cards(),
        "arms": arms,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
