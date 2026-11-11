#!/usr/bin/env python3
"""Local-model lane for the Agent Autoloop trial: one Ollama call, last reply on stdout.

The model and host come from LOCAL_MODEL (default qwen2.5-coder:1.5b) and
OLLAMA_URL (default http://127.0.0.1:11434), or OLLAMA_SOCK (a unix socket
that forwards to it, used inside the trial's network namespace). No API key, no cloud model.
"""
import json
import os
import sys
import http.client
import socket
import urllib.request
from pathlib import Path


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.sock_path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.sock_path)

ctx_path = os.environ.get("AGENT_AUTOLOOP_CONTEXT", "")
ctx = json.loads(Path(ctx_path).read_text()) if ctx_path and Path(ctx_path).is_file() else {}
events = ctx.get("events") or []
slug = str((events[0] if events else {}).get("subject") or "unknown")
prompt = ("In one short English sentence, name one cheap smoke test a catalog lane could run "
          "for a developer tool called '%s'. Reply with the sentence only." % slug)
body = json.dumps({"model": os.environ.get("LOCAL_MODEL", "qwen2.5-coder:1.5b"), "prompt": prompt,
                   "stream": False, "options": {"num_predict": 60, "temperature": 0}}).encode()
sock = os.environ.get("OLLAMA_SOCK", "")
try:
    if sock:
        conn = UnixHTTP(sock, 120)
        conn.request("POST", "/api/generate", body=body, headers={"Content-Type": "application/json"})
        out = json.loads(conn.getresponse().read())
    else:
        url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/generate"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            out = json.loads(resp.read())
except Exception as exc:  # temporary failure: autoloop retries a "没跑成" round
    print("没跑成: local model unreachable (%s)" % type(exc).__name__)
    sys.exit(0)
text = " ".join(str(out.get("response", "")).split())[:300] or "(empty reply)"
lane = Path.cwd() / "lanes" / slug
lane.mkdir(parents=True, exist_ok=True)
(lane / "state.json").write_text(json.dumps({"slug": slug, "state": "done", "model": out.get("model"),
                                             "eval_count": out.get("eval_count"), "reply": text}))
print("Lane %s done (local model): %s" % (slug, text))
