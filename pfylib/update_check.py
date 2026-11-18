"""Read-only pfy update --check. Never applies an update and never writes."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .version import product_version

GITHUB_REPO = "themark-net/pfy-deanery"
RELEASES_URL = "https://api.github.com/repos/%s/releases/latest" % GITHUB_REPO
TAGS_URL = "https://api.github.com/repos/%s/tags?per_page=1" % GITHUB_REPO
TIMEOUT = 5.0


class UpdateError(Exception):
    def __init__(self, reason: str, next_step: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.next_step = next_step


def normalize_tag(tag: str | None) -> str | None:
    text = (tag or "").strip()
    if not text:
        return None
    if text[:1] in "vV" and len(text) > 1 and text[1].isdigit():
        return text[1:]
    return text


def _parts(version: str) -> tuple[int, ...]:
    out: list[int] = []
    for piece in (version or "").split("."):
        digits = []
        for ch in piece:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        out.append(int("".join(digits) or "0"))
    return tuple(out)


def is_newer(remote: str, local: str) -> bool:
    r, loc = _parts(remote), _parts(local)
    n = max(len(r), len(loc))
    r = r + (0,) * (n - len(r))
    loc = loc + (0,) * (n - len(loc))
    return r > loc


def load_injected(path: str | os.PathLike) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise UpdateError("injected update source is not an object", next_step="fix PFY_TEST_UPDATE_SOURCE")
    return {"tag": data.get("tag"), "kind": data.get("kind")}


def fetch_github_latest(timeout: float = TIMEOUT) -> dict[str, Any]:
    """One public GitHub API read. No token, no write, no clone."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pfy/%s (+https://github.com/%s)" % (product_version(), GITHUB_REPO),
        "X-GitHub-Api-Version": "2022-11-28",
    }

    def get(url: str) -> tuple[int, Any]:
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return int(getattr(resp, "status", 200)), json.loads(body) if body.strip() else None
        except urllib.error.HTTPError as exc:
            return int(exc.code), None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise UpdateError(
                "GitHub lookup failed (%s)" % exc,
                next_step="retry pfy update --check when the network is available",
            ) from exc

    status, data = get(RELEASES_URL)
    if status == 200 and isinstance(data, dict):
        tag = data.get("tag_name") or data.get("name")
        if tag:
            return {"tag": tag, "kind": "release"}
    if status not in (200, 404):
        raise UpdateError(
            "GitHub release lookup failed (HTTP %s)" % status,
            next_step="retry pfy update --check",
        )
    status, data = get(TAGS_URL)
    if status == 200 and isinstance(data, list) and data and isinstance(data[0], dict):
        tag = data[0].get("name")
        if tag:
            return {"tag": tag, "kind": "tag"}
    if status in (200, 404):
        return {"tag": None, "kind": None}
    raise UpdateError(
        "GitHub tag lookup failed (HTTP %s)" % status,
        next_step="retry pfy update --check",
    )


def check_update(
    root: str | os.PathLike | None = None,
    fetcher: Callable[[], dict[str, Any]] | None = None,
    source_path: str | os.PathLike | None = None,
) -> dict[str, Any]:
    injected = source_path or os.environ.get("PFY_TEST_UPDATE_SOURCE")
    if injected:
        raw = load_injected(injected)
    else:
        raw = (fetcher or fetch_github_latest)()
    local = product_version(root)
    remote = normalize_tag(str(raw.get("tag") or "") or None)
    kind = raw.get("kind") or None
    if remote is None:
        kind = None
    newer = bool(remote and is_newer(remote, local))
    if remote is None:
        next_step = "no tagged release found on %s" % GITHUB_REPO
    elif newer:
        next_step = "a newer tagged release exists; pfy update apply is not in this slice"
    else:
        next_step = "already at the latest tagged release"
    return {
        "ok": True,
        "local": local,
        "remote": remote,
        "remote_kind": kind,
        "newer": newer,
        "wrote": False,
        "auto_update": False,
        "next_step": next_step,
    }
