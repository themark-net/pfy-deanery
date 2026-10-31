#!/usr/bin/env python3
"""AgentDescent vs DSPy vs baseline on X intake triage (eval-auto trial, Entry 119).

Usage (from the worktree root):
  python3 examples/agentdescent-trial/harness.py [--stage all|baseline|evolve|dspy]   run into tmp/agentdescent-trial-run/
  python3 examples/agentdescent-trial/harness.py --promote                            copy that run into tracked results/

Runs never write tracked files: everything goes to $TRIAL_OUT (default <worktree>/tmp/agentdescent-trial-run, gitignored).
Each stage writes its own <stage>.json, replaced wholesale; results.json is rebuilt from the stage files of the
current run dir only (no merge with older results). `--promote` is the only path into results/ and SKILL.evolved.md.
Exit codes: 0 ok, 1 a stage failed or timed out, 3 a watched real-HOME dir changed (checked in a finally, timeouts too).

Every child goes through examples/x-intake-local/smoke.py run_isolated (new session, killpg on timeout,
stripped env, temp HOME). Venv, AgentDescent run store and scratch live in <worktree>/tmp. The real skill text
is never a target: AgentDescent evolves a copy in tmp/, and `apply` is never called. ~/.agentdescent in the
real HOME is snapshotted before and after. Waits (never kills) while Ollama has another model loaded.
"""
import argparse, hashlib, json, os, shutil, stat, sys, tempfile, threading, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[1]
sys.path.insert(0, str(WT / "examples/x-intake-local"))
from smoke import run_isolated  # noqa: E402

TMPD = WT / "tmp"
VENV = TMPD / ".venv/bin"
STORE = TMPD / "adstore"
RES = Path(os.environ.get("TRIAL_OUT") or (TMPD / "agentdescent-trial-run"))
TRACKED_RES = HERE / "results"
REAL_HOME = Path(os.environ.get("TRIAL_REAL_HOME") or os.path.expanduser("~"))
WATCH = (".agentdescent", ".cache/agentdescent", ".dspy_cache", ".cache/dspy", ".ollama")
HASH_MAX = 1 << 20  # sha256 content for files up to 1 MiB, size+mtime_ns for bigger ones (model blobs)
MODEL = "qwen3.6:35b"
BASE = "http://localhost:11434/v1"
MEM_CAP_GIB = 85


def _snap_entry(path: Path, st) -> str:
    """One lstat fingerprint. Symlinks store mode and readlink text and are not opened.
    Small regular files keep a content sha256. Anything larger, or unreadable, keeps size and mtime_ns."""
    mode = stat.S_IMODE(st.st_mode)
    if stat.S_ISLNK(st.st_mode):
        try:
            link = os.readlink(path)
        except OSError:
            link = ""
        return f"mode:{mode:o}:mt:{st.st_mtime_ns}:link:{link}"
    meta = f"sz:{st.st_size}:mt:{st.st_mtime_ns}:mode:{mode:o}"
    if not stat.S_ISREG(st.st_mode) or st.st_size > HASH_MAX:
        return meta
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return meta
    return f"sha:{digest}:mode:{mode:o}"


def snap_dir(p: Path):
    """Per-entry fingerprint. None if p is missing. A symlinked root keeps its readlink; entries under the target are still hashed."""
    if not p.exists() and not p.is_symlink():
        return None
    out = {}
    # is_dir follows a symlinked root so the target tree is hashed; lstat below does not follow.
    for f in [p, *sorted(p.rglob("*"))] if p.is_dir() else [p]:
        try:
            st = f.lstat()
        except OSError:
            continue
        rel = "." if f == p else str(f.relative_to(p))
        out[rel] = _snap_entry(f, st)
    return out


def snap(home: Path = None):
    home = home or REAL_HOME
    return {d: snap_dir(home / d) for d in WATCH}


def home_diff(before, after):
    changed = {}
    for d in WATCH:
        b, a = before.get(d), after.get(d)
        if b != a:
            if b is None or a is None:
                changed[d] = "created" if b is None else "removed"
            else:
                keys = sorted(k for k in set(b) | set(a) if b.get(k) != a.get(k))
                changed[d] = keys[:20]
    return changed


