"""Toolset x harness matrix, plan and apply (ADR-0017).

A toolset is declared once in ``data/toolsets.json`` and applied to any
harness in ``data/harnesses.json``. ``matrix()`` is the honest status grid;
``plan()`` turns one cell into a concrete apply plan (env dict, files to
write, MCP/config fragments, brief text) or an honest STUB / FAIL with a next
step; ``apply()`` writes a plan only with ``yes=True`` and only under
``$PFY_STATE_DIR`` or the harness's own config dir.

Every ``plan()`` body imports its issue-numbered script through ``_legacy``
and translates that script's existing "apply env / write brief / MCP
fragment" behaviour into a plan -- no decision logic is duplicated and no
behaviour is added (T-0121). Reference toolset: **jev** (ADR-0016).

File modes understood by ``apply()``: ``write``, ``append-marker`` (idempotent
``<!-- pfy-toolset:<id> -->`` block), ``json-merge`` (list union / dict update),
``symlink`` (via ``pfy_attach_mode_208._link_skill``) and ``legacy`` (call the
named script function, e.g. ``pfy_code_graph_215.apply_grok_mcp``, because its
TOML upsert / merge_config.py step has no declarative equivalent here).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import _legacy, registry

STATUSES = registry.STATUSES
LANES = registry.LANES

MARK_BEGIN = "<!-- pfy-toolset:%s begin -->"
MARK_END = "<!-- pfy-toolset:%s end -->"

def harness_home(hid: str, root_dir: Path | None = None) -> Path | None:
    """Harness-native config dir from ``harnesses.json[].attach.config_dir``.

    Only these dirs, plus ``$PFY_STATE_DIR``, are writable by ``apply()``.
    """
    return registry.harness_home(hid, root_dir)


# ---------------------------------------------------------------- matrix ---

def matrix(root_dir: Path | None = None) -> list[dict]:
    """One row per toolset x harness cell: toolset, harness, status, how, lanes."""
    hids = registry.harness_ids(root_dir)
    rows: list[dict] = []
    for t in registry.toolset_rows(root_dir):
        impl = t.get("implementation") or {}
        for hid in hids:
            cell = impl.get(hid) or {}
            rows.append(
                {
                    "toolset": t.get("id"),
                    "harness": hid,
                    "status": cell.get("status") or "stub",
                    "how": cell.get("how") or "",
                    "lanes": list(t.get("lanes") or []),
                    "catalog_tool": t.get("catalog_tool"),
                }
            )
    return rows


def matrix_grid(root_dir: Path | None = None) -> tuple[list[str], list[list[str]]]:
    """(header, rows) for a compact table: toolset then one column per harness."""
    hids = registry.harness_ids(root_dir)
    header = ["TOOLSET"] + hids
    grid: list[list[str]] = []
    for t in registry.toolset_rows(root_dir):
        impl = t.get("implementation") or {}
        grid.append([str(t.get("id"))] + [str((impl.get(h) or {}).get("status") or "stub") for h in hids])
    return header, grid


def matrix_text(root_dir: Path | None = None) -> str:
    header, grid = matrix_grid(root_dir)
    widths = [max(len(str(r[i])) for r in [header] + grid) for i in range(len(header))]
    lines = ["  ".join(str(c).ljust(widths[i]) for i, c in enumerate(header))]
    lines.append("  ".join("-" * w for w in widths))
    for r in grid:
        lines.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
    counts = {s: 0 for s in STATUSES}
    for row in matrix(root_dir):
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    lines.append("")
    lines.append(
        "cells: %d · implemented %d · partial %d · stub %d   (IMPLEMENTATION column, not live STATUS; ADR-0017)"
        % (sum(counts.values()), counts["implemented"], counts["partial"], counts["stub"])
    )
    return "\n".join(lines)


def cell(tid: str, hid: str, root_dir: Path | None = None) -> dict | None:
    t = registry.toolset(tid, root_dir)
    if t is None:
        return None
    return (t.get("implementation") or {}).get(hid)


# ------------------------------------------------------------------ plan ---

def _result(kind: str, tid: str, hid: str, lane: str | None, **extra) -> dict:
    out = {
        "ok": kind == "READY",
        "live": kind,
        "toolset": tid,
        "harness": hid,
        "lane": lane,
        "status": extra.pop("status", None),
        "env": {},
        "files": [],
        "mcp": [],
        "brief": "",
        "commands": [],
        "next_step": "",
        "copy": "",
    }
    out.update(extra)
    if not out["copy"]:
        tail = (" · " + out["next_step"]) if out["next_step"] else ""
        out["copy"] = "%s toolset %s → %s%s" % (kind, tid, hid, tail)
    return out


def plan(
    tid: str,
    hid: str,
    lane: str | None = None,
    *,
    root_dir: Path | None = None,
    state: Path | None = None,
) -> dict:
    """Concrete apply plan, or honest STUB / FAIL with next step. Never writes."""
    t = registry.toolset(tid, root_dir)
    if t is None:
        return _result(
            "FAIL", tid, hid, lane,
            error="unknown toolset %r" % tid,
            next_step="pick one of: %s" % ", ".join(registry.toolset_ids(root_dir)),
        )
    hids = registry.harness_ids(root_dir)
    if hid not in hids:
        return _result(
            "FAIL", tid, hid, lane,
            error="unknown harness %r" % hid,
            next_step="pick one of: %s" % ", ".join(hids),
        )
    lanes = list(t.get("lanes") or [])
    if lane is None:
        lane = "local" if "local" in lanes else lanes[0]
    if lane not in LANES:
        return _result("FAIL", tid, hid, lane, error="unknown lane %r" % lane, next_step="use --lane local|cloud")
    if lane not in lanes:
        return _result(
            "FAIL", tid, hid, lane,
            error="toolset %s has no %s lane" % (tid, lane),
            next_step="use --lane %s" % "|".join(lanes),
            status=(cell(tid, hid, root_dir) or {}).get("status"),
        )
    c = cell(tid, hid, root_dir) or {"status": "stub", "how": "stub: no cell"}
    status = c.get("status") or "stub"
    if status == "stub":
        return _result(
            "STUB", tid, hid, lane,
            status=status,
            how=c.get("how") or "",
            next_step=_stub_next(t, hid, root_dir),
        )
    planner = _PLANNERS.get(tid)
    if planner is not None:
        return planner(t, hid, lane, status, root_dir=root_dir, state=state)
    # A toolset row without a planner: report the status the script earns, do not fake a plan.
    prov = t.get("provides") or {}
    return _result(
        "STUB", tid, hid, lane,
        status=status,
        how=c.get("how") or "",
        ported=False,
        commands=list(prov.get("commands") or []),
        next_step="no _plan_%s in pfylib/toolsets.py · today: %s · via %s"
        % (tid.replace("-", "_"), " | ".join(prov.get("commands") or []) or "n/a", t.get("source") or "?"),
        copy="STUB plan -- %s on %s is %s via %s; no pfylib planner"
        % (tid, hid, status, t.get("source") or "?"),
    )


def _sid(hid: str, root_dir: Path | None) -> str:
    """Session id the scripts use for this harness (``claude`` for ``claude-code``)."""
    prof = registry.attach_profile(hid, root_dir)
    return str(prof["session_id"]) if prof else hid


def _ready(t: dict, hid: str, lane: str, status: str, *, env: dict, files: list, brief: str, root_dir: Path | None, mcp=None, note: str = "", next_step: str = "", **extra) -> dict:
    tid = str(t["id"])
    how = (cell(tid, hid, root_dir) or {}).get("how") or ""
    if not note and status != "implemented":
        note = "partial: %s" % how
    return _result(
        "READY", tid, hid, lane,
        status=status,
        env=env,
        files=files,
        mcp=list(mcp or []),
        brief=brief,
        commands=list((t.get("provides") or {}).get("commands") or []),
        note=note,
        next_step=next_step,
        copy="READY plan -- %s → %s (%s, %s) · %d file(s) · %d env" % (tid, hid, lane, status, len(files), len(env)),
        **extra,
    )


def _stub_next(t: dict, hid: str, root_dir: Path | None) -> str:
    h = registry.harness(hid, root_dir) or {}
    issue = h.get("github_issue")
    bits = ["no config surface wired for %s" % hid]
    if issue:
        bits.append("harness adapter issue #%s" % issue)
    impl_h = [x for x in registry.harness_ids(root_dir) if ((t.get("implementation") or {}).get(x) or {}).get("status") == "implemented"]
    if impl_h:
        bits.append("implemented today on: %s" % ", ".join(impl_h))
    return " · ".join(bits)


# --------------------------------------------------------------- jev ref ---

def _jev_brief(jev, hid: str, lane: str, path: str, state: Path, gate: float) -> str:
    invoke = {
        "grok": "Grok: skill `pfy-jev-decision` is in `GROK_HOME/skills`; shell out to `./pfy decision …` for a typed Choice/Score.",
        "opencode": "OpenCode: this brief is listed under `instructions` in `$OPENCODE_CONFIG`; shell out to `./pfy decision …`.",
        "claude-code": "Claude Code: this brief is appended to `$PFY_ATTACH_AGENTS` and to `CLAUDE.md` under `CLAUDE_CONFIG_DIR`; shell out to `./pfy decision …`.",
        "codex": "Codex: this brief is appended to `$PFY_ATTACH_AGENTS` and to `AGENTS.md` under `CODEX_HOME`; shell out to `./pfy decision …`.",
        "hermes": "Hermes: read `$PFY_ATTACH_AGENTS` (env only; no hermes-native surface is written -- partial).",
    }.get(hid, "Read `$PFY_TOOLSET_BRIEF`.")
    lane_line = (
        "Lane **local**: engine `%s` (%s). No cloud call." % (path, jev.path_paint(path))
        if lane == "local"
        else "Lane **cloud**: TypeSafe `%s` at `%s` (key from TYPESAFE_API_KEY). Budgeted by `./pfy hedge`." % (jev.typesafe_model(), jev.TYPESAFE_URL)
    )
    lines = [
        "# Toolset: jev -- decision layer (typed Choice/Score)",
        "",
        "Applied by `./pfy toolset apply jev --harness %s --lane %s` (ADR-0017; decision semantics ADR-0016, #230)." % (hid, lane),
        "",
        "- %s" % jev.CHIP_DECISION,
        "- %s" % jev.CHIP_HONEST,
        "- %s" % jev.CHIP_CORE,
        "- Confidence is a **margin** chip (`%s` / `%s`), never percent-correct. Gate: %.2f -> below gate the layer FAILs and escalates; no silent auto-act." % (jev.CHIP_CONF_OK, jev.CHIP_CONF_LOW, gate),
        "- %s" % lane_line,
        "",
        "## Use in this session",
        "",
        "- `./pfy decision route`   -> Choice over live models/lane/harness/toolset (options rebuilt from live state).",
        "- `./pfy decision compact` -> keep|truncate|drop per stale tool result; user text is kept verbatim.",
        "- `./pfy decision queue put|next` -> local JSONL queue at `%s`." % (state / jev.QUEUE_FILE),
        "- State: `%s`." % (state / jev.STATE_FILE),
        "",
        "## Harness",
        "",
        invoke,
        "",
        "Do not paint Jev as chat. Do not equate decision with Gab `auto` or local recommend order.",
    ]
    return "\n".join(lines) + "\n"


def _jev_skill_md(brief: str) -> str:
    front = (
        "---\n"
        "name: pfy-jev-decision\n"
        "description: Use the pfy-deanery Jev-style decision layer (typed Choice/Score, margin confidence) via ./pfy decision. Applied by ./pfy toolset apply jev --harness grok (ADR-0017).\n"
        "---\n\n"
    )
    return front + brief


def _plan_jev(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    jev = _legacy.jev(root_dir)
    st = registry.state_dir(state)
    gate = jev.conf_gate()
    if lane == "cloud":
        path = "typesafe"
        if not jev.typesafe_key():
            return _result(
                "FAIL", t["id"], hid, lane,
                status=status,
                error="TypeSafe key missing (cloud lane)",
                next_step=jev.NEXT_KEY + " · or --lane local",
            )
    else:
        path = jev.PRIMARY_LOCAL
    brief_path = st / str((t.get("provides") or {}).get("brief") or "toolset-jev-brief.md")
    brief = _jev_brief(jev, hid, lane, path, st, gate)
    env = {
        "PFY_DECISION_PATH": path,
        "PFY_DECISION_STATE": str(st / jev.STATE_FILE),
        "PFY_DECISION_QUEUE": str(st / jev.QUEUE_FILE),
        "PFY_JEV_CONF_GATE": "%.2f" % gate,
        "PFY_TOOLSET_BRIEF": str(brief_path),
    }
    files: list[dict] = [{"path": str(brief_path), "mode": "write", "content": brief}]
    agents = st / "attach-agents.md"
    if hid == "grok":
        home = harness_home("grok", root_dir)
        files.append({"path": str(home / "skills" / "pfy-jev-decision" / "SKILL.md"), "mode": "write", "content": _jev_skill_md(brief)})
    elif hid == "opencode":
        files.append({"path": str(st / "opencode.json"), "mode": "json-merge", "fragment": {"instructions": [str(brief_path)]}})
    elif hid == "claude-code":
        env["PFY_ATTACH_AGENTS"] = str(agents)
        files.append({"path": str(agents), "mode": "append-marker", "content": brief})
        files.append({"path": str(harness_home("claude-code", root_dir) / "CLAUDE.md"), "mode": "append-marker", "content": brief})
    elif hid == "codex":
        env["PFY_ATTACH_AGENTS"] = str(agents)
        files.append({"path": str(agents), "mode": "append-marker", "content": brief})
        files.append({"path": str(harness_home("codex", root_dir) / "AGENTS.md"), "mode": "append-marker", "content": brief})
    elif hid == "hermes":
        env["PFY_ATTACH_AGENTS"] = str(agents)
        files.append({"path": str(agents), "mode": "append-marker", "content": brief})
    commands = list((t.get("provides") or {}).get("commands") or [])
    note = "" if status == "implemented" else "partial: %s" % ((cell("jev", hid, root_dir) or {}).get("how") or "")
    return _result(
        "READY", t["id"], hid, lane,
        status=status,
        env=env,
        files=files,
        mcp=[],
        brief=brief,
        commands=commands,
        note=note,
        next_step="" if status == "implemented" else "hermes-native config surface unknown (partial)",
        copy="READY plan -- jev → %s (%s, %s) · %d file(s) · %d env" % (hid, lane, status, len(files), len(env)),
    )


# -------------------------------------------------------------------- gab ---

GAB_KEY_PLACEHOLDER = "${GAB_API_KEY}"  # same placeholder pfy_gab_228.cloud_lane persists; the plan never carries the key


_GAB_ENV_KEYS = (
    "OPENAI_BASE_URL", "OPENAI_API_KEY", "GAB_API_KEY", "PFY_GAB_MODEL",
    "LOCAL_CODER_MODEL", "PFY_CLOUD_PROVIDER", "PFY_CLOUD_ENDPOINT",
)


def _plan_gab(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    """``./pfy start gab`` env (pfy_gab_228.apply_cloud_env): cloud lane only, key-gated, env only."""
    gab = _legacy.gab(root_dir)
    model = os.environ.get("PFY_GAB_MODEL") or "auto"
    # apply_cloud_env treats a falsy env as os.environ; pass a dummy so we do not dump the host env.
    raw, err = gab.apply_cloud_env({"_pfy": "1"}, model=model)
    if raw is None:
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="GAB_API_KEY missing (cloud lane)",
            next_step=(err or {}).get("next_step") or gab.NEXT_KEY,
            commands=list((t.get("provides") or {}).get("commands") or []),
        )
    env = {k: (GAB_KEY_PLACEHOLDER if k in ("OPENAI_API_KEY", "GAB_API_KEY") else raw[k]) for k in _GAB_ENV_KEYS if k in raw}
    how = (cell("gab", hid, root_dir) or {}).get("how") or ""
    return _ready(
        t, hid, lane, status, env=env, files=[], brief="", root_dir=root_dir,
        note="partial: %s · %s" % (how, gab.CHIP_HONEST),
        next_step="open the TUI with this env (no %s-native provider fragment is written)" % hid,
    )


# ------------------------------------------------------------ opencontext ---

def _plan_opencontext(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    """Attach child env (pfy_opencontext_205.apply_child_env): env only; missing ``oc`` is FAIL+install."""
    oc = _legacy.opencontext(root_dir)
    env = oc.apply_child_env({})
    if not env.get("OPENCONTEXT_BIN"):
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="oc missing",
            next_step=oc.NEXT_INSTALL,
            commands=list((t.get("provides") or {}).get("commands") or []),
        )
    return _ready(
        t, hid, lane, status, env=env, files=[], brief="", root_dir=root_dir,
        mcp=["opencontext (oc mcp)"],
        next_step="MCP fragment not written by attach (see `./pfy context` output for the Grok/OpenCode lines)",
    )


# ------------------------------------------------------------- code-graph ---

def _code_graph_mcp_fragment(cg, gpath: str, bin_path: str) -> dict:
    """Run pfy_code_graph_215.decorate_opencode_config against a scratch opencode.json to get its exact fragment."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="pfylib-cg-") as tmp:
        scratch = Path(tmp)
        (scratch / "opencode.json").write_text("{}\n", encoding="utf-8")
        ok, err = cg.decorate_opencode_config(scratch, gpath, bin_path)
        if not ok:
            raise RuntimeError(err or "decorate_opencode_config failed")
        return {"mcp": json.loads((scratch / "opencode.json").read_text(encoding="utf-8")).get("mcp") or {}}


