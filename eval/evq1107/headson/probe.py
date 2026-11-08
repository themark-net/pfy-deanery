#!/usr/bin/env python3
"""Score a byte-budget JSON preview: pinned hson versus head -c and jq.

Reads documents in this repo, plus one receipt built from data/stages.
No network and no model. A missing binary exits 2 and does not write --out.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = Path(__file__).resolve().parent / "results.json"
CACHE = Path(os.environ.get("HEADSON_CACHE", str(Path.home() / ".cache" / "pfy" / "tools" / "headson")))

VERSION = "0.17.1"
COMMIT = "26ccc98d9e90150ff4c2d9a7299f7ad85544cd23"
TARBALL_SHA256 = "90f5880efcacd16000e12e6f461e7e486ea56636d2f67243de2a65160006ac58"
BINARY_SHA256 = "1a5920a7088db2f2eaf3e53c588fb5133b020a4b9aa417631977e16ead136422"
BUDGET_DEFAULT = 1024
NEEDLE_DEFAULT = "FAIL"
DERIVED_ROWS = 3000
DERIVED_FAIL_ID = 2500
DERIVED_LAST_ID = DERIVED_ROWS - 1

REPO_FILES = (
    "pipelines/dogfood/local-bench/receipt.json",
    "eval/ev1107/neatroots/traces/session-local-build-grep.json",
    "docs/ops/grill-samples/TICKET-pk2.md.grill.json",
    "data/decision-gates/laya-trial.cases.v0.json",
    ".github/workflows/eval-structural.yml",
)

WATCH = frozenset(
    {
        "context",
        "token",
        "tokens",
        "preview",
        "trim",
        "trimming",
        "budget",
        "yaml",
        "memory",
        "head",
    }
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
JQ_SHRINK = (
    "def shrink: "
    'if type == "array" then (if length == 0 then [] else [.[0] | shrink] end) '
    'elif type == "object" then with_entries(.value |= shrink) '
    'elif type == "string" then .[0:40] '
    "else . end; shrink"
)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_bytes(path: Path) -> int:
    total = 0
    if not path.is_dir():
        return 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    return total


def home_stamp(path: Path) -> str:
    if not path.exists():
        return "absent"
    if path.is_symlink():
        return "symlink"
    info = path.stat()
    return "%s:%s:%s" % (info.st_mode, info.st_size, info.st_mtime_ns)


def isolated_env(home: Path) -> dict[str, str]:
    for rel in ("xdg/config", "xdg/cache", "xdg/data", "tmp"):
        (home / rel).mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg/config"),
        "XDG_CACHE_HOME": str(home / "xdg/cache"),
        "XDG_DATA_HOME": str(home / "xdg/data"),
        "TMPDIR": str(home / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    if os.environ.get("STUB_MODE"):
        env["STUB_MODE"] = os.environ["STUB_MODE"]
    return env


def run_cmd(cmd: list[str], env: dict[str, str]) -> tuple[int, bytes, bytes, float]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, bytes) else b""
        err = exc.stderr if isinstance(exc.stderr, bytes) else b"timeout"
        return 124, out, err, time.perf_counter() - started
    return proc.returncode, proc.stdout or b"", proc.stderr or b"", time.perf_counter() - started


def payload_len(raw: bytes) -> int:
    if raw.endswith(b"\n"):
        return len(raw) - 1
    return len(raw)


def json_top_keys(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [str(key) for key in data]
    return []


def yaml_top_keys(path: Path) -> list[str]:
    keys: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if not line or line[0] in " \t#-" or line.startswith("---"):
            continue
        if ":" not in line:
            continue
        key = line.split(":", 1)[0].strip().strip("\"'")
        if key:
            keys.append(key)
    return keys


def top_keys(path: Path) -> list[str]:
    if path.suffix in {".yaml", ".yml"}:
        return yaml_top_keys(path)
    return json_top_keys(path)


def is_yaml(path: Path) -> bool:
    return path.suffix in {".yaml", ".yml"}


def walk_preview(parsed: object, needle: str, sentinel: int | None) -> dict:
    ids: list[int] = []
    needle_kept = False
    sentinel_kept = False

    def rec(node: object) -> None:
        nonlocal needle_kept, sentinel_kept
        if isinstance(node, dict):
            verdict = node.get("verdict")
            if isinstance(verdict, str) and needle in verdict:
                needle_kept = True
            if "id" in node and "verdict" in node and isinstance(node.get("id"), int):
                ids.append(node["id"])
                if sentinel is not None and node["id"] == sentinel:
                    sentinel_kept = True
            for value in node.values():
                rec(value)
        elif isinstance(node, list):
            for value in node:
                rec(value)
        elif isinstance(node, str) and needle in node:
            needle_kept = True

    rec(parsed)
    return {
        "needle_kept": needle_kept,
        "sentinel_id_kept": (sentinel_kept if sentinel is not None else None),
        "ids": ids,
    }


def score_output(
    raw: bytes,
    budget: int,
    keys: list[str],
    needle: str,
    sentinel: int | None,
    last_id: int | None,
) -> dict:
    preview: object | None
    try:
        preview = json.loads(raw.decode("utf-8"))
        parse_ok = True
    except (UnicodeDecodeError, json.JSONDecodeError):
        preview = None
        parse_ok = False
    got = [str(key) for key in preview] if isinstance(preview, dict) else []
    missing = [key for key in keys if key not in got]
    found = walk_preview(preview, needle, sentinel) if parse_ok else {
        "needle_kept": False,
        "sentinel_id_kept": None if sentinel is None else False,
        "ids": [],
    }
    ids = found["ids"]
    payload = payload_len(raw)
    under = payload <= budget
    stdout_under = len(raw) <= budget
    keys_ok = bool(keys) and not missing
    sentinel_kept = found["sentinel_id_kept"]
    shape_only = bool(found["needle_kept"]) and sentinel_kept is False
    return {
        "stdout_bytes": len(raw),
        "payload_bytes": payload,
        "under_budget": under,
        "stdout_under_budget": stdout_under,
        "parse_ok": parse_ok,
        "keys_kept": len(keys) - len(missing),
        "keys_total": len(keys),
        "keys_ok": keys_ok,
        "keys_missing": missing[:20],
        "hard_cap_pass": bool(parse_ok and keys_ok and under),
        "stdout_hard_cap_pass": bool(parse_ok and keys_ok and stdout_under),
        "needle_kept": bool(found["needle_kept"]),
        "sentinel_id_kept": sentinel_kept,
        "shape_only": shape_only,
        "last_id_kept": (last_id in ids) if last_id is not None else None,
        "sampled_ids": ids[:24],
        "id_count": len(ids),
        "stdout_sha256": hashlib.sha256(raw).hexdigest(),
    }


def score_cmd(
    cmd: list[str],
    env: dict[str, str],
    budget: int,
    keys: list[str],
    needle: str,
    sentinel: int | None,
    last_id: int | None,
    rerun: bool,
) -> dict:
    code, out, err, seconds = run_cmd(cmd, env)
    scored = score_output(out, budget, keys, needle, sentinel, last_id)
    scored["returncode"] = code
    scored["seconds"] = round(seconds, 4)
    scored["stderr_bytes"] = len(err)
    scored["rerun_identical"] = None
    if code != 0:
        scored["hard_cap_pass"] = False
        scored["stdout_hard_cap_pass"] = False
    if rerun:
        code2, out2, err2, seconds2 = run_cmd(cmd, env)
        scored["rerun_identical"] = out2 == out and code2 == code
        scored["seconds"] = round(seconds + seconds2, 4)
        scored["stderr_bytes"] = len(err) + len(err2)
    return scored


def hson_cmd(binary: str, budget: int, path: Path, extra: list[str]) -> list[str]:
    kind = "yaml" if is_yaml(path) else "json"
    return [
        binary,
        "-c",
        str(budget),
        "-i",
        kind,
        "-f",
        "json",
        "-t",
        "strict",
        "--no-color",
        *extra,
        str(path),
    ]


def measure_file(
    path: Path,
    label: str,
    kind: str,
    binary: str,
    env: dict[str, str],
    budget: int,
    needle: str,
    sentinel: int | None,
    last_id: int | None,
    with_jq: bool,
) -> dict:
    keys = top_keys(path)
    modes: dict[str, dict] = {}
    head_cmd = ["head", "-c", str(budget), str(path)]
    modes["head_c"] = score_cmd(head_cmd, env, budget, keys, needle, sentinel, last_id, False)
    plan = (
        ("hson", []),
        ("hson_head", ["--head"]),
        ("hson_tail", ["--tail"]),
        ("hson_grep", ["--grep", needle]),
        ("hson_capped_grep", ["--capped-grep", needle]),
    )
    for name, extra in plan:
        modes[name] = score_cmd(
            hson_cmd(binary, budget, path, extra),
            env,
            budget,
            keys,
            needle,
            sentinel,
            last_id,
            name == "hson",
        )
    if with_jq and not is_yaml(path):
        modes["jq_shrink"] = score_cmd(
            ["jq", "-c", JQ_SHRINK, str(path)],
            env,
            budget,
            keys,
            needle,
            sentinel,
            last_id,
            False,
        )
    return {
        "label": label,
        "kind": kind,
        "input_bytes": path.stat().st_size,
        "top_keys": keys,
        "sentinel_id": sentinel,
        "last_id": last_id,
        "modes": modes,
    }


def build_derived(cache: Path, root: Path) -> tuple[Path, int]:
    sources: list[dict] = []
    for path in sorted((root / "data" / "stages").glob("*.json")):
        if path.name in {"_registry.json", "headson.json"}:
            continue
        card = json.loads(path.read_text(encoding="utf-8"))
        name = card.get("name")
        stage = card.get("integration_stage")
        sources.append(
            {
                "file": path.name,
                "name": name if isinstance(name, str) else "",
                "stage": stage if isinstance(stage, str) else "",
            }
        )
    if not sources:
        raise SystemExit("no stage cards to build the receipt")
    rows = []
    collisions = 0
    for index in range(DERIVED_ROWS):
        src = sources[index % len(sources)]
        row = {
            "id": index,
            "file": src["file"],
            "name": src["name"],
            "stage": src["stage"],
            "verdict": "FAIL" if index == DERIVED_FAIL_ID else "PASS",
        }
        if index != DERIVED_FAIL_ID and NEEDLE_DEFAULT in json.dumps(row):
            collisions += 1
        rows.append(row)
    doc = {
        "run": "evq-headson",
        "results": rows,
        "meta": {
            "source": "data/stages",
            "stage_cards": len(sources),
            "count": DERIVED_ROWS,
            "fail_id": DERIVED_FAIL_ID,
            "needle_collisions": collisions,
        },
    }
    dest = cache / "tmp" / "stages-receipt.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    return dest, collisions


def catalog_hits(root: Path) -> list[dict]:
    hits = []
    directory = root / "data" / "stages"
    for path in sorted(directory.glob("*.json")):
        if path.name in {"_registry.json", "headson.json"}:
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(card, dict):
            continue
        parts: list[str] = []
        for key in ("uses", "features", "tags", "catalog_tags"):
            value = card.get(key)
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item) for item in value)
        tokens = set(TOKEN_RE.findall(" ".join(parts).lower()))
        matched = sorted(tokens & WATCH)
        if not matched:
            continue
        uses = card.get("uses")
        if not isinstance(uses, str):
            uses = ""
        hits.append(
            {
                "name": card.get("name"),
                "stage": card.get("integration_stage"),
                "matched": matched,
                "uses": " ".join(uses.split())[:180],
            }
        )
    return hits


def count_mode(docs: list[dict], mode: str, field: str) -> int:
    total = 0
    for doc in docs:
        row = doc.get("modes", {}).get(mode)
        if isinstance(row, dict) and row.get(field):
            total += 1
    return total


def mode_count(docs: list[dict], mode: str) -> int:
    return sum(1 for doc in docs if mode in doc.get("modes", {}))


def summarize(docs: list[dict], started: float) -> dict:
    derived = next((doc for doc in docs if doc.get("kind") == "derived"), None)
    derived_modes = derived.get("modes", {}) if derived else {}
    grep = derived_modes.get("hson_grep", {})
    capped = derived_modes.get("hson_capped_grep", {})
    default = derived_modes.get("hson", {})
    tail = derived_modes.get("hson_tail", {})
    return {
        "documents": len(docs),
        "hson_hard_cap_pass": count_mode(docs, "hson", "hard_cap_pass"),
        "hson_stdout_hard_cap_pass": count_mode(docs, "hson", "stdout_hard_cap_pass"),
        "hson_keys_ok": count_mode(docs, "hson", "keys_ok"),
        "hson_parse_ok": count_mode(docs, "hson", "parse_ok"),
        "head_c_hard_cap_pass": count_mode(docs, "head_c", "hard_cap_pass"),
        "head_c_parse_ok": count_mode(docs, "head_c", "parse_ok"),
        "jq_shrink_scored": mode_count(docs, "jq_shrink"),
        "jq_shrink_hard_cap_pass": count_mode(docs, "jq_shrink", "hard_cap_pass"),
        "jq_shrink_keys_ok": count_mode(docs, "jq_shrink", "keys_ok"),
        "grep_hard_cap_pass": count_mode(docs, "hson_grep", "hard_cap_pass"),
        "capped_grep_hard_cap_pass": count_mode(docs, "hson_capped_grep", "hard_cap_pass"),
        "capped_grep_keys_ok": count_mode(docs, "hson_capped_grep", "keys_ok"),
        "rerun_identical": count_mode(docs, "hson", "rerun_identical"),
        "derived_default_sentinel_kept": default.get("sentinel_id_kept"),
        "derived_default_ids": default.get("sampled_ids"),
        "derived_tail_last_id_kept": tail.get("last_id_kept"),
        "derived_grep_needle_kept": grep.get("needle_kept"),
        "derived_grep_sentinel_kept": grep.get("sentinel_id_kept"),
        "derived_grep_hard_cap_pass": grep.get("hard_cap_pass"),
        "derived_grep_stdout_bytes": grep.get("stdout_bytes"),
        "derived_capped_grep_sentinel_kept": capped.get("sentinel_id_kept"),
        "derived_capped_grep_hard_cap_pass": capped.get("hard_cap_pass"),
        "seconds": round(time.perf_counter() - started, 4),
    }


def pin_block(binary: Path, cache: Path, version_text: str, fixture: bool) -> dict:
    digest = sha256_file(binary)
    tarball = cache / "src" / "hson-x86_64-unknown-linux-musl.tar.gz"
    tarball_digest = None if fixture else sha256_file(tarball)
    expected_binary = CACHE / "bin" / "hson"
    same_install = False
    try:
        same_install = binary.resolve() == expected_binary.resolve() and expected_binary.is_file()
    except OSError:
        same_install = False
    pin_ok = None
    if same_install and not fixture:
        pin_ok = (
            digest == BINARY_SHA256
            and tarball_digest == TARBALL_SHA256
            and VERSION in version_text
        )
    return {
        "version_expected": VERSION,
        "version_got": version_text,
        "commit": COMMIT,
        "tarball_sha256_expected": TARBALL_SHA256,
        "tarball_sha256": tarball_digest,
        "binary_sha256_expected": BINARY_SHA256,
        "binary_sha256": digest,
        "binary_bytes": binary.stat().st_size if binary.is_file() else None,
        "install_bytes": None if fixture else tree_bytes(cache),
        "pin_ok": pin_ok,
    }


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score hson byte-budget previews on this repo.")
    parser.add_argument("--fixture", default="", help="Score this one file and skip the repo set.")
    parser.add_argument("--out", default="", help="Result JSON path. Required with --fixture.")
    parser.add_argument("--budget", type=int, default=BUDGET_DEFAULT)
    parser.add_argument("--sentinel-id", type=int, default=None)
    parser.add_argument("--needle", default=NEEDLE_DEFAULT)
    parser.add_argument("--child-home", default="", help="HOME for the hson child process.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.budget < 1:
        print(json.dumps({"error": "budget must be >= 1"}))
        return 2
    fixture = Path(args.fixture) if args.fixture else None
    if fixture is not None and not args.out:
        print(json.dumps({"error": "--fixture needs --out"}))
        return 2
    binary = Path(os.environ.get("HSON_BIN", str(CACHE / "bin" / "hson")))
    if not binary.is_file():
        print(json.dumps({"error": "hson missing"}))
        return 2
    child_home = Path(args.child_home) if args.child_home else (CACHE / "home")
    env = isolated_env(child_home)
    code, out, _err, _dt = run_cmd([str(binary), "--version"], env)
    version_text = out.decode("utf-8", "replace").strip()
    if code != 0 or VERSION not in version_text:
        print(json.dumps({"error": "version mismatch", "got": version_text, "code": code}))
        return 2

    started = time.perf_counter()
    real_state = Path.home() / ".local" / "state" / "headson"
    before = home_stamp(real_state)
    documents: list[dict] = []
    collisions = None
    if fixture is not None:
        documents.append(
            measure_file(
                fixture,
                fixture.name,
                "fixture",
                str(binary),
                env,
                args.budget,
                args.needle,
                args.sentinel_id,
                None,
                False,
            )
        )
    else:
        for rel in REPO_FILES:
            path = ROOT / rel
            if not path.is_file():
                documents.append({"label": rel, "kind": "repo", "error": "missing", "modes": {}})
                continue
            documents.append(
                measure_file(
                    path,
                    rel,
                    "repo",
                    str(binary),
                    env,
                    args.budget,
                    args.needle,
                    None,
                    None,
                    True,
                )
            )
        derived, collisions = build_derived(CACHE, ROOT)
        documents.append(
            measure_file(
                derived,
                "derived:data/stages",
                "derived",
                str(binary),
                env,
                args.budget,
                args.needle,
                DERIVED_FAIL_ID,
                DERIVED_LAST_ID,
                True,
            )
        )
        documents[-1]["needle_collisions"] = collisions
    after = home_stamp(real_state)
    summary = summarize(documents, started)
    jq_code, jq_out, _, _ = run_cmd(["jq", "--version"], env)
    body = {
        "budget": args.budget,
        "needle": args.needle,
        "pin": pin_block(binary, CACHE, version_text, fixture is not None),
        "real_home_untouched": before == after,
        "real_home_state": after,
        "jq": {
            "present": jq_code == 0,
            "version": jq_out.decode("utf-8", "replace").strip() if jq_code == 0 else "",
        },
        "catalog_hits": [] if fixture is not None else catalog_hits(ROOT),
        "documents": documents,
        "summary": summary,
    }
    dest = Path(args.out) if args.out else DEFAULT_OUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    line = (
        "hson %s/%s head %s/%s jq %s/%s"
        % (
            summary["hson_hard_cap_pass"],
            summary["documents"],
            summary["head_c_hard_cap_pass"],
            summary["documents"],
            summary["jq_shrink_hard_cap_pass"],
            summary["jq_shrink_scored"],
        )
    )
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