def rel(text: str) -> str:
    """Strip absolute worktree/home paths from anything we keep."""
    return text.replace(str(WT) + "/", "").replace(str(WT), ".").replace(str(REAL_HOME), "~")


def meminfo():
    d = {}
    for l in open("/proc/meminfo"):
        k, v = l.split(":"); d[k] = int(v.split()[0]) // 1024 // 1024
    return d


class MemWatch(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True); self.min_avail = 10**9; self.max_used = 0; self.stop = False
    def run(self):
        while not self.stop:
            m = meminfo(); self.min_avail = min(self.min_avail, m["MemAvailable"])
            self.max_used = max(self.max_used, m["MemTotal"] - m["MemAvailable"]); time.sleep(5)


def wait_ollama(log):
    while True:
        with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=10) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        others = [n for n in names if n != MODEL]
        if not others:
            return names
        log(f"ollama busy with {others}; waiting 60s (never killed)"); time.sleep(60)


def child_env():
    return {"OPENAI_BASE_URL": BASE, "OPENAI_API_KEY": "ollama-local-dummy", "TRIAL_MODEL": MODEL,
            "PYTHONDONTWRITEBYTECODE": "1"}


def iso(cmd, timeout):
    with tempfile.TemporaryDirectory(prefix="home-", dir=TMPD) as home:
        t0 = time.time()
        p = run_isolated(cmd, home=home, cwd=str(TMPD), timeout=timeout, path=f"{VENV}:/usr/bin:/bin",
                         extra=child_env(), bwrap_writable=None)  # bwrap --unshare-net would cut localhost:11434
        leftover = sorted(str(x.relative_to(home)) for x in Path(home).rglob("*"))
        return p, round(time.time() - t0, 1), leftover


def score(skill: Path, cases: Path, tag: str):
    out = RES / f"score_{tag}.json"
    p, wall, left = iso([str(VENV / "python"), str(HERE / "child.py"), "score", str(skill), str(cases), str(out)], 3600)
    if p.returncode != 0:
        raise RuntimeError(f"score {tag} rc={p.returncode}: {p.stderr[-800:]}")
    r = json.loads(out.read_text()); r["child_wall_s"] = wall; r["temp_home_leftover"] = left
    out.write_text(json.dumps(r, indent=1)); return r


def spec_for(target: Path):
    oa = "agentdescent.agents:openai_compatible"
    return {"version": 1, "kind": "text", "name": "x-intake-triage", "target": str(target),
            "data": {"path": str(HERE / "train.jsonl"), "prompt": "prompt", "gold": "gold", "id": "id"},
            "score": "exact",
            "agent": {"ref": oa, **{"model": MODEL, "default_base_url": BASE, "max_tokens": 16,
                                            "temperature": 0, "reasoning_effort": "none", "timeout": 300.0}},
            "reflect": {"ref": oa, **{"model": MODEL, "default_base_url": BASE, "max_tokens": 12000,
                                   "temperature": 0.6, "stream": True, "timeout": 1200.0}},
            "evolve": {"rounds": 6, "n_workers": 4, "seed": 230}}