def _plan_code_graph(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    """pfy_code_graph_215.prepare as a plan: Axon preferred, codebase-memory equivalent, never claim Axon."""
    cg = _legacy.code_graph(root_dir)
    st = registry.state_dir(state)
    sid = _sid(hid, root_dir)
    commands = list((t.get("provides") or {}).get("commands") or [])
    resolved = cg.resolve()
    if not resolved.get("ok"):
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error=resolved.get("error") or "code-graph unwired",
            next_step=resolved.get("next_step") or cg.NEXT_BOTH,
            commands=commands,
        )
    gpath, bin_path = resolved["graph_path"], resolved["bin"]
    if hid in ("hermes", "codex", "claude-code") and gpath != cg.PATH_AXON:
        # Same gate and wording as cg.prepare() (returns before any write on this path).
        who = {"hermes": "Hermes", "codex": "Codex"}.get(hid, "Claude")
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="code-graph unwired for %s (no Axon CLI; MCP-only)" % who,
            next_step=cg.NEXT_HERMES,
            commands=commands,
            graph_path=gpath,
        )
    env = {"PFY_GRAPH_PATH": gpath, "PFY_CODE_GRAPH": gpath}
    if gpath == cg.PATH_AXON:
        env["AXON_BIN"] = bin_path
    else:
        env["CODEBASE_MEMORY_MCP"] = bin_path
        env["PFY_MCP"] = "1"
    handoff = cg._handoff_text(sid, gpath, bin_path)
    env["PFY_GRAPH_HANDOFF"] = str(st / cg.HANDOFF_FILE)
    env["PFY_GRAPH_PROMPT"] = str(st / cg.PROMPT_FILE)
    files: list[dict] = [
        {"path": str(st / cg.PATH_FILE), "mode": "write", "content": gpath + "\n"},
        {"path": str(st / cg.HANDOFF_FILE), "mode": "write", "content": handoff},
        {"path": str(st / cg.PROMPT_FILE), "mode": "write", "content": cg._prompt_text(gpath)},
    ]
    mcp: list[str] = []
    if hid in ("opencode", "grok"):
        fragment = _code_graph_mcp_fragment(cg, gpath, bin_path)
        mcp = list(fragment["mcp"])
        files.append({"path": str(st / "opencode.json"), "mode": "json-merge", "fragment": fragment})
    if hid == "grok":
        home = harness_home("grok", root_dir)
        files.append(
            {
                "path": str(home / "config.toml"),
                "mode": "legacy",
                "via": "pfy_code_graph_215.apply_grok_mcp",
                "args": [gpath, bin_path],
                "also": [str(st / "grok-config.toml")],
                "content": "[mcp_servers.axon] upsert" if gpath == cg.PATH_AXON else "bootstrap/grok-cli/scripts/merge_config.py (mcp_servers.codebase-memory)",
            }
        )
    return _ready(
        t, hid, lane, status, env=env, files=files, brief=handoff, root_dir=root_dir, mcp=mcp,
        graph_path=gpath,
        graph_copy=resolved.get("copy") or "",
        next_step="" if status == "implemented" else "env + handoff only (Axon CLI present); no %s-native MCP surface" % hid,
    )


