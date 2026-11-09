#!/usr/bin/env python3
"""Map a diff to the unittest modules it can affect.

  python3 scripts/test_select.py --base origin/main [--head HEAD]
  python3 scripts/test_select.py --paths docs/ops/PREGATE.md scripts/catalog_check.py
  python3 scripts/test_select.py --structural-checks --selection selection.json

Prints JSON: mode (none|structural|affected|full), reason, modules, changed,
source. source is ast. The import graph is stdlib ast over the repo. A test
is selected when it imports a changed module (transitively) or when its
source contains the changed path or a specific basename. codebase-memory-mcp
is not consulted: a host-only index would make ubuntu and nimo select
different modules for the same tree. Path strings are the git-grep fallback
from scripts/pfy_build_cloud.py change_impact_map.

mode none: nothing changed.
mode structural: only docs and catalog intake data that tests do not reference.
mode affected: the modules list is the tests to run.
mode full: run every tests/test_*.py. Risky, core, unknown, and unparseable
paths always take this mode. A full list is never shortened.
"""
from __future__ import annotations

import ast
import argparse
import fnmatch
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

SCAN_DIRS = ("tests", "scripts", "pfylib", "harness", "examples", "eval", "bootstrap", "gui")
DATA_SUFFIXES = {".json", ".md", ".yml", ".yaml", ".txt", ".csv"}
GENERIC_BASENAMES = {
    "__init__.py",
    "__main__.py",
    "README.md",
    "SKILL.md",
    "Makefile",
    "setup.py",
    "conftest.py",
    # One file per tool. The full path still selects a test that names it.
    # The basename would select every verdict or receipt test in the tree.
    "VERDICT.json",
    "receipt.json",
}
# Same two names. An unreferenced artifact stays structural. It must not
# take mode full just because no test has mentioned this tool yet.
PER_TOOL_ARTIFACTS = {
    "VERDICT.json",
    "receipt.json",
}
STRUCTURAL_SKIP_PREFIXES = ("tests/",)


def script_repo() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(root: Path | None = None) -> dict:
    path = (root or script_repo()) / "config" / "test_select.json"
    if not path.is_file():
        path = script_repo() / "config" / "test_select.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"config/test_select.json unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("config/test_select.json is not an object")
    for key in ("core_globs", "risky_globs", "structural_globs", "comment"):
        if key not in data:
            raise SystemExit(f"config/test_select.json missing {key}")
    if not data["risky_globs"] or not data["core_globs"]:
        raise SystemExit("config/test_select.json risky_globs and core_globs must not be empty")
    try:
        ratio = float(data.get("fan_in_core_ratio", 0.4))
    except (TypeError, ValueError) as exc:
        raise SystemExit("fan_in_core_ratio is not a number") from exc
    data["fan_in_core_ratio"] = ratio
    return data


def glob_match(path: str, pattern: str, *, casefold: bool = False) -> bool:
    if casefold:
        path = path.lower()
        pattern = pattern.lower()
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if pattern.startswith("**/"):
        rest = pattern[3:]
        parts = path.split("/")
        for index in range(len(parts)):
            tail = "/".join(parts[index:])
            if fnmatch.fnmatch(tail, rest) or fnmatch.fnmatch(parts[index], rest):
                return True
        return False
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatch(path, pattern)


def first_glob(path: str, patterns: list[str], *, casefold: bool = False) -> str | None:
    for pattern in patterns:
        if glob_match(path, pattern, casefold=casefold):
            return pattern
    return None


def is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return rel.startswith("tests/") and name.startswith("test_") and rel.endswith(".py") and "/fixtures/" not in rel


def is_shared_helper(rel: str) -> bool:
    if not rel.startswith("tests/") or not rel.endswith(".py"):
        return False
    if "/fixtures/" in rel:
        return False
    name = rel.rsplit("/", 1)[-1]
    return not name.startswith("test_")


def dotted_from_path(rel: str) -> str | None:
    if not rel.endswith(".py"):
        return None
    stem = rel[:-3]
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem.replace("/", ".")


def is_structural_path(rel: str, config: dict) -> bool:
    if rel.startswith(STRUCTURAL_SKIP_PREFIXES):
        return False
    if first_glob(rel, list(config["structural_globs"])) is None:
        return False
    if rel.startswith("data/") or rel.startswith("sources/"):
        return Path(rel).suffix.lower() in DATA_SUFFIXES
    if rel.startswith("docs/") or rel.endswith(".md"):
        return True
    return False


def under_catalog_data(rel: str) -> bool:
    return rel.startswith("data/") or rel.startswith("sources/")