def evolve(log):
    work = TMPD / "ad-target"; work.mkdir(parents=True, exist_ok=True)
    target = work / "SKILL.md"; shutil.copy2(HERE / "skill/SKILL.md", target)
    before_sha = hashlib.sha256((HERE / "skill/SKILL.md").read_bytes()).hexdigest()
    spec = work / "spec.json"; spec.write_text(json.dumps(spec_for(target), indent=1))
    (RES / "agentdescent_spec.json").write_text(rel(spec.read_text()))
    ad = str(VENV / "agentdescent")
    p, _, _ = iso([ad, "--store", str(STORE), "--json", "plan", str(spec)], 300)
    (RES / "agentdescent_plan.txt").write_text(rel(p.stdout[-6000:] + p.stderr[-2000:]))
    if p.returncode != 0:
        raise RuntimeError(f"agentdescent plan rc={p.returncode}: {p.stderr[-800:]}")
    existing = set(STORE.glob("*")) if STORE.exists() else set()
    p, wall, left = iso([ad, "--store", str(STORE), "--json", "evolve", str(spec)], 4 * 3600)
    (RES / "agentdescent_evolve.log").write_text(rel(p.stdout[-20000:] + "\n--- stderr ---\n" + p.stderr[-8000:]))
    if p.returncode != 0:
        raise RuntimeError(f"agentdescent evolve rc={p.returncode}: {p.stderr[-800:]}")
    run_id = created_run_dir(existing).name
    s, _, _ = iso([ad, "--store", str(STORE), "--json", "show", run_id, "--diff"], 300)
    show = json.loads(s.stdout)
    (RES / "agentdescent_show.json").write_text(rel(json.dumps(show, indent=1)))
    # evidence for call/round counts: AgentDescent's own result.json and rounds.jsonl
    rd = STORE / run_id
    for src, dst in (("result.json", "agentdescent_result.json"), ("rounds.jsonl", "agentdescent_rounds.jsonl")):
        if (rd / src).exists():
            (RES / dst).write_text(rel((rd / src).read_text()))
    evolved = RES / "SKILL.evolved.md"; evolved.write_text(show.get("rendered", ""))
    after_sha = hashlib.sha256((HERE / "skill/SKILL.md").read_bytes()).hexdigest()
    return {"run_id": run_id, "evolve_wall_s": wall, "temp_home_leftover": left,
            "final_reward_train_internal": show.get("final_reward"), "outcomes": show.get("outcomes"),
            "stop_reason": show.get("stop_reason"), "usage": show.get("usage"),
            "baseline_skill_untouched": before_sha == after_sha, "tmp_target_changed":
            hashlib.sha256(target.read_bytes()).hexdigest() != before_sha}


def created_run_dir(existing):
    """The AgentDescent run dir this invocation created (never an older one picked by name)."""
    new = sorted(set(STORE.glob("*")) - set(existing)) if STORE.exists() else []
    if len(new) != 1:
        raise RuntimeError(f"expected exactly one new AgentDescent run dir in {STORE}, found {len(new)}")
    return new[0]


def dspy_stage():
    out = RES / "dspy-out"  # inside the run dir, and cleared here so nothing stale is ever read
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    p, wall, left = iso([str(VENV / "python"), str(HERE / "child.py"), "dspy", str(HERE / "skill/SKILL.md"),
                         str(HERE / "train.jsonl"), str(HERE / "heldout.jsonl"), str(out)], 4 * 3600)
    (RES / "dspy.log").write_text(rel(p.stdout[-20000:] + "\n--- stderr ---\n" + p.stderr[-12000:]))
    if p.returncode != 0:
        raise RuntimeError(f"dspy rc={p.returncode}: {p.stderr[-800:]}")
    missing = [n for n in ("dspy_result.json", "dspy_program.json") if not (out / n).exists()]
    if missing:
        raise RuntimeError(f"dspy child exited 0 but wrote no {missing}")
    r = json.loads((out / "dspy_result.json").read_text()); r["child_wall_s"] = wall; r["temp_home_leftover"] = left
    shutil.copy2(out / "dspy_program.json", RES / "dspy_program.json")
    return r


STAGES = {}  # filled below; tests replace entries


def _baseline():
    return score(HERE / "skill/SKILL.md", HERE / "heldout.jsonl", "baseline")


def _evolve():
    r = evolve(print)
    r["heldout"] = score(RES / "SKILL.evolved.md", HERE / "heldout.jsonl", "agentdescent")
    return r


STAGES.update(baseline=_baseline, evolve=_evolve, dspy=lambda: dspy_stage())
KEY = {"baseline": "baseline", "evolve": "agentdescent", "dspy": "dspy"}