# ---------------------------------------------------------- orchestration ---

def _plan_orchestration(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    """pfy_attach_mode_208.prepare(mode=orchestration) as a plan: agent-loops skill links + mode handoff files + env."""
    m = _legacy.attach_mode(root_dir)
    st = registry.state_dir(state)
    root = registry.root(root_dir)
    sid = _sid(hid, root_dir)
    commands = list((t.get("provides") or {}).get("commands") or [])
    src = m._agent_loops_skill(root)
    if src is None:
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="orchestration unwired -- agent-loops skill missing",
            next_step=m.NEXT_SETUP,
            commands=commands,
        )
    handoff = m._handoff_text("orchestration", sid)
    prompt = m._prompt_text("orchestration")
    files: list[dict] = [
        {"path": str(st / m.MODE_FILE), "mode": "write", "content": "orchestration\n"},
        {"path": str(st / m.HANDOFF_FILE), "mode": "write", "content": handoff},
        {"path": str(st / m.PROMPT_FILE), "mode": "write", "content": prompt},
        {"path": str(st / m.AGENTS_FILE), "mode": "write", "content": handoff},
        {"path": str(st / "opencode-skills" / "agent-loops"), "mode": "symlink", "target": str(src)},
        {"path": str(st / "attach-skills" / "agent-loops"), "mode": "symlink", "target": str(src)},
    ]
    grok_home = harness_home("grok", root_dir)
    if hid == "grok" and grok_home is not None:
        # 208.prepare also links GROK_HOME for other harnesses as an attach-time
        # side effect; toolset apply is per-harness and only writes that harness's home.
        files.append({"path": str(grok_home / "skills" / "agent-loops"), "mode": "symlink", "target": str(src)})
    env = {
        "PFY_ATTACH_MODE": "orchestration",
        "PFY_ATTACH_HANDOFF": str(st / m.HANDOFF_FILE),
        "PFY_ATTACH_PROMPT": str(st / m.PROMPT_FILE),
        "PFY_ATTACH_AGENTS": str(st / m.AGENTS_FILE),
        "PFY_ATTACH_SKILL": "agent-loops",
        "OPENCODE_SKILLS": str(st / "opencode-skills"),
    }
    return _ready(
        t, hid, lane, status, env=env, files=files, brief=handoff, root_dir=root_dir,
        next_step=("" if status == "implemented" else "no %s-native skills dir; brief via PFY_ATTACH_AGENTS" % hid),
        runtime_note="PFY_LOOP_CARD/EVIDENCE/PROMPT + PFY_MONITOR_NOTE are written by pfy_orchestration_213 --start at attach (needs a live local engine)",
    )


