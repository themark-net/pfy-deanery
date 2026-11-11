#!/usr/bin/env python3
"""Refresh data/model-prices.json from the public price pages. GET only.

No auth header and no secrets. Updates in/out (and cached_in or long_context
only when that key is already on the model) and the fetched date, and only
when every listed model for every HTTP source parsed with sane numbers.
Otherwise the file is left untouched. One line names the provider and why.

At most one attempt per 7 days. A failed fetch or parse still stamps the
attempt. Not-due does not fetch and does not rewrite the stamp.
PFY_CATALOG_OFFLINE=1 exits 0 before any fetch or state write.
Always exits 0 except usage (2).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

USER_AGENT = "pfy-model-prices/1"
TIMEOUT_S = 10
INTERVAL_DAYS = 7
MAX_USD = Decimal("1000")
STATE_NAME = "model-prices-refresh.json"

_TAG = re.compile(r"<[^>]+>")
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
_DOLLAR = re.compile(r"\$(\d+(?:\.\d+)?)")


def prices_path(root: Path) -> Path:
    return root / "data" / "model-prices.json"


def state_file(state_dir: Path | None) -> Path:
    if state_dir is not None:
        return Path(state_dir) / STATE_NAME
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from pfylib.model_choice import compare_state_path
    return compare_state_path().with_name(STATE_NAME)


def build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT},
        method="GET",
    )


def http_get(url: str) -> str:
    request = build_request(url)
    if request.get_header("Authorization"):
        raise RuntimeError("price fetch must not send Authorization")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_best(url: str, fetch) -> str:
    """Prefer the docs' markdown twin (<url>.md); both providers serve one and
    the HTML pages render their tables client-side. Fall back to the page."""
    md_url = url.rstrip("/") + ".md"
    try:
        text = fetch(md_url)
    except Exception:
        text = ""
    if text and "| $" in text:
        return text
    return fetch(url)


def _plain(text: str) -> str:
    return html.unescape(_TAG.sub("", text or "")).strip()


def events_from_html(text: str) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    pattern = re.compile(
        r"<h[1-6][^>]*>(.*?)</h[1-6]>|<tr[^>]*>(.*?)</tr>",
        re.I | re.S,
    )
    for match in pattern.finditer(text):
        if match.group(1) is not None:
            events.append(("heading", _plain(match.group(1))))
        else:
            cells = [_plain(cell) for cell in _CELL.findall(match.group(2) or "")]
            if cells:
                events.append(("row", cells))
    return events


def events_from_markdown(text: str) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            events.append(("heading", stripped.lstrip("#").strip()))
            continue
        low = stripped.lower()
        if low in ("standard", "batch", "flex", "priority", "scale"):
            events.append(("heading", stripped))
            continue
        if not stripped.startswith("|"):
            continue
        cells = [_plain(cell) for cell in stripped.strip("|").split("|")]
        joined = "".join(cells).replace("-", "").replace(":", "").replace(" ", "")
        if not joined:
            continue
        events.append(("row", cells))
    return events


def document_events(text: str) -> list[tuple[str, object]]:
    if "<tr" in text.lower() or "<td" in text.lower():
        return events_from_html(text)
    return events_from_markdown(text)


def base_name(cell: str) -> str:
    text = _plain(cell).strip("`")
    return re.split(r"\s*[(\[]", text, maxsplit=1)[0].strip()


def context_kind(cell: str) -> str:
    text = _plain(cell)
    if "<" in text and "200" in text:
        return "short"
    if re.search(r"(>=|≥|>\s*200)", text):
        return "long"
    return "standard"


def dollar_amounts(cells: list[str]) -> list[Decimal]:
    found: list[Decimal] = []
    for cell in cells:
        for match in _DOLLAR.finditer(cell):
            found.append(Decimal(match.group(1)))
    return found


def sane(value: Decimal) -> bool:
    return value > 0 and value <= MAX_USD


def _prices_from_amounts(amounts: list[Decimal], layout: str) -> dict[str, Decimal] | None:
    if len(amounts) < 2 or any(not sane(amount) for amount in amounts[:3]):
        return None
    if len(amounts) == 2:
        return {"in": amounts[0], "out": amounts[1]}
    if layout == "xai":
        return {"in": amounts[0], "cached": amounts[1], "out": amounts[2]}
    return {"in": amounts[0], "out": amounts[1], "cached": amounts[2]}


def parse_table(text: str, layout: str, wanted: set[str]) -> tuple[dict, str | None]:
    """Return (by model, error). error is set when a wanted model is bad."""
    parsed: dict[str, dict] = {}
    problems: dict[str, str] = {}
    section = "all"
    saw_standard = False
    for kind, payload in document_events(text):
        if kind == "heading":
            title = str(payload).lower()
            if "standard" in title:
                section = "standard"
                saw_standard = True
            elif any(word in title for word in ("batch", "flex", "priority", "scale")):
                section = "other"
            continue
        if saw_standard and section != "standard":
            continue
        if section == "other":
            continue
        cells = list(payload) if isinstance(payload, list) else []
        if not cells:
            continue
        name = base_name(str(cells[0]))
        if name.lower() in ("model", "name", ""):
            continue
        if name not in wanted:
            continue
        amounts = dollar_amounts(cells)
        got = _prices_from_amounts(amounts, layout)
        if got is None:
            problems[name] = "bad price"
            continue
        slot = "long" if context_kind(str(cells[0])) == "long" else "standard"
        bucket = parsed.setdefault(name, {})
        if slot not in bucket:
            bucket[slot] = got
    missing = [name for name in sorted(wanted) if name not in parsed and name not in problems]
    if missing:
        return parsed, "model %s not found" % missing[0]
    if problems:
        name = sorted(problems)[0]
        return parsed, "%s for %s" % (problems[name], name)
    return parsed, None


def layout_for(url: str) -> str:
    if "openai.com" in url:
        return "openai"
    return "xai"


def _set_num(container: dict, key: str, value: Decimal) -> bool:
    if key not in container:
        return False
    if Decimal(str(container[key])) == value:
        return False
    container[key] = float(value)
    return True


def apply_parsed(row: dict, parsed: dict, today: str) -> bool:
    changed = False
    standard = parsed.get("standard") or {}
    if standard:
        changed = _set_num(row, "in", standard["in"]) or changed
        changed = _set_num(row, "out", standard["out"]) or changed
        if "cached" in standard:
            changed = _set_num(row, "cached_in", standard["cached"]) or changed
    long_row = parsed.get("long") or {}
    long_ctx = row.get("long_context")
    if long_row and isinstance(long_ctx, dict):
        changed = _set_num(long_ctx, "in", long_row["in"]) or changed
        changed = _set_num(long_ctx, "out", long_row["out"]) or changed
    if row.get("fetched") != today:
        row["fetched"] = today
        changed = True
    return changed


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _due(path: Path, today: date) -> bool:
    if not path.is_file():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        stamp = date.fromisoformat(str(data.get("attempted") or ""))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return True
    return (today - stamp).days >= INTERVAL_DAYS


def _stamp(path: Path, today: date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"attempted": today.isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )


def _provider(rows: list[tuple[str, dict]]) -> str:
    if rows:
        return str(rows[0][1].get("provider") or "provider")
    return "provider"


def refresh(
    *,
    root: Path,
    state_dir: Path | None,
    today: date,
    xai_text: str | None = None,
    openai_text: str | None = None,
    fetch=http_get,
) -> int:
    """Return 0. Prints one line per skipped or failed provider."""
    path = prices_path(root)
    stamp_path = state_file(state_dir)
    if not _due(stamp_path, today):
        print("model-prices: skipped, last attempt %s" % _load(stamp_path).get("attempted"))
        return 0
    if not path.is_file():
        print("model-prices: price file missing")
        _stamp(stamp_path, today)
        return 0
    original = path.read_text(encoding="utf-8")
    data = json.loads(original)
    models = data.get("models") if isinstance(data.get("models"), dict) else {}
    groups: dict[str, list[tuple[str, dict]]] = {}
    for name, row in models.items():
        if not isinstance(row, dict):
            continue
        source = str(row.get("source") or "")
        if not source.startswith("http"):
            continue
        groups.setdefault(source, []).append((name, row))
    failures: list[str] = []
    parsed_groups: list[tuple[str, dict]] = []
    for url, rows in groups.items():
        provider = _provider(rows)
        wanted = {name for name, _row in rows}
        text = None
        if "x.ai" in url and xai_text is not None:
            text = xai_text
        elif "openai.com" in url and openai_text is not None:
            text = openai_text
        if text is None:
            try:
                text = fetch_best(url, fetch)
            except Exception:
                failures.append("%s: fetch failed" % provider)
                continue
        parsed, problem = parse_table(text, layout_for(url), wanted)
        if problem:
            failures.append("%s: %s" % (provider, problem))
            continue
        parsed_groups.append((url, parsed))
    _stamp(stamp_path, today)
    if failures:
        for line in failures:
            print("model-prices: %s" % line)
        return 0
    changed = False
    by_url = dict(parsed_groups)
    for url, rows in groups.items():
        parsed = by_url.get(url) or {}
        for name, row in rows:
            if apply_parsed(row, parsed.get(name) or {}, today.isoformat()):
                changed = True
    if not changed:
        print("model-prices: unchanged")
        return 0
    rendered = json.dumps(data, indent=2) + "\n"
    if rendered != original:
        path.write_text(rendered, encoding="utf-8")
    print("model-prices: updated %s" % path)
    return 0


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("PFY_CATALOG_OFFLINE") == "1":
        return 0
    parser = argparse.ArgumentParser(prog="model_prices_refresh")
    parser.add_argument("--state", default="", help="loop STATE dir for the 7-day stamp")
    parser.add_argument("--root", default="", help="repo root (default: cwd)")
    parser.add_argument("--xai-fixture", default="", help="local xAI page, skips that GET")
    parser.add_argument("--openai-fixture", default="", help="local OpenAI page, skips that GET")
    parser.add_argument("--today", default="", help="YYYY-MM-DD (tests)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2
    root = Path(args.root).expanduser() if args.root else Path.cwd()
    state = Path(args.state).expanduser() if args.state else None
    if args.today:
        today = date.fromisoformat(args.today)
    else:
        today = datetime.now().date()
    xai = Path(args.xai_fixture).read_text(encoding="utf-8") if args.xai_fixture else None
    openai = Path(args.openai_fixture).read_text(encoding="utf-8") if args.openai_fixture else None
    try:
        return refresh(
            root=root,
            state_dir=state,
            today=today,
            xai_text=xai,
            openai_text=openai,
        )
    except Exception as exc:
        print("model-prices: %s" % exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