# The assembly test reads every card. It does not embed each filename, so a
# basename search misses it. Selecting this one module keeps a card edit off
# mode full.
STAGE_ASSEMBLY_TEST = "tests/test_stage_registry.py"


def is_stage_card_path(rel: str) -> bool:
    return rel.startswith("data/stages/") and rel.endswith(".json")


class Graph:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: set[str] = set()
        self.unparseable: set[str] = set()
        self.index: dict[str, str] = {}
        self.edges: dict[str, set[str]] = defaultdict(set)
        self.sources: dict[str, str] = {}
        self._scan()

    def _py_paths(self) -> list[Path]:
        paths: list[Path] = []
        for name in SCAN_DIRS:
            base = self.root / name
            if not base.is_dir():
                continue
            for path in base.rglob("*.py"):
                if any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts):
                    continue
                paths.append(path)
        for path in self.root.glob("*.py"):
            paths.append(path)
        return paths

    def _scan(self) -> None:
        # Index every module before resolving imports. A single pass misses
        # edges when the importer is visited before the target file.
        texts: dict[str, str] = {}
        for path in self._py_paths():
            rel = path.relative_to(self.root).as_posix()
            self.files.add(rel)
            mod = dotted_from_path(rel)
            if mod:
                self.index[mod] = rel
            try:
                texts[rel] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self.unparseable.add(rel)
        for rel, text in texts.items():
            if is_test_path(rel):
                self.sources[rel] = text
            self._parse(rel, text)

    def _parse(self, rel: str, text: str) -> None:
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            self.unparseable.add(rel)
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_name(rel, alias.name)
            elif isinstance(node, ast.ImportFrom):
                self._add_from(rel, node)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                name = node.value.strip()
                if "." in name and name in self.index:
                    self._link(rel, self.index[name])

    def _add_name(self, src: str, name: str) -> None:
        target = self._resolve(name)
        if target:
            self._link(src, target)

    def _add_from(self, src: str, node: ast.ImportFrom) -> None:
        if node.level:
            base = self._relative_base(src, node.level, node.module)
        else:
            base = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                if base:
                    self._add_name(src, base)
                continue
            cands = []
            if base:
                cands.append(f"{base}.{alias.name}")
                cands.append(base)
            else:
                cands.append(alias.name)
            linked = False
            for cand in cands:
                target = self._resolve(cand)
                if target:
                    self._link(src, target)
                    linked = True
            if not linked and base:
                self._add_name(src, base)

    def _relative_base(self, src: str, level: int, module: str | None) -> str:
        parts = src.split("/")
        if parts[-1] == "__init__.py":
            pkg = parts[:-1]
        else:
            pkg = parts[:-1]
        keep = len(pkg) - (level - 1)
        if keep < 0:
            return module or ""
        base_parts = pkg[:keep]
        if module:
            base_parts.extend(module.split("."))
        return ".".join(base_parts)

    def _resolve(self, name: str) -> str | None:
        parts = name.split(".")
        while parts:
            cand = ".".join(parts)
            if cand in self.index:
                return self.index[cand]
            parts.pop()
        # Unique stem, for `sys.path` inserts that import a script by filename.
        stems = [rel for rel in self.files if rel.endswith("/" + name + ".py") or rel == name + ".py"]
        if len(stems) == 1:
            return stems[0]
        return None

    def _link(self, src: str, target: str) -> None:
        if not target or target == src:
            return
        self.edges[src].add(target)
        parts = target.split("/")
        if parts[-1] == "__init__.py":
            dirs = parts[:-1]
        else:
            dirs = parts[:-1]
        acc: list[str] = []
        for part in dirs:
            acc.append(part)
            init = "/".join(acc + ["__init__.py"])
            if init in self.files and init != src:
                self.edges[src].add(init)

    def test_rels(self) -> list[str]:
        return sorted(rel for rel in self.files if is_test_path(rel))

    def dependents(self, start: str) -> set[str]:
        reverse: dict[str, set[str]] = defaultdict(set)
        for src, dsts in self.edges.items():
            for dst in dsts:
                reverse[dst].add(src)
        seen = {start}
        stack = [start]
        out: set[str] = set()
        while stack:
            cur = stack.pop()
            for parent in reverse.get(cur, ()):
                if parent in seen:
                    continue
                seen.add(parent)
                out.add(parent)
                stack.append(parent)
        return out

    def test_dependents(self, start: str) -> set[str]:
        return {rel for rel in self.dependents(start) if is_test_path(rel)}


