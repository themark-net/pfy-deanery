#!/usr/bin/env python3
"""Stand-in for grok inside the lane cage. Probes what the cage allows.

Prints one JSON line: whether ~/.ssh and the real ~/.grok are readable, whether
a direct connection leaves the container, and what the egress proxy answers
for a non-xAI host and for api.x.ai. Also records the grok argv it was given.
"""
import json
import os
import socket
import sys

# The host home path comes from a file the test writes into the worktree
# (cwd in the cage). The cage's own HOME is a throwaway, so it cannot be used.
host_home = os.environ.get("PROBE_HOST_HOME") or open(".probe_host_home").read().strip()
out = {"argv": sys.argv[1:]}
out["ssh_visible"] = os.path.exists(os.path.join(host_home, ".ssh"))
out["real_grok_visible"] = os.path.exists(os.path.join(host_home, ".grok", "config.toml"))
out["grok_home"] = os.environ.get("GROK_HOME", "")
out["memory_off"] = "enabled = false" in open(os.path.join(out["grok_home"], "config.toml")).read() if out["grok_home"] else False
try:
    s = socket.create_connection(("140.82.112.3", 22), timeout=3)  # github.com ssh
    s.close()
    out["direct_egress"] = True
except OSError:
    out["direct_egress"] = False


def via_proxy(host):
    try:
        s = socket.create_connection(("127.0.0.1", int(os.environ.get("PFY_CAGE_PROXY_PORT", "3128"))), timeout=5)
        s.sendall(f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode())
        line = s.recv(200).split(b"\r\n", 1)[0].decode()
        s.close()
        return line
    except OSError as exc:
        return f"error {exc}"


out["proxy_github"] = via_proxy("github.com")
out["proxy_example"] = via_proxy("example.com")
out["proxy_xai"] = via_proxy(os.environ.get("PROBE_XAI_HOST", "api.x.ai"))
try:
    open(os.path.join(os.getcwd(), ".cage-write-probe"), "w").write("x")
    os.remove(os.path.join(os.getcwd(), ".cage-write-probe"))
    out["wt_writable"] = True
except OSError:
    out["wt_writable"] = False
print("CAGE_PROBE " + json.dumps(out))
