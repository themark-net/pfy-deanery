#!/usr/bin/env python3
"""Offline OpenContext probe for gap H1.

Uses the cached npm CLI. Store, HOME, and temp dirs stay under
~/.cache/pfy/tools/opencontext/. No model, no API key, no oc init, no oc ui,
no oc index build.
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
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
PIN = "0649e7134346f6f5038a9b29cc5c824ae6a54f3f"
NPM_GIT_HEAD = "9c26c0ba35249b26b5325abcd9c79703a220536f"
NPM_SHA1 = "518bf681bdd1565225723b81305b499776a7effb"

REPO_NEEDLES = (
    "PFY_OPENCONTEXT_205_HELLO",
    "OPENCONTEXT_CONTEXTS_ROOT",
    "0649e7134346f6f5038a9b29cc5c824ae6a54f3f",
    "@aicontextlab/cli",
    "pfy-205-hello",
    "Catalog HOLD this round",
    "smoke-codebase-memory",
    "opencontext.db",
)
NOVEL = tuple("OC1107_NOVEL_%02d" % i for i in range(1, 9))

OVERLAP_WORDS = ("memory", "context", "rag", "knowledge", "handoff")
H1_NAMES = ("skill-up", "harness2", "Harness Score", "eval-harness (pfy)", "neatroots")


def cache_base() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cache" / "pfy" / "tools" / "opencontext"


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def oc_bin() -> Path:
    return cache_base() / "prefix" / "node_modules" / ".bin" / "oc"


def pin_tree() -> Path:
    return cache_base() / "src" / "OpenContext"


def tarball() -> Path:
    return cache_base() / "npm" / "aicontextlab-cli-0.2.2.tgz"


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


def home_fingerprint(root: Path) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            rows.append(
                {
                    "rel": str(path.relative_to(root)),
                    "mtime_ns": stat.st_mtime_ns,
                    "size": stat.st_size,
                    "mode": stat.st_mode,
                }
            )
    stat = root.lstat()
    rows.append(
        {
            "rel": ".",
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
            "mode": stat.st_mode,
        }
    )
    return rows


def oc_env(store: Path, home: Path | None = None, tmp: Path | None = None) -> dict[str, str]:
    base = cache_base()
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home or (base / "home")),
        "XDG_CONFIG_HOME": str(base / "xdg-config"),
        "XDG_CACHE_HOME": str(base / "xdg-cache"),
        "TMPDIR": str(tmp or (base / "tmp")),
        "OPENCONTEXT_ROOT": str(store),
        "OPENCONTEXT_CONTEXTS_ROOT": str(store / "contexts"),
        "OPENCONTEXT_DB_PATH": str(store / "opencontext.db"),
        "CI": "1",
        "LANG": "C.UTF-8",
        "NO_COLOR": "1",
    }


def run_cmd(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int) -> dict:
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
            "stderr": exc.stderr or "timeout",
            "ms": ms(start),
        }
    except OSError as exc:
        return {"exit": 127, "stdout": "", "stderr": str(exc)[:240], "ms": ms(start)}
    return {
        "exit": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "ms": ms(start),
    }


def run_oc(
    store: Path,
    args: list[str],
    timeout: int = 30,
    binary: Path | None = None,
    home: Path | None = None,
    tmp: Path | None = None,
) -> dict:
    return run_cmd([str(binary or oc_bin())] + args, ROOT, oc_env(store, home, tmp), timeout)


def repo_hits(needle: str, rg: str = "rg") -> dict:
    """Count files in this worktree that contain needle. Skip our own outputs."""
    cmd = [
        rg,
        "-F",
        "-l",
        "--glob",
        "!.git/**",
        "--glob",
        "!eval/evq1107/opencontext/**",
        "--glob",
        "!data/stages/opencontext.json",
        needle,
    ]
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    files = [line for line in (proc.stdout or "").splitlines() if line]
    return {
        "needle_present": proc.returncode == 0 and len(files) > 0,
        "file_count": len(files),
        "ms": ms(start),
    }


def file_walk_hits(contexts: Path, needles: tuple[str, ...]) -> dict[str, bool]:
    found = {needle: False for needle in needles}
    if not contexts.is_dir():
        return found
    pending = set(needles)
    for path in contexts.rglob("*"):
        if not path.is_file() or not pending:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hit = {needle for needle in pending if needle in text or needle in path.name}
        for needle in hit:
            found[needle] = True
        pending -= hit
    return found


def count_hits(found: dict[str, bool], needles: tuple[str, ...]) -> int:
    return sum(1 for needle in needles if found.get(needle))


def recall_subprocess(contexts: Path, needles: tuple[str, ...]) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--recall", str(contexts), *needles],
        text=True,
        capture_output=True,
        timeout=60,
    )
    found: dict[str, bool] = {}
    if proc.returncode == 0:
        found = json.loads(proc.stdout or "{}")
    return {
        "exit": proc.returncode,
        "found": found,
        "hits": count_hits(found, needles),
        "ms": ms(start),
        "stderr": (proc.stderr or "")[:240],
    }


def manifest_tokens(
    store: Path,
    folder: str,
    binary: Path | None = None,
    home: Path | None = None,
    tmp: Path | None = None,
) -> dict:
    result = run_oc(
        store,
        ["context", "manifest", folder, "--limit", "20", "--format", "json"],
        binary=binary,
        home=home,
        tmp=tmp,
    )
    rows = []
    parse_ok = False
    if result["exit"] == 0:
        try:
            parsed = json.loads(result["stdout"] or "[]")
            if isinstance(parsed, list):
                rows = parsed
                parse_ok = True
        except json.JSONDecodeError:
            parse_ok = False
    blob = json.dumps(rows)
    return {
        "exit": result["exit"],
        "ms": result["ms"],
        "parse_ok": parse_ok,
        "doc_count": len(rows),
        "novel_hits": sum(1 for needle in NOVEL if needle in blob),
        "repo_hits": sum(1 for needle in REPO_NEEDLES if needle in blob),
        "stderr": (result["stderr"] or "")[:240],
    }


def overlap_cards() -> list[dict]:
    rows = []
    stages = ROOT / "data" / "stages"
    for path in sorted(stages.glob("*.json")):
        if path.name in ("_registry.json", "opencontext.json"):
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(card, dict):
            continue
        blob_parts = [str(card.get("name") or ""), str(card.get("uses") or "")]
        for key in ("features", "tags", "catalog_tags"):
            value = card.get(key)
            if isinstance(value, list):
                blob_parts.extend(str(item) for item in value)
        blob = " ".join(blob_parts).lower()
        tokens = set(re.findall(r"[a-z0-9]+", blob))
        words = [word for word in OVERLAP_WORDS if word in tokens]
        name = str(card.get("name") or path.stem)
        if not words and name not in H1_NAMES:
            continue
        rows.append(
            {
                "file": path.name,
                "name": name,
                "stage": card.get("integration_stage"),
                "uses": card.get("uses") or "",
                "words": words,
                "h1_named": name in H1_NAMES,
            }
        )
    return rows


def skill_up_note() -> dict:
    path = ROOT / "eval" / "catchup-1107" / "skill-up" / "summary.json"
    if not path.is_file():
        return {"present": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    benchmark = (data.get("iterations") or [{}])[0].get("benchmark") or {}
    return {
        "present": True,
        "case_count": len(data.get("case_ids") or []),
        "delta_pass_rate": (benchmark.get("delta") or {}).get("pass_rate"),
        "with_mean": ((benchmark.get("with_skill") or {}).get("pass_rate") or {}).get("mean"),
        "without_mean": ((benchmark.get("without_skill") or {}).get("pass_rate") or {}).get("mean"),
    }


def cmd_recall(argv: list[str]) -> int:
    contexts = Path(argv[0])
    needles = tuple(argv[1:])
    print(json.dumps(file_walk_hits(contexts, needles)))
    return 0


def pin_facts() -> dict:
    tree = pin_tree()
    head = ""
    if (tree / ".git").exists():
        proc = subprocess.run(
            ["git", "-C", str(tree), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            env={
                "PATH": os.environ.get("PATH", ""),
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        head = (proc.stdout or "").strip()
    package = {}
    package_path = tree / "package.json"
    if package_path.is_file():
        package = json.loads(package_path.read_text(encoding="utf-8"))
    npm_package = {}
    npm_path = cache_base() / "prefix" / "node_modules" / "@aicontextlab" / "cli" / "package.json"
    if npm_path.is_file():
        npm_package = json.loads(npm_path.read_text(encoding="utf-8"))
    native_version = ""
    native_path = (
        cache_base() / "prefix" / "node_modules" / "@aicontextlab" / "core-native" / "package.json"
    )
    if native_path.is_file():
        native_version = json.loads(native_path.read_text(encoding="utf-8")).get("version", "")
    ball = tarball()
    pin_oc = tree / "bin" / "oc.js"
    npm_oc = cache_base() / "extract" / "package" / "bin" / "oc.js"
    start_attempt = {"skipped": True}
    if pin_oc.is_file():
        start_attempt = run_cmd(
            ["node", str(pin_oc), "folder", "ls"],
            tree,
            oc_env(cache_base() / "run" / "pin-start"),
            20,
        )
        # Keep the failure class, not a long stack.
        lines = [line.strip() for line in (start_attempt.get("stderr") or "").splitlines() if line.strip()]
        interesting = [
            line
            for line in lines
            if "Cannot find module" in line or "Error" in line or "not available" in line
        ]
        tail = (interesting or lines or [""])[0]
        start_attempt = {
            "exit": start_attempt["exit"],
            "ms": start_attempt["ms"],
            "stderr_tail": tail[:240],
        }
    same_bytes = []
    for rel in (
        "bin/oc.js",
        "src/core/search/index.js",
        "src/core/search/native-adapter.js",
        "src/core/store/index.js",
        "src/core/native.js",
        "package.json",
    ):
        left = tree / rel
        right = cache_base() / "extract" / "package" / rel
        if left.is_file() and right.is_file():
            same_bytes.append({"path": rel, "same": sha256_file(left) == sha256_file(right)})
    return {
        "entry_pin": PIN,
        "checkout_head": head,
        "checkout_matches_entry_pin": head == PIN,
        "checkout_package_version": package.get("version"),
        "checkout_license_field": package.get("license"),
        "npm_version": npm_package.get("version"),
        "npm_license_field": npm_package.get("license"),
        "npm_git_head_on_registry": NPM_GIT_HEAD,
        "npm_git_head_equals_entry_pin": NPM_GIT_HEAD == PIN,
        "core_native_version": native_version,
        "tarball_sha256": sha256_file(ball) if ball.is_file() else "",
        "tarball_sha1": sha1_file(ball) if ball.is_file() else "",
        "tarball_sha1_matches_registry": (sha1_file(ball) == NPM_SHA1) if ball.is_file() else False,
        "pin_oc_sha256": sha256_file(pin_oc) if pin_oc.is_file() else "",
        "npm_oc_sha256": sha256_file(npm_oc) if npm_oc.is_file() else "",
        "pin_vs_npm_bytes": same_bytes,
        "pin_cli_start": start_attempt,
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--recall":
        return cmd_recall(argv[1:])

    parser = argparse.ArgumentParser(description="Offline OpenContext recall probe")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--oc-bin", type=Path, default=None)
    parser.add_argument("--rg-bin", default="rg")
    parser.add_argument("--store", type=Path, default=None)
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--tmp", type=Path, default=None)
    parser.add_argument("--skip-pins", action="store_true")
    parser.add_argument("--skip-home", action="store_true")
    args = parser.parse_args(argv)
    binary = args.oc_bin
    home = args.home
    tmp = args.tmp

    before = [] if args.skip_home else home_fingerprint(real_home() / ".opencontext")
    facts = {"skipped": True} if args.skip_pins else pin_facts()
    store = args.store or (cache_base() / "run" / "h1")
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)
    (store / "contexts").mkdir()

    rg_start = time.perf_counter()
    repo_novel = {needle: repo_hits(needle, args.rg_bin) for needle in NOVEL}
    repo_known = {needle: repo_hits(needle, args.rg_bin) for needle in REPO_NEEDLES}
    rg_ms = ms(rg_start)

    folder = run_oc(
        store, ["folder", "create", "evq1107-h1", "-d", "evq1107 probe"], binary=binary, home=home, tmp=tmp
    )
    created = []
    capture_start = time.perf_counter()
    # folder create time is inside capture_ms together with the docs
    for index, needle in enumerate(NOVEL, start=1):
        created.append(
            run_oc(
                store,
                ["doc", "create", "evq1107-h1", "note-%02d.md" % index, "-d", needle],
                binary=binary,
                home=home,
                tmp=tmp,
            )
        )
    capture_ms = round(folder["ms"] + (time.perf_counter() - capture_start) * 1000.0, 1)

    contexts = store / "contexts"
    walk_before = file_walk_hits(contexts, NOVEL + REPO_NEEDLES)
    manifest_before_body = manifest_tokens(store, "evq1107-h1", binary=binary, home=home, tmp=tmp)

    bodies_written = 0
    for index, needle in enumerate(NOVEL, start=1):
        path = contexts / "evq1107-h1" / ("note-%02d.md" % index)
        if path.is_file():
            path.write_text(needle + "\n", encoding="utf-8")
            bodies_written += 1

    walk_after = file_walk_hits(contexts, NOVEL + REPO_NEEDLES)
    recall = recall_subprocess(contexts, NOVEL + REPO_NEEDLES)
    manifest_again = manifest_tokens(store, "evq1107-h1", binary=binary, home=home, tmp=tmp)

    search = run_oc(
        store,
        ["search", NOVEL[0], "--mode", "keyword", "--format", "json", "--limit", "5"],
        timeout=30,
        binary=binary,
        home=home,
        tmp=tmp,
    )
    search_blob = (search["stdout"] + "\n" + search["stderr"]).strip()
    search_skipped = "API key not configured" in search_blob

    novel_agree = 0
    for needle in NOVEL:
        left = bool(walk_after.get(needle))
        right = bool((recall.get("found") or {}).get(needle))
        if left == right:
            novel_agree += 1

    doc_exits = [item["exit"] for item in created]
    result = {
        "gap": "H1",
        "pins": facts,
        "repo_scan_ms": rg_ms,
        "repo_novel_hits": sum(1 for row in repo_novel.values() if row["needle_present"]),
        "repo_known_hits": sum(1 for row in repo_known.values() if row["needle_present"]),
        "repo_novel_files": {needle: row["file_count"] for needle, row in repo_novel.items()},
        "repo_known_files": {needle: row["file_count"] for needle, row in repo_known.items()},
        "folder_create_exit": folder["exit"],
        "doc_create_exits": doc_exits,
        "doc_create_ok": sum(1 for code in doc_exits if code == 0),
        "capture_ms": capture_ms,
        "bodies_written": bodies_written,
        "file_walk_before_body_novel": count_hits(walk_before, NOVEL),
        "file_walk_before_body_repo": count_hits(walk_before, REPO_NEEDLES),
        "file_walk_after_body_novel": count_hits(walk_after, NOVEL),
        "file_walk_after_body_repo": count_hits(walk_after, REPO_NEEDLES),
        "second_process_exit": recall["exit"],
        "second_process_novel": count_hits(recall.get("found") or {}, NOVEL),
        "second_process_repo": count_hits(recall.get("found") or {}, REPO_NEEDLES),
        "second_process_ms": recall["ms"],
        "novel_walk_agreement": novel_agree,
        "novel_asked": len(NOVEL),
        "repo_asked": len(REPO_NEEDLES),
        "manifest_after_create": {
            "exit": manifest_before_body["exit"],
            "ms": manifest_before_body["ms"],
            "parse_ok": manifest_before_body["parse_ok"],
            "doc_count": manifest_before_body["doc_count"],
            "novel_hits": manifest_before_body["novel_hits"],
            "repo_hits": manifest_before_body["repo_hits"],
        },
        "manifest_second": {
            "exit": manifest_again["exit"],
            "ms": manifest_again["ms"],
            "parse_ok": manifest_again["parse_ok"],
            "doc_count": manifest_again["doc_count"],
            "novel_hits": manifest_again["novel_hits"],
            "repo_hits": manifest_again["repo_hits"],
        },
        "search_keyword": {
            "exit": search["exit"],
            "ms": search["ms"],
            "skipped_api_key": search_skipped,
            "stdout_has_novel": NOVEL[0] in (search["stdout"] or ""),
        },
        "h1_graded_cases": 0,
        "h1_score_delta": None,
        "skill_up": skill_up_note(),
        "overlap": overlap_cards(),
        "real_opencontext_unchanged": (
            None if args.skip_home else home_fingerprint(real_home() / ".opencontext") == before
        ),
        "oc_init_ran": False,
        "oc_ui_ran": False,
        "oc_index_build_ran": False,
        "model_lock_taken": False,
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "novel manifest %s/%s file-walk-after %s/%s second %s/%s repo-rg %s/%s search_skip %s"
        % (
            result["manifest_after_create"]["novel_hits"],
            len(NOVEL),
            result["file_walk_after_body_novel"],
            len(NOVEL),
            result["second_process_novel"],
            len(NOVEL),
            result["repo_known_hits"],
            len(REPO_NEEDLES),
            result["search_keyword"]["skipped_api_key"],
        )
    )
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