def string_refs(path: str, sources: dict[str, str], extra: list[str] | None = None) -> set[str]:
    base = path.rsplit("/", 1)[-1]
    needles = [path]
    if extra:
        needles.extend(extra)
    if base not in GENERIC_BASENAMES and "." in base and len(base) >= 5:
        needles.append(base)
    hits: set[str] = set()
    for rel, text in sources.items():
        for needle in needles:
            if needle and needle in text:
                hits.add(rel)
                break
    return hits


def to_modules(rels: set[str]) -> list[str]:
    mods = []
    for rel in sorted(rels):
        mod = dotted_from_path(rel)
        if mod and is_test_path(rel):
            mods.append(mod)
    return mods


def parse_diff(raw: bytes) -> list[dict[str, str]]:
    parts = raw.split(b"\0")
    out: list[dict[str, str]] = []
    index = 0
    while index < len(parts):
        if not parts[index]:
            index += 1
            continue
        status = parts[index].decode("utf-8", "surrogateescape")
        index += 1
        if index >= len(parts):
            break
        path = parts[index].decode("utf-8", "surrogateescape")
        index += 1
        code = status[:1]
        if code in {"R", "C"}:
            if index >= len(parts):
                break
            new = parts[index].decode("utf-8", "surrogateescape")
            index += 1
            out.append({"path": path, "status": "D"})
            out.append({"path": new, "status": "A"})
        else:
            out.append({"path": path, "status": code})
    return out


def changed_between(root: Path, base: str, head: str) -> list[dict[str, str]]:
    proc = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", "-z", base, head],
        cwd=root,
        capture_output=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise SystemExit(err or f"git diff {base} {head} failed")
    return parse_diff(proc.stdout or b"")


def known_text_suffix(rel: str) -> bool:
    suffix = Path(rel).suffix.lower()
    if suffix in {".py", ".json", ".md", ".yml", ".yaml", ".txt", ".sh", ".toml", ".ini", ".cfg", ".csv"}:
        return True
    name = rel.rsplit("/", 1)[-1]
    return name in {"Makefile", "pfy", "Dockerfile"} or name.startswith("Dockerfile")


def select(root: Path, changes: list[dict[str, str]], config: dict, graph: Graph | None = None) -> dict:
    graph = graph or Graph(root)
    all_tests = to_modules(set(graph.test_rels()))
    n_tests = len(all_tests) or 1
    ratio = float(config["fan_in_core_ratio"])
    if not changes:
        return {
            "mode": "none",
            "reason": "nothing changed",
            "modules": [],
            "changed": [],
            "source": "ast",
        }
    force: list[str] = []
    selected: set[str] = set()
    structural_only = True
    for change in changes:
        rel = change["path"]
        status = change["status"]
        if not rel or rel.startswith(".git/"):
            continue
        risky = first_glob(rel, list(config["risky_globs"]), casefold=True)
        core = first_glob(rel, list(config["core_globs"]))
        if risky:
            force.append(f"risky glob {risky}: {rel}")
            structural_only = False
            continue
        if core or is_shared_helper(rel):
            label = core or "tests helper"
            force.append(f"core glob {label}: {rel}")
            structural_only = False
            continue
        if status == "U":
            force.append(f"unmerged: {rel}")
            structural_only = False
            continue
        if rel.endswith(".py"):
            structural_only = False
            extra = []
            dotted = dotted_from_path(rel)
            if dotted:
                extra.append(dotted)
            if status == "D":
                refs = string_refs(rel, graph.sources, extra)
                if is_test_path(rel):
                    selected |= refs
                    continue
                if refs:
                    selected |= refs
                else:
                    force.append(f"deleted with no test reference: {rel}")
                continue
            if rel in graph.unparseable:
                force.append(f"unparseable: {rel}")
                continue
            if rel not in graph.files:
                refs = string_refs(rel, graph.sources, extra)
                if refs:
                    selected |= refs
                else:
                    force.append(f"outside import graph: {rel}")
                continue
            if is_test_path(rel):
                selected.add(rel)
                selected |= graph.test_dependents(rel)
                selected |= string_refs(rel, graph.sources, extra)
                continue
            fan_rels = graph.test_dependents(rel)
            fan = len(fan_rels)
            if fan / n_tests > ratio:
                force.append(f"core fan-in: {rel} {fan}/{len(all_tests)}")
                continue
            affected = set(fan_rels) | string_refs(rel, graph.sources, extra)
            if not affected:
                force.append(f"no importing test: {rel}")
                continue
            selected |= affected
            continue
        if is_structural_path(rel, config):
            if under_catalog_data(rel):
                refs = string_refs(rel, graph.sources)
                if is_stage_card_path(rel) and STAGE_ASSEMBLY_TEST in graph.files:
                    refs.add(STAGE_ASSEMBLY_TEST)
                if refs:
                    structural_only = False
                    selected |= refs
            continue
        # A new tool's VERDICT.json or receipt.json is not named by any test
        # yet. Matching the basename would pull in every other tool's tests.
        # Naming this path still selects that test. No name stays structural.
        if rel.rsplit("/", 1)[-1] in PER_TOOL_ARTIFACTS:
            refs = string_refs(rel, graph.sources)
            if refs:
                structural_only = False
                selected |= refs
            continue
        structural_only = False
        refs = string_refs(rel, graph.sources)
        if not known_text_suffix(rel):
            force.append(f"unknown file: {rel}")
            continue
        if refs:
            selected |= refs
            continue
        force.append(f"no test reference: {rel}")
    changed = sorted({item["path"] for item in changes if item.get("path")})
    if force:
        return {
            "mode": "full",
            "reason": "; ".join(sorted(force)),
            "modules": all_tests,
            "changed": changed,
            "source": "ast",
        }
    if selected:
        return {
            "mode": "affected",
            "reason": f"import graph selected {len(selected)} module(s)",
            "modules": to_modules(selected),
            "changed": changed,
            "source": "ast",
        }
    if structural_only:
        return {
            "mode": "structural",
            "reason": "docs or catalog data only",
            "modules": [],
            "changed": changed,
            "source": "ast",
        }
    return {
        "mode": "full",
        "reason": "unsure",
        "modules": all_tests,
        "changed": changed,
        "source": "ast",
    }


