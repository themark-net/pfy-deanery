#!/usr/bin/env python3
"""Turn a Grok Build log or session dump into one Neatlogs HTTP trace.

    python3 scripts/grok_trace_export.py SOURCE -o TRACE.json

SOURCE may be a plain log, a Grok --output-format json envelope, a
chat_history.jsonl, a directory that holds that file (optional events.jsonl
beside it), or a grok trace --local tar.gz. OTLP JSON and Neatlogs HTTP JSON
already in that shape are redacted and passed through.

Secrets are removed before the file is written. A later success after tool
errors stays status OK, so an error streak can recover. Long tool outputs are
clipped, and a sha256 of the full redacted text keeps two different outputs
from looking the same.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pfylib.redact import redact  # noqa: E402

LIMIT = 400
PROJECT = "pfy-grok"
CHAT_TYPES = {"assistant", "tool_result", "user", "system", "reasoning"}
ROLES = {"assistant", "tool", "user", "system"}

_LEAK = re.compile(
    r"REDACTME|sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
_NARRATIVE_FAIL = re.compile(
    r"(?im)^(error:|couldn't create session|overall=fail\b|\[fail\])"
)


def bound(text: str) -> str:
    """Clip redacted text and keep a hash of the full redacted value."""
    clean = redact(text)
    digest = hashlib.sha256(clean.encode()).hexdigest()
    if len(clean) > LIMIT:
        clean = clean[:LIMIT] + "...[truncated]"
    return clean + "\nsha256:" + digest


def redact_json(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_json(item) for key, item in value.items()}
    return value


def as_input(value) -> str:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return bound(value)
        if isinstance(parsed, (dict, list)):
            value = parsed
        else:
            return bound(value)
    if isinstance(value, (dict, list)):
        dumped = json.dumps(redact_json(value), sort_keys=True, separators=(",", ":"))
        return bound(dumped)
    if value is None:
        return bound("")
    return bound(str(value))


def text_of(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                chunk = item.get("text")
                if not isinstance(chunk, str):
                    chunk = item.get("content") if isinstance(item.get("content"), str) else ""
                if chunk:
                    parts.append(chunk)
        return "\n".join(parts)
    if isinstance(content, dict):
        return text_of(content.get("text") or content.get("content") or "")
    return ""


def iso_at(index: int) -> str:
    moment = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def tool_span(name: str, tool_input, output: str, status: str, error: str | None, index: int) -> dict:
    start = iso_at(index)
    end = iso_at(index + 1)
    span = {
        "name": name or "tool",
        "kind": "TOOL",
        "tool_name": name or "tool",
        "input": as_input(tool_input),
        "output": bound(output),
        "status": "ERROR" if status.upper().startswith("ERR") else "OK",
        "start": start,
        "end": end,
    }
    if span["status"] == "ERROR":
        span["error"] = bound(error or output or "tool error").split("\n", 1)[0][:200]
    return span


def llm_span(text: str, index: int) -> dict:
    start = iso_at(index)
    return {
        "name": "assistant",
        "kind": "LLM",
        "model": "grok",
        "input": "",
        "output": bound(text),
        "status": "OK",
        "start": start,
        "end": iso_at(index + 1),
    }


def trace_doc(name: str, user: str, final: str, children: list, failed: bool, error: str) -> dict:
    doc = {
        "name": name or "grok-run",
        "project": PROJECT,
        "input": bound(user) if user else "",
        "output": bound(final) if final else "",
        "status": "ERROR" if failed else "OK",
        "children": children,
    }
    if failed:
        doc["error"] = bound(error or "error").split("\n", 1)[0][:200]
    return doc


def split_call(rest: str) -> tuple[str | None, dict, str]:
    name = None
    fields: dict[str, str] = {}
    extra: list[str] = []
    for token in rest.split():
        if "=" in token and not token.startswith("="):
            key, value = token.split("=", 1)
            fields[key] = redact(value)
        elif name is None:
            name = token
        else:
            extra.append(redact(token))
    return name, fields, " ".join(extra)


def from_plain(text: str, name: str) -> dict:
    children: list[dict] = []
    index = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("tool_call"):
            rest = line.split(None, 1)[1] if " " in line else ""
            tool, fields, extra = split_call(rest)
            status = fields.pop("status", "OK")
            err = fields.pop("error", None)
            output = fields.pop("output", extra)
            children.append(tool_span(tool or "tool", fields, output, status, err, index))
            index += 2
            continue
        if lower.startswith("tool_result"):
            rest = line.split(None, 1)[1] if " " in line else ""
            tool, fields, extra = split_call(rest)
            status = fields.pop("status", "OK")
            err = fields.pop("error", None)
            output = fields.pop("output", extra)
            target = None
            if tool:
                for pos in range(len(children) - 1, -1, -1):
                    if children[pos].get("name") == tool and children[pos].get("output", "").startswith("\nsha256:"):
                        target = pos
                        break
            if target is None and children:
                target = len(children) - 1
            span = tool_span(tool or (children[target]["name"] if target is not None else "tool"), fields, output, status, err, index)
            if target is None:
                children.append(span)
            else:
                span["name"] = children[target]["name"]
                span["tool_name"] = children[target]["tool_name"]
                if not fields:
                    span["input"] = children[target]["input"]
                children[target] = span
            index += 2
    if children:
        final = ""
        failed = False
        error = ""
    else:
        match = _NARRATIVE_FAIL.search(text)
        failed = match is not None
        error = match.group(0) if match else ""
        final = text
    return trace_doc(name, "", final if not children else "", children, failed, error)


def tool_calls_of(message: dict):
    for call in message.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else {}
        name = call.get("name") or fn.get("name") or "tool"
        args = call.get("arguments")
        if args is None:
            args = fn.get("arguments")
        cid = call.get("id") or call.get("tool_call_id")
        yield cid, str(name), args


def from_messages(messages: list, outcomes: dict[str, str], name: str) -> dict:
    results: dict[str, str] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        kind = message.get("type") or message.get("role")
        if kind in {"tool_result", "tool"}:
            cid = message.get("tool_call_id") or message.get("id")
            if cid:
                results[str(cid)] = text_of(message.get("content"))
    children = []
    user = ""
    final = ""
    index = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        kind = message.get("type") or message.get("role")
        if kind == "user" and not user:
            user = text_of(message.get("content"))
        if kind == "assistant":
            body = text_of(message.get("content"))
            if body.strip():
                children.append(llm_span(body, index))
                final = body
                index += 2
            for cid, tool, args in tool_calls_of(message):
                output = results.get(str(cid), "") if cid else ""
                outcome = outcomes.get(str(cid), "success") if cid else "success"
                status = "ERROR" if outcome == "error" else "OK"
                children.append(tool_span(tool, args if args is not None else {}, output, status, output, index))
                index += 2
    return trace_doc(name, user, final, children, False, "")


def outcomes_of(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("type") == "tool_completed" and row.get("tool_call_id"):
            found[str(row["tool_call_id"])] = str(row.get("outcome") or "")
    return found


def is_chat_row(row: dict) -> bool:
    return row.get("type") in CHAT_TYPES or row.get("role") in ROLES


def from_payload(text: str, name: str):
    stripped = text.strip()
    if not stripped:
        raise ValueError("source is empty")
    if stripped[0] in "{[":
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            data = None
        else:
            return from_json_value(data, name)
        rows = []
        jsonl_ok = True
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                jsonl_ok = False
                break
        if jsonl_ok and rows and all(isinstance(row, dict) and is_chat_row(row) for row in rows):
            return from_messages(rows, {}, name)
        if jsonl_ok and rows and all(isinstance(row, dict) and isinstance(row.get("name"), str) for row in rows):
            return [redact_json(row) for row in rows]
        # A pregate log starts with "[PASS]" or "[FAIL]". That is text, not JSON.
    return from_plain(text, name)


def from_json_value(data, name: str):
    if isinstance(data, dict):
        if isinstance(data.get("resourceSpans") or data.get("resource_spans"), list):
            return redact_json(data)
        if isinstance(data.get("name"), str) and (
            "children" in data or "kind" in data or "output" in data
        ):
            return redact_json(data)
        if "stopReason" in data or "num_turns" in data or "text" in data and "modelUsage" in data:
            messages = data.get("messages")
            if isinstance(messages, list):
                return from_messages(messages, {}, name)
            stop = str(data.get("stopReason") or "")
            failed = stop not in {"", "end_turn"}
            return trace_doc(name, "", str(data.get("text") or ""), [
                llm_span(str(data.get("text") or ""), 0)
            ] if data.get("text") else [], failed, stop if failed else "")
        if is_chat_row(data):
            return from_messages([data], {}, name)
    if isinstance(data, list) and data and all(isinstance(row, dict) and is_chat_row(row) for row in data):
        return from_messages(data, {}, name)
    if isinstance(data, list) and data and all(isinstance(row, dict) and isinstance(row.get("name"), str) for row in data):
        return [redact_json(row) for row in data]
    raise ValueError("json is not OTLP, Neatlogs, or a Grok session")


def from_chat_text(history: str, events: str, name: str) -> dict:
    rows = []
    for line in history.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("chat_history.jsonl has a bad line") from exc
        if isinstance(row, dict):
            rows.append(row)
    if not rows:
        raise ValueError("chat_history.jsonl is empty")
    return from_messages(rows, outcomes_of(events), name)


def from_tar(path: Path) -> dict:
    history = events = None
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            if member.name.endswith("chat_history.jsonl") and history is None:
                history = archive.extractfile(member).read().decode("utf-8", "replace")
            elif member.name.endswith("/events.jsonl") and events is None:
                events = archive.extractfile(member).read().decode("utf-8", "replace")
    if history is None:
        raise ValueError("archive has no chat_history.jsonl")
    return from_chat_text(history, events or "", path.stem)


def convert(src: Path):
    if src.is_dir():
        history = src / "chat_history.jsonl"
        if not history.is_file():
            raise ValueError("directory has no chat_history.jsonl")
        events = src / "events.jsonl"
        event_text = events.read_text(encoding="utf-8", errors="replace") if events.is_file() else ""
        return from_chat_text(history.read_text(encoding="utf-8", errors="replace"), event_text, src.name)
    if src.name.endswith(".tar.gz") or src.name.endswith(".tgz"):
        return from_tar(src)
    raw = src.read_bytes()
    if b"\0" in raw[:4096]:
        raise ValueError("source is binary")
    return from_payload(raw.decode("utf-8", "replace"), src.stem)


def dump(doc) -> str:
    if isinstance(doc, list):
        return "".join(json.dumps(redact_json(item), sort_keys=True) + "\n" for item in doc)
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a Grok log or session as a Neatlogs trace")
    parser.add_argument("src", help="log, json, session directory, or grok trace archive")
    parser.add_argument("-o", "--output", required=True, help="trace file to write")
    args = parser.parse_args(argv)
    src = Path(args.src)
    if not src.exists():
        print("source not found: %s" % src, file=sys.stderr)
        return 2
    try:
        doc = convert(src)
        blob = dump(doc)
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if _LEAK.search(blob):
        print("redaction failed; trace not written", file=sys.stderr)
        return 2
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(blob, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