# ------------------------------------------------------------ catalog-ask ---

def _plan_catalog_ask(t: dict, hid: str, lane: str, status: str, *, root_dir: Path | None, state: Path | None) -> dict:
    """pfy_catalog_ask_queue_209.apply_child_env as a plan: prompt/handoff artifact from the last `./pfy catalog ask`."""
    ca = _legacy.catalog_ask(root_dir)
    st = registry.state_dir(state)
    sid = _sid(hid, root_dir)
    commands = list((t.get("provides") or {}).get("commands") or [])
    if sid not in ca.SIDECAR_OK:
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="%s is not a catalog-ask sidecar" % hid,
            next_step=ca.NEXT_ATTACH,
            commands=commands,
        )
    env = ca.apply_child_env({}, st)
    if not env.get("PFY_CATALOG_ASK_PROMPT"):
        return _result(
            "FAIL", t["id"], hid, lane,
            status=status,
            error="no pending catalog ask (no %s in %s)" % (ca.PROMPT_FILE, st),
            next_step="./pfy catalog ask <name>",
            commands=commands,
        )
    brief = ca._read(Path(env["PFY_CATALOG_ASK_PROMPT"]))
    return _ready(
        t, hid, lane, status, env=env, files=[], brief=brief, root_dir=root_dir,
        next_step="paste the prompt into the attached TUI or rely on auto-handoff at next Attach",
    )


