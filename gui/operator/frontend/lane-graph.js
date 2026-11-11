/* Runs lane graph. Design: docs/design/LANE-GRAPH-IA.md */
(function () {
  var POLL_MS = 5000;
  var DOWN = "Phoenix is down. Start it with scripts/phoenix_service.sh enable";
  var COLORS = {local: "#3dd68c", cloud: "#4d8dff", mixed: "#e6c15a", unknown: "#7d8796"};
  var cy = null;
  var timer = null;
  var refreshing = false;
  var didFit = false;
  var selectedId = null;
  var activeTab = "reasoning";
  var autoLane = null;
  var lastDetailKey = "";

  var TAB_DEFS = [
    ["reasoning", "Reasoning"],
    ["file_ops", "File ops"],
    ["mcp_calls", "MCP calls"],
    ["tool_calls", "Tool calls"]
  ];

  function $(id) { return document.getElementById(id); }

  function routeOf(value) {
    return COLORS[value] ? value : "unknown";
  }

  function fmtDur(ms) {
    if (ms === null || ms === undefined || ms === "") return "n/a";
    var n = Number(ms);
    if (!isFinite(n)) return "n/a";
    if (n < 1000) return Math.round(n) + "ms";
    return (n / 1000).toFixed(1) + "s";
  }

  function fmtCost(value) {
    if (value === null || value === undefined || value === "") return "n/a";
    var n = Number(value);
    if (!isFinite(n)) return "n/a";
    return "$" + n.toFixed(4);
  }

  function emptyNote(hours) {
    var n = Number(hours);
    if (!n) return "No lane runs yet.";
    if (n % 24 === 0) {
      var days = n / 24;
      return "No lane runs in the last " + days + (days === 1 ? " day." : " days.");
    }
    return "No lane runs in the last " + n + " hours.";
  }

  function setNote(text) {
    var el = $("lane-note");
    if (!el) return;
    el.textContent = text || "";
    el.className = text ? "why" : "why";
  }

  function viewOn() {
    var el = $("view-runs");
    return !!(el && el.classList.contains("on"));
  }

  function ensure(parent, id, tag, className) {
    var el = $(id);
    if (el) return el;
    el = document.createElement(tag);
    el.id = id;
    if (className) el.className = className;
    parent.appendChild(el);
    return el;
  }

  function ensureChrome() {
    var host = $("view-runs") || document.body;
    ensure(host, "lane-note", "p", "why");
    var legend = $("lane-legend");
    if (!legend) {
      legend = document.createElement("div");
      legend.id = "lane-legend";
      legend.className = "lane-legend";
      [
        ["local", "local"],
        ["cloud", "cloud"],
        ["mixed", "mixed"],
        ["unknown", "unknown"],
        ["loop", "retry / eval loop"]
      ].forEach(function (item) {
        var span = document.createElement("span");
        span.className = "lg " + item[0];
        var swatch = document.createElement("i");
        span.appendChild(swatch);
        span.appendChild(document.createTextNode(item[1]));
        legend.appendChild(span);
      });
      var note = $("lane-note");
      if (note && note.parentNode) note.parentNode.insertBefore(legend, note.nextSibling);
      else host.appendChild(legend);
    }
    ensure(host, "lane-cy", "div", "");
    var detail = $("lane-detail");
    if (!detail) {
      detail = document.createElement("aside");
      detail.id = "lane-detail";
      detail.className = "pane";
      detail.hidden = true;
      host.appendChild(detail);
    }
    if (!$("lane-detail-title")) {
      var title = document.createElement("h3");
      title.id = "lane-detail-title";
      title.textContent = "Lane";
      detail.appendChild(title);
    }
    ensure(detail, "lane-steps", "ol", "");
    ensure(detail, "lane-tabs", "div", "acts");
    ensure(detail, "lane-tab-body", "div", "");
    var link = $("lane-phoenix");
    if (!link) {
      link = document.createElement("a");
      link.id = "lane-phoenix";
      link.className = "hit";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Open in Phoenix";
      detail.appendChild(link);
    }
    if (!$("lane-tip")) {
      var tip = document.createElement("div");
      tip.id = "lane-tip";
      tip.className = "lane-tip";
      tip.hidden = true;
      document.body.appendChild(tip);
    }
    link = $("lane-phoenix");
    if (link && !link.dataset.bound) {
      link.dataset.bound = "1";
      link.addEventListener("click", function (event) {
        var tauri = window.__TAURI__ || {};
        var opener = tauri.opener && tauri.opener.openUrl;
        var shell = tauri.shell && tauri.shell.open;
        if (typeof opener !== "function" && typeof shell !== "function") return;
        event.preventDefault();
        var url = link.getAttribute("href");
        try {
          if (typeof opener === "function") opener(url);
          else shell(url);
        } catch (err) {
          window.open(url, "_blank", "noopener");
        }
      });
    }
  }

  function styles() {
    return [
      {
        selector: "node",
        style: {
          "background-color": "#18202c",
          "border-width": 2,
          "border-color": "#334155",
          color: "#e8edf4",
          "font-size": 12,
          "text-wrap": "wrap",
          "text-max-width": 140,
          "text-valign": "center",
          "text-halign": "center",
          label: "data(label)",
          width: 128,
          height: 52,
          shape: "round-rectangle"
        }
      },
      {selector: "node.route-local", style: {"border-color": COLORS.local}},
      {selector: "node.route-cloud", style: {"border-color": COLORS.cloud}},
      {selector: "node.route-mixed", style: {"border-color": COLORS.mixed}},
      {selector: "node.route-unknown", style: {"border-color": COLORS.unknown}},
      {selector: "node.status-error", style: {"border-color": "#e8875b"}},
      {selector: "node.status-running", style: {"border-color": "#e6c15a"}},
      {selector: "node:selected", style: {"border-width": 3, "border-color": "#4d8dff"}},
      {
        selector: "edge",
        style: {
          width: 2,
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "line-color": COLORS.unknown,
          "target-arrow-color": COLORS.unknown,
          label: "data(label)",
          color: "#8b97a8",
          "font-size": 11,
          "text-background-color": "#0e1116",
          "text-background-opacity": 0.85,
          "text-background-padding": 2
        }
      },
      {selector: "edge.route-local", style: {"line-color": COLORS.local, "target-arrow-color": COLORS.local}},
      {selector: "edge.route-cloud", style: {"line-color": COLORS.cloud, "target-arrow-color": COLORS.cloud}},
      {selector: "edge.route-mixed", style: {"line-color": COLORS.mixed, "target-arrow-color": COLORS.mixed}},
      {selector: "edge.route-unknown", style: {"line-color": COLORS.unknown, "target-arrow-color": COLORS.unknown}},
      {
        selector: "edge.loop",
        style: {
          "line-style": "dashed",
          "curve-style": "unbundled-bezier",
          "control-point-distances": -70,
          "control-point-weights": 0.5
        }
      }
    ];
  }

  function mount(host) {
    if (cy) return cy;
    if (!host || typeof cytoscape !== "function") {
      setNote("Lane graph did not load.");
      return null;
    }
    cy = cytoscape({
      container: host,
      elements: [],
      style: styles(),
      layout: {name: "preset"},
      wheelSensitivity: 0.2,
      boxSelectionEnabled: false
    });
    cy.on("mouseover", "node", onOver);
    cy.on("mouseout", "node", function () { hideTip(); });
    cy.on("tap", "node", onTap);
    return cy;
  }

  function nodeLabel(node) {
    var title = node.name || node.lane_id || node.id || "lane";
    return title + "\n" + routeOf(node.route) + " \u00b7 " + (node.status || "ok");
  }

  function nodeClasses(node) {
    return "route-" + routeOf(node.route) + " status-" + (node.status || "ok");
  }

  function edgeClasses(edge) {
    var cls = "route-" + routeOf(edge.route);
    if (edge.kind === "loop") cls += " loop";
    return cls;
  }

  function runLayout(keepView) {
    if (!cy) return;
    var eles = cy.elements().not(".loop");
    if (!eles.length) return;
    var zoom = cy.zoom();
    var pan = cy.pan();
    // Depth already runs left to right here. direction "rightward" rotates that row vertical.
    eles.layout({
      name: "breadthfirst",
      directed: true,
      padding: 28,
      spacingFactor: 1.35,
      animate: false,
      fit: false
    }).run();
    if (keepView) {
      cy.zoom(zoom);
      cy.pan(pan);
    }
  }

  function applyGraph(payload) {
    ensureChrome();
    var host = $("lane-cy");
    if (!mount(host)) return;
    var nodes = (payload && payload.nodes) || [];
    var edges = (payload && payload.edges) || [];
    var prevN = cy.nodes().map(function (n) { return n.id(); }).sort().join("|");
    var prevE = cy.edges().map(function (e) { return e.id(); }).sort().join("|");
    var nextN = nodes.map(function (n) { return n.id; }).sort().join("|");
    var nextE = edges.map(function (e) { return e.id; }).sort().join("|");
    var topology = prevN !== nextN || prevE !== nextE;
    var wantN = {};
    var wantE = {};
    nodes.forEach(function (node) { wantN[node.id] = node; });
    edges.forEach(function (edge) { wantE[edge.id] = edge; });
    cy.batch(function () {
      cy.nodes().forEach(function (ele) {
        if (!wantN[ele.id()]) ele.remove();
      });
      cy.edges().forEach(function (ele) {
        if (!wantE[ele.id()]) ele.remove();
      });
      nodes.forEach(function (node) {
        var data = {
          id: node.id,
          lane_id: node.lane_id || node.id,
          trace_id: node.trace_id || "",
          label: nodeLabel(node),
          summary: node.summary || node,
          phoenix_url: node.phoenix_url || "",
          task_class: node.task_class || "",
          route: routeOf(node.route),
          status: node.status || "ok"
        };
        var ele = cy.getElementById(node.id);
        if (!ele || !ele.length) cy.add({group: "nodes", data: data, classes: nodeClasses(node)});
        else {
          ele.data(data);
          ele.classes(nodeClasses(node));
        }
      });
      edges.forEach(function (edge) {
        if (!wantN[edge.source] || !wantN[edge.target]) return;
        var data = {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label || "",
          route: routeOf(edge.route),
          kind: edge.kind || "calls"
        };
        var ele = cy.getElementById(edge.id);
        if (!ele || !ele.length) cy.add({group: "edges", data: data, classes: edgeClasses(edge)});
        else {
          ele.data(data);
          ele.classes(edgeClasses(edge));
        }
      });
    });
    if (!didFit || topology) {
      runLayout(didFit);
      if (!didFit) {
        cy.fit(cy.elements(), 36);
        didFit = true;
      }
    }
    if (selectedId) {
      var sel = cy.getElementById(selectedId);
      if (sel && sel.length) sel.select();
      else selectedId = null;
    }
    maybeAuto();
  }

  function hideTip() {
    var tip = $("lane-tip");
    if (tip) tip.hidden = true;
  }

  function line(parent, text) {
    var div = document.createElement("div");
    div.textContent = text;
    parent.appendChild(div);
  }

  function onOver(evt) {
    var tip = $("lane-tip");
    if (!tip) return;
    var data = evt.target.data();
    var summary = data.summary || {};
    tip.replaceChildren();
    line(tip, "task  " + (summary.task || data.lane_id || ""));
    line(tip, "model  " + (summary.model || "n/a"));
    line(tip, "provider  " + (summary.provider || "n/a"));
    line(tip, "route  " + routeOf(summary.route || data.route));
    line(tip, "status  " + (summary.status || data.status || ""));
    line(tip, "duration  " + fmtDur(summary.duration_ms));
    line(tip, "cost  " + fmtCost(summary.cost));
    line(tip, "iteration  " + (summary.iteration === 0 || summary.iteration ? summary.iteration : "0"));
    var oe = evt.originalEvent || {};
    tip.style.left = ((oe.clientX || 24) + 14) + "px";
    tip.style.top = ((oe.clientY || 24) + 14) + "px";
    tip.hidden = false;
  }

  function onTap(evt) {
    var data = evt.target.data();
    selectedId = data.id;
    hideTip();
    openLane(data);
  }

  function tabLine(key, row) {
    if (key === "reasoning") return row.summary || "";
    if (key === "file_ops") return (row.op || "") + "  " + (row.path || "");
    if (key === "mcp_calls") {
      return (row.server || "") + " / " + (row.tool || "") + "  " + (row.status || "") + "  " + fmtDur(row.duration_ms);
    }
    return (row.name || "") + "  " + (row.status || "") + "  " + fmtDur(row.duration_ms);
  }

  function paintTab(detail) {
    var body = $("lane-tab-body");
    var tabs = $("lane-tabs");
    if (!body || !tabs) return;
    var rows = ((detail && detail.tabs) || {})[activeTab] || [];
    body.replaceChildren();
    if (!rows.length) {
      var none = document.createElement("p");
      none.className = "muted";
      none.textContent = "None";
      body.appendChild(none);
    } else {
      var list = document.createElement("ul");
      list.className = "lane-rows";
      rows.forEach(function (row) {
        var item = document.createElement("li");
        item.textContent = tabLine(activeTab, row);
        list.appendChild(item);
      });
      body.appendChild(list);
    }
    Array.prototype.forEach.call(tabs.querySelectorAll("button"), function (button) {
      button.classList.toggle("on", button.getAttribute("data-tab") === activeTab);
    });
  }

  // Lane task class -> the model-choice row on Loop (pfylib/model_choice TASK_ORDER).
  function modelTaskOf(taskClass) {
    var t = String(taskClass || "").toLowerCase();
    if (!t) return "";
    if (["catalog-fit", "eval-lane", "eval-suite", "matrix", "decision-route", "build-lane"].indexOf(t) >= 0) return t;
    if (t.indexOf("eval") === 0) return "eval-lane";
    if (t.indexOf("build") === 0 || t.indexOf("integrate") === 0) return "build-lane";
    return "";
  }

  function paintModelLever(node) {
    var detail = $("lane-detail");
    if (!detail) return;
    var btn = $("lane-model");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.id = "lane-model";
      detail.appendChild(btn);
      btn.addEventListener("click", function () {
        var task = btn.getAttribute("data-model-task") || "";
        if (typeof window.show === "function") window.show("loop");
        var sel = document.querySelector('#task-models select.task-model[data-task="' + task + '"]');
        if (sel) {
          sel.scrollIntoView({block: "center"});
          sel.focus();
        }
      });
    }
    var task = modelTaskOf((node && (node.task_class || (node.summary && node.summary.task_class))) || "");
    btn.setAttribute("data-model-task", task);
    btn.textContent = task ? "Model for " + task : "";
    btn.hidden = !task;
  }

  function paintDetail(detail, node) {
    ensureChrome();
    var panel = $("lane-detail");
    if (panel) panel.hidden = false;
    var title = $("lane-detail-title");
    if (title) title.textContent = (node && (node.name || node.lane_id || node.id)) || "Lane";
    var steps = $("lane-steps");
    if (steps) {
      steps.replaceChildren();
      ((detail && detail.steps) || []).forEach(function (step) {
        var item = document.createElement("li");
        item.textContent = (step.name || "") + "  " + (step.kind || "") + "  " + (step.status || "") + "  " + fmtDur(step.duration_ms);
        steps.appendChild(item);
      });
    }
    var tabs = $("lane-tabs");
    if (tabs && !tabs.childElementCount) {
      TAB_DEFS.forEach(function (def) {
        var button = document.createElement("button");
        button.type = "button";
        button.setAttribute("data-tab", def[0]);
        button.textContent = def[1];
        button.addEventListener("click", function () {
          activeTab = def[0];
          paintTab(panel && panel._detail);
        });
        tabs.appendChild(button);
      });
    }
    if (panel) panel._detail = detail;
    paintTab(detail);
    paintModelLever(node);
    var link = $("lane-phoenix");
    var url = (detail && detail.phoenix_url) || (node && node.phoenix_url) || "";
    if (link) {
      if (url) {
        link.href = url;
        link.hidden = false;
      } else {
        link.removeAttribute("href");
        link.hidden = true;
      }
    }
  }

  function openLane(data) {
    if (data && data._injectedDetail) {
      paintDetail(data._injectedDetail, data);
      return;
    }
    var trace = data.trace_id || "";
    var lane = data.lane_id || data.id || "";
    var key = trace + "\n" + lane;
    lastDetailKey = key;
    fetchDetail(trace, lane).then(function (detail) {
      if (lastDetailKey !== key) return;
      if (!detail || detail.ok === false) {
        paintDetail({steps: [], tabs: {}, why: (detail && detail.why) || DOWN, phoenix_url: data.phoenix_url}, data);
        var body = $("lane-tab-body");
        if (body && detail && detail.why) {
          body.replaceChildren();
          var note = document.createElement("p");
          note.className = "why";
          note.textContent = detail.why;
          body.appendChild(note);
        }
        return;
      }
      paintDetail(detail, data);
    }).catch(function () {
      paintDetail({steps: [], tabs: {}, why: DOWN, phoenix_url: data.phoenix_url}, data);
    });
  }

  function liveRoot() {
    if (typeof apiRoot === "function") return apiRoot();
    if (location.protocol === "http:" || location.protocol === "https:") return "";
    return null;
  }

  function fetchLanes() {
    if (typeof isTauri === "function" && isTauri()) {
      return window.__TAURI__.core.invoke("lanes").then(function (value) {
        return typeof value === "string" ? JSON.parse(value) : value;
      });
    }
    var root = liveRoot();
    if (root === null) return Promise.resolve({ok: false, why: DOWN, nodes: [], edges: []});
    return fetch(root + "/lanes", {cache: "no-store"}).then(function (response) { return response.json(); });
  }

  function fetchDetail(trace, lane) {
    if (typeof isTauri === "function" && isTauri()) {
      return window.__TAURI__.core.invoke("lane_detail", {trace: trace, lane: lane}).then(function (value) {
        return typeof value === "string" ? JSON.parse(value) : value;
      });
    }
    var root = liveRoot();
    if (root === null) return Promise.resolve({ok: false, why: DOWN});
    var url = root + "/lanes/detail?trace=" + encodeURIComponent(trace) + "&lane=" + encodeURIComponent(lane);
    return fetch(url, {cache: "no-store"}).then(function (response) { return response.json(); });
  }

  function clearGraph() {
    if (cy) cy.elements().remove();
  }

  function refresh() {
    if (refreshing) return Promise.resolve();
    refreshing = true;
    return fetchLanes().then(function (payload) {
      if (!payload || payload.ok === false) {
        setNote((payload && payload.why) || DOWN);
        if (!didFit) clearGraph();
        return;
      }
      var nodes = payload.nodes || [];
      setNote(nodes.length ? "" : emptyNote(payload.window_hours));
      applyGraph(payload);
    }).catch(function () {
      setNote(DOWN);
    }).then(function () {
      refreshing = false;
    });
  }

  function startPoll() {
    if (timer) return;
    refresh();
    timer = setInterval(function () {
      if (viewOn()) refresh();
      else stopPoll();
    }, POLL_MS);
  }

  function stopPoll() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  function maybeAuto() {
    if (!autoLane || !cy) return;
    var matches = cy.nodes().filter(function (node) {
      return node.data("lane_id") === autoLane || node.id() === autoLane;
    });
    if (!matches.length) return;
    var node = matches[0];
    node.select();
    selectedId = node.id();
    autoLane = null;
    openLane(node.data());
  }

  function showRunsForShot(lane) {
    var runs = $("view-runs");
    document.querySelectorAll(".view").forEach(function (el) {
      el.classList.toggle("on", el === runs);
    });
    document.querySelectorAll(".navbtn").forEach(function (btn) {
      btn.classList.toggle("on", btn.dataset.go === "runs");
    });
    var root = liveRoot() || "";
    var xhr = new XMLHttpRequest();
    xhr.open("GET", root + "/lanes", false);
    xhr.send(null);
    var payload = JSON.parse(xhr.responseText);
    if (!payload.ok) {
      setNote(payload.why || DOWN);
      return;
    }
    setNote((payload.nodes || []).length ? "" : emptyNote(payload.window_hours));
    applyGraph(payload);
    if (!lane || !cy) return;
    var matches = cy.nodes().filter(function (node) {
      return node.data("lane_id") === lane || node.id() === lane;
    });
    if (!matches.length) return;
    var node = matches[0];
    node.select();
    selectedId = node.id();
    var detailXhr = new XMLHttpRequest();
    detailXhr.open(
      "GET",
      root + "/lanes/detail?trace=" + encodeURIComponent(node.data("trace_id")) + "&lane=" + encodeURIComponent(node.data("lane_id")),
      false
    );
    detailXhr.send(null);
    paintDetail(JSON.parse(detailXhr.responseText), node.data());
  }

  function boot() {
    ensureChrome();
    var host = $("lane-cy");
    if (host) mount(host);
    document.querySelectorAll(".navbtn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.go === "runs") startPoll();
        else stopPoll();
      });
    });
    var runs = $("view-runs");
    if (runs && window.MutationObserver) {
      new MutationObserver(function () {
        if (viewOn()) startPoll();
        else stopPoll();
      }).observe(runs, {attributes: true, attributeFilter: ["class"]});
    }
    var params = new URLSearchParams(location.search || "");
    autoLane = params.get("lane");
    if (params.get("shot") === "1") {
      try {
        showRunsForShot(params.get("lane"));
      } catch (err) {
        setNote(DOWN);
      }
      return;
    }
    if (params.get("view") === "runs") {
      var button = document.querySelector('.navbtn[data-go="runs"]');
      if (button) button.click();
      else {
        if (runs) runs.classList.add("on");
        startPoll();
      }
    }
  }

  function classString(ele) {
    var raw = ele.classes();
    if (Array.isArray(raw)) raw = raw.join(" ");
    return String(raw || "").split(/\s+/).filter(Boolean).sort().join(" ");
  }

  function renderForTest(opts) {
    opts = opts || {};
    if (opts.tab) activeTab = opts.tab;
    ensureChrome();
    var host = $("lane-cy");
    if (host) {
      if (!host.style.width) host.style.width = "900px";
      if (!host.style.height) host.style.height = "520px";
    }
    mount(host);
    applyGraph(opts.graph || {nodes: [], edges: []});
    var lane = opts.lane;
    var node = null;
    ((opts.graph && opts.graph.nodes) || []).some(function (item) {
      if (item.id === lane || item.lane_id === lane) {
        node = item;
        return true;
      }
      return false;
    });
    if (node && opts.detail) {
      selectedId = node.id;
      var ele = cy.getElementById(node.id);
      if (ele && ele.length) ele.select();
      node._injectedDetail = opts.detail;
      openLane(node);
    }
    var out = $("lane-graph-summary");
    if (!out) {
      out = document.createElement("pre");
      out.id = "lane-graph-summary";
      document.body.appendChild(out);
    }
    var summary = {
      nodes: cy ? cy.nodes().map(function (n) { return n.id(); }) : [],
      edges: cy ? cy.edges().map(function (e) {
        return {id: e.id(), classes: classString(e), route: e.data("route"), kind: e.data("kind")};
      }) : [],
      loops: cy ? cy.edges(".loop").map(function (e) { return e.id(); }) : [],
      tabs: Array.prototype.map.call(document.querySelectorAll("#lane-tabs button"), function (button) {
        return button.textContent;
      }),
      legend: !!$("lane-legend"),
      detail_open: !!($("lane-detail") && !$("lane-detail").hidden),
      tab_body: ($("lane-tab-body") && $("lane-tab-body").textContent) || "",
      model_lever: ($("lane-model") && !$("lane-model").hidden && $("lane-model").getAttribute("data-model-task")) || ""
    };
    out.textContent = JSON.stringify(summary);
  }

  window.LaneGraph = {
    renderForTest: renderForTest,
    refresh: refresh,
    applyGraph: applyGraph
  };

  window.addEventListener("error", function (ev) {
    var out = $("lane-graph-summary");
    if (!out) return;
    out.textContent = JSON.stringify({error: String(ev.message || "error")});
  });

  if (document.body && document.body.dataset.laneTest === "1") {
    return;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
