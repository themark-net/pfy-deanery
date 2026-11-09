#!/usr/bin/env python3
"""Race eight disjoint lands on one branch: plain git fast-forward versus gitai.

The fixture is a throwaway repository. It is shaped like this repo's lane
landing (one branch, one new file per agent). It does not read or write the
pfy-mentat git directory. gitai runs only when the pinned build is already
present under the cache. Tokens stay in that work directory and are stripped
from the result file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# GITAI_OUT lets a check run write elsewhere. The default is the recorded file.
OUT = Path(os.environ.get("GITAI_OUT", str(Path(__file__).resolve().parent / "results.json")))
AGENTS = 8
MAX_ROUNDS = 20
PIN = "914e481ef057ca7b9dc9a5a7338d96bca16790e1"
# HOME is redirected into the cache for the server, so Path.home() is not the
# install root. The lane always installs under this user's cache directory.
CACHE = Path(os.environ.get("GITAI_CACHE", str(Path.home() / ".cache/pfy/tools/gitai")))
SRC = Path(os.environ.get("GITAI_SRC", CACHE / "src/git-ai"))
BIN = SRC / "_build/bin"

ATTEMPT_RE = re.compile(r"(\d+) attempts?")


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    env["GIT_AUTHOR_NAME"] = "probe"
    env["GIT_AUTHOR_EMAIL"] = "probe@example.com"
    env["GIT_COMMITTER_NAME"] = "probe"
    env["GIT_COMMITTER_EMAIL"] = "probe@example.com"
    return env


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 60):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def git(repo: Path, *args: str, timeout: int = 60):
    return run(["git", "-C", str(repo), *args], env=git_env(), timeout=timeout)


def must_git(repo: Path, *args: str):
    code, out, err = git(repo, *args)
    if code != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {err.strip() or out.strip()}")
    return out


def init_bare(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    code, out, err = run(["git", "init", "--bare", "--initial-branch=main", str(path)], env=git_env())
    if code != 0:
        raise RuntimeError(err.strip() or out.strip())


def seed_repo(bare: Path, seed_path: Path, text: str) -> None:
    seed = bare.parent / (bare.name + "-seed")
    if seed.exists():
        shutil.rmtree(seed)
    code, out, err = run(["git", "init", "--initial-branch=main", str(seed)], env=git_env())
    if code != 0:
        raise RuntimeError(err.strip() or out.strip())
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    # path is relative to the seed repo
    dest = seed / seed_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    must_git(seed, "add", str(seed_path))
    must_git(seed, "commit", "-m", "seed")
    must_git(seed, "push", str(bare), "HEAD:refs/heads/main")


def prepare_agents(bare: Path, work: Path, mutate) -> list[Path]:
    clones: list[Path] = []
    for i in range(AGENTS):
        dest = work / f"agent-{i}"
        if dest.exists():
            shutil.rmtree(dest)
        code, out, err = run(["git", "clone", "--quiet", str(bare), str(dest)], env=git_env())
        if code != 0:
            raise RuntimeError(err.strip() or out.strip())
        mutate(dest, i)
        must_git(dest, "add", "-A")
        must_git(dest, "commit", "-m", f"lane {i}")
        clones.append(dest)
    return clones


def push_ff(repo: Path) -> tuple[int, str]:
    # This git rejects a non-fast-forward push unless --force is set. There is
    # no push --ff-only flag in the installed build.
    code, out, err = git(repo, "push", "origin", "HEAD:refs/heads/main")
    return code, (err or out).strip()


def rebase_onto_origin(repo: Path) -> str:
    code, _, err = git(repo, "fetch", "--quiet", "origin")
    if code != 0:
        return "fetch-failed"
    code, _, err = git(repo, "rebase", "origin/main")
    if code != 0:
        git(repo, "rebase", "--abort")
        if "conflict" in err.lower() or "could not apply" in err.lower():
            return "conflict"
        return "rebase-failed"
    return "ok"


def plain_race(bare: Path, clones: list[Path]) -> dict:
    pending = set(range(len(clones)))
    conflicts: list[int] = []
    attempts = [0] * len(clones)
    first_ok = 0
    rounds = 0
    push_error = ""
    started = time.perf_counter()
    while pending and rounds < MAX_ROUNDS:
        rounds += 1
        ready: list[int] = []
        for i in list(pending):
            if rounds > 1:
                state = rebase_onto_origin(clones[i])
                if state == "conflict":
                    pending.remove(i)
                    conflicts.append(i)
                    continue
                if state != "ok":
                    pending.remove(i)
                    conflicts.append(i)
                    continue
            ready.append(i)
        if not ready:
            break
        codes: dict[int, tuple[int, str]] = {}
        lock = threading.Lock()

        def one(i: int) -> None:
            code, err = push_ff(clones[i])
            with lock:
                codes[i] = (code, err)

        threads = [threading.Thread(target=one, args=(i,)) for i in ready]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for i, (code, err) in codes.items():
            attempts[i] += 1
            if code == 0:
                pending.discard(i)
                if rounds == 1:
                    first_ok += 1
            elif not push_error:
                push_error = err[:300]
    wall_ms = round((time.perf_counter() - started) * 1000, 1)
    tip = must_git(bare, "ls-tree", "-r", "--name-only", "HEAD").split()
    return {
        "first_push_ok": first_ok,
        "rounds": rounds,
        "push_attempts": sum(attempts),
        "landed": len(clones) - len(pending) - len(conflicts),
        "conflicts": len(conflicts),
        "unresolved": len(pending),
        "wall_ms": wall_ms,
        "tip_files": len(tip),
        "push_error": push_error,
    }


def disjoint_mutate(repo: Path, i: int) -> None:
    path = repo / "data" / "stages" / f"lane-{i}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"name":"lane-%d","integration_stage":"I0"}\n' % i)


def force_stage(card: str, stage: str) -> str:
    """Put a known stage on the seed so both writers change the same line.

    The live card moves after the probe (I0 to I1). A same-line race that
    reads the live text and looks for I0 would then have nothing to commit.
    """
    updated, n = re.subn(
        r'"integration_stage": "I[0-9]"',
        '"integration_stage": "%s"' % stage,
        card,
        count=1,
    )
    if n != 1:
        raise RuntimeError("seed card has no integration_stage line to race")
    return updated


def same_line_mutate(repo: Path, i: int) -> None:
    path = repo / "data" / "stages" / "gitai.json"
    text = path.read_text()
    old = '"integration_stage": "I0"'
    new = '"integration_stage": "I%d"' % (i + 1)
    if old not in text:
        raise RuntimeError("seed card has no integration_stage line to race")
    path.write_text(text.replace(old, new, 1))


def plain_case(work: Path, name: str, seed_rel: Path, seed_text: str, mutate, agents: int | None = None) -> dict:
    global AGENTS
    saved = AGENTS
    if agents is not None:
        AGENTS = agents
    try:
        bare = work / f"{name}.git"
        init_bare(bare)
        seed_repo(bare, seed_rel, seed_text)
        clones = prepare_agents(bare, work / name, mutate)
        result = plain_race(bare, clones)
        result["case"] = name
        return result
    finally:
        AGENTS = saved


def scrub(text: str, secrets: list[str]) -> str:
    out = text
    for secret in secrets:
        if secret:
            out = out.replace(secret, "[redacted]")
    return out


def wait_socket(path: Path, proc: subprocess.Popen, timeout: float = 30.0) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if path.is_socket():
            return True
        if proc.poll() is not None:
            return False
        time.sleep(0.1)
    return path.is_socket()


def write_config(work: Path, bin_dir: Path, names: list[str]) -> tuple[Path, list[str]]:
    run_dir = work / "run"
    repos = work / "repos"
    tokens = work / "tokens"
    for d in (run_dir, repos, tokens):
        d.mkdir(parents=True, exist_ok=True)
    secrets: list[str] = []
    agent_blocks = []
    for name in names:
        token = subprocess.check_output(["openssl", "rand", "-hex", "32"], text=True).strip()
        secrets.append(token)
        dest = tokens / name
        dest.write_text(token + "\n")
        dest.chmod(0o600)
        agent_blocks.append(
            '[[graft.agent]]\nname = "%s"\ntoken_file = "%s"\n' % (name, dest)
        )
    shared = subprocess.check_output(["openssl", "rand", "-hex", "32"], text=True).strip()
    secrets.append(shared)
    cfg = work / "config.toml"
    cfg.write_text(
        "\n".join(
            [
                'bin_dir = "%s"' % bin_dir,
                'socket_path = "%s"' % (run_dir / "gitaly.sock"),
                'runtime_dir = "%s"' % run_dir,
                "",
                "[auth]",
                'token = "%s"' % shared,
                "",
                "[[storage]]",
                'name = "default"',
                'path = "%s"' % repos,
                "",
                "[graft]",
                "standalone = true",
                "",
                *agent_blocks,
                "[[graft.policy]]",
                'refs = ["refs/heads/**"]',
                "allow = true",
                "",
                "[graft.changelog]",
                "disabled = false",
                "",
            ]
        )
    )
    return cfg, secrets


def gitai_case(graft: Path, address: str, repo: str, work: Path, tokens: dict[str, str], mutate, n: int) -> dict:
    results: list[dict | None] = [None] * n
    barrier = threading.Barrier(n)
    clock = {"start": None, "end": None}
    clock_lock = threading.Lock()

    def one(i: int) -> None:
        user = "lane-%d" % i
        try:
            prep = graft_land_prepare(
                graft, address, repo, work / ("ws-%d" % i), tokens[user], user, mutate, i
            )
        except Exception as exc:
            prep = {"ready": False, "ok": False, "kind": "clone", "out": "", "err": str(exc), "attempts": 0}
        if not prep["ready"]:
            results[i] = prep
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError:
                pass
            return
        try:
            barrier.wait(timeout=120)
        except threading.BrokenBarrierError:
            results[i] = {"ok": False, "kind": "barrier", "out": "", "err": "barrier failed", "attempts": 0}
            return
        with clock_lock:
            now = time.perf_counter()
            if clock["start"] is None:
                clock["start"] = now
        results[i] = graft_land_commit(graft, prep["env"], work / ("ws-%d" % i), "lane %d" % i)
        with clock_lock:
            clock["end"] = time.perf_counter()

    threads = [threading.Thread(target=one, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if clock["start"] is None or clock["end"] is None:
        wall_ms = 0.0
    else:
        wall_ms = round((clock["end"] - clock["start"]) * 1000, 1)
    landed = sum(1 for r in results if r and r.get("kind") == "landed")
    conflicts = sum(1 for r in results if r and r.get("kind") == "conflict")
    errors = [r for r in results if r and r.get("kind") not in ("landed", "conflict")]
    notes = []
    for r in results:
        if not r:
            continue
        lines = [ln.strip() for ln in ((r.get("out") or "") + "\n" + (r.get("err") or "")).splitlines() if ln.strip()]
        picked = ""
        for ln in lines:
            low = ln.lower()
            if "landed it on" in low or "conflict" in low or "landing failed" in low:
                picked = ln
                break
        if not picked and lines:
            picked = lines[-1]
        if len(picked) > 240:
            picked = picked[:240].rsplit(" ", 1)[0]
        if picked:
            notes.append(picked)
    return {
        "landed": landed,
        "conflicts": conflicts,
        "errors": len(errors),
        "attempts_sum": sum(int(r.get("attempts") or 0) for r in results if r),
        "batched": sum(1 for r in results if r and "batch" in (r.get("out") or "")),
        "wall_ms": wall_ms,
        "error_kinds": sorted({r.get("kind", "") for r in errors}),
        "sample_error": (errors[0].get("err") or errors[0].get("out") or "")[:400] if errors else "",
        "notes": notes,
    }


def graft_land_prepare(graft, address, repo, ws, token, user, mutate, i) -> dict:
    env = git_env()
    env.update(
        {
            "HOME": str(CACHE / "home"),
            "TMPDIR": str(CACHE / "tmp"),
            "XDG_CONFIG_HOME": str(CACHE / "config"),
            "XDG_CACHE_HOME": str(CACHE / "cache"),
            "GRAFT_ADDRESS": address,
            "GRAFT_STORAGE": "default",
            "GRAFT_TOKEN": token,
            "GRAFT_USER": user,
            "GRAFT_AUTHOR": "%s <%s@example.com>" % (user, user),
        }
    )
    code, out, err = run(
        [str(graft), "clone", address, repo, str(ws), "--branch", "main"],
        env=env,
        timeout=90,
    )
    if code != 0:
        return {"ready": False, "ok": False, "kind": "clone", "out": out, "err": err, "attempts": 0}
    mutate(ws, i)
    return {"ready": True, "env": env}


def graft_land_commit(graft, env, ws, message) -> dict:
    code, out, err = run(
        [str(graft), "commit", "-C", str(ws), "-m", message, "--land", "main"],
        env=env,
        timeout=90,
    )
    blob = out + "\n" + err
    found = ATTEMPT_RE.search(blob)
    attempts = int(found.group(1)) if found else (1 if code == 0 else 0)
    if code == 0 and "landed it on" in out:
        return {"ok": True, "kind": "landed", "out": out, "err": err, "attempts": attempts}
    if "conflict" in blob.lower():
        return {"ok": False, "kind": "conflict", "out": out, "err": err, "attempts": attempts}
    return {"ok": False, "kind": "error", "out": out, "err": err, "attempts": attempts}


def tip_count(bare: Path) -> int:
    out = must_git(bare, "ls-tree", "-r", "--name-only", "HEAD")
    return len(out.split())


def start_gitai(work: Path, names: list[str]):
    gitaly = BIN / "gitaly"
    graft = BIN / "graft"
    missing = [p.name for p in (gitaly, graft, BIN / "gitaly-hooks", BIN / "gitaly-ssh") if not os.access(p, os.X_OK)]
    if missing:
        return None, None, [], "SKIPPED missing binaries: " + ", ".join(missing)
    cfg, secrets = write_config(work, BIN, names)
    log_path = work / "gitaly.log"
    log_f = log_path.open("w")
    env = git_env()
    env["HOME"] = str(CACHE / "home")
    env["TMPDIR"] = str(CACHE / "tmp")
    proc = subprocess.Popen(
        [str(gitaly), "serve", str(cfg)],
        stdout=log_f,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    sock = work / "run" / "gitaly.sock"
    if not wait_socket(sock, proc):
        tail = log_path.read_text(errors="replace")[-800:]
        stop_proc(proc)
        log_f.close()
        return None, None, secrets, "SKIPPED server did not listen: " + scrub(tail, secrets)
    log_f.close()
    code, out, err = run([str(gitaly), "--version"], env=env)
    version = (out or err).strip()
    return proc, version, secrets, ""


def stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, 15)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 9)
        proc.wait(timeout=5)


def load_tokens(work: Path, names: list[str]) -> dict[str, str]:
    return {name: (work / "tokens" / name).read_text().strip() for name in names}


def gitai_repo(server_repos: Path, name: str, seed_rel: Path, seed_text: str) -> Path:
    bare = server_repos / name
    init_bare(bare)
    seed_repo(bare, seed_rel, seed_text)
    return bare


def main() -> int:
    card = (ROOT / "data/stages/gitai.json").read_text()
    work = Path(os.environ.get("GITAI_WORK", "")) if os.environ.get("GITAI_WORK") else CACHE / "tmp" / ("probe-%d" % os.getpid())
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    head = ""
    if (SRC / ".git").exists():
        code, out, _ = run(["git", "-C", str(SRC), "rev-parse", "HEAD"])
        head = out.strip() if code == 0 else ""
    version = ""
    if (BIN / "gitaly").is_file():
        code, out, err = run([str(BIN / "gitaly"), "--version"])
        version = (out or err).strip() if code == 0 else ""

    plain_disjoint = plain_case(
        work / "plain",
        "disjoint",
        Path("data/stages/gitai.json"),
        card,
        disjoint_mutate,
        AGENTS,
    )
    plain_clash = plain_case(
        work / "plain",
        "same-line",
        Path("data/stages/gitai.json"),
        force_stage(card, "I0"),
        same_line_mutate,
        2,
    )

    names = ["lane-%d" % i for i in range(AGENTS)]
    proc = None
    secrets: list[str] = []
    gitai: dict = {"status": "SKIPPED", "reason": "not started"}
    try:
        proc, version_run, secrets, reason = start_gitai(work / "server", names)
        if version_run:
            version = version_run
        if reason:
            gitai = {"status": "SKIPPED", "reason": scrub(reason, secrets)[:500]}
        else:
            assert proc is not None
            tokens = load_tokens(work / "server", names)
            address = "unix:" + str(work / "server" / "run" / "gitaly.sock")
            repos = work / "server" / "repos"
            bare = gitai_repo(repos, "demo.git", Path("data/stages/gitai.json"), card)
            disjoint = gitai_case(BIN / "graft", address, "demo.git", work / "gitai-disjoint", tokens, disjoint_mutate, AGENTS)
            disjoint["tip_files"] = tip_count(bare)
            clash_names = names[:2]
            bare2 = gitai_repo(repos, "clash.git", Path("data/stages/gitai.json"), force_stage(card, "I0"))
            clash = gitai_case(
                BIN / "graft",
                address,
                "clash.git",
                work / "gitai-clash",
                {k: tokens[k] for k in clash_names},
                same_line_mutate,
                2,
            )
            clash["tip_files"] = tip_count(bare2)
            for row in (disjoint, clash):
                row["sample_error"] = scrub(str(row.get("sample_error", "")), secrets)[:400]
            gitai = {"status": "ok", "disjoint": disjoint, "same_line": clash}
    finally:
        stop_proc(proc)

    payload = {
        "pin_expected": PIN,
        "pin_head": head,
        "pin_match": head == PIN,
        "gitaly_version": version,
        "agents_disjoint": AGENTS,
        "plain": {"disjoint": plain_disjoint, "same_line": plain_clash},
        "gitai": gitai,
    }
    # Drop any secret that survived.
    text = json.dumps(payload, indent=2)
    text = scrub(text, secrets)
    OUT.write_text(text + "\n")
    if not os.environ.get("GITAI_KEEP"):
        shutil.rmtree(work, ignore_errors=True)
    print(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        err = {"status": "PROBE_ERROR", "error": str(exc)}
        OUT.write_text(json.dumps(err, indent=2) + "\n")
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)
