#!/usr/bin/env python3
"""Count pinned HarnessRouter backends that accept a caller base URL.

Offline. Reads a source tree (the cache checkout, or a fixture). No docker,
no network, no model. Exit 0 writes JSON. Exit 2 writes nothing.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

LOCAL_TARGETS = frozenset({"openai-api", "tokenrouter"})
WEIGHT_SUFFIXES = frozenset({".gguf", ".safetensors", ".onnx", ".pt", ".pth"})
BIG_BYTES = 20_000_000


def _assigns(path: Path) -> list[tuple[str, ast.AST]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        value = None
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value
        if isinstance(target, ast.Name) and value is not None:
            found.append((target.id, value))
    return found


def _strings(node: ast.AST) -> set[str] | None:
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        out: set[str] = set()
        for elt in node.elts:
            if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
                return None
            out.add(elt.value)
        return out
    if isinstance(node, ast.Dict):
        out = set()
        for key in node.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                return None
            out.add(key.value)
        return out
    return None


def provider_sets(server_py: Path) -> dict[str, set[str]]:
    resolved: dict[str, set[str]] = {}
    for name, value in _assigns(server_py):
        if not name.endswith("_PROVIDERS"):
            continue
        direct = _strings(value)
        if direct is not None:
            resolved[name] = direct
            continue
        if isinstance(value, ast.Name) and value.id in resolved:
            resolved[name] = set(resolved[value.id])
            continue
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "set"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Name)
            and value.args[0].id in resolved
        ):
            resolved[name] = set(resolved[value.args[0].id])
            continue
        raise ValueError(f"unreadable provider set {name}")
    if not resolved:
        raise ValueError("no provider sets")
    return resolved


def custom_wiring(app_py: Path) -> dict[str, str]:
    wiring = None
    for name, value in _assigns(app_py):
        if name == "_INTEGRATION_WIRING":
            wiring = ast.literal_eval(value)
    if not isinstance(wiring, dict) or not wiring:
        raise ValueError("integration wiring missing")
    custom: dict[str, str] = {}
    for key, target in wiring.items():
        if (
            isinstance(key, tuple)
            and len(key) == 2
            and key[0] == "custom"
            and isinstance(key[1], str)
            and isinstance(target, str)
        ):
            custom[key[1]] = target
    if not custom:
        raise ValueError("no custom wiring rows")
    return custom


def default_backends(entrypoint: Path) -> list[str]:
    text = entrypoint.read_text(encoding="utf-8")
    marker = 'export HR_BACKENDS="${HR_BACKENDS:-'
    start = text.find(marker)
    if start < 0:
        raise ValueError("default HR_BACKENDS missing")
    rest = text[start + len(marker):]
    end = rest.find("}")
    if end < 0:
        raise ValueError("default HR_BACKENDS not closed")
    names = [part for part in rest[:end].split(",") if part]
    if not names:
        raise ValueError("default HR_BACKENDS empty")
    return names


def weight_files(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if path.suffix.lower() in WEIGHT_SUFFIXES or size >= BIG_BYTES:
            found.append(str(path.relative_to(root)))
    return sorted(found)


def measure(root: Path) -> dict:
    app_py = root / "gateway" / "app.py"
    server_py = root / "runner" / "server.py"
    entry = root / "docker" / "entrypoint.sh"
    for path in (app_py, server_py, entry):
        if not path.is_file():
            raise ValueError(f"missing {path.name}")
    backends = default_backends(entry)
    custom = custom_wiring(app_py)
    providers = provider_sets(server_py)
    by_target: dict[str, list[str]] = {}
    missing: list[str] = []
    openai_api: list[str] = []
    for name in backends:
        target = custom.get(name)
        if target is None:
            missing.append(name)
        else:
            by_target.setdefault(target, []).append(name)
        key = f"{name.upper()}_PROVIDERS"
        if "openai-api" in providers.get(key, ()):
            openai_api.append(name)
    local = [
        name
        for name in backends
        if custom.get(name) in LOCAL_TARGETS
    ]
    weights = weight_files(root)
    return {
        "default_backend_count": len(backends),
        "default_backends": backends,
        "custom_by_target": {key: by_target[key] for key in sorted(by_target)},
        "custom_missing": missing,
        "local_base_url_backends": local,
        "local_base_url_count": len(local),
        "local_base_url_targets": sorted(LOCAL_TARGETS),
        "openai_api_provider_backends": openai_api,
        "openai_api_provider_count": len(openai_api),
        "provider_set_count": len(providers),
        "weight_files": weights,
        "weight_file_count": len(weights),
        "engines_added": 0 if not weights else len(weights),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Count local base URL wiring in a HarnessRouter tree")
    ap.add_argument("--src", required=True, help="Pinned source root")
    ap.add_argument("--out", required=True, help="JSON path to write on success")
    args = ap.parse_args(argv)
    root = Path(args.src)
    out = Path(args.out)
    try:
        doc = measure(root)
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"probe failed: {exc}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(
        f"local_base_url {doc['local_base_url_count']}/{doc['default_backend_count']}"
        f" weight_files {doc['weight_file_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
