#!/usr/bin/env node
// Minimal ACP agent on stdin/stdout. No model, no network, no account.
// Overtime spawns this as a customBackends command. Every line is one JSON-RPC message.
import fs from "node:fs";

const logPath = process.env.OVERTIME_STUB_LOG;
const statePath = process.env.OVERTIME_STUB_STATE;
const profilePath = process.env.OVERTIME_STUB_PROFILE;
const SESSION = "stub-session-1";

function emit(obj) {
  fs.writeSync(1, JSON.stringify(obj) + "\n");
}

function log(obj) {
  if (!logPath) return;
  fs.appendFileSync(logPath, JSON.stringify({ t: Date.now(), pid: process.pid, ...obj }) + "\n");
}

function profile() {
  try {
    return JSON.parse(fs.readFileSync(profilePath, "utf8"));
  } catch {
    return {};
  }
}

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(statePath, "utf8"));
  } catch {
    return {};
  }
}

function saveState(s) {
  if (!statePath) return;
  fs.writeFileSync(statePath, JSON.stringify(s));
}

function brief(params) {
  if (!params || typeof params !== "object") return null;
  return {
    sessionId: params.sessionId ?? null,
    cwd: params.cwd ?? null,
    mcp: Array.isArray(params.mcpServers) ? params.mcpServers.length : null,
    protocolVersion: params.protocolVersion ?? null,
  };
}

function tryWrite(p) {
  if (!p) return { path: null, ok: false, error: "no path" };
  try {
    fs.mkdirSync(p.replace(/\/[^/]+$/, ""), { recursive: true });
    fs.writeFileSync(p, "stub\n");
    return { path: p, ok: true, error: null };
  } catch (e) {
    return { path: p, ok: false, error: e.code || String(e.message || e) };
  }
}

function handle(msg) {
  const method = msg.method;
  const params = msg.params || {};
  if (method === "initialize") {
    return {
      protocolVersion: 1,
      agentCapabilities: {
        loadSession: true,
        promptCapabilities: { image: false, audio: false, embeddedContext: false },
        mcpCapabilities: { http: false, sse: false, acp: false },
      },
      authMethods: [],
    };
  }
  if (method === "session/new") {
    saveState({ sessionId: SESSION, createdAt: Date.now() });
    return { sessionId: SESSION };
  }
  if (method === "session/load") {
    const known = loadState().sessionId;
    const ok = params.sessionId === known && known === SESSION;
    log({ event: "load", requested: params.sessionId ?? null, known: known ?? null, ok });
    if (!ok) return { error: { code: -32602, message: "unknown session" } };
    return {};
  }
  if (method === "session/prompt") {
    const prof = profile();
    const writes = {
      allow: tryWrite(prof.write_ok || ""),
      deny: tryWrite(prof.write_deny || ""),
    };
    log({ event: "writes", writes });
    const cost = Number(prof.session_cost ?? 0);
    const tokens = Number(prof.tokens ?? 0);
    emit({
      jsonrpc: "2.0",
      method: "session/update",
      params: {
        sessionId: params.sessionId,
        update: {
          sessionUpdate: "agent_message_chunk",
          content: { type: "text", text: "STUB_OK" },
        },
      },
    });
    emit({
      jsonrpc: "2.0",
      method: "session/update",
      params: {
        sessionId: params.sessionId,
        update: {
          sessionUpdate: "usage_update",
          used: 10,
          size: 1000,
          cost: { amount: cost, currency: "USD" },
        },
      },
    });
    return {
      stopReason: "end_turn",
      usage: { totalTokens: tokens, inputTokens: tokens, outputTokens: 0 },
    };
  }
  if (method === "session/set_mode" || method === "session/set_config_option" || method === "session/set_model") {
    return {};
  }
  return { error: { code: -32601, message: "method not used by this stub" } };
}

log({ event: "start" });

let buf = "";
process.stdin.on("data", (chunk) => {
  buf += chunk.toString("utf8");
  let nl;
  while ((nl = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, nl);
    buf = buf.slice(nl + 1);
    if (!line.trim()) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      log({ event: "bad-json" });
      continue;
    }
    log({ event: "in", method: msg.method ?? null, id: msg.id ?? null, brief: brief(msg.params) });
    if (msg.id === undefined || msg.id === null) continue;
    const result = handle(msg);
    if (result && result.error) emit({ jsonrpc: "2.0", id: msg.id, error: result.error });
    else emit({ jsonrpc: "2.0", id: msg.id, result });
    log({ event: "out", method: msg.method ?? null, id: msg.id });
  }
});

process.stdin.on("end", () => {
  log({ event: "end" });
  process.exit(0);
});
