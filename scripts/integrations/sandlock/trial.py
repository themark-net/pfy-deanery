#!/usr/bin/env python3
"""Run one security-tool trial under sandlock and write sandbox-trial.json.

  python3 scripts/integrations/sandlock/trial.py --slug SLUG \
      --out eval/integrate/SLUG/sandbox-trial.json [--read DIR]... \
      [--scan-json NAME] [--tool-version TEXT] [--pin SHA] [--did TEXT] -- COMMAND...

The command runs through wrap.py with PFY_SANDLOCK=all and
SANDLOCK_BIN=confine.py, so it is confined: reads on the system dirs, the
command's absolute paths and each --read dir; writes only to the stage dir
under the trial cache (tmp/sandlock-trial/<slug>/stage, exported as
SANDLOCK_STAGE and as {stage} in COMMAND, with TMPDIR={stage}/tmp);
default-deny network; clean env. Repo paths are written as ./...
confine.py writes the profile of that run; it goes into the trial record.

--scan-json NAME reads verdict and findings from {stage}/NAME after the run
(scan_verdict and findings). outcome is ok only when the command exited 0,
started inside sandlock, logged no "sandlock: unsandboxed" line, and a
profile was written. Home paths are written as $HOME. The record is what
data/promotion-rules.json rules S-sandlock-trial-clean and S-profile-readonly
read. Exit code: the command's, or 1 when the trial is not ok.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _label(text: str) -> str:
    """Repo paths become ./..., other home paths $HOME/... (no host path in a public record)."""
    text = text.replace(str(ROOT), ".")
    return text.replace(str(Path.home()), "$HOME")


def _label_profile(profile: dict) -> dict:
    out = dict(profile)
    for key in ("reads", "writes"):
        if isinstance(out.get(key), list):
            out[key] = [_label(str(item)).replace("$HOME/" + ROOT.relative_to(Path.home()).as_posix(), ".")
                        if ROOT.is_relative_to(Path.home()) else _label(str(item)) for item in out[key]]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sandlock trial for a security tool.")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--read", action="append", default=[])
    parser.add_argument("--scan-json", default="")
    parser.add_argument("--tool-version", default="")
    parser.add_argument("--pin", default="")
    parser.add_argument("--did", default="")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("COMMAND is required after --")
    cache = ROOT / "tmp" / "sandlock-trial" / args.slug
    if cache.exists():
        shutil.rmtree(cache)
    stage = cache / "stage"
    stage.mkdir(parents=True)
    (stage / "tmp").mkdir()
    profile_path = cache / "profile.json"
    cmd = [part.replace("{stage}", str(stage)) for part in cmd]
    env = dict(os.environ)
    env.update({
        "PFY_SANDLOCK": "all",
        "SANDLOCK_BIN": str(HERE / "confine.py"),
        "SANDLOCK_STAGE": str(stage),
        "SANDLOCK_PROFILE": str(profile_path),
        "TMPDIR": str(stage / "tmp"),
        "SANDLOCK_EXTRA_READS": ":".join(str(Path(item).expanduser().resolve()) for item in args.read),
    })
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    proc = subprocess.run(
        [sys.executable, str(HERE / "wrap.py"), "--cache", str(cache / "wrap"), "--action", "run", "--", *cmd],
        env=env, capture_output=True, text=True, timeout=600,
    )
    finished = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    unsandboxed = sum(1 for line in proc.stderr.splitlines() if line.strip() == "sandlock: unsandboxed")
    profile = None
    if profile_path.is_file():
        try:
            profile = _label_profile(json.loads(profile_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            profile = None
    record = {
        "slug": args.slug,
        "run_kind": "sandbox-trial",
        "sandbox": "sandlock",
        "wrapper": "scripts/integrations/sandlock/trial.py (wrap.py --action run, PFY_SANDLOCK=all, SANDLOCK_BIN=confine.py)",
        "started": started,
        "finished": finished,
        "command": [_label(part) for part in cmd],
        "exit_code": proc.returncode,
        "unsandboxed_lines": unsandboxed,
        "profile": profile,
    }
    if args.tool_version:
        record["tool_version"] = args.tool_version
    if args.pin:
        record["pin"] = args.pin
    if args.did:
        record["did"] = args.did
    if args.scan_json:
        try:
            scan = json.loads((stage / args.scan_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            scan = {}
        record["scan_verdict"] = str(scan.get("verdict") or "missing")
        findings = scan.get("findings")
        record["findings"] = len(findings) if isinstance(findings, list) else findings if isinstance(findings, int) else None
    ok = proc.returncode == 0 and unsandboxed == 0 and isinstance(profile, dict)
    record["outcome"] = "ok" if ok else "failed"
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{record['outcome']} {args.slug} exit={proc.returncode} unsandboxed={unsandboxed} -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out.name}")
    if not ok:
        sys.stderr.write(proc.stderr[-2000:])
    return proc.returncode if proc.returncode else (0 if ok else 1)


if __name__ == "__main__":
    raise SystemExit(main())
