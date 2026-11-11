# Lane graph - information architecture

**Cite:** operator Runs view. Implementation: `pfylib/lane_graph.py`, `scripts/pfy-board.py` (`GET /lanes`, `GET /lanes/detail`), `gui/operator/frontend/lane-graph.js`.
**Read with:** [LOOP-243-IA.md](LOOP-243-IA.md). Loop stays the launch front door. This view is what already ran.

UI: Design-in-loop. Pack in docs/design/ before product UI. Never ask what we know. Levers stay contextual to the current view.

---

## Where it lives

```
pfy (native window)
├── Loop     product front door (unchanged)
├── Runs     this slice. One click under Loop
├── Engine
├── Stage
├── Attach
├── Tools
└── Org
```

Runs is a sibling tab directly under Loop, not a block inside the Loop canvas and not a new settings page.

Loop already holds the launch journey: where the next session can run, how hard it is, which modules ride along, Launch session. Model choice for that next session lives on that same canvas. A graph of finished lanes would bury both.

Runs is the same job one step later: see the lanes that ran, which route they took, and open the trace. One nav button under Loop. No second product area.

---

## Primary journey

1. Open **Runs** (the tab under Loop).
2. See the lane graph for the recent window (default last 7 days). Left to right: parent lane to child lane.
3. Hover a lane. The tooltip is the summary: task, model, provider, route, status, duration, cost, iteration.
4. Click the lane. The outline opens beside the graph: ordered steps, then tabs **Reasoning**, **File ops**, **MCP calls**, **Tool calls**.
5. **Open in Phoenix** opens that trace in the local Phoenix UI.

Edge color is the child lane's model route: local green `#3dd68c`, cloud blue `#4d8dff`, mixed amber `#e6c15a`, unknown grey. A retry or eval loop is a dashed curve back to the parent, labeled `retry N` or `eval loop N`. The legend sits on this view.

The graph polls `GET /lanes` every 5 seconds only while Runs is visible. Selection and zoom stay put. Nodes and edges update in place.

---

## Contextual levers

On this view only:

- Hover, click, tab, **Open in Phoenix**.
- The legend (not a control).

No endpoint field, no project picker, no time-range form, no settings link. Changing where the next session runs stays on Loop.

---

## What we already know

| Fact | Source | We do not ask |
|------|--------|----------------|
| Phoenix base URL | `PFY_PHOENIX_URL`, else `http://127.0.0.1:6006` | no URL field |
| Project name | `PFY_PHOENIX_PROJECT`, else `deanery` | no project field |
| Loopback only | same rule as the Phoenix unit | refuse any other host |
| Window | `PFY_LANE_GRAPH_HOURS`, else 168 (7 days); `0` means no time filter | no range picker |
| Trace link | `GET /v1/projects/{name}` once per fetch, then `/projects/{global id}/traces/{trace_id}` | no "paste a trace id" box |

Span attrs we read when present: `deanery.lane_id`, `deanery.parent_lane`, `deanery.task_class`, `deanery.route`, `deanery.iteration`, `llm.model_name`, `llm.provider`, `llm.token_count.*`, `llm.cost.total` (or the same cost family), `openinference.span.kind`, `tool.name`. MCP: `deanery.mcp` plus `deanery.mcp.server` and `deanery.mcp.tool`. File ops: child span `file_op` with `deanery.file.path` and `deanery.file.op` (never contents). Reasoning: event or child span `reasoning` with `deanery.reasoning.summary`.

Missing keys fall back: route from `llm.provider`, lane from the root span name, parent from the parent span's lane. Absent cost is null. Absent optional fields do not error.

---

## Empty and down

| State | Paint |
|-------|--------|
| Phoenix up, no spans in the window | One line: `No lane runs in the last 7 days.` |
| Phoenix down, timeout, or bad response | One line: `Phoenix is down. Start it with scripts/phoenix_service.sh enable` |
| Non-loopback `PFY_PHOENIX_URL` | One line that names the refusal and the same start command. No request is sent. |
| Detail for a lane with no rows in a tab | The tab says `None`. |

No stack trace, no adapter lecture, no raw JSON in the window. `GET /lanes` still returns HTTP 200 with `{"ok": false, "why": "..."}` so the window can paint that line.

---

## Out of this slice

- Writing spans (the tracing lane owns that).
- A second trace store or a disk cache. The process may keep the last Phoenix response in memory.
- Editing Loop's launch controls, model choice, or Engine.
- Asking the operator for anything in the table above.