STAGE_FILES = {
    "baseline": ["score_baseline.json"],
    "evolve": ["score_agentdescent.json", "agentdescent_spec.json", "agentdescent_plan.txt", "agentdescent_evolve.log",
               "agentdescent_show.json", "agentdescent_result.json", "agentdescent_rounds.jsonl", "SKILL.evolved.md"],
    "dspy": ["dspy.log", "dspy_program.json", "dspy-out"],
}
INPUTS = ["skill/SKILL.md", "cases.jsonl", "train.jsonl", "heldout.jsonl", "harness.py", "child.py"]


def input_hashes():
    return {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in INPUTS}


def current_run():
    """The run the next record belongs to: run.json if its input hashes still match, else None."""
    f = RES / "run.json"
    if f.exists():
        r = json.loads(f.read_text())
        if r.get("inputs") == input_hashes():
            return r["run_id"]
    return None


def new_run(clear: bool):
    if clear and RES.exists():
        shutil.rmtree(RES)
    RES.mkdir(parents=True, exist_ok=True)
    rid = time.strftime("%Y%m%dT%H%M%S") + "-" + os.urandom(4).hex()
    (RES / "run.json").write_text(json.dumps({"run_id": rid, "inputs": input_hashes()}, indent=1))
    return rid


def matching_records():
    """(good, refused): stage records stamped with the current run id and input hashes, and the rest."""
    rid, inputs = current_run(), input_hashes()
    good, refused = {}, {}
    for st in STAGE_FILES:
        f = RES / f"stage_{st}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        if rid and d.get("run_id") == rid and d.get("inputs") == inputs:
            good[st] = d
        else:
            refused[st] = {"run_id": d.get("run_id"), "why": "run id or input hashes do not match the current run"}
    return good, refused


def build_results():
    """results.json from stage records of the current run (same run id and input hashes) only."""
    good, refused = matching_records()
    R = {"model": MODEL, "base_url": BASE, "run_id": current_run(), "inputs": input_hashes(),
         "stages": {}, "errors": {}, "guards": {}, "refused_stale": refused}
    for st, d in good.items():
        if d.get("error"):
            R["errors"][st] = d["error"]
        else:
            R["stages"][KEY[st]] = d["result"]
        R["guards"][st] = d.get("guard")
    (RES / "results.json").write_text(json.dumps(R, indent=1))
    return R


# Indirection so tests can inject faults at each filesystem step.
_rename = os.rename
_replace = os.replace
_fault = lambda point: None  # tests set this to raise at a named point
JOURNAL_NAME = ".promote-journal.json"


class Crash(BaseException):
    """Test hook: raised from _fault to simulate SIGKILL. promote re-raises it without rolling back."""


def _paths():
    parent = TRACKED_RES.parent
    evolved = HERE / "skill/SKILL.evolved.md"
    return parent, evolved, evolved.with_name(".SKILL.evolved.md.new"), parent / JOURNAL_NAME


def _fsync_dir(d: Path):
    try:
        fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def write_journal(state: str, tag: str):
    """Temp file, fsync, rename into place, fsync the dir: a reader sees the old or the new journal, never a torn one."""
    parent, _, _, journal = _paths()
    tmp = journal.with_name(JOURNAL_NAME + ".tmp")
    with open(tmp, "w") as f:
        f.write(json.dumps({"state": state, "tag": tag})); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, journal)
    _fsync_dir(parent)


def read_journal():
    """(state, tag) from a readable journal; (None, None) when it is missing, empty or garbled (treated alike)."""
    _, _, _, journal = _paths()
    if not journal.exists():
        return None, None
    try:
        j = json.loads(journal.read_text())
        if isinstance(j, dict) and j.get("state") in ("swapping", "committed"):
            return j["state"], j.get("tag")
    except (ValueError, OSError, UnicodeDecodeError):
        pass
    return None, None


def _rm(x: Path):
    if x.is_dir() and not x.is_symlink():
        shutil.rmtree(x)
    elif x.exists() or x.is_symlink():
        x.unlink()


def _restore_skill(evolved: Path, candidates_bak, candidates_absent):
    baks = [x for x in candidates_bak if x.exists()]
    absent = [x for x in candidates_absent if x.exists()]
    if baks:
        os.replace(baks[0], evolved)
    elif absent and evolved.exists():
        evolved.unlink()       # there was no SKILL.evolved.md before this promote


