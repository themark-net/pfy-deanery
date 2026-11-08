#!/usr/bin/env python3
"""Score the pinned anti-slop pack offline. No model and no network.

The pack is prompt text. This probe measures three numbers:

- context: bytes and chars/4 of the core skill versus skills already in tree
- executable rules: R-xx ids that appear in program files, not only in the skill
- a lexical score: em dashes, quoted FORBIDDEN phrases, and comment snippets

The lexical score runs twice. The two passes must match. Upstream
scripts/check-repo.mjs audits the pack itself. It does not take a path, so
it is not a score of this repo. contrast-check.py scores color pairs.

Exit 0: versions agree, the two lexical passes match, and the self-check
was skipped or passed.
Exit 1: versions agree and the lexical score is in the result file, but
check-repo or the contrast selftest ran and failed.
Exit 2: the version files disagree, or the core text is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EM = "\u2014"
EN = "\u2013"
RULE_HEAD = re.compile(r"^#### (R-\d{2})\b", re.M)
QUOTED = re.compile(r'"([^"]+)"')
COMMENT_TICK = re.compile(r"`([^`\n]+)`")
NOT_A_BAN = re.compile(r"^##\s+Not a Ban\b", re.M)
TEXT_EXT = {
    ".md", ".py", ".txt", ".js", ".mjs", ".css", ".html", ".tsx", ".jsx",
    ".yml", ".yaml", ".rst",
}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "tmp",
}
# Operator text and code the pack would sit on. Eval receipts stay out.
REPO_INCLUDE = (
    "AGENTS.md",
    "docs",
    "bootstrap/grok-cli/skills",
    "bootstrap/grok-cli/skills-external/ponytail",
    ".grok/skills",
    "pfylib",
    "scripts",
)
OURS = (
    "bootstrap/grok-cli/skills/karpathy-guidelines/SKILL.md",
    "bootstrap/grok-cli/skills/ui-is-the-app-design-in-loop/SKILL.md",
    "bootstrap/grok-cli/skills-external/ponytail/ponytail/SKILL.md",
)
CATALOG_WORDS = (
    "slop", "copywriting", "buzzword", "contrast", "baseline", "yagni",
    "comment",
)
MAX_FILE = 1_000_000
EXAMPLE_LIMIT = 12


def default_src() -> Path:
    env = os.environ.get("ANTISLOP_SRC")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "pfy" / "tools" / "anti-slop" / "src"


def cache_root() -> Path:
    env = os.environ.get("ANTISLOP_CACHE")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "pfy" / "tools" / "anti-slop"


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_versions(src: Path) -> dict:
    found: dict[str, str | None] = {}
    version_file = src / "skills" / "antislop" / "VERSION"
    if version_file.is_file():
        found["VERSION"] = version_file.read_text(encoding="utf-8").strip()
    for label, rel in (("package.json", "package.json"), ("cli/package.json", "cli/package.json")):
        path = src / rel
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            found[label] = None
            continue
        value = payload.get("version") if isinstance(payload, dict) else None
        found[label] = value if isinstance(value, str) else None
    values = [item for item in found.values() if isinstance(item, str) and item]
    agree = len(found) >= 2 and len(values) == len(found) and len(set(values)) == 1
    return {"files": found, "agree": agree, "version": values[0] if agree else None}


def section(text: str, rule_id: str) -> str:
    match = re.search(rf"^#### {re.escape(rule_id)}\b.*$", text, re.M)
    if not match:
        return ""
    rest = text[match.end():]
    nxt = re.search(r"^#### ", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    return text[match.start(): match.end()] + body


def forbidden_phrases(body: str) -> list[str]:
    phrases: list[str] = []
    for line in body.splitlines():
        if "FORBIDDEN" not in line:
            continue
        phrases.extend(QUOTED.findall(line))
    return phrases


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in phrase.split()]
    body = r"[\s-]+".join(parts)
    return re.compile(rf"(?i)(?<!\w){body}(?!\w)")


def comment_snippets(text: str) -> list[str]:
    cut = NOT_A_BAN.split(text, maxsplit=1)[0]
    found: list[str] = []
    for match in COMMENT_TICK.finditer(cut):
        snippet = match.group(1).strip()
        if len(snippet) < 8 or len(snippet) > 120:
            continue
        if snippet.startswith("#") or snippet.startswith("/*") or "//" in snippet:
            found.append(snippet)
    return list(dict.fromkeys(found))


def load_rules(src: Path) -> dict:
    core_path = src / "antislop.md"
    if not core_path.is_file():
        return {"ok": False, "reason": "antislop.md missing"}
    core = core_path.read_text(encoding="utf-8", errors="replace")
    defined = RULE_HEAD.findall(core)
    phrases: list[str] = []
    for rule_id in ("R-15", "R-16"):
        phrases.extend(forbidden_phrases(section(core, rule_id)))
    phrases = list(dict.fromkeys(phrases))
    r02 = section(core, "R-02")
    ban_em = EM in r02 or "em dash" in r02.lower()
    checker = src / "scripts" / "check-repo.mjs"
    checker_text = checker.read_text(encoding="utf-8", errors="replace") if checker.is_file() else ""
    ban_en = EN in checker_text
    code_path = src / "skills" / "antislop-code" / "SKILL.md"
    snippets: list[str] = []
    if code_path.is_file():
        snippets = comment_snippets(code_path.read_text(encoding="utf-8", errors="replace"))
    executable = rule_ids_in_programs(src)
    return {
        "ok": True,
        "defined": defined,
        "phrases": phrases,
        "patterns": [(phrase, phrase_pattern(phrase)) for phrase in phrases],
        "snippets": snippets,
        "ban_em": ban_em,
        "ban_en": ban_en,
        "check_repo_reads_argv": "process.argv" in checker_text,
        "executable_rule_ids": executable,
    }


def rule_ids_in_programs(src: Path) -> list[str]:
    found: set[str] = set()
    roots = [src / "scripts", src / "skills", src / "cli"]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".mjs", ".js"}:
                continue
            if path.name == "SKILL.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            found.update(re.findall(r"\b(R-\d{2})\b", text))
    return sorted(found)


def file_stat(path: Path) -> dict:
    data = path.read_bytes()
    chars = len(data.decode("utf-8", errors="replace"))
    return {
        "path": str(path),
        "bytes": len(data),
        "chars_div_4": chars // 4,
    }


def context_block(src: Path, repo: Path) -> dict:
    rels = [
        "antislop.md",
        "skills/antislop/SKILL.md",
        "skills/antislop-code/SKILL.md",
        "skills/antislop-copywriting/SKILL.md",
        "skills/antislop-human/SKILL.md",
        "skills/antislop-layoutmobile/SKILL.md",
        "skills/antislop-ui/SKILL.md",
    ]
    files = []
    for rel in rels:
        path = src / rel
        if path.is_file():
            row = file_stat(path)
            row["rel"] = rel
            files.append(row)
    skill_bytes = sum(row["bytes"] for row in files if row["rel"].startswith("skills/"))
    ours = []
    for rel in OURS:
        path = repo / rel
        if path.is_file():
            row = file_stat(path)
            row["rel"] = rel
            ours.append(row)
    ponytail = repo / "bootstrap/grok-cli/skills-external/ponytail"
    ponytail_bytes = 0
    if ponytail.is_dir():
        for path in ponytail.rglob("SKILL.md"):
            ponytail_bytes += path.stat().st_size
    return {
        "files": files,
        "skill_bytes": skill_bytes,
        "skill_chars_div_4": sum(row["chars_div_4"] for row in files if row["rel"].startswith("skills/")),
        "ours": ours,
        "ponytail_pack_bytes": ponytail_bytes,
    }


def iter_text_files(root: Path, product_layout: bool) -> list[Path]:
    if root.is_file():
        return [root]
    roots: list[Path]
    if product_layout:
        roots = []
        for rel in REPO_INCLUDE:
            path = root / rel
            if path.exists():
                roots.append(path)
    else:
        roots = [root]
    found: list[Path] = []
    seen: set[Path] = set()
    for start in roots:
        if start.is_file():
            candidates = [start]
        else:
            candidates = []
            for dirpath, dirnames, filenames in os.walk(start):
                dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
                for name in sorted(filenames):
                    candidates.append(Path(dirpath) / name)
        for path in candidates:
            if path.suffix.lower() not in TEXT_EXT:
                continue
            try:
                if path.stat().st_size > MAX_FILE:
                    continue
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)
    found.sort(key=lambda item: str(item))
    return found


def score_files(paths: list[Path], rules: dict, root: Path | None = None) -> dict:
    em_dash = 0
    en_dash = 0
    phrase_hits: dict[str, int] = {phrase: 0 for phrase in rules["phrases"]}
    comment_hits: dict[str, int] = {snippet: 0 for snippet in rules["snippets"]}
    files_with_hits = 0
    examples: list[dict] = []
    areas: dict[str, dict[str, int]] = {}
    phrase_files: dict[str, dict[str, int]] = {phrase: {} for phrase in rules["phrases"]}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        shown = display_path(path, root)
        area_name = area_of(path, root)
        area = areas.setdefault(area_name, {
            "files": 0,
            "files_with_hits": 0,
            "em_dash": 0,
            "en_dash": 0,
            "single_word_hits": 0,
            "multi_word_hits": 0,
        })
        area["files"] += 1
        file_hit = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if rules["ban_em"]:
                count = line.count(EM)
                if count:
                    em_dash += count
                    area["em_dash"] += count
                    file_hit = True
                    _example(examples, shown, lineno, "em_dash", "em_dash")
            if rules["ban_en"]:
                count = line.count(EN)
                if count:
                    en_dash += count
                    area["en_dash"] += count
                    file_hit = True
                    _example(examples, shown, lineno, "en_dash", "en_dash")
            for phrase, pattern in rules["patterns"]:
                found = len(pattern.findall(line))
                if not found:
                    continue
                phrase_hits[phrase] += found
                phrase_files[phrase][shown] = phrase_files[phrase].get(shown, 0) + found
                if len(phrase.split()) == 1:
                    area["single_word_hits"] += found
                else:
                    area["multi_word_hits"] += found
                file_hit = True
                _example(examples, shown, lineno, "phrase", phrase)
            for snippet in rules["snippets"]:
                found = line.count(snippet)
                if found:
                    comment_hits[snippet] += found
                    file_hit = True
                    _example(examples, shown, lineno, "comment", snippet)
        if file_hit:
            files_with_hits += 1
            area["files_with_hits"] += 1
    single = {key: value for key, value in phrase_hits.items() if len(key.split()) == 1}
    multi = {key: value for key, value in phrase_hits.items() if len(key.split()) > 1}
    comments_fired = {key: value for key, value in comment_hits.items() if value}
    top_phrases = {}
    for phrase, places in phrase_files.items():
        if not places:
            continue
        ranked = sorted(places.items(), key=lambda item: (-item[1], item[0]))[:5]
        top_phrases[phrase] = [{"path": path, "n": count} for path, count in ranked]
    return {
        "files": len(paths),
        "files_with_hits": files_with_hits,
        "em_dash": em_dash,
        "en_dash": en_dash,
        "phrase_hits": phrase_hits,
        "single_word_hits": sum(single.values()),
        "multi_word_hits": sum(multi.values()),
        "comment_hits": comments_fired,
        "comment_hit_total": sum(comment_hits.values()),
        "areas": areas,
        "phrase_top": top_phrases,
        "examples": examples,
    }


def display_path(path: Path, root: Path | None) -> str:
    if root is None:
        return path.name
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def area_of(path: Path, root: Path | None) -> str:
    if root is None:
        return path.name
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return path.name
    if not parts:
        return "."
    if parts[0] in {"bootstrap", ".grok"} and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0]


def _example(examples: list[dict], shown: str, lineno: int, kind: str, label: str) -> None:
    if len(examples) >= EXAMPLE_LIMIT:
        return
    examples.append({
        "path": shown,
        "line": lineno,
        "kind": kind,
        "label": label,
    })


def product_layout(repo: Path) -> bool:
    return (repo / "AGENTS.md").is_file() and (repo / "docs").is_dir()


def child_env(cache: Path) -> dict[str, str]:
    home = cache / "home"
    tmp = cache / "tmp"
    xdg_config = cache / "xdg-config"
    xdg_cache = cache / "xdg-cache"
    for path in (home, tmp, xdg_config, xdg_cache):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(xdg_config),
        "XDG_CACHE_HOME": str(xdg_cache),
        "TMPDIR": str(tmp),
        "npm_config_cache": str(xdg_cache / "npm"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "LANG": "C.UTF-8",
    }


def run_cmd(argv: list[str], cwd: Path, env: dict[str, str]) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "skipped",
            "ok": False,
            "exit": None,
            "summary": str(exc),
            "seconds": round(time.perf_counter() - started, 4),
        }
    lines = [line.strip() for line in ((proc.stdout or "") + (proc.stderr or "")).splitlines() if line.strip()]
    last = lines[-1] if lines else ""
    return {
        "status": "ok" if proc.returncode == 0 else "fail",
        "ok": proc.returncode == 0,
        "exit": proc.returncode,
        "summary": last[:300],
        "lines": lines[:20],
        "seconds": round(time.perf_counter() - started, 4),
    }


def resolve_node(explicit: str) -> str | None:
    if explicit and explicit != "node":
        path = Path(explicit)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        return None
    found = shutil.which("node")
    return found


def run_upstream(src: Path, node: str | None, env: dict[str, str]) -> dict:
    checker = src / "scripts" / "check-repo.mjs"
    contrast = src / "skills" / "antislop-human" / "contrast-check.py"
    out: dict = {"check_repo": None, "contrast_selftest": None, "contrast_pairs": []}
    if not checker.is_file():
        out["check_repo"] = {"status": "skipped", "ok": False, "exit": None, "summary": "no scripts/check-repo.mjs", "seconds": 0}
    elif not node:
        out["check_repo"] = {"status": "skipped", "ok": False, "exit": None, "summary": "node missing", "seconds": 0}
    else:
        out["check_repo"] = run_cmd([node, "scripts/check-repo.mjs"], src, env)
    if not contrast.is_file():
        out["contrast_selftest"] = {
            "status": "skipped", "ok": False, "exit": None,
            "summary": "no contrast-check.py", "seconds": 0,
        }
    else:
        out["contrast_selftest"] = run_cmd([sys.executable, str(contrast), "--selftest"], src, env)
        for pair in (("#FFFFFF", "#777777"), ("#000000", "#FFFFFF")):
            row = run_cmd([sys.executable, str(contrast), pair[0], pair[1]], src, env)
            row["pair"] = list(pair)
            out["contrast_pairs"].append(row)
    return out


def git_head(src: Path) -> str | None:
    if not (src / ".git").exists():
        return None
    proc = subprocess.run(
        ["git", "-C", str(src), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_CONFIG_NOSYSTEM": "1"},
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def catalog_hits(repo: Path) -> list[dict]:
    stages = repo / "data" / "stages"
    if not stages.is_dir():
        return []
    hits = []
    for path in sorted(stages.glob("*.json")):
        if path.name in {"_registry.json", "anti-slop.json"}:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        blob_parts = [str(payload.get("uses") or "")]
        for key in ("features", "tags", "catalog_tags"):
            value = payload.get(key)
            if isinstance(value, list):
                blob_parts.extend(str(item) for item in value)
            elif isinstance(value, str):
                blob_parts.append(value)
        blob = " ".join(blob_parts).lower()
        matched = [word for word in CATALOG_WORDS if word in blob]
        if not matched:
            continue
        hits.append({
            "file": path.name,
            "name": payload.get("name"),
            "stage": payload.get("integration_stage"),
            "words": matched,
        })
    return hits


def passes_equal(left: dict, right: dict) -> bool:
    keys = (
        "files", "files_with_hits", "em_dash", "en_dash",
        "phrase_hits", "comment_hits", "areas", "phrase_top", "examples",
    )
    return all(left.get(key) == right.get(key) for key in keys)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline anti-slop probe")
    parser.add_argument("--src", type=Path, default=None)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--node", default="node")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    src = (args.src or default_src()).resolve()
    repo = args.repo.resolve()
    versions = read_versions(src)
    rules = load_rules(src)
    result: dict = {
        "src": str(src),
        "commit": git_head(src),
        "versions": versions,
        "sha256": {
            "antislop.md": sha256_file(src / "antislop.md"),
            "skills/antislop/VERSION": sha256_file(src / "skills" / "antislop" / "VERSION"),
            "contrast-check.py": sha256_file(src / "skills" / "antislop-human" / "contrast-check.py"),
        },
    }
    if not rules.get("ok"):
        result["error"] = rules.get("reason")
        result["seconds"] = round(time.perf_counter() - started, 4)
        write_result(args.out, result)
        return 2

    fixture_paths = iter_text_files(args.fixtures.resolve(), False) if args.fixtures.exists() else []
    repo_paths = iter_text_files(repo, product_layout(repo))
    fixture_root = args.fixtures.resolve() if args.fixtures.exists() else None
    first_fixtures = score_files(fixture_paths, rules, fixture_root)
    second_fixtures = score_files(fixture_paths, rules, fixture_root)
    first_repo = score_files(repo_paths, rules, repo)
    second_repo = score_files(repo_paths, rules, repo)
    agree = passes_equal(first_fixtures, second_fixtures) and passes_equal(first_repo, second_repo)
    per_file = []
    for path in fixture_paths:
        per_file.append({
            "name": path.name,
            **score_files([path], rules, fixture_root),
        })
    upstream_env = child_env(cache_root())
    node = resolve_node(args.node)
    upstream = run_upstream(src, node, upstream_env)
    result.update({
        "rules": {
            "defined": len(rules["defined"]),
            "ids": rules["defined"],
            "executable_rule_ids": rules["executable_rule_ids"],
            "executable_count": len(rules["executable_rule_ids"]),
            "phrases": rules["phrases"],
            "comment_snippets": len(rules["snippets"]),
            "ban_em": rules["ban_em"],
            "ban_en": rules["ban_en"],
            "check_repo_reads_argv": rules["check_repo_reads_argv"],
        },
        "context": context_block(src, repo),
        "lexical": {
            "passes_agree": agree,
            "fixtures": first_fixtures,
            "fixture_files": per_file,
            "repo": first_repo,
        },
        "upstream": upstream,
        "catalog_keyword_hits": catalog_hits(repo),
        "seconds": round(time.perf_counter() - started, 4),
    })
    write_result(args.out, result)
    if not versions["agree"]:
        return 2
    if not agree:
        return 3
    check = upstream["check_repo"]
    contrast = upstream["contrast_selftest"]
    if check and check["status"] == "fail":
        return 1
    if contrast and contrast["status"] == "fail":
        return 1
    return 0


def write_result(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