_PLANNERS = {
    "jev": _plan_jev,
    "gab": _plan_gab,
    "opencontext": _plan_opencontext,
    "code-graph": _plan_code_graph,
    "orchestration": _plan_orchestration,
    "catalog-ask": _plan_catalog_ask,
}


# ----------------------------------------------------------------- apply ---

def _allowed_roots(hid: str, state: Path | None, root_dir: Path | None = None) -> list[Path]:
    roots = [registry.state_dir(state).resolve()]
    home = harness_home(hid, root_dir)
    if home is not None:
        roots.append(home.expanduser().resolve())
    return roots


def _under(path: Path, roots: list[Path]) -> bool:
    p = path.expanduser().resolve()
    return any(p == r or r in p.parents for r in roots)


def _write_marker(path: Path, tid: str, content: str) -> str:
    begin, end = MARK_BEGIN % tid, MARK_END % tid
    block = "%s\n%s\n%s\n" % (begin, content.rstrip("\n"), end)
    existing = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if begin in existing and end in existing:
        head = existing.split(begin, 1)[0]
        tail = existing.split(end, 1)[1]
        new = head + block + tail.lstrip("\n")
        action = "replaced"
    else:
        new = (existing.rstrip("\n") + "\n\n" if existing.strip() else "") + block
        action = "appended"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return action