def _manual_fix(old: Path, sk_bak, sk_abs, staged: Path, why: str) -> str:
    """Refusal text with literal commands (run from examples/agentdescent-trial/) that keep results/ and the skill
    from the same promote."""
    tag = old.name[len(".results.old-"):]
    inner_bak, inner_abs = old / ".skill_backup", old / ".skill_absent"
    bak = next((x for x in [*sk_bak, inner_bak] if x.exists()), None)
    absent = next((x for x in [*sk_abs, inner_abs] if x.exists()), None)
    rel = lambda x: str(x.relative_to(old.parent))
    # keep results/ (the new set): finish the skill replace if it hadn't happened, then drop the backups and old set
    keep = []
    if staged.exists():
        keep.append(f"mv {rel(staged)} skill/SKILL.evolved.md")
    keep += [f"rm -f {rel(x)}" for x in [*sk_bak, *sk_abs]] + [f"rm -rf {old.name}"]
    # restore the old set: put the old skill back (or remove it if there was none), then the old results
    restore = []
    if bak is not None:
        restore.append(f"mv {rel(bak)} skill/SKILL.evolved.md")
    elif absent is not None:
        restore.append("rm -f skill/SKILL.evolved.md")
    restore += [f"rm -f {rel(x)}" for x in [*sk_abs, *([staged] if staged.exists() else [])]]
    restore += [f"rm -rf {rel(x)}" for x in (inner_bak, inner_abs) if x.exists() and x != bak]
    restore += (["rm -rf results"] if TRACKED_RES.exists() else []) + [f"mv {old.name} results"]
    msg = f"{why}; nothing changed. Manual fix, from examples/agentdescent-trial/: "
    if TRACKED_RES.exists():
        msg += f"keep results/: `{' && '.join(keep)}`; or "
    else:
        msg += f"results/ is missing and {old.name} (tag {tag}) is the only copy, so do not delete it; "
    return msg + f"restore the old set: `{' && '.join(restore)}`. Then rm -f .promote-journal.json"


