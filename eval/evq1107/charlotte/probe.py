#!/usr/bin/env python3
"""Measure Charlotte 0.8.0 against one local operator page.

The number is how many of the visible buttons a core-profile summary names,
how many hidden buttons leak into that summary, and how many bytes that
summary is next to the HTML file and a raw accessibility tree.

Chrome and the MCP server are awkward processes. Tests point --node and
--server at stubs. This script does not open a network URL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

EXPECT_VERSION = "0.8.0"
EXPECT_SHA256 = "b6a94defc8ea1d42cf5e89110cf32d77c22cd5fa7fb992db23621e04ec333eec"
EXPECT_SHA1 = "0e91783ac0496ca9ebac60eb2e573189c1af349d"
CORE_TOOLS = [
    "charlotte_click",
    "charlotte_find",
    "charlotte_navigate",
    "charlotte_observe",
    "charlotte_submit",
    "charlotte_tools",
    "charlotte_type",
]
LAUNCH = "Launch session"
# 0.8.0 stays up after stdin hits EOF. Close stdin, wait, then signal the
# process group so a Chrome child does not survive the parent.
EOF_GRACE_S = 2.0
TERM_WAIT_S = 10.0
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
TAURI_PATHS = (
    "gui/operator/src-tauri/target/release/pfy-operator",
    "gui/operator/src-tauri/target/debug/pfy-operator",
)
CHROME_NAMES = {
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
}

AX_JS = r"""
const fs = require("fs");
const puppeteer = require(process.env.PUPPETEER_MODULE);
(async () => {
  const out = process.env.AX_OUT;
  const noSandbox = process.env.CHARLOTTE_NO_SANDBOX === "1";
  const args = ["--disable-gpu", "--disable-dev-shm-usage", "--allow-file-access-from-files"];
  if (noSandbox) args.unshift("--no-sandbox", "--disable-setuid-sandbox");
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH,
    args,
  });
  try {
    const page = await browser.newPage();
    await page.goto(process.env.PAGE_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
    const dom = await page.evaluate(() => {
      function label(el) {
        return (el.innerText || "").replace(/\s+/g, " ").trim();
      }
      function shown(el) {
        const style = getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const box = el.getBoundingClientRect();
        return box.width > 0 && box.height > 0;
      }
      const buttons = Array.from(document.querySelectorAll("button"));
      const visible = [];
      const hidden = [];
      for (const el of buttons) {
        const text = label(el);
        if (!text) continue;
        (shown(el) ? visible : hidden).push(text);
      }
      const html = document.documentElement.outerHTML;
      return {
        visible,
        hidden,
        button_total: buttons.length,
        outer_html_bytes: new TextEncoder().encode(html).length,
      };
    });
    let axFullBytes = null;
    let axNodes = null;
    let axError = null;
    try {
      const client = await page.createCDPSession();
      const tree = await client.send("Accessibility.getFullAXTree");
      axFullBytes = Buffer.byteLength(JSON.stringify(tree));
      axNodes = (tree.nodes || []).length;
    } catch (err) {
      axError = String(err && err.message || err).slice(0, 300);
    }
    fs.writeFileSync(out, JSON.stringify({
      status: axError ? "partial" : "ok",
      ax_error: axError,
      ax_full_bytes: axFullBytes,
      ax_nodes: axNodes,
      outer_html_bytes: dom.outer_html_bytes,
      visible_labels: dom.visible,
      hidden_labels: dom.hidden,
      button_total: dom.button_total,
    }));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  try {
    fs.writeFileSync(process.env.AX_OUT, JSON.stringify({
      status: "failed",
      error: String(err && err.stack || err).slice(0, 500),
    }));
  } catch (writeErr) {
    process.stderr.write(String(writeErr) + "\n");
  }
  process.exit(1);
});
"""


class VisibleButtons(HTMLParser):
    """Buttons a static file shows before JavaScript runs.

    A `.view` without `.on` is `display:none` in gui/operator/frontend.
    Void tags must not keep that region open.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.capture: dict | None = None
        self.visible: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        hidden = self._hidden(attrs)
        if tag == "button":
            self.capture = {"hidden": hidden, "parts": []}
        if tag not in VOID_TAGS:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag: str) -> None:
        if self.capture is not None and tag == "button":
            label = " ".join("".join(self.capture["parts"]).split())
            if label:
                bucket = self.hidden if self.capture["hidden"] else self.visible
                bucket.append(label)
            self.capture = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.capture["parts"].append(data)

    def _hidden(self, attrs) -> bool:
        if self.stack and self.stack[-1][1]:
            return True
        values = {key.lower(): (value or "") for key, value in attrs}
        style = values.get("style", "").replace(" ", "").lower()
        if "display:none" in style:
            return True
        if "hidden" in values:
            return True
        classes = values.get("class", "").split()
        if "view" in classes and "on" not in classes:
            return True
        return False