def _merge_json(path: Path, fragment: dict) -> str:
    cfg: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            cfg = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return "FAIL: existing %s is not valid JSON" % path
    for key, val in fragment.items():
        if isinstance(val, list):
            cur = cfg.get(key) if isinstance(cfg.get(key), list) else []
            for item in val:
                if item not in cur:
                    cur.append(item)
            cfg[key] = cur
        elif isinstance(val, dict):
            cur = cfg.get(key) if isinstance(cfg.get(key), dict) else {}
            cur.update(val)
            cfg[key] = cur
        else:
            cfg[key] = val
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return "merged"


def _apply_symlink(path: Path, target: str, root_dir: Path | None) -> str:
    ok, err = _legacy.attach_mode(root_dir)._link_skill(path.parent, Path(target), path.name)
    return "linked" if ok else "FAIL: %s" % (err or "symlink failed")


def _apply_legacy(f: dict, root_dir: Path | None, state: Path | None) -> str:
    via = str(f.get("via") or "")
    args = list(f.get("args") or [])
    if via == "pfy_code_graph_215.apply_grok_mcp":
        ok, err = _legacy.code_graph(root_dir).apply_grok_mcp(registry.root(root_dir), registry.state_dir(state), *args)
        return "applied via %s" % via if ok else "FAIL: %s" % (err or via)
    return "FAIL: unknown legacy applier %s" % (via or "(none)")


