// Probe harness. Calls skill_validate only. Does not call skill_eval or skill_optimize_loop.
import { readFileSync } from "fs";

const spec = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = { tools: [], results: [], error: null };
try {
  const mod = await import(spec.entry);
  const tools = {};
  const ctx = {
    location: { directory: spec.proj },
    tool: { transform: async (f) => f({ add: (t) => { tools[t.name] = t; } }) },
  };
  const dispose = await mod.default.setup(ctx);
  out.tools = Object.keys(tools).sort();
  if (!tools.skill_validate) {
    throw new Error("skill_validate was not registered");
  }
  for (const skillPath of spec.skills) {
    const row = { path: skillPath, pass: false, failing_keys: [], message: "" };
    try {
      const res = await tools.skill_validate.execute({ skillPath }, {});
      const parsed = JSON.parse(res.content);
      const message = String(parsed.message || "");
      row.pass = parsed.valid === true;
      row.message = message;
      const unexpected = message.match(/Unexpected key\(s\) in SKILL\.md frontmatter: ([^.]+)\./);
      if (unexpected) {
        row.failing_keys.push(...unexpected[1].split(",").map((s) => s.trim()).filter(Boolean));
      }
      const invalid = message.match(/Invalid frontmatter value for '([^']+)'/);
      if (invalid && !row.failing_keys.includes(invalid[1])) {
        row.failing_keys.push(invalid[1]);
      }
    } catch (err) {
      row.pass = false;
      row.message = String(err && err.stack || err).slice(0, 400);
      row.error = true;
    }
    out.results.push(row);
  }
  if (typeof dispose === "function") await dispose();
} catch (err) {
  out.error = String(err && err.stack || err).slice(0, 800);
}
console.log(JSON.stringify(out));