def md_link_problems(root: Path, path: Path) -> list[str]:
    import re

    if not path.is_file():
        return [f"{path} missing"]
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        path_part = target.split("#", 1)[0].strip().split()[0]
        if not path_part or path_part.startswith("~/"):
            continue
        resolved = (path.parent / path_part).resolve()
        alt = (root / path_part).resolve()
        if resolved.exists() or alt.exists():
            continue
        try:
            shown = path.relative_to(root).as_posix()
        except ValueError:
            shown = str(path)
        missing.append(f"{shown} -> {path_part}")
    return missing


def run_structural_checks(root: Path, changed: list[str]) -> int:
    rc = 0
    for rel in changed:
        if rel.endswith(".json"):
            path = root / rel
            if not path.is_file():
                print(f"FAIL json missing {rel}")
                rc = 1
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"FAIL json {rel}: {exc}")
                rc = 1
            else:
                print(f"PASS json {rel}")
        if rel.endswith(".md"):
            problems = md_link_problems(root, root / rel)
            if problems:
                print("FAIL md links " + "; ".join(problems[:8]))
                rc = 1
            else:
                print(f"PASS md links {rel}")
    for script in (
        "scripts/catalog_check.py",
        "scripts/smoke_contract_lint.py",
        "scripts/check_no_encoded_payloads.py",
        "scripts/check_public_paths.py",
    ):
        proc = subprocess.run(
            [sys.executable, script],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-6:]
            print(f"FAIL {script}")
            for line in tail:
                print(line)
            rc = 1
        else:
            print(f"PASS {script}")
    proc = subprocess.run(["./pfy", "help"], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FAIL ./pfy help")
        rc = 1
    else:
        print("PASS ./pfy help")
    return rc


def paths_as_changes(paths: list[str], root: Path) -> list[dict[str, str]]:
    out = []
    for rel in paths:
        rel = rel.replace("\\", "/").strip()
        # Strip a literal ./ prefix only. str.lstrip("./") would also eat the
        # leading dot of .github and miss the core glob.
        while rel.startswith("./"):
            rel = rel[2:]
        status = "M" if (root / rel).exists() else "D"
        out.append({"path": rel, "status": status})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--paths", nargs="*", default=None)
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--selection", default=None, help="selection JSON for --structural-checks")
    ap.add_argument("--structural-checks", action="store_true")
    args = ap.parse_args(argv)
    root = (args.root or Path.cwd()).resolve()
    config = load_config(script_repo())
    if args.structural_checks:
        if args.selection:
            data = json.loads(Path(args.selection).read_text(encoding="utf-8"))
            changed = list(data.get("changed") or [])
        elif args.paths is not None:
            changed = list(args.paths)
        elif args.base:
            changed = [item["path"] for item in changed_between(root, args.base, args.head)]
        else:
            raise SystemExit("--structural-checks needs --selection, --paths, or --base")
        return run_structural_checks(root, changed)
    if args.paths is not None:
        changes = paths_as_changes(args.paths, root)
    elif args.base:
        changes = changed_between(root, args.base, args.head)
    else:
        raise SystemExit("pass --base REF or --paths")
    result = select(root, changes, config)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