def recover():
    """Run at the very top of --promote. Works from the files on disk; the journal only says roll forward or back.

    Returns None when clean (or recovered), else a message with the manual fix. Never raises for bad state.
    """
    parent, evolved, staged_skill, journal = _paths()
    try:
        olds = sorted(parent.glob(".results.old-*"))
        news = sorted(parent.glob(".results.new-*"))
        sk_bak = sorted(evolved.parent.glob(".SKILL.evolved.md.bak-*"))
        sk_abs = sorted(evolved.parent.glob(".SKILL.evolved.md.absent-*"))
        state, jtag = read_journal()
        if len(olds) > 1 or len(sk_bak) + len(sk_abs) > 1:
            return (f"ambiguous promote leftovers {[o.name for o in olds + sk_bak + sk_abs]}; restore results/ from the "
                    "right .results.old-* (or `git checkout -- examples/agentdescent-trial/results`) and delete the rest")
        old = olds[0] if olds else None
        tag_ok = old is not None and jtag is not None and old.name == f".results.old-{jtag}"
        if old is not None and state == "committed":
            if not tag_ok:
                return _manual_fix(old, sk_bak, sk_abs, staged_skill,
                                   f"{old.name} with a committed journal for tag {jtag!r}")
            for x in [*(sk_bak + sk_abs), old]:
                _rm(x)
            print(f"recovery: finished committed promote {jtag}, removed {old.name}")
        elif old is not None:
            if TRACKED_RES.exists() and not (state == "swapping" and tag_ok):
                # never replace a valid results/ without a readable mid-swap journal for this old set
                return _manual_fix(old, sk_bak, sk_abs, staged_skill,
                                   f"stale {old.name} next to a valid results/ with no matching journal")
            _restore_skill(evolved, sk_bak + [old / ".skill_backup"], sk_abs + [old / ".skill_absent"])
            for x in (*sk_bak, *sk_abs, old / ".skill_backup", old / ".skill_absent"):
                _rm(x)
            if TRACKED_RES.exists():
                _rm(TRACKED_RES)
            os.rename(old, TRACKED_RES)
            print(f"recovery: rolled back interrupted promote, restored results/ from {old.name}")
        else:
            # no old set: skill backups/staged skill may be deleted only if a .results.new-<same tag> proves the swap
            # never started
            skill_left = [*sk_bak, *sk_abs, *([staged_skill] if staged_skill.exists() else [])]
            tags = {x.name.rsplit("-", 1)[-1] for x in [*sk_bak, *sk_abs]}
            proven = bool(news) and all(parent / f".results.new-{t}" in news for t in tags)
            if skill_left and not proven:
                return (f"skill promote leftovers {[str(x.relative_to(parent)) for x in skill_left]} with no matching "
                        ".results.new-<tag>, so the swap may have started; nothing changed. Check that "
                        "skill/SKILL.evolved.md matches results/ (results/agentdescent_vs_baseline.diff), then delete "
                        "or `mv` those files by hand")
            if skill_left:
                for x in skill_left:
                    _rm(x)
                print("recovery: removed skill backup from a promote interrupted before the swap")
        for x in [*parent.glob(".results.new-*"), *parent.glob(".results.trash-*"), staged_skill,
                  journal.with_name(JOURNAL_NAME + ".tmp"), journal]:
            _rm(x)
        _fsync_dir(parent)
        if not TRACKED_RES.exists():
            return ("results/ is missing and no .results.old-* to restore it from; run "
                    "`git checkout -- examples/agentdescent-trial/results`")
        return None
    except OSError as e:
        return (f"could not recover promote leftovers ({type(e).__name__}: {e}); restore results/ by hand from "
                ".results.old-* or `git checkout -- examples/agentdescent-trial/results`, then delete .results.* and "
                ".promote-journal.json")


