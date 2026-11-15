"""Local Grok session spend and a weekly-cap projection.

Reads ``usage.json`` and ``updates.jsonl`` only. Does not read ``auth.json``
or ``config.toml``, does not write the session directory, and does not use
the network.

Done sessions contribute ``session.costUsdTicks / 1e10`` USD. An open session
has no ``usage.json`` yet: the newest useful ``usage`` object in
``updates.jsonl`` contributes the same ticks when they are present, otherwise
``totalTokens / 1e6 * 0.062`` USD. One point on the weekly Build meter is
``4.40`` USD unless the operator passes another rate. Projected percent is
the baseline reading plus points spent at or after ``--baseline-time``.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

USD_PER_MILLION_TOKENS = Decimal("0.062")
DEFAULT_USD_PER_POINT = Decimal("4.40")
DEFAULT_THRESHOLD = Decimal("75")
TICKS_PER_USD = Decimal("10000000000")
_TIME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<hms>\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<frac>\d+))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2}|[+-]\d{4})?$"
)


def parse_time(value):
    """UTC datetime from an ISO string or a unix timestamp. None if unusable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if abs(seconds) >= 10**12:
            seconds = seconds / 1000.0
        try:
            return datetime.fromtimestamp(seconds, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return parse_time(float(text))
    match = _TIME_RE.match(text)
    if not match:
        return None
    frac = (match.group("frac") or "0")[:6].ljust(6, "0")
    tz = match.group("tz") or "Z"
    if tz == "Z":
        tz_norm = "+00:00"
    elif len(tz) == 5 and tz[3] != ":":
        tz_norm = tz[:3] + ":" + tz[3:]
    else:
        tz_norm = tz
    try:
        parsed = datetime.fromisoformat(
            f"{match.group('date')}T{match.group('hms')}.{frac}{tz_norm}"
        )
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_decimal(text, label):
    try:
        value = Decimal(str(text).strip())
    except InvalidOperation as exc:
        raise ValueError("bad %s: %s" % (label, text)) from exc
    if not value.is_finite():
        raise ValueError("bad %s: %s" % (label, text))
    return value


def _parse_count(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value < 0 or value != int(value):
            return None
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return _parse_count(int(stripped, 10))
        except ValueError:
            return None
    return None


def _token_count(usage):
    total = _parse_count(usage.get("totalTokens"))
    if total is not None:
        return total
    incoming = _parse_count(usage.get("inputTokens"))
    outgoing = _parse_count(usage.get("outputTokens"))
    if incoming is None and outgoing is None:
        return None
    return (incoming or 0) + (outgoing or 0)


def _ticks_to_usd(ticks):
    return Decimal(ticks) / TICKS_PER_USD


def _tokens_to_usd(tokens):
    return Decimal(tokens) / Decimal(1_000_000) * USD_PER_MILLION_TOKENS


def _money(value):
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _number(value):
    if value is None:
        return None
    quantized = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return float(quantized)


def _iso(value):
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_mtime(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError:
        return None


def lane_and_cwd(encoded):
    """Worktree name from a percent-encoded session cwd directory."""
    cwd = urllib.parse.unquote(encoded)
    marker = "DEVELOP%2F"
    if marker in encoded:
        piece = encoded.split(marker)[-1].split("%2F")[0]
        lane = urllib.parse.unquote(piece)
        if lane:
            return lane, cwd
    name = Path(cwd).name
    return (name or encoded), cwd


def _glob_match(pattern, encoded, cwd, lane):
    if pattern is None or pattern == "" or pattern == "*":
        return True
    return any(fnmatch.fnmatchcase(text, pattern) for text in (encoded, cwd, lane))


def _contained_dir(root, path):
    try:
        if path.is_symlink():
            real = path.resolve()
        elif not path.is_dir():
            return None
        else:
            real = path.resolve()
        real.relative_to(root)
    except (OSError, ValueError):
        return None
    if not real.is_dir():
        return None
    return real


def _contained_file(root, folder, name):
    """Return the file only when it resolves inside this session directory."""
    candidate = folder / name
    try:
        if not candidate.exists() and not candidate.is_symlink():
            return None
        real = candidate.resolve()
        real.relative_to(root)
    except (OSError, ValueError):
        return None
    if not real.is_file() or real.name != name:
        return None
    try:
        if real.parent.resolve() != folder.resolve():
            return None
    except OSError:
        return None
    return real


def _load_json(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, "malformed usage.json"
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, "malformed usage.json"


def _usage_from_document(data):
    if not isinstance(data, dict):
        return None
    session = data.get("session")
    if not isinstance(session, dict):
        return None
    ticks = _parse_count(session.get("costUsdTicks"))
    tokens = _token_count(session)
    when = parse_time(data.get("updatedAt"))
    if when is None:
        when = parse_time(session.get("updatedAt"))
    if ticks is None and tokens is None:
        return None
    if ticks is not None:
        return {
            "status": "done",
            "usd": _ticks_to_usd(ticks),
            "tokens": tokens,
            "estimated": False,
            "source": "usage.json",
            "time": when,
        }
    return {
        "status": "live-est",
        "usd": _tokens_to_usd(tokens),
        "tokens": tokens,
        "estimated": True,
        "source": "usage.json",
        "time": when,
    }


def _iter_update_usage(obj):
    if not isinstance(obj, dict):
        return
    params = obj.get("params")
    if isinstance(params, dict):
        update = params.get("update")
        if isinstance(update, dict) and isinstance(update.get("usage"), dict):
            yield update["usage"], obj.get("timestamp")
    if isinstance(obj.get("usage"), dict):
        yield obj["usage"], obj.get("timestamp")


def _usage_from_updates(path):
    best = None
    best_key = None
    try:
        handle = path.open("rb")
    except OSError:
        return None
    with handle:
        for raw in handle:
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeError:
                continue
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for usage, stamp in _iter_update_usage(obj):
                ticks = _parse_count(usage.get("costUsdTicks"))
                tokens = _token_count(usage)
                if ticks is None and tokens is None:
                    continue
                when = parse_time(stamp)
                key = (
                    0 if ticks is None else 1,
                    -1 if ticks is None else ticks,
                    -1 if tokens is None else tokens,
                    0 if when is None else when.timestamp(),
                )
                if best_key is not None and key <= best_key:
                    continue
                best_key = key
                if ticks is not None:
                    best = {
                        "status": "live",
                        "usd": _ticks_to_usd(ticks),
                        "tokens": tokens,
                        "estimated": False,
                        "source": "updates.jsonl",
                        "time": when,
                    }
                else:
                    best = {
                        "status": "live-est",
                        "usd": _tokens_to_usd(tokens),
                        "tokens": tokens,
                        "estimated": True,
                        "source": "updates.jsonl",
                        "time": when,
                    }
    return best


def _read_session(root, folder, lane, cwd):
    sid = folder.name
    problem = None
    record = None
    usage_path = folder / "usage.json"
    saw_usage = usage_path.exists() or usage_path.is_symlink()
    if saw_usage:
        real_usage = _contained_file(root, folder, "usage.json")
        if real_usage is None:
            problem = "malformed usage.json"
        else:
            data, error = _load_json(real_usage)
            if error or data is None:
                problem = "malformed usage.json"
            else:
                record = _usage_from_document(data)
                if record is None:
                    problem = "malformed usage.json"
                elif record["time"] is None:
                    record["time"] = _file_mtime(real_usage)
    if record is None:
        real_updates = _contained_file(root, folder, "updates.jsonl")
        if real_updates is not None:
            record = _usage_from_updates(real_updates)
            if record is not None and record["time"] is None:
                record["time"] = _file_mtime(real_updates)
            if record is not None and problem:
                problem = "malformed usage.json for %s; used updates.jsonl" % sid
        if record is None and problem:
            problem = "malformed usage.json for %s" % sid
    if record is None:
        record = {
            "status": "malformed" if problem else "missing",
            "usd": Decimal(0),
            "tokens": None,
            "estimated": False,
            "source": "none",
            "time": _file_mtime(folder),
        }
    record.update({"id": sid, "lane": lane, "cwd": cwd, "problem": problem})
    return record


def scan_sessions(root, pattern=None):
    """Return (sessions, problems) for worktrees under a sessions root.

    ``problems`` includes directories that resolve outside ``root``. Those
    directories are not opened.
    """
    rows = []
    problems = []
    try:
        children = list(root.iterdir())
    except OSError as exc:
        raise ValueError("sessions dir not readable: %s" % root) from exc
    for encoded in sorted(children, key=lambda item: item.name):
        if encoded.name.startswith("."):
            continue
        if not encoded.is_dir() and not encoded.is_symlink():
            continue
        lane, cwd = lane_and_cwd(encoded.name)
        if not _glob_match(pattern, encoded.name, cwd, lane):
            continue
        real = _contained_dir(root, encoded)
        if real is None:
            problems.append("skipped %s: resolves outside the sessions root" % encoded.name)
            continue
        try:
            sessions = list(real.iterdir())
        except OSError:
            problems.append("skipped %s: session directory is not readable" % encoded.name)
            continue
        for folder in sorted(sessions, key=lambda item: item.name):
            if folder.is_symlink():
                inner = _contained_dir(root, folder)
                if inner is None:
                    problems.append(
                        "skipped %s/%s: resolves outside the sessions root" % (encoded.name, folder.name)
                    )
                    continue
                folder = inner
            elif not folder.is_dir():
                continue
            else:
                try:
                    folder.resolve().relative_to(root)
                except (OSError, ValueError):
                    problems.append(
                        "skipped %s/%s: resolves outside the sessions root" % (encoded.name, folder.name)
                    )
                    continue
            rows.append(_read_session(root, folder, lane, cwd))
    return rows, problems


def _pick_number(flag, env_name, default, label, *, positive=False, nonnegative=False):
    if flag is not None:
        raw = flag
    else:
        raw = os.environ.get(env_name, "").strip()
        if not raw:
            value = default
            raw = None
        else:
            value = None
    if raw is not None:
        value = _parse_decimal(raw, label)
    if positive and value <= 0:
        raise ValueError("%s must be positive" % label)
    if nonnegative and value < 0:
        raise ValueError("%s must be zero or positive" % label)
    return value


def _require_time(text):
    parsed = parse_time(text)
    if parsed is None:
        raise ValueError("bad time: %s" % text)
    return parsed


def build_report(rows, problems, *, root, pattern, since, baseline_percent, baseline_time, usd_per_point, threshold):
    kept = []
    excluded = 0
    extra_problems = list(problems)
    for row in rows:
        if since is not None and (row["time"] is None or row["time"] < since):
            excluded += 1
            if row["time"] is None:
                extra_problems.append("no timestamp for %s; excluded by --since" % row["id"])
            continue
        kept.append(row)

    applied = baseline_percent is not None and baseline_time is not None
    delta = Decimal(0)
    for row in kept:
        if not applied:
            row["in_baseline_delta"] = False
        elif row["time"] is None or row["time"] >= baseline_time:
            row["in_baseline_delta"] = True
            delta += row["usd"]
            if row["time"] is None:
                extra_problems.append("no timestamp for %s; counted in the projection" % row["id"])
        else:
            row["in_baseline_delta"] = False
        if row.get("problem"):
            extra_problems.append(row["problem"])

    done = Decimal(0)
    live = Decimal(0)
    lanes = {}
    for row in kept:
        slot = lanes.setdefault(
            row["lane"],
            {"lane": row["lane"], "cwd": row["cwd"], "done": Decimal(0), "live": Decimal(0)},
        )
        if row["status"] == "done":
            slot["done"] += row["usd"]
            done += row["usd"]
        elif row["status"] in ("live", "live-est"):
            slot["live"] += row["usd"]
            live += row["usd"]

    if applied:
        projected = baseline_percent + (delta / usd_per_point)
        shown = projected.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        limit = threshold.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        stop = shown >= limit
        if stop:
            message = "STOP projected %s%% is at or above threshold %s%%" % (_money(shown), _money(limit))
        else:
            message = "under threshold %s%% (projected %s%%)" % (_money(limit), _money(shown))
        added = delta / usd_per_point
    else:
        projected = None
        stop = False
        message = "no baseline; threshold not applied"
        added = None

    if not kept and excluded == 0:
        message = "no sessions; " + message

    session_rows = []
    for row in sorted(kept, key=lambda item: (item["lane"], item["id"])):
        session_rows.append(
            {
                "cwd": row["cwd"],
                "estimated": bool(row["estimated"]),
                "id": row["id"],
                "in_baseline_delta": bool(row["in_baseline_delta"]),
                "lane": row["lane"],
                "source": row["source"],
                "status": row["status"],
                "time": _iso(row["time"]),
                "tokens": row["tokens"],
                "usd": _number(row["usd"]),
            }
        )
    lane_rows = []
    for lane in sorted(lanes):
        slot = lanes[lane]
        lane_rows.append(
            {
                "cwd": slot["cwd"],
                "done_usd": _number(slot["done"]),
                "lane": slot["lane"],
                "live_usd": _number(slot["live"]),
                "total_usd": _number(slot["done"] + slot["live"]),
            }
        )
    # Problems are phrased for operators. Session ids are directory names.
    unique = []
    seen = set()
    for item in extra_problems:
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return {
        "added_points": _number(added) if added is not None else None,
        "baseline_percent": _number(baseline_percent) if applied else None,
        "baseline_time": _iso(baseline_time) if applied else None,
        "excluded_by_since": excluded,
        "glob": pattern,
        "lanes": lane_rows,
        "message": message,
        "ok": True,
        "problems": unique,
        "projected_percent": _number(projected) if projected is not None else None,
        "sessions": session_rows,
        "sessions_root": str(root),
        "since": _iso(since) if since is not None else None,
        "since_baseline_usd": _number(delta) if applied else None,
        "stop": stop,
        "threshold": _number(threshold),
        "threshold_applied": applied,
        "total_done_usd": _number(done),
        "total_live_usd": _number(live),
        "total_usd": _number(done + live),
        "usd_per_million_tokens": _number(USD_PER_MILLION_TOKENS),
        "usd_per_point": _number(usd_per_point),
    }


def format_text(report):
    lines = []
    for lane in report["lanes"]:
        done = Decimal(str(lane["done_usd"]))
        live = Decimal(str(lane["live_usd"]))
        lines.append("%-34s done $%6s  live~$%6s" % (lane["lane"], _money(done), _money(live)))
    done = Decimal(str(report["total_done_usd"]))
    live = Decimal(str(report["total_live_usd"]))
    lines.append("TOTAL done $%s + live~$%s = ~$%s" % (_money(done), _money(live), _money(done + live)))
    for problem in report["problems"]:
        lines.append("problem: %s" % problem)
    if report["threshold_applied"]:
        lines.append(
            "baseline %s%% at %s" % (_money(Decimal(str(report["baseline_percent"]))), report["baseline_time"])
        )
        lines.append(
            "since baseline $%s = %s points"
            % (_money(Decimal(str(report["since_baseline_usd"]))), _money(Decimal(str(report["added_points"]))))
        )
        lines.append("usd/point %s" % _money(Decimal(str(report["usd_per_point"]))))
    lines.append(report["message"])
    return "\n".join(lines) + "\n"


def report_from_args(args):
    usd_per_point = _pick_number(
        args.usd_per_point,
        "PFY_LANE_USD_PER_POINT",
        DEFAULT_USD_PER_POINT,
        "usd-per-point",
        positive=True,
    )
    threshold = _pick_number(
        args.threshold,
        "PFY_LANE_SPEND_THRESHOLD",
        DEFAULT_THRESHOLD,
        "threshold",
        nonnegative=True,
    )
    percent_raw = None if args.baseline_percent is None else str(args.baseline_percent).strip()
    time_raw = None if args.baseline_time is None else str(args.baseline_time).strip()
    if percent_raw == "":
        percent_raw = None
    if time_raw == "":
        time_raw = None
    if (percent_raw is None) != (time_raw is None):
        raise ValueError("baseline-percent and baseline-time are both required")
    baseline_percent = None
    baseline_time = None
    if percent_raw is not None:
        if percent_raw.endswith("%"):
            percent_raw = percent_raw[:-1].strip()
        baseline_percent = _parse_decimal(percent_raw, "baseline-percent")
        baseline_time = _require_time(time_raw)
    since = None
    if args.since is not None and str(args.since).strip() != "":
        since = _require_time(str(args.since).strip())
    if args.sessions:
        root = Path(args.sessions)
        if not root.is_dir():
            raise ValueError("sessions dir not found: %s" % root)
    else:
        grok_home = os.environ.get("GROK_HOME", "").strip()
        if grok_home:
            root = Path(grok_home) / "sessions"
        else:
            root = Path.home() / ".grok" / "sessions"
        if not root.is_dir():
            report = build_report(
                [],
                [],
                root=root,
                pattern=args.glob,
                since=since,
                baseline_percent=baseline_percent,
                baseline_time=baseline_time,
                usd_per_point=usd_per_point,
                threshold=threshold,
            )
            return report
    root = root.resolve()
    rows, problems = scan_sessions(root, args.glob)
    return build_report(
        rows,
        problems,
        root=root,
        pattern=args.glob,
        since=since,
        baseline_percent=baseline_percent,
        baseline_time=baseline_time,
        usd_per_point=usd_per_point,
        threshold=threshold,
    )


def emit(report, as_json):
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        sys.stdout.write(format_text(report))
    if report["stop"]:
        print(report["message"], file=sys.stderr)


def cmd_spend(args):
    try:
        report = report_from_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    emit(report, bool(args.json))
    return 1 if report["stop"] else 0


def register(verbs):
    lanes = verbs.add_parser("lanes", help="local Grok session spend")
    sub = lanes.add_subparsers(dest="lanes_cmd", required=True)
    spend = sub.add_parser(
        "spend",
        help="sum session USD and project the weekly Build cap",
        description=(
            "Read usage.json and updates.jsonl under a Grok sessions directory. "
            "Does not read auth.json or config.toml. Does not use the network. "
            "Exit 1 when the projected weekly percent is at or above the threshold."
        ),
    )
    spend.add_argument("--sessions", default=None, help="sessions root (default: $GROK_HOME/sessions or ~/.grok/sessions)")
    spend.add_argument("--glob", default=None, help="fnmatch against the encoded cwd, decoded cwd, or lane name")
    spend.add_argument("--since", default=None, help="include sessions at or after this ISO time")
    spend.add_argument("--json", action="store_true")
    spend.add_argument("--usd-per-point", default=None, help="USD per weekly-cap point (default 4.40, or PFY_LANE_USD_PER_POINT)")
    spend.add_argument("--baseline-percent", default=None, help="weekly percent already shown at --baseline-time")
    spend.add_argument("--baseline-time", default=None, help="ISO time of the baseline reading")
    spend.add_argument("--threshold", default=None, help="stop at or above this projected percent (default 75)")
    spend.set_defaults(fn=cmd_spend)
    return spend
