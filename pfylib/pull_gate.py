"""Refuse an Ollama model download over 25 GB unless the operator opts in.

Auto-pull of a default tag may proceed only when the size is known and at or
under 25 GB (25 x 10^9 bytes). Explicit ``./pfy models pull`` may pull an
unknown-size tag after a warning. A known over-cap tag needs ``--opt-in-huge``.

Tests inject a size with ``PFY_PULL_SIZE_BYTES`` and a cap with
``PFY_PULL_MAX_BYTES``. They must not touch the registry or ``ollama``. This
module does not start a pull.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Callable, Mapping
from urllib.parse import quote

CAP_BYTES = 25 * 10**9
REGISTRY = "https://registry.ollama.ai/v2"
GetUrl = Callable[[str, Mapping[str, str] | None], bytes]


def cap_bytes(env: Mapping[str, str] | None = None) -> int:
    src = os.environ if env is None else env
    raw = str(src.get("PFY_PULL_MAX_BYTES") or "").strip()
    if raw:
        return int(raw)
    return CAP_BYTES


def format_bytes(n: int) -> str:
    gb = n / 10**9
    if gb >= 10:
        return "%.1f GB" % gb
    if gb >= 1:
        return "%.2f GB" % gb
    mb = n / 10**6
    if mb >= 1:
        return "%.0f MB" % mb
    return "%s bytes" % n


def split_tag(tag: str) -> tuple[str, str]:
    name = (tag or "").strip()
    if not name:
        raise ValueError("missing tag")
    if name.startswith("http://") or name.startswith("https://") or "/" in name and name.count("/") > 1:
        # Reject URLs; allow namespace/name:tag (one slash).
        if "://" in name:
            raise ValueError("tag must be a library name, not a URL")
    if ":" in name:
        repo, ver = name.rsplit(":", 1)
    else:
        repo, ver = name, "latest"
    repo = repo.strip().strip("/")
    if "/" not in repo:
        repo = "library/" + repo
    return repo, ver.strip() or "latest"


def injected_size(env: Mapping[str, str] | None = None) -> int | None:
    src = os.environ if env is None else env
    raw = src.get("PFY_PULL_SIZE_BYTES")
    if raw is None or str(raw).strip() == "":
        return None
    return int(str(raw).strip())


def _default_get(url: str, headers: Mapping[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read()


def registry_size(
    tag: str,
    *,
    get: GetUrl | None = None,
    env: Mapping[str, str] | None = None,
) -> int | None:
    """Sum manifest layer sizes. None if skipped or the registry cannot say."""
    src = os.environ if env is None else env
    if str(src.get("PFY_CATALOG_OFFLINE") or "").strip() in ("1", "true", "yes"):
        return None
    if str(src.get("PFY_PULL_NO_REGISTRY") or "").strip() in ("1", "true", "yes"):
        return None
    # An injected size is the test seam. Never contact the registry then.
    if injected_size(env=src) is not None:
        return None
    repo, ver = split_tag(tag)
    url = "%s/%s/manifests/%s" % (REGISTRY, quote(repo, safe="/"), quote(ver, safe=""))
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    fetch = get or _default_get
    try:
        raw = fetch(url, headers)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None
    total = 0
    found = False
    config = data.get("config") if isinstance(data, dict) else None
    if isinstance(config, dict) and isinstance(config.get("size"), int):
        total += config["size"]
        found = True
    layers = data.get("layers") if isinstance(data, dict) else None
    if isinstance(layers, list):
        for layer in layers:
            if isinstance(layer, dict) and isinstance(layer.get("size"), int):
                total += layer["size"]
                found = True
    if not found:
        return None
    return total


def probe_size(
    tag: str,
    *,
    get: GetUrl | None = None,
    env: Mapping[str, str] | None = None,
) -> int | None:
    src = os.environ if env is None else env
    injected = injected_size(env=src)
    if injected is not None:
        return injected
    return registry_size(tag, get=get, env=src)


def decide(
    tag: str,
    *,
    mode: str,
    opt_in_huge: bool = False,
    get: GetUrl | None = None,
    env: Mapping[str, str] | None = None,
) -> dict:
    """Return a verdict. Never starts a pull.

    decision: allow | refuse-over-cap | refuse-unknown
    """
    name = (tag or "").strip()
    if not name:
        raise ValueError("missing tag")
    kind = (mode or "").strip() or "explicit"
    if kind not in ("auto", "explicit"):
        raise ValueError("mode must be auto or explicit")
    src = os.environ if env is None else env
    cap = cap_bytes(env=src)
    size = probe_size(name, get=get, env=src)
    allowed_env = str(src.get("PFY_PULL_ALLOW_OVER_25GB") or "").strip() in (
        "1",
        "true",
        "yes",
    )
    # Auto-pull is unattended (./pfy start / adapter). Opt-in is only for
    # an explicit operator pull, never for the default-model path.
    if kind == "auto":
        opted = False
    else:
        opted = bool(opt_in_huge) or allowed_env
    payload = {
        "tag": name,
        "mode": kind,
        "bytes": size,
        "cap_bytes": cap,
        "opt_in_huge": opted,
        "decision": "allow",
        "reason": "",
        "size_line": "",
    }
    if size is None:
        payload["size_line"] = "pull size: unknown for %s" % name
        if kind == "auto":
            payload["decision"] = "refuse-unknown"
            payload["reason"] = (
                "size not known; auto-pull only when the download is at or under 25 GB"
            )
        else:
            payload["decision"] = "allow"
            payload["reason"] = (
                "size unknown; proceeding on an explicit pull (cannot verify the 25 GB cap)"
            )
        return payload
    payload["size_line"] = "pull size: %s (%s bytes) for %s" % (
        format_bytes(size),
        size,
        name,
    )
    if size > cap and not opted:
        payload["decision"] = "refuse-over-cap"
        payload["reason"] = (
            "over 25 GB; pass --opt-in-huge to pull anyway"
        )
        return payload
    if size > cap and opted:
        payload["reason"] = "over 25 GB; operator opted in"
        return payload
    payload["reason"] = "under cap"
    return payload


def format_verdict(payload: dict) -> str:
    lines = [payload.get("size_line") or ""]
    cap = payload.get("cap_bytes")
    if isinstance(cap, int):
        lines.append("cap: %s" % format_bytes(cap))
    decision = payload.get("decision")
    reason = payload.get("reason") or ""
    if decision and str(decision).startswith("refuse"):
        lines.append("refusing: %s" % reason)
        lines.append("No model was pulled")
    else:
        lines.append("ok: %s" % reason)
    return "\n".join(line for line in lines if line)


def exit_code(decision: str) -> int:
    if decision == "allow":
        return 0
    if decision == "refuse-over-cap":
        return 2
    if decision == "refuse-unknown":
        return 3
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pfylib.pull_gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check", help="print the verdict; do not pull")
    check.add_argument("--tag", required=True)
    check.add_argument("--mode", choices=("auto", "explicit"), default="explicit")
    check.add_argument("--opt-in-huge", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = decide(args.tag, mode=args.mode, opt_in_huge=bool(args.opt_in_huge))
    except ValueError as exc:
        print("refusing: %s" % exc)
        print("No model was pulled")
        return 1
    print(format_verdict(payload))
    return exit_code(str(payload["decision"]))


if __name__ == "__main__":
    if __package__ in (None, ""):
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
        __package__ = "pfylib"  # noqa: A001
    raise SystemExit(main())
