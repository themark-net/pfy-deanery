#!/usr/bin/env node
// Store, recall, or corrupt one opencode-mem project shard.
// HOME must already point at the cache home. Prints one JSON object.

import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";

const SALTS = [
  "OCM1107_SALT_01",
  "OCM1107_SALT_02",
  "OCM1107_SALT_03",
  "OCM1107_SALT_04",
  "OCM1107_SALT_05",
  "OCM1107_SALT_06",
  "OCM1107_SALT_07",
  "OCM1107_SALT_08",
];
const DECOY = "smoke-codebase-memory";

function arg(name) {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return "";
  return process.argv[index + 1];
}

function fail(command, error) {
  const doc = { ok: false, command, error: String(error).slice(0, 400), rows: [] };
  const out = arg("--out");
  if (out) {
    try {
      fs.writeFileSync(out, JSON.stringify(doc));
    } catch {
      // The parent still reads stdout.
    }
  }
  process.stdout.write(JSON.stringify(doc) + "\n");
  process.exit(0);
}

function sentence(salt) {
  return "pfy opencode-mem lane salt " + salt + " is private to this probe.";
}

function shardFiles(storage, hash) {
  const dir = path.join(storage, "projects");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.includes(hash))
    .map((name) => path.join(dir, name));
}

async function finish(memoryClient, doc, out) {
  fs.writeFileSync(out, JSON.stringify(doc));
  process.stdout.write(JSON.stringify(doc) + "\n");
  await Promise.race([
    memoryClient.close().catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 5000)),
  ]);
  process.exit(0);
}

const command = process.argv[2] || "";
const out = arg("--out");
const directory = arg("--dir");
const pkg = process.env.OCM_PKG || "";

if (!out || !directory || !pkg) {
  fail(command || "usage", "need --out, --dir, and OCM_PKG");
}
if (command !== "store" && command !== "recall" && command !== "corrupt") {
  fail(command || "usage", "command must be store, recall, or corrupt");
}

const root = path.resolve(pkg);
const clientUrl = pathToFileURL(path.join(root, "dist/services/client.js")).href;
const tagsUrl = pathToFileURL(path.join(root, "dist/services/tags.js")).href;
const configUrl = pathToFileURL(path.join(root, "dist/config.js")).href;

let memoryClient;
let getProjectTagInfo;
let CONFIG;
try {
  ({ memoryClient } = await import(clientUrl));
  ({ getProjectTagInfo } = await import(tagsUrl));
  ({ CONFIG } = await import(configUrl));
} catch (error) {
  fail(command, error instanceof Error ? error.message : error);
}

const tagInfo = getProjectTagInfo(directory);
const tag = tagInfo.tag;
const hash = tag.split("_").pop();
const storage = CONFIG.storagePath;

if (command === "store") {
  const removed = process.argv.includes("--fresh") ? [] : null;
  if (removed) {
    for (const file of shardFiles(storage, hash)) {
      fs.rmSync(file, { force: true });
      removed.push(path.basename(file));
    }
  }
  const warmStart = Date.now();
  let warmError = null;
  try {
    await memoryClient.warmup();
  } catch (error) {
    warmError = String(error instanceof Error ? error.message : error).slice(0, 240);
  }
  const warmupMs = Date.now() - warmStart;
  const rows = [];
  for (const salt of SALTS) {
    let res = await memoryClient.addMemory(sentence(salt), tag, {
      source: "manual",
      type: "manual",
      projectPath: directory,
    });
    let attempts = 1;
    if (!res.success) {
      try {
        await memoryClient.warmup();
      } catch {
        // The retry below records the second error.
      }
      res = await memoryClient.addMemory(sentence(salt), tag, {
        source: "manual",
        type: "manual",
        projectPath: directory,
      });
      attempts = 2;
    }
    rows.push({
      salt,
      success: res.success === true,
      attempts,
      error: res.success ? null : String(res.error || "add failed").slice(0, 240),
    });
  }
  await finish(memoryClient, {
    ok: rows.every((row) => row.success),
    command,
    tag,
    model: CONFIG.embeddingModel,
    storage,
    warmup_ms: warmupMs,
    warm_error: warmError,
    removed,
    stored: rows.filter((row) => row.success).length,
    rows,
  }, out);
}

