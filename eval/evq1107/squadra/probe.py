#!/usr/bin/env python3
"""One Squadra defect-fix task on a throwaway git repo.

The product checkout is not the registry project. The fixture is one file
whose test must fail on the registered base and pass on the candidate.
Exit 0 only when each labeled refuse holds and the red/green split holds.
A checkout that lets work start with no ACK, or that treats an always-passing
test as a matched defect, exits 2.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIN_COMMIT = "5081a06ae054bc80072d8109ee2ef088b52513c3"
PIN_TAG = "v3.10.1"
PIN_TAG_OBJECT = "acd9e6d6099903e5fd128eb0906f061a4e72e88e"
PIN_VERSION = "3.10.1"

GREEN_TEST = (
    "import unittest\n"
    "class Bug(unittest.TestCase):\n"
    "    def test_value(self):\n"
    "        self.assertTrue(True)\n"
)
REAL_TEST = (
    "import pathlib, unittest\n"
    "class Bug(unittest.TestCase):\n"
    "    def test_value(self):\n"
    "        self.assertEqual(pathlib.Path('code.py').read_text(), 'VALUE = 2\\n')\n"
)
CONTRACT = {"ids": ["test_bug.Bug.test_value"], "files": ["tests/test_bug.py"]}


def _first_json(text: str) -> dict | None:
    start = text.find("{")
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _child_env(work: Path) -> dict[str, str]:
    env = {}
    for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    env.update(
        {
            "HOME": str(work / "home"),
            "XDG_CONFIG_HOME": str(work / "config"),
            "XDG_CACHE_HOME": str(work / "cache"),
            "TMPDIR": str(work / "tmp"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Probe",
            "GIT_AUTHOR_EMAIL": "probe@example.invalid",
            "GIT_COMMITTER_NAME": "Probe",
            "GIT_COMMITTER_EMAIL": "probe@example.invalid",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def _homes(real_home: Path) -> list[Path]:
    return [
        real_home / ".local" / "state" / "squadra",
        real_home / ".cache" / "squadra",
        real_home / ".squadra",
    ]


class Driver:
    def __init__(self, squadra: Path, work: Path) -> None:
        self.squadra = squadra
        self.work = work
        self.repo = work / "repo"
        self.reg = work / "reg"
        self.ev = work / "ev"
        self.env = _child_env(work)
        self.steps: list[dict] = []

    def git(self, *args: str) -> None:
        run = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode != 0:
            tail = (run.stderr or run.stdout or "").strip()[:200]
            raise RuntimeError("git %s failed: %s" % (" ".join(args), tail))

    def call(self, args: list[str], name: str) -> subprocess.CompletedProcess[str]:
        started = time.perf_counter()
        run = subprocess.run(
            [sys.executable, "-B", str(self.squadra), "--root", str(self.reg), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(self.work),
        )
        err = (run.stderr or "").strip().splitlines()
        self.steps.append(
            {
                "name": name,
                "exit": run.returncode,
                "seconds": round(time.perf_counter() - started, 4),
                "err": (err[0][:240] if err else ""),
            }
        )
        return run

    def prepare_repo(self, proof_argv: list[str]) -> None:
        for folder in (self.work / "home", self.work / "config", self.work / "cache", self.work / "tmp", self.ev):
            folder.mkdir(parents=True, exist_ok=True)
        self.repo.mkdir()
        self.git("init", "-q")
        (self.repo / "code.py").write_text("VALUE = 1\n")
        self.git("add", "code.py")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
        (self.ev / "scope.md").write_text(
            "Stand-in for gap B on this repo. The 3 hour ./pfy build timeout and the two "
            "parked pregate FAILs stay as they are. This task only checks a one-file value defect.\n"
        )
        (self.ev / "proof.json").write_text(json.dumps(proof_argv))
        (self.ev / "report.md").write_text(
            "Independent read of the one-file value change. The build timeout is not this diff.\n"
        )


def _runs(folder: Path) -> list[dict]:
    path = folder / "RESULT.json"
    if not path.is_file():
        return []
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    runs = record.get("runs") if isinstance(record, dict) else None
    if not isinstance(runs, list):
        return []
    out = []
    for item in runs:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "label": item.get("label"),
                "native_rc": item.get("native_rc"),
                "outcome": item.get("outcome"),
            }
        )
    return out


def _pin(squadra: Path) -> dict:
    script_sha = _sha256(squadra) if squadra.is_file() else ""
    checkout = squadra.resolve().parents[1] if len(squadra.resolve().parents) > 1 else squadra.parent
    commit = ""
    git_dir = checkout / ".git"
    if git_dir.exists():
        run = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode == 0:
            commit = run.stdout.strip()
    return {
        "tag": PIN_TAG,
        "tag_object": PIN_TAG_OBJECT,
        "commit": commit,
        "commit_expected": PIN_COMMIT,
        "commit_ok": (not git_dir.exists()) or commit == PIN_COMMIT,
        "script_sha256": script_sha,
        "checkout_has_git": git_dir.exists(),
    }


def _problem(ok: bool, text: str, problems: list[str]) -> None:
    if not ok:
        problems.append(text)


def evaluate(steps: dict[str, dict], green: list[dict], real: list[dict], doctor: dict | None, handoff: str) -> list[str]:
    problems: list[str] = []

    def step(name: str) -> dict:
        return steps.get(name) or {}

    _problem(step("version").get("exit") == 0, "version exit", problems)
    _problem(step("init").get("exit") == 0, "init exit", problems)
    _problem(step("task").get("exit") == 0, "task exit", problems)
    _problem(step("start-before-ack").get("exit") == 1, "start before ack was not refused", problems)
    _problem("ACK" in str(step("start-before-ack").get("err", "")), "start before ack did not name ACK", problems)
    _problem(step("close-before-deliver").get("exit") == 1, "close before deliver was not refused", problems)
    _problem(step("ack-assign").get("exit") == 0, "assignment ack exit", problems)
    _problem(step("register-green").get("exit") == 0, "register always-passing contract exit", problems)
    _problem(step("challenge-green").get("exit") == 1, "always-passing challenge was not refused", problems)
    _problem(
        len(green) == 2 and all(item.get("native_rc") == 0 and item.get("outcome") == "passed" for item in green),
        "always-passing challenge did not pass on both inputs",
        problems,
    )
    _problem(step("register-real").get("exit") == 0, "register real contract exit", problems)
    _problem(step("challenge-real").get("exit") == 0, "real challenge exit", problems)
    original = next((item for item in real if item.get("label") == "original"), {})
    remedy = next((item for item in real if item.get("label") == "remedy"), {})
    _problem(
        original.get("native_rc") == 1 and original.get("outcome") == "assertion",
        "original did not fail by assertion",
        problems,
    )
    _problem(
        remedy.get("native_rc") == 0 and remedy.get("outcome") == "passed",
        "remedy did not pass",
        problems,
    )
    _problem(step("prove").get("exit") == 0, "prove exit", problems)
    _problem(step("deliver").get("exit") == 0 and bool(handoff), "deliver did not return a handoff", problems)
    _problem(step("review-author").get("exit") == 1, "author review was not refused", problems)
    _problem("Author" in str(step("review-author").get("err", "")), "author review did not name the author", problems)
    _problem(step("close-before-review").get("exit") == 1, "close before independent review was not refused", problems)
    _problem("review" in str(step("close-before-review").get("err", "")).lower(), "close before review did not name review", problems)
    _problem(step("ack-review").get("exit") == 0, "review handoff ack exit", problems)
    _problem(step("review-reader").get("exit") == 0, "independent review exit", problems)
    _problem(step("check").get("exit") == 0, "check exit", problems)
    _problem(step("close").get("exit") == 0, "close exit", problems)
    _problem(bool(doctor) and doctor.get("integrity") == "passed", "doctor integrity", problems)
    _problem(bool(doctor) and doctor.get("pending_ack") == [], "doctor pending ack", problems)
    return problems


def _safe_work(work: Path) -> Path:
    """Only wipe a directory under this repo's tmp/ or the system temp dir."""
    work = work.resolve()
    allowed = [(ROOT / "tmp").resolve(), Path(tempfile.gettempdir()).resolve()]
    if work in {ROOT, Path("/"), Path.home(), *allowed}:
        raise RuntimeError("refusing to wipe %s" % work)
    if not any(root in work.parents for root in allowed):
        raise RuntimeError("work dir must stay under tmp")
    return work