class SandboxCrash(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        super().__init__(message)
        self.stderr = stderr


class Mcp:
    def __init__(self, argv: list[str], cwd: Path, env: dict[str, str]) -> None:
        self.p = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        self.pgid = os.getpgid(self.p.pid)
        if self.pgid == os.getpgrp():
            self.p.kill()
            raise RuntimeError("server stayed in the probe process group")
        self.err: list[str] = []
        self.q: queue.Queue[str | None] = queue.Queue()
        self.n = 0
        self._err_thread = threading.Thread(target=self._read_err, daemon=True)
        self._out_thread = threading.Thread(target=self._read_out, daemon=True)
        self._err_thread.start()
        self._out_thread.start()

    def _read_err(self) -> None:
        assert self.p.stderr is not None
        try:
            for line in self.p.stderr:
                if len(self.err) > 200:
                    self.err.pop(0)
                self.err.append(line)
        except Exception:
            return

    def _read_out(self) -> None:
        assert self.p.stdout is not None
        try:
            for line in self.p.stdout:
                self.q.put(line)
        except Exception:
            pass
        self.q.put(None)

    def stderr_text(self) -> str:
        self._err_thread.join(timeout=1)
        return "".join(self.err)[-800:]

    def req(self, method: str, params: dict | None = None, timeout: float = 45) -> dict:
        self.n += 1
        ident = self.n
        assert self.p.stdin is not None
        self.p.stdin.write(json.dumps({
            "jsonrpc": "2.0", "id": ident, "method": method, "params": params or {},
        }) + "\n")
        self.p.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            remain = deadline - time.monotonic()
            if remain <= 0:
                raise TimeoutError("mcp read timeout during " + method)
            try:
                line = self.q.get(timeout=remain)
            except queue.Empty as exc:
                raise TimeoutError("mcp read timeout during " + method) from exc
            if line is None:
                raise RuntimeError("server closed stdout: " + self.stderr_text()[-400:])
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == ident:
                return message

    def notify(self, method: str) -> None:
        assert self.p.stdin is not None
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.p.stdin.flush()

    def init(self) -> dict:
        response = self.req("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pfy-charlotte-probe", "version": "0"},
        }, timeout=30)
        self.notify("notifications/initialized")
        return (response.get("result") or {}).get("serverInfo") or {}

    def tools(self) -> tuple[list[str], int]:
        response = self.req("tools/list", timeout=30)
        result = response.get("result") or {}
        names = sorted(
            tool["name"] for tool in result.get("tools", []) if isinstance(tool, dict) and tool.get("name")
        )
        size = len(json.dumps(result).encode())
        return names, size

    def call(self, name: str, args: dict, timeout: float = 45) -> dict:
        started = time.monotonic()
        try:
            response = self.req("tools/call", {"name": name, "arguments": args}, timeout=timeout)
        except Exception:
            err = self.stderr_text()
            blob = err.lower()
            if "sandbox" in blob:
                raise SandboxCrash(name + " failed", err)
            raise
        result = response.get("result") or {}
        text = "".join(
            part.get("text", "") for part in result.get("content", []) if isinstance(part, dict)
        )
        try:
            body = json.loads(text) if text else {}
        except ValueError:
            body = text
        is_error = bool(result.get("isError")) or bool(response.get("error"))
        if is_error:
            err = self.stderr_text()
            if "sandbox" in err.lower():
                raise SandboxCrash(name + " failed", err)
        return {
            "error": response.get("error"),
            "is_error": is_error,
            "body": body,
            "bytes": len(text.encode()),
            "text": text,
            "seconds": round(time.monotonic() - started, 3),
        }

    def _signal(self, sig: int) -> None:
        try:
            os.killpg(self.pgid, sig)
        except ProcessLookupError:
            return

    def stop(self) -> str:
        how = "eof"
        try:
            if self.p.stdin:
                self.p.stdin.close()
        except OSError:
            pass
        try:
            self.p.wait(timeout=EOF_GRACE_S)
        except subprocess.TimeoutExpired:
            how = "term"
            self._signal(signal.SIGTERM)
            try:
                self.p.wait(timeout=TERM_WAIT_S)
            except subprocess.TimeoutExpired:
                how = "kill"
                self._signal(signal.SIGKILL)
                try:
                    self.p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    how = "stuck"
        # The parent can exit on EOF and leave Chrome in the same group.
        self._signal(signal.SIGTERM)
        return how