if (command === "recall") {
  const warmStart = Date.now();
  let warmError = null;
  try {
    await memoryClient.warmup();
  } catch (error) {
    warmError = String(error instanceof Error ? error.message : error).slice(0, 240);
  }
  const warmupMs = Date.now() - warmStart;
  const listed = await memoryClient.listMemories(tag, 20, "project");
  const texts = (listed.memories || []).map((row) => String(row.summary || ""));
  const rows = [];
  for (const salt of SALTS) {
    const res = await memoryClient.searchMemories(sentence(salt), tag, "project", { limit: 5 });
    const memories = (res.results || []).map((row) => String(row.memory || ""));
    const top = (res.results || [])[0];
    rows.push({
      salt,
      listed: texts.some((text) => text.includes(salt)),
      searched: res.success === true && memories.some((text) => text.includes(salt)),
      similarity: top && typeof top.similarity === "number" ? Number(top.similarity.toFixed(4)) : null,
      error: res.success === true ? null : String(res.error || "search failed").slice(0, 240),
    });
  }
  const decoy = await memoryClient.searchMemories(DECOY, tag, "project", { limit: 3 });
  const decoyHit =
    decoy.success === true &&
    (decoy.results || []).some((row) => String(row.memory || "").includes(DECOY));
  await finish(memoryClient, {
    ok: listed.success === true,
    command,
    tag,
    model: CONFIG.embeddingModel,
    storage,
    warmup_ms: warmupMs,
    warm_error: warmError,
    list_count: (listed.memories || []).length,
    list_error: listed.success === true ? null : String(listed.error || "list failed").slice(0, 240),
    rows,
    decoy_hit: decoyHit,
    decoy_success: decoy.success === true,
  }, out);
}

const damaged = [];
for (const file of shardFiles(storage, hash)) {
  if (file.endsWith(".db")) {
    fs.writeFileSync(file, "not a database\n");
    damaged.push(path.basename(file));
  } else {
    fs.rmSync(file, { force: true });
  }
}
let listError = null;
let rows = [];
try {
  const listed = await memoryClient.listMemories(tag, 20, "project");
  if (listed.success !== true) {
    listError = String(listed.error || "list failed").slice(0, 240);
  } else {
    const texts = (listed.memories || []).map((row) => String(row.summary || ""));
    rows = SALTS.map((salt) => ({
      salt,
      listed: texts.some((text) => text.includes(salt)),
      searched: false,
    }));
  }
} catch (error) {
  listError = String(error instanceof Error ? error.message : error).slice(0, 240);
}
let searchError = null;
try {
  const res = await memoryClient.searchMemories(sentence(SALTS[0]), tag, "project", { limit: 5 });
  if (res.success !== true) {
    searchError = String(res.error || "search failed").slice(0, 240);
  } else {
    const memories = (res.results || []).map((row) => String(row.memory || ""));
    rows = SALTS.map((salt) => ({
      salt,
      listed: rows.find((row) => row.salt === salt)?.listed === true,
      searched: memories.some((text) => text.includes(salt)),
    }));
  }
} catch (error) {
  searchError = String(error instanceof Error ? error.message : error).slice(0, 240);
}
const found = rows.filter((row) => row.listed === true || row.searched === true).length;
const recovered = found === SALTS.length && !listError && !searchError;
const error = recovered
  ? null
  : [listError, searchError].filter(Boolean).join("; ") || "stored salts missing after corrupt";
await finish(memoryClient, {
  ok: recovered,
  command,
  tag,
  damaged,
  error,
  rows,
}, out);