def run(squadra: Path, work: Path, out: Path) -> dict:
    real_home = Path.home()
    before = {str(path): path.exists() for path in _homes(real_home)}
    started = time.perf_counter()
    work = _safe_work(work)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    driver = Driver(squadra, work)
    proof_argv = [sys.executable, "-c", "print('contract passed')"]
    driver.prepare_repo(proof_argv)
    repo = str(driver.repo)
    scope = str(driver.ev / "scope.md")
    proof = str(driver.ev / "proof.json")
    report = str(driver.ev / "report.md")
    version_started = time.perf_counter()
    version = subprocess.run(
        [sys.executable, "-B", str(squadra), "--version"],
        env=driver.env,
        capture_output=True,
        text=True,
        check=False,
    )
    driver.steps.append(
        {
            "name": "version",
            "exit": version.returncode,
            "seconds": round(time.perf_counter() - version_started, 4),
            "err": (version.stderr or "").strip()[:240],
            "stdout": (version.stdout or "").strip()[:80],
        }
    )
    driver.call(
        ["init", "--name", "pfy-squadra-probe", "--project", repo, "--lang", "en", "--temporary"],
        "init",
    )
    for agent_id, identity, role in (
        ("c1", "coord-window", "coordinator"),
        ("w1", "builder-window", "builder"),
        ("r1", "reader-window", "reviewer"),
    ):
        driver.call(
            [
                "agent",
                "--id",
                agent_id,
                "--identity",
                identity,
                "--role",
                role,
                "--client",
                "manual",
                "--repo",
                repo,
            ],
            "agent-" + agent_id,
        )
    driver.call(
        [
            "task",
            "--id",
            "T1",
            "--title",
            "value defect stand-in for gap B",
            "--actor",
            "c1",
            "--owner",
            "w1",
            "--repo",
            repo,
            "--scope-file",
            scope,
            "--proof-file",
            proof,
            "--reviewer",
            "r1",
            "--defect-fix",
        ],
        "task",
    )
    driver.call(["start", "--actor", "w1", "--task", "T1"], "start-before-ack")
    driver.call(["close", "--actor", "c1", "--task", "T1"], "close-before-deliver")
    driver.call(["ack", "--actor", "w1", "--message", "assign-T1"], "ack-assign")
    tests = driver.repo / "tests"
    tests.mkdir()
    (tests / "test_bug.py").write_text(GREEN_TEST)
    green_contract = driver.ev / "green.json"
    green_contract.write_text(json.dumps(CONTRACT))
    driver.call(
        [
            "challenge",
            "--actor",
            "c1",
            "--task",
            "T1",
            "--register",
            "--contract-file",
            str(green_contract),
            "--reason",
            "always-passing control",
        ],
        "register-green",
    )
    green_dir = driver.ev / "challenge-green"
    driver.call(
        ["challenge", "--actor", "w1", "--task", "T1", "--output", str(green_dir), "--timeout", "30"],
        "challenge-green",
    )
    (driver.repo / "code.py").write_text("VALUE = 2\n")
    (tests / "test_bug.py").write_text(REAL_TEST)
    real_contract = driver.ev / "real.json"
    real_contract.write_text(json.dumps(CONTRACT))
    driver.call(
        [
            "challenge",
            "--actor",
            "c1",
            "--task",
            "T1",
            "--register",
            "--contract-file",
            str(real_contract),
            "--reason",
            "value regression",
        ],
        "register-real",
    )
    real_dir = driver.ev / "challenge-real"
    driver.call(
        ["challenge", "--actor", "w1", "--task", "T1", "--output", str(real_dir), "--timeout", "30"],
        "challenge-real",
    )
    driver.call(["prove", "--actor", "w1", "--task", "T1", "--timeout", "30", "--", *proof_argv], "prove")
    delivered = driver.call(["deliver", "--actor", "w1", "--task", "T1"], "deliver")
    payload = _first_json(delivered.stdout)
    handoff = str(payload.get("handoff") or "") if payload else ""
    driver.call(
        ["review", "--actor", "w1", "--task", "T1", "--verdict", "accepted", "--report", report],
        "review-author",
    )
    driver.call(["close", "--actor", "c1", "--task", "T1"], "close-before-review")
    if handoff:
        driver.call(["ack", "--actor", "r1", "--message", handoff], "ack-review")
    else:
        driver.steps.append({"name": "ack-review", "exit": 1, "seconds": 0.0, "err": "no handoff"})
    driver.call(
        ["review", "--actor", "r1", "--task", "T1", "--verdict", "accepted", "--report", report],
        "review-reader",
    )
    driver.call(["check", "--actor", "c1", "--task", "T1"], "check")
    driver.call(["close", "--actor", "c1", "--task", "T1"], "close")
    doctor_run = driver.call(["doctor"], "doctor")
    doctor = _first_json(doctor_run.stdout)
    after = {str(path): path.exists() for path in _homes(real_home)}
    by_name = {item["name"]: item for item in driver.steps}
    green = _runs(green_dir)
    real = _runs(real_dir)
    pin = _pin(squadra)
    version_text = str(by_name.get("version", {}).get("stdout", ""))
    problems = []
    if pin["checkout_has_git"] and not pin["commit_ok"]:
        problems.append("pin commit")
    if version_text.splitlines()[:1] != [PIN_VERSION]:
        problems.append("version text")
    problems.extend(evaluate(by_name, green, real, doctor, handoff))
    if before != after:
        problems.append("real home changed")
    refuses = {
        "start_before_ack": by_name.get("start-before-ack", {}).get("exit") == 1,
        "close_before_deliver": by_name.get("close-before-deliver", {}).get("exit") == 1,
        "always_passing_not_matched": by_name.get("challenge-green", {}).get("exit") == 1
        and len(green) == 2
        and all(item.get("outcome") == "passed" for item in green),
        "author_review": by_name.get("review-author", {}).get("exit") == 1,
        "close_before_independent_review": by_name.get("close-before-review", {}).get("exit") == 1,
    }
    result = {
        "pin": pin,
        "version_text": version_text,
        "wall_s": round(time.perf_counter() - started, 4),
        "steps": driver.steps,
        "green_runs": green,
        "real_runs": real,
        "handoff": handoff,
        "doctor": {key: (doctor or {}).get(key) for key in ("integrity", "events", "pending_ack")},
        "refuses": refuses,
        "refuse_count": sum(1 for value in refuses.values() if value),
        "refuse_of": len(refuses),
        "real_challenge_matched": original_ok(real) and by_name.get("challenge-real", {}).get("exit") == 0,
        "close_exit": by_name.get("close", {}).get("exit"),
        "gap_b": {
            "pfy_build_invoked": False,
            "timeout_hours_changed": 0,
            "pregate_fails_cleared": 0,
        },
        "real_home_before": before,
        "real_home_after": after,
        "real_home_untouched": before == after,
        "problems": problems,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def original_ok(runs: list[dict]) -> bool:
    original = next((item for item in runs if item.get("label") == "original"), {})
    remedy = next((item for item in runs if item.get("label") == "remedy"), {})
    return (
        original.get("native_rc") == 1
        and original.get("outcome") == "assertion"
        and remedy.get("native_rc") == 0
        and remedy.get("outcome") == "passed"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe a Squadra checkout. No network.")
    parser.add_argument("--squadra", default="", help="Path to scripts/squadra.py")
    parser.add_argument("--work", default="", help="Throwaway work directory")
    parser.add_argument("--out", default="", help="Results JSON path")
    args = parser.parse_args(argv)
    squadra = Path(args.squadra or (Path.home() / ".cache/pfy/tools/squadra/src/scripts/squadra.py"))
    work = Path(args.work or (ROOT / "tmp" / "squadra-probe"))
    out = Path(args.out or (ROOT / "eval" / "evq1107" / "squadra" / "results.json"))
    if not squadra.is_file():
        print("squadra script missing: %s" % squadra, file=sys.stderr)
        return 2
    try:
        result = run(squadra, work, out)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("probe failed: %s" % exc, file=sys.stderr)
        return 2
    print(
        "refuse %s/%s real_matched %s close %s wall %ss problems %s"
        % (
            result["refuse_count"],
            result["refuse_of"],
            result["real_challenge_matched"],
            result["close_exit"],
            result["wall_s"],
            len(result["problems"]),
        )
    )
    return 0 if not result["problems"] else 2


if __name__ == "__main__":
    sys.exit(main())