def parse_buttons(html: str) -> tuple[list[str], list[str]]:
    parser = VisibleButtons()
    parser.feed(html)
    parser.close()
    return parser.visible, parser.hidden


def unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def score_labels(visible: list[str], hidden: list[str], labels: list[str]) -> dict:
    visible_u = unique(visible)
    hidden_u = [item for item in unique(hidden) if item not in visible_u]
    found = [item for item in visible_u if item in labels]
    leaked = [item for item in hidden_u if item in labels]
    extra = [item for item in unique(labels) if item not in visible_u and item not in hidden_u]
    agreement = round(len(found) / len(visible_u), 4) if visible_u else None
    return {
        "visible_expected": sorted(visible_u),
        "visible_expected_count": len(visible_u),
        "visible_found": len(found),
        "agreement": agreement,
        "hidden_leaked": sorted(leaked),
        "hidden_leaked_count": len(leaked),
        "extra_labels": sorted(extra),
    }


def element_rows(body: object) -> list[dict]:
    if not isinstance(body, dict):
        return []
    rows = body.get("interactive")
    if not isinstance(rows, list):
        rows = body.get("elements") if isinstance(body.get("elements"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def element_fields(body: object) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    ids: list[str] = []
    for row in element_rows(body):
        label = " ".join(str(row.get("label") or row.get("name") or "").split())
        if label:
            labels.append(label)
        if row.get("id"):
            ids.append(str(row["id"]))
    return labels, ids


def launch_ids(body: object) -> list[str]:
    found = []
    for row in element_rows(body):
        label = " ".join(str(row.get("label") or row.get("name") or "").split())
        if label == LAUNCH and row.get("id"):
            found.append(str(row["id"]))
    return found


def page_bits(call: dict) -> dict:
    body = call.get("body")
    text = call.get("text") or ""
    labels, ids = element_fields(body)
    title = None
    total = None
    console_count = 0
    network_count = 0
    console_sample: list[str] = []
    full_chars = None
    if isinstance(body, dict):
        title = body.get("title")
        summary = body.get("interactive_summary") or {}
        if isinstance(summary, dict) and "total" in summary:
            total = summary.get("total")
        errors = body.get("errors") or {}
        if isinstance(errors, dict):
            console = errors.get("console") or []
            network = errors.get("network") or []
            console_count = len(console) if isinstance(console, list) else 0
            network_count = len(network) if isinstance(network, list) else 0
            if isinstance(console, list):
                for row in console[:5]:
                    if isinstance(row, dict):
                        console_sample.append(str(row.get("text") or "")[:120])
        structure = body.get("structure") or {}
        if isinstance(structure, dict) and isinstance(structure.get("full_content"), str):
            full_chars = len(structure["full_content"])
    return {
        "bytes": call.get("bytes") or 0,
        "seconds": call.get("seconds"),
        "is_error": bool(call.get("is_error") or call.get("error")),
        "has_ids": ("btn-" in text) or any(item.startswith(("btn-", "inp-", "dom-")) for item in ids),
        "title": title,
        "interactive_total": total,
        "labels": labels[:100],
        "label_count": len(labels),
        "ids": ids[:100],
        "id_count": len(ids),
        "console_count": console_count,
        "network_count": network_count,
        "console_sample": console_sample,
        "full_chars": full_chars,
        "has_launch": LAUNCH in text or LAUNCH in labels,
    }


def find_bits(call: dict) -> dict:
    labels, ids = element_fields(call.get("body"))
    return {
        "bytes": call.get("bytes") or 0,
        "seconds": call.get("seconds"),
        "is_error": bool(call.get("is_error") or call.get("error")),
        "labels": labels[:20],
        "ids": ids[:20],
    }


def click_bits(call: dict) -> dict:
    code = None
    body = call.get("body")
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")
    return {
        "bytes": call.get("bytes") or 0,
        "seconds": call.get("seconds"),
        "is_error": bool(call.get("is_error")) or bool(code),
        "code": code,
    }


def file_sha(path: Path) -> tuple[str, str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), hashlib.sha1(data).hexdigest(), len(data)


def tree_bytes(root: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            total += path.stat().st_size
    return total


def tauri_count(repo: Path) -> int:
    return sum(1 for rel in TAURI_PATHS if (repo / rel).is_file())


def child_env(home: Path, tmp: Path, chrome: Path) -> dict[str, str]:
    # Fresh map on purpose: the parent env can hold keys and a real HOME.
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "XDG_STATE_HOME": str(home / "state"),
        "TMPDIR": str(tmp),
        "PUPPETEER_SKIP_DOWNLOAD": "1",
        "PUPPETEER_CACHE_DIR": str(home / "cache" / "puppeteer"),
        "PUPPETEER_EXECUTABLE_PATH": str(chrome),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def chrome_version(chrome: Path, env: dict[str, str]) -> str | None:
    if chrome.name not in CHROME_NAMES:
        return None
    try:
        done = subprocess.run(
            [str(chrome), "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = (done.stdout or done.stderr or "").strip().splitlines()
    return line[0][:120] if line else None


def write_out(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def profiles_left(tmp: Path) -> list[str]:
    """Puppeteer profiles and other Chrome temp dirs left under TMPDIR."""
    if not tmp.is_dir():
        return []
    names = []
    for path in tmp.iterdir():
        name = path.name
        if name.startswith("puppeteer_dev_chrome_profile") or name.startswith("com.google.Chrome"):
            names.append(name)
    return sorted(names)


def soft_call(mcp: Mcp, name: str, args: dict, timeout: float) -> dict:
    try:
        return mcp.call(name, args, timeout=timeout)
    except SandboxCrash:
        raise
    except Exception as exc:
        return {
            "error": str(exc)[:300],
            "is_error": True,
            "body": None,
            "bytes": 0,
            "text": "",
            "seconds": None,
        }


def run_session(mcp: Mcp, url: str, navigate_timeout: float, call_timeout: float) -> dict:
    tools, tools_bytes = mcp.tools()
    navigate = mcp.call("charlotte_navigate", {
        "url": url,
        "wait_for": "domcontentloaded",
        "timeout": int(navigate_timeout * 1000),
    }, timeout=navigate_timeout)
    if navigate.get("is_error") or navigate.get("error"):
        raise RuntimeError("navigate failed: " + str(navigate.get("error") or navigate.get("text"))[:300])
    summary = mcp.call("charlotte_observe", {"detail": "summary"}, timeout=call_timeout)
    summary_again = mcp.call("charlotte_observe", {"detail": "summary"}, timeout=call_timeout)
    minimal = soft_call(mcp, "charlotte_observe", {"detail": "minimal"}, call_timeout)
    full = soft_call(mcp, "charlotte_observe", {"detail": "full"}, call_timeout)
    tree = soft_call(mcp, "charlotte_observe", {"view": "tree"}, call_timeout)
    tree_labeled = soft_call(mcp, "charlotte_observe", {"view": "tree-labeled"}, call_timeout)
    found = mcp.call("charlotte_find", {"text": LAUNCH}, timeout=call_timeout)
    bad = mcp.call("charlotte_click", {"element_id": "btn-000000"}, timeout=call_timeout)
    found_after = mcp.call("charlotte_find", {"text": LAUNCH}, timeout=call_timeout)
    summary_bits = page_bits(summary)
    again_bits = page_bits(summary_again)
    find_view = find_bits(found)
    after_view = find_bits(found_after)
    wanted = launch_ids(summary.get("body"))
    return {
        "tools": tools,
        "tools_exact_core": tools == sorted(CORE_TOOLS),
        "tools_list_bytes": tools_bytes,
        "calls": {
            "navigate": page_bits(navigate),
            "summary": summary_bits,
            "summary_again": again_bits,
            "minimal": page_bits(minimal),
            "full": page_bits(full),
            "tree": page_bits(tree),
            "tree_labeled": page_bits(tree_labeled),
            "find": find_view,
            "bad_click": click_bits(bad),
            "find_after": after_view,
        },
        "summary_labels": summary_bits["labels"],
        "ids_stable": bool(summary_bits["ids"]) and summary_bits["ids"] == again_bits["ids"],
        "find_matches_summary": bool(wanted) and find_view["ids"] == wanted,
        "server_survived_bad_id": (
            click_bits(bad)["is_error"] and bool(after_view["ids"]) and after_view["ids"] == find_view["ids"]
        ),
    }


def browser_score(ax: dict, labels: list[str]) -> dict:
    if ax.get("status") not in ("ok", "partial"):
        return {}
    visible = [str(item) for item in ax.get("visible_labels") or []]
    hidden = [str(item) for item in ax.get("hidden_labels") or []]
    scored = score_labels(visible, hidden, labels)
    return {
        "browser_visible_count": scored["visible_expected_count"],
        "browser_visible_found": scored["visible_found"],
        "browser_agreement": scored["agreement"],
        "browser_hidden_leaked_count": scored["hidden_leaked_count"],
        "browser_hidden_leaked": scored["hidden_leaked"][:40],
        "browser_extra_labels": scored["extra_labels"][:40],
    }


def run_ax(node: str, module: Path, url: str, out: Path, env: dict[str, str], no_sandbox: bool) -> dict:
    script = out.with_suffix(".ax.js")
    script.write_text(AX_JS, encoding="utf-8")
    child_env_map = dict(env)
    child_env_map["PUPPETEER_MODULE"] = str(module)
    child_env_map["PAGE_URL"] = url
    child_env_map["AX_OUT"] = str(out)
    child_env_map["CHARLOTTE_NO_SANDBOX"] = "1" if no_sandbox else "0"
    started = time.monotonic()
    proc = subprocess.Popen(
        [node, str(script)],
        cwd=str(out.parent),
        env=child_env_map,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        proc.communicate(timeout=5)
        return {"status": "failed", "error": "ax timeout", "seconds": round(time.monotonic() - started, 3)}
    seconds = round(time.monotonic() - started, 3)
    if out.is_file():
        try:
            payload = json.loads(out.read_text(encoding="utf-8"))
        except ValueError:
            payload = {"status": "failed", "error": "ax output was not json"}
    else:
        payload = {"status": "failed", "error": (stderr or stdout or "no ax output")[-400:]}
    if not isinstance(payload, dict):
        payload = {"status": "failed", "error": "ax output was not an object"}
    payload["seconds"] = seconds
    # Drop the label lists from the ax blob after scoring. The caller copies
    # the counts. Keep the lists here so browser_score can read them, then
    # the caller may trim. Labels of one page are small.
    return payload


def launch(node: str, server: Path, cwd: Path, env: dict[str, str], no_sandbox: bool) -> tuple[Mcp, dict]:
    argv = [node, str(server), "--profile", "core"]
    if no_sandbox:
        argv.append("--no-sandbox")
    mcp = Mcp(argv, cwd, env)
    try:
        info = mcp.init()
    except SandboxCrash:
        err = mcp.stderr_text()
        mcp.stop()
        raise SandboxCrash("init failed", err)
    except Exception as exc:
        err = mcp.stderr_text()
        mcp.stop()
        if "sandbox" in (str(exc) + err).lower():
            raise SandboxCrash(str(exc), err)
        raise RuntimeError(str(exc)[:400] + " " + err[-200:])
    return mcp, info


def preflight(args, page: Path, page_dir: Path) -> tuple[str | None, dict]:
    pin: dict = {"expect_version": args.expect_version}
    try:
        page.resolve().relative_to(page_dir.resolve())
    except ValueError:
        return "page is outside the page dir", pin
    if args.tarball:
        tarball = Path(args.tarball)
        if not tarball.is_file():
            return "tarball is not a file", pin
        sha256, sha1, size = file_sha(tarball)
        pin.update({"tarball_bytes": size, "tarball_sha256": sha256, "tarball_sha1": sha1})
        if sha256 != EXPECT_SHA256:
            return "tarball sha256 is %s, not %s" % (sha256, EXPECT_SHA256), pin
        if sha1 != EXPECT_SHA1:
            return "tarball sha1 is %s, not %s" % (sha1, EXPECT_SHA1), pin
    package = Path(args.prefix) / "node_modules" / "@ticktockbent" / "charlotte" / "package.json"
    if not package.is_file():
        return "charlotte package.json is missing", pin
    try:
        meta = json.loads(package.read_text(encoding="utf-8"))
    except ValueError:
        return "charlotte package.json is not json", pin
    got = str(meta.get("version"))
    pin["package_version"] = got
    if meta.get("gitHead"):
        pin["git_head"] = str(meta.get("gitHead"))
    if got != args.expect_version:
        return "package version is %s, not %s" % (got, args.expect_version), pin
    node = Path(args.node)
    server = Path(args.server) if args.server else package.parent / "dist" / "index.js"
    chrome = Path(args.chrome)
    pin["server"] = str(server)
    if not executable(node):
        return "node is not an executable file", pin
    if not server.is_file():
        return "server is not a file", pin
    if not executable(chrome):
        return "chrome is not an executable file", pin
    return None, pin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe Charlotte against one local HTML page")
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--page", required=True)
    parser.add_argument("--page-dir", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--tmp", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--chrome", required=True)
    parser.add_argument("--server", default="")
    parser.add_argument("--tarball", default="")
    parser.add_argument("--expect-version", default=EXPECT_VERSION)
    parser.add_argument("--skip-ax", action="store_true")
    parser.add_argument("--no-sandbox", action="store_true")
    parser.add_argument("--navigate-timeout", type=float, default=90)
    parser.add_argument("--call-timeout", type=float, default=45)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    page = Path(args.page)
    page_dir = Path(args.page_dir)
    home = Path(args.home).resolve()
    tmp = Path(args.tmp).resolve()
    out = Path(args.out)
    for path in (home, home / "config", home / "cache", home / "data", home / "state", tmp):
        path.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "ok": False,
        "tool": "charlotte",
        "expect_version": args.expect_version,
        "tauri_binaries": tauri_count(Path(args.repo)),
    }
    code = 2
    mcp: Mcp | None = None
    try:
        reason, pin = preflight(args, page, page_dir)
        result["pin"] = pin
        if reason:
            result["reason"] = reason
            code = 2
            return code
        html = page.read_text(encoding="utf-8")
        visible, hidden = parse_buttons(html)
        result["page_bytes"] = page.stat().st_size
        site = tmp / "site"
        if site.exists():
            shutil.rmtree(site)
        shutil.copytree(page_dir, site, symlinks=True)
        result["frontend_bytes"] = tree_bytes(site)
        rel = page.resolve().relative_to(page_dir.resolve())
        target = (site / rel).resolve()
        url = target.as_uri()
        result["page_url_in_scratch"] = "/site/" in url
        env = child_env(home, tmp, Path(args.chrome).resolve())
        result["chrome_version"] = chrome_version(Path(args.chrome), env)
        node_version = subprocess.run(
            [args.node, "--version"],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        result["node_version"] = (node_version.stdout or "").strip()[:40]
        server = Path(pin["server"])
        started = time.monotonic()
        sandbox = "off" if args.no_sandbox else "on"
        attempts = 0
        session = None
        info: dict = {}
        last_error = ""
        for attempt in (1, 2):
            no_sandbox = bool(args.no_sandbox) or attempt == 2
            attempts = attempt
            try:
                mcp, info = launch(args.node, server, tmp, env, no_sandbox)
                session = run_session(mcp, url, args.navigate_timeout, args.call_timeout)
                sandbox = "off" if no_sandbox else "on"
                break
            except SandboxCrash as exc:
                last_error = (str(exc) + " " + exc.stderr)[-400:]
                if mcp is not None:
                    mcp.stop()
                    mcp = None
                if attempt == 2 or args.no_sandbox:
                    result["reason"] = "sandbox failed: " + last_error[:300]
                    result["stderr"] = exc.stderr[-400:]
                    code = 1
                    return code
                sandbox = "retry"
                continue
            except Exception as exc:
                last_error = str(exc)[:400]
                if mcp is not None:
                    err = mcp.stderr_text()
                    mcp.stop()
                    mcp = None
                    if "sandbox" in (last_error + err).lower() and attempt == 1 and not args.no_sandbox:
                        last_error = (last_error + " " + err)[-400:]
                        sandbox = "retry"
                        continue
                    result["stderr"] = err[-400:]
                result["error"] = last_error
                code = 1
                return code
        result["sandbox"] = sandbox
        result["sandbox_attempts"] = attempts
        if last_error and sandbox == "off":
            result["sandbox_error"] = last_error[:300]
        result["server_version"] = info.get("version")
        result["seconds"] = round(time.monotonic() - started, 3)
        if not session:
            result["error"] = last_error or "no session"
            code = 1
            return code
        labels = session.pop("summary_labels")
        result.update(session)
        result.update(score_labels(visible, hidden, labels))
        static_agreement = result.get("agreement")
        result["static_agreement"] = static_agreement
        if args.skip_ax:
            result["ax"] = {"status": "skipped", "reason": "not requested"}
        else:
            module = Path(args.prefix) / "node_modules" / "puppeteer"
            if not module.is_dir():
                result["ax"] = {"status": "skipped", "reason": "puppeteer is not installed"}
            else:
                ax_out = tmp / "ax.json"
                ax = run_ax(args.node, module, url, ax_out, env, sandbox == "off")
                result["ax"] = {
                    key: ax.get(key)
                    for key in (
                        "status", "error", "ax_error", "ax_full_bytes", "ax_nodes",
                        "outer_html_bytes", "button_total", "seconds",
                    )
                }
                result.update(browser_score(ax, labels))
        result["ok"] = True
        code = 0
        return code
    finally:
        if mcp is not None:
            result["stopped"] = mcp.stop()
        result["profiles_left"] = profiles_left(tmp)
        result["exit_code"] = code
        write_out(out, result)
        print("ok=%s exit=%s" % (result.get("ok"), code))


if __name__ == "__main__":
    sys.exit(main())
