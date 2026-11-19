#!/usr/bin/env python3
"""Test stand-in for podman. Records argv; for `run`, executes the command on
the host with the container's --env values, so lane tests keep exercising the
real driver without a container runtime. It never adds mounts or network.

FAKE_PODMAN_LOG: append one JSON argv per call.
FAKE_PODMAN_REFUSE=1: `image exists` fails (cage unavailable).
"""
import json
import os
import subprocess
import sys

argv = sys.argv[1:]
log = os.environ.get("FAKE_PODMAN_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(argv) + "\n")
if argv[:2] == ["image", "exists"]:
    sys.exit(1 if os.environ.get("FAKE_PODMAN_REFUSE") == "1" else 0)
if argv[:1] != ["run"]:
    sys.exit(0)
env = dict(os.environ)
workdir = None
i = 1
while i < len(argv) and argv[i].startswith("-"):
    a = argv[i]
    if a.startswith("--env="):
        kv = a[len("--env="):]
        if "=" in kv:
            k, v = kv.split("=", 1)
            env[k] = v
    elif a.startswith("--workdir="):
        workdir = a[len("--workdir="):]
    i += 1
cmd = argv[i + 1:]  # skip the image
env["PFY_CAGE_FAKE"] = "1"
sys.exit(subprocess.run(cmd, env=env, cwd=workdir).returncode)