def promote():
    """Recover first, then accept only a COMPLETE current run, then a journaled swap (not atomic; see the handoff)."""
    why = recover()
    if why:
        print(f"refusing to promote: {why}", file=sys.stderr); return 1
    if not current_run():
        print(f"refusing to promote: no current run in {RES} (missing run.json or inputs changed)", file=sys.stderr); return 1
    good, refused = matching_records()
    missing = [st for st in STAGE_FILES if st not in good]
    if missing:
        print(f"refusing to promote an incomplete run: missing or stale {missing}", file=sys.stderr); return 1
    errs = [st for st, d in good.items() if d.get("error") or "result" not in d]
    if errs:
        print(f"refusing to promote a run with failed stages: {errs}", file=sys.stderr); return 1
    bad = [st for st, d in good.items() if not isinstance(d.get("guard"), dict) or d["guard"].get("real_home_untouched") is not True]
    if bad:
        print(f"refusing to promote: real-HOME guard failed or missing for {bad}", file=sys.stderr); return 1
    R = build_results()
    parent, evolved, staged_skill, journal = _paths()
    tag = os.urandom(4).hex()
    new = parent / f".results.new-{tag}"; old = parent / f".results.old-{tag}"; trash = parent / f".results.trash-{tag}"
    bak = evolved.with_name(f".SKILL.evolved.md.bak-{tag}"); absent = evolved.with_name(f".SKILL.evolved.md.absent-{tag}")
    try:
        # 1. stage everything (results set + skill) without touching tracked files
        new.mkdir()
        for name in ["results.json", "run.json", *[f"stage_{st}.json" for st in STAGE_FILES],
                     *[n for st in STAGE_FILES for n in STAGE_FILES[st] if n not in ("SKILL.evolved.md", "dspy-out")]]:
            if (RES / name).exists():
                shutil.copy2(RES / name, new / name)
        produced = RES / "SKILL.evolved.md"
        if produced.exists():
            import difflib
            base = (HERE / "skill/SKILL.md").read_text().splitlines(keepends=True)
            (new / "agentdescent_vs_baseline.diff").write_text("".join(difflib.unified_diff(
                base, produced.read_text().splitlines(keepends=True), "skill/SKILL.md", "skill/SKILL.evolved.md")))
            shutil.copy2(produced, staged_skill)
        if evolved.exists():
            shutil.copy2(evolved, bak)
        else:
            absent.write_text("")
        write_journal("swapping", tag)
        _fault("staged")
        # 2. swap results/, then the skill
        _rename(TRACKED_RES, old)
        _fault("after_old_rename")
        _rename(new, TRACKED_RES)
        _fault("before_skill_replace")
        if staged_skill.exists():
            _replace(staged_skill, evolved)
        elif evolved.exists():
            evolved.unlink()
        _fault("before_commit")
        write_journal("committed", tag)
        _fault("committed")
    except Crash:
        raise
    except BaseException as e:
        why = recover()  # journal is still 'swapping' (or absent): this rolls back from the files on disk
        print(f"promote failed and was rolled back: {type(e).__name__}: {e}" + (f"; {why}" if why else ""), file=sys.stderr)
        return 1
    # 3. cleanup: move the skill backup into the old set, retire it with one rename, then delete
    for x, name in ((bak, ".skill_backup"), (absent, ".skill_absent")):
        if x.exists():
            os.rename(x, old / name)
    _fault("bak_moved")
    os.rename(old, trash)
    _fault("trashed")
    shutil.rmtree(trash)
    journal.unlink(missing_ok=True)
    _fsync_dir(parent)
    print(f"promoted complete run {R['run_id']} -> {TRACKED_RES}"); return 0


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="all"); ap.add_argument("--promote", action="store_true")
    a = ap.parse_args(argv)
    if a.promote:
        return promote()
    TMPD.mkdir(exist_ok=True)
    log = lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)
    stages = list(STAGES) if a.stage == "all" else [a.stage]
    # --stage all starts clean; a single stage joins the current run only if the inputs are unchanged
    rid = (current_run() if a.stage != "all" else None) or new_run(clear=True)  # any new run id starts clean
    inputs = input_hashes()
    failed, home_changed = [], {}
    for st in stages:
        rec = {"stage": st, "run_id": rid, "inputs": inputs, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        for name in [f"stage_{st}.json", *STAGE_FILES.get(st, [])]:  # never reuse this stage's old outputs
            x = RES / name
            if x.is_dir():
                shutil.rmtree(x)
            elif x.exists():
                x.unlink()
        before = snap()
        mw = MemWatch(); mw.start()
        try:
            rec["ollama_ps_at_start"] = wait_ollama(log)
            m = meminfo()
            if m["MemTotal"] - m["MemAvailable"] > MEM_CAP_GIB - 25:
                raise RuntimeError(f"memory too high to start {st}: used {m['MemTotal']-m['MemAvailable']} GiB")
            log(f"stage {st} start"); t0 = time.time()
            rec["result"] = STAGES[st]()
            rec["wall_s"] = round(time.time() - t0, 1)
        except BaseException as e:  # failures and timeouts both fail the run
            rec["error"] = f"{type(e).__name__}: {str(e)[-1500:]}"; failed.append(st); log(f"stage {st} ERROR {rec['error']}")
            if isinstance(e, KeyboardInterrupt):
                raise
        finally:
            mw.stop = True
            diff = home_diff(before, snap())
            rec["guard"] = {"real_home_untouched": not diff, "changed": diff, "watched": list(WATCH),
                            "min_MemAvailable_GiB": mw.min_avail, "max_used_GiB": mw.max_used, "cap_GiB": MEM_CAP_GIB}
            if diff:
                home_changed[st] = diff
            (RES / f"stage_{st}.json").write_text(rel(json.dumps(rec, indent=1)))
    build_results()
    if home_changed:
        log(f"REAL HOME CHANGED: {home_changed}"); return 3
    if failed:
        log(f"stages failed: {failed}"); return 1
    log(f"ok; outputs in {RES} (run --promote to copy into results/)"); return 0


if __name__ == "__main__":
    sys.exit(main())