def apply(p: dict, *, yes: bool = False, state: Path | None = None, root_dir: Path | None = None) -> dict:
    """Write a plan's files. Without ``yes`` returns the plan marked dry_run."""
    out = dict(p)
    if not p.get("ok"):
        out["applied"] = []
        out["dry_run"] = not yes
        return out
    if not yes:
        out["dry_run"] = True
        out["applied"] = []
        out["copy"] = "DRY-RUN %s · pass --yes to write %d file(s)" % (p.get("copy", ""), len(p.get("files") or []))
        return out
    tid = str(p.get("toolset"))
    hid = str(p.get("harness"))
    roots = _allowed_roots(hid, state, root_dir)
    applied: list[dict] = []
    failed: list[dict] = []
    for f in p.get("files") or []:
        path = Path(str(f.get("path")))
        if not _under(path, roots):
            failed.append({"path": str(path), "result": "refused: outside %s" % ", ".join(str(r) for r in roots)})
            continue
        mode = f.get("mode") or "write"
        try:
            if mode == "write":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(f.get("content") or ""), encoding="utf-8")
                res = "written"
            elif mode == "append-marker":
                res = _write_marker(path, tid, str(f.get("content") or ""))
            elif mode == "json-merge":
                res = _merge_json(path, dict(f.get("fragment") or {}))
            elif mode == "symlink":
                res = _apply_symlink(path, str(f.get("target") or ""), root_dir)
            elif mode == "legacy":
                res = _apply_legacy(f, root_dir, state)
            else:
                res = "FAIL: unknown mode %s" % mode
        except OSError as e:
            res = "FAIL: %s" % str(e)[:160]
        (failed if res.startswith("FAIL") else applied).append({"path": str(path), "result": res})
    out["applied"] = applied
    out["failed"] = failed
    out["dry_run"] = False
    if failed:
        out["ok"] = False
        out["live"] = "FAIL"
        out["copy"] = "FAIL apply -- %d of %d file(s) failed" % (len(failed), len(applied) + len(failed))
        out["next_step"] = failed[0]["result"]
    else:
        out["copy"] = "READY applied %s → %s · %d file(s)" % (tid, hid, len(applied))
    return out


def export_env_lines(p: dict) -> list[str]:
    return ["export %s=%s" % (k, json.dumps(str(v))) for k, v in sorted((p.get("env") or {}).items())]
