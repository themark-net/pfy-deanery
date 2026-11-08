#!/usr/bin/env python3
"""Offline cass-memory probe for gap H1 (memory and context).

Scores a hand-written playbook against token overlap on the same rules, and
counts rules extracted from one synthetic session. No model, no API key, no
cm doctor --fix, no cm hook, no cm update, no cass install. Child HOME stays
under the directory passed as --home.
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
HERE = Path(__file__).resolve().parent
RULES_PATH = HERE / "rules.json"
PIN_SHA256 = "06e1563881f8bb1225cf7036068252ef210f242704a27f8ce32518b822181bd7"
PIN_COMMIT = "229a312b696aa347d1e2c491d3d466c925716dc0"
EXPECTED_VERSION = "0.5.0"

STOP = {
    "a", "an", "the", "of", "to", "and", "or", "for", "in", "on", "with",
    "before", "after", "when", "one", "it", "its", "by", "is", "are", "be",
    "this", "that", "from", "into", "not", "any", "must", "stay", "how",
    "should", "which", "where", "what", "while", "under", "out", "own",
    "does", "do", "can", "will", "than",
}
BLOCKED_NAMES = (
    "claude", "codex", "cursor", "ollama", "cass", "grok", "aider", "opencode",
)
LLM_NAMES = {"claude", "codex", "cursor", "grok", "aider", "opencode", "ollama"}
SCAN_ROOTS = ("AGENTS.md", "docs", "data/stages", "scripts", "sources/entries")
H1_NEIGHBORS = (
    "skill-up",
    "harness2",
    "Harness Score",
    "eval-harness (pfy)",
    "neatroots",
)
OVERLAP_WORDS = ("memory", "playbook", "procedural", "session")
TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def tokens(text: str) -> set[str]:
    return {tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOP}


def overlap_winner(query: str, rows: list[dict]) -> str | None:
    wanted = tokens(query)
    best_name = None
    best_score = 0
    for row in rows:
        score = len(wanted & tokens(row["content"]))
        if score > best_score:
            best_score = score
            best_name = row["name"]
    return best_name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def real_user_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def home_snapshot(root: Path) -> dict:
    if not root.exists():
        return {"exists": False, "entries": 0}
    count = 0
    if root.is_file():
        return {"exists": True, "entries": 1}
    for dirpath, dirnames, filenames in os.walk(root):
        count += len(dirnames) + len(filenames)
        if count > 40:
            break
    return {"exists": True, "entries": count}


def load_rules(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SystemExit("rules file is not an object")
    rules = doc.get("rules")
    distractor = doc.get("distractor")
    needles = doc.get("repo_needles")
    if not isinstance(rules, list) or not rules:
        raise SystemExit("rules file has no rules")
    if not isinstance(distractor, dict):
        raise SystemExit("rules file has no distractor")
    if not isinstance(needles, list) or not needles:
        raise SystemExit("rules file has no repo needles")
    return doc


def write_blockers(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    script = (
        "#!/bin/sh\n"
        "printf '%s\\n' \"$0\" >> \"$CM_BLOCK_LOG\"\n"
        "exit 2\n"
    )
    for name in BLOCKED_NAMES:
        path = directory / name
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)


def child_env(home: Path, block_log: Path) -> dict[str, str]:
    stub = home / "pathbin"
    return {
        "PATH": str(stub) + ":/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "TMPDIR": str(home / "tmp"),
        "NO_COLOR": "1",
        "CASS_MEMORY_NO_EMOJI": "1",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "CM_BLOCK_LOG": str(block_log),
    }


def run_cm(
    binary: str,
    args: list[str],
    env: dict[str, str],
    cwd: Path,
    timeout: float,
    isolate_net: bool,
) -> dict:
    cmd = [binary, *args]
    if isolate_net:
        unshare = shutil.which("unshare")
        if unshare:
            cmd = [unshare, "-rn", binary, *args]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "args": args,
            "rc": None,
            "ms": round((time.perf_counter() - started) * 1000.0, 1),
            "timeout": True,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "data": None,
            "parse_ok": False,
        }
    stdout = proc.stdout or ""
    data = None
    parse_ok = False
    try:
        doc = json.loads(stdout)
    except json.JSONDecodeError:
        doc = None
    if isinstance(doc, dict) and doc.get("success") is True and isinstance(doc.get("data"), dict):
        data = doc["data"]
        parse_ok = True
    return {
        "args": args,
        "rc": proc.returncode,
        "ms": round((time.perf_counter() - started) * 1000.0, 1),
        "timeout": False,
        "stdout": stdout,
        "stderr": proc.stderr or "",
        "data": data,
        "parse_ok": parse_ok,
        "success": isinstance(doc, dict) and doc.get("success") is True,
    }


def bullet_contents(data: dict | None) -> list[dict]:
    if not isinstance(data, dict):
        return []
    rows = data.get("relevantBullets")
    if not isinstance(rows, list):
        rows = data.get("bullets")
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def count_bullets(data: dict | None) -> int | None:
    if not isinstance(data, dict):
        return None
    rows = data.get("bullets")
    if isinstance(rows, list):
        return len(rows)
    return None


def marker_index(rows: list[dict], marker: str) -> int | None:
    for index, row in enumerate(rows):
        if marker in str(row.get("content") or ""):
            return index
    return None


def read_blocked(path: Path) -> list[str]:
    if not path.is_file():
        return []
    names = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        name = Path(line.strip()).name
        if name:
            names.append(name)
    return names


def repo_has_needle(repo: Path, needle: str, rg_bin: str | None) -> bool:
    roots = [str(repo / rel) for rel in SCAN_ROOTS if (repo / rel).exists()]
    if not roots:
        return False
    if rg_bin:
        proc = subprocess.run(
            [rg_bin, "-l", "--fixed-string", "--glob", "!.git/**", needle, *roots],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    for root_name in SCAN_ROOTS:
        base = repo / root_name
        if not base.exists():
            continue
        files = [base] if base.is_file() else base.rglob("*")
        for path in files:
            if not path.is_file():
                continue
            if path.stat().st_size > 2_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if needle in text:
                return True
    return False


def catalog_overlap(repo: Path) -> list[dict]:
    stages = repo / "data" / "stages"
    if not stages.is_dir():
        return []
    rows = []
    for path in sorted(stages.glob("*.json")):
        if path.name == "_registry.json":
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(card, dict):
            continue
        blob_parts = [str(card.get("uses") or ""), str(card.get("name") or "")]
        for key in ("features", "tags", "catalog_tags", "non_goals"):
            value = card.get(key)
            if isinstance(value, list):
                blob_parts.extend(str(item) for item in value)
            elif isinstance(value, str):
                blob_parts.append(value)
        blob = " ".join(blob_parts)
        found = [word for word in OVERLAP_WORDS if re.search(r"\b" + word + r"\b", blob, re.I)]
        name = str(card.get("name") or path.stem)
        if found or name in H1_NEIGHBORS:
            rows.append(
                {
                    "name": name,
                    "slug": path.stem,
                    "stage": card.get("integration_stage"),
                    "uses": str(card.get("uses") or "")[:240],
                    "words": found,
                    "h1_neighbor": name in H1_NEIGHBORS,
                }
            )
    return rows


def query_row(rule: dict, call: dict, watch: list[str]) -> dict:
    rows = bullet_contents(call["data"]) if call["parse_ok"] else []
    index = marker_index(rows, rule["marker"]) if call["parse_ok"] else None
    top = str(rows[0].get("content") or "") if rows else ""
    seen = []
    ranked = []
    if call["parse_ok"]:
        for marker in watch:
            if any(marker in str(item.get("content") or "") for item in rows):
                seen.append(marker)
        for item in rows:
            content = str(item.get("content") or "")
            marker = next((name for name in watch if name in content), None)
            ranked.append({"marker": marker, "score": item.get("relevanceScore")})
    top_marker = ranked[0]["marker"] if ranked else None
    return {
        "name": rule["name"],
        "marker": rule["marker"],
        "rc": call["rc"],
        "ms": call["ms"],
        "parse_ok": call["parse_ok"],
        "timeout": call["timeout"],
        "hit": index == 0,
        "recalled": index is not None,
        "rank": index,
        "returned": len(rows),
        "top_has_marker": rule["marker"] in top,
        "top_marker": top_marker,
        "top_score": ranked[0]["score"] if ranked else None,
        "ranked": ranked,
        "seen_markers": seen,
        "semantic_mode": (call["data"] or {}).get("semanticMode") if call["parse_ok"] else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline cass-memory H1 probe")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--rules", type=Path, default=RULES_PATH)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--cm-bin", default="")
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--real-home", type=Path, default=None)
    parser.add_argument("--rg-bin", default="")
    parser.add_argument("--sha-expect", default=PIN_SHA256)
    parser.add_argument("--skip-sha", action="store_true")
    parser.add_argument("--no-unshare", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    started = time.perf_counter()
    pack = load_rules(args.rules)
    rules = list(pack["rules"])
    distractor = pack["distractor"]
    needles = [str(item) for item in pack["repo_needles"]]
    session_lines = pack.get("session_lines") or []
    repo = args.repo.resolve()
    real_home = (args.real_home or real_user_home()).resolve()
    cache_home = args.home
    if cache_home is None:
        cache_home = real_user_home() / ".cache" / "pfy" / "tools" / "cass-memory" / "probe-home"
    cache_home = cache_home.resolve()
    watched = {
        "cass-memory": real_home / ".cass-memory",
        "cache-cass-memory": real_home / ".cache" / "cass-memory",
        "cass": real_home / ".cass",
    }
    before = {name: home_snapshot(path) for name, path in watched.items()}
    binary = args.cm_bin or str(
        real_user_home() / ".cache" / "pfy" / "tools" / "cass-memory" / "bin" / "cass-memory-linux-x64"
    )
    binary_path = Path(binary)
    sha = sha256_file(binary_path) if binary_path.is_file() else ""
    sha_ok = bool(sha) and sha == args.sha_expect
    result: dict = {
        "pin_commit": PIN_COMMIT,
        "pin_sha256": PIN_SHA256,
        "version_expect": EXPECTED_VERSION,
        "binary": str(binary_path),
        "binary_bytes": binary_path.stat().st_size if binary_path.is_file() else 0,
        "sha256": sha,
        "sha256_ok": sha_ok if not args.skip_sha else True,
        "skip_sha": args.skip_sha,
        "ran": False,
        "h1_graded_cases": 0,
        "history": {"status": "SKIPPED", "rules_extracted": 0, "llm_skipped": True},
    }
    if not args.skip_sha and not sha_ok:
        result["reason"] = "sha256 mismatch or missing binary; cm was not executed"
        result["real_home_before"] = before
        result["real_home_after"] = before
        result["real_home_changed"] = False
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ran": False, "sha256_ok": False}))
        return 0

    if cache_home.exists():
        shutil.rmtree(cache_home)
    for rel in ("tmp", "config", "cache", "data", "work"):
        (cache_home / rel).mkdir(parents=True)
    block_log = cache_home / "blocked.log"
    write_blockers(cache_home / "pathbin")
    env = child_env(cache_home, block_log)
    work = cache_home / "work"
    session_path = work / "session.jsonl"
    session_path.write_text("\n".join(session_lines) + "\n", encoding="utf-8")
    isolate = not args.no_unshare

    def call(argv: list[str], timeout: float = 30.0, net: bool = False) -> dict:
        return run_cm(str(binary_path), argv, env, work, timeout, isolate_net=net)

    version = call(["--version"], timeout=20)
    init = call(["init", "--json", "--no-interactive"])
    doctor = call(["doctor", "--json", "--no-interactive"], timeout=40)
    before_ls = call(["ls", "--json"])
    reflect_dry = call(["reflect", "--dry-run", "--json", "--days", "1", "--max-sessions", "1"], timeout=25)
    after_dry = call(["ls", "--json"])
    reflect_session = call(
        ["reflect", "--session", str(session_path), "--json"],
        timeout=25,
        net=isolate,
    )
    after_reflect = call(["ls", "--json"])
    blocked = read_blocked(block_log)
    llm_called = sorted({name for name in blocked if name in LLM_NAMES})
    before_count = count_bullets(before_ls["data"]) or 0
    dry_count = count_bullets(after_dry["data"]) or 0
    after_count = count_bullets(after_reflect["data"]) or 0
    extracted = max(0, after_count - before_count)
    new_rows = bullet_contents(after_reflect["data"])
    history_has_sha = any("sha256" in str(row.get("content") or "") for row in new_rows[before_count:])
    reflect_stderr = (reflect_session["stderr"] or "").lower()
    llm_phrase = "not configured" in reflect_stderr or "local cli" in reflect_stderr
    history = {
        "status": "ran" if not reflect_session["timeout"] else "SKIPPED",
        "reason": "timeout" if reflect_session["timeout"] else "",
        "rules_extracted": extracted,
        "dry_run_added": max(0, dry_count - before_count),
        "reflect_rc": reflect_session["rc"],
        "reflect_ms": reflect_session["ms"],
        "reflect_parse_ok": reflect_session["parse_ok"],
        "dry_run_rc": reflect_dry["rc"],
        "dry_run_parse_ok": reflect_dry["parse_ok"],
        "sha256_in_extracted": history_has_sha,
        "llm_skipped": extracted == 0 and (bool(llm_called) or llm_phrase or not reflect_session["parse_ok"]),
        "llm_binaries_blocked": llm_called,
        "blocked": blocked,
        "cass_available": (init["data"] or {}).get("cassAvailable") if init["parse_ok"] else None,
        "isolate_net": isolate,
    }
    if reflect_session["timeout"]:
        history["llm_skipped"] = True
        history["rules_extracted"] = 0

    added = []
    for rule in rules + [distractor]:
        row = call(["add", rule["content"], "--category", rule["category"], "--json"])
        bullet = (row["data"] or {}).get("bullet") if row["parse_ok"] else None
        added.append(
            {
                "name": rule["name"],
                "marker": rule["marker"],
                "parse_ok": row["parse_ok"],
                "rc": row["rc"],
                "ms": row["ms"],
                "id": (bullet or {}).get("id") if isinstance(bullet, dict) else None,
            }
        )

    watch = [rule["marker"] for rule in rules] + [distractor["marker"]]
    first = []
    second = []
    for rule in rules:
        first.append(query_row(rule, call(["context", rule["query"], "--json"]), watch))
        second.append(query_row(rule, call(["context", rule["query"], "--json"]), watch))
    agreement = sum(
        1
        for left, right in zip(first, second)
        if left["parse_ok"] and right["parse_ok"] and left["rank"] == right["rank"] and left["hit"] == right["hit"]
    )
    overlap_hits = 0
    for rule in rules:
        winner = overlap_winner(rule["query"], rules)
        if winner == rule["name"]:
            overlap_hits += 1
    distractor_leaks = sum(1 for row in first if distractor["marker"] in row["seen_markers"])

    repo_rows = []
    for needle in needles:
        found = repo_has_needle(repo, needle, args.rg_bin or None)
        probed = call(["context", needle, "--json"])
        rows = bullet_contents(probed["data"]) if probed["parse_ok"] else []
        in_playbook = any(needle in str(item.get("content") or "") for item in rows)
        repo_rows.append(
            {
                "needle": needle,
                "rg_hit": found,
                "playbook_hit": in_playbook,
                "parse_ok": probed["parse_ok"],
                "ms": probed["ms"],
            }
        )

    plant = next(item for item in added if item["name"] == distractor["name"])
    states = []
    mark_ok = True
    for _ in range(3):
        marked = call(
            ["mark", str(plant["id"] or ""), "--harmful", "--reason", "other", "--json"]
        )
        state = (marked["data"] or {}).get("newState") if marked["parse_ok"] else None
        states.append(state)
        if not marked["parse_ok"]:
            mark_ok = False
    after_plant = call(["context", distractor["query"], "--json"])
    plant_rows = bullet_contents(after_plant["data"]) if after_plant["parse_ok"] else []
    removed = after_plant["parse_ok"] and all(
        distractor["marker"] not in str(item.get("content") or "") for item in plant_rows
    )
    usage = call(["usage", "--json"])
    version_text = (version["stdout"] or "").strip().splitlines()
    doctor_data = doctor["data"] if doctor["parse_ok"] else {}
    cass_check = {}
    for check in doctor_data.get("checks") or []:
        if isinstance(check, dict) and check.get("item") == "cass":
            cass_check = check
            break
    after = {name: home_snapshot(path) for name, path in watched.items()}
    top1 = sum(1 for row in first if row["hit"])
    recalled = sum(1 for row in first if row["recalled"])
    bad_json = sum(1 for row in first if not row["parse_ok"])
    result.update(
        {
            "ran": True,
            "version": version_text[0] if version_text else "",
            "init_ok": init["parse_ok"],
            "init_ms": init["ms"],
            "cass_available": history["cass_available"],
            "doctor": {
                "parse_ok": doctor["parse_ok"],
                "rc": doctor["rc"],
                "ms": doctor["ms"],
                "overall": doctor_data.get("overallStatus"),
                "cass_status": cass_check.get("status"),
                "cass_message": cass_check.get("message"),
            },
            "history": history,
            "added": added,
            "queries": first,
            "repeat": second,
            "playbook_queries": len(rules),
            "playbook_top1": top1,
            "playbook_recall": recalled,
            "bad_json_queries": bad_json,
            "agreement": agreement,
            "overlap_top1": overlap_hits,
            "top1_delta": top1 - overlap_hits,
            "distractor_leaks": distractor_leaks,
            "semantic_mode": next((row["semantic_mode"] for row in first if row["semantic_mode"]), None),
            "repo_needles": repo_rows,
            "repo_rg_hits": sum(1 for row in repo_rows if row["rg_hit"]),
            "repo_playbook_hits": sum(1 for row in repo_rows if row["playbook_hit"]),
            "deprecation": {
                "id": plant["id"],
                "mark_ok": mark_ok,
                "states": states,
                "last_state": states[-1] if states else None,
                "removed_from_context": removed,
                "context_parse_ok": after_plant["parse_ok"],
                "context_ms": after_plant["ms"],
            },
            "usage": {
                "parse_ok": usage["parse_ok"],
                "today": (usage["data"] or {}).get("today") if usage["parse_ok"] else None,
                "total": (usage["data"] or {}).get("total") if usage["parse_ok"] else None,
            },
            "h1_graded_cases": 0,
            "catalog_overlap": catalog_overlap(repo),
            "skipped_commands": ["diary", "validate", "audit", "hook", "update", "doctor --fix", "serve"],
            "real_home_before": before,
            "real_home_after": after,
            "real_home_changed": before != after,
            "wall_ms": round((time.perf_counter() - started) * 1000.0, 1),
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ran": True,
                "version": result["version"],
                "history_rules": history["rules_extracted"],
                "top1": top1,
                "overlap_top1": overlap_hits,
                "delta": top1 - overlap_hits,
                "repo_rg": result["repo_rg_hits"],
                "repo_playbook": result["repo_playbook_hits"],
                "deprecated_removed": removed,
                "usage_total": result["usage"]["total"],
                "wall_ms": result["wall_ms"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
