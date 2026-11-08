// Load the pinned workflow-engine and score one step input.
// SchemaValidator.validate and routeNode are the checks AgentDirectiveHandler
// runs after an agent submits a step. The completion string is passed through
// and not read by either function.

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const src = process.env.MOIRA_SRC || "";
const jobPath = process.argv[2] || "";

function fail(message) {
  process.stderr.write(message + "\n");
  process.exit(2);
}

if (!src || !jobPath) {
  fail("MOIRA_SRC and a job path are required");
}

const job = JSON.parse(readFileSync(jobPath, "utf8"));
const validatorUrl = pathToFileURL(
  src + "/packages/workflow-engine/src/utils/schema-validator.ts",
).href;
const routeUrl = pathToFileURL(
  src + "/packages/workflow-engine/src/services/node-routing.ts",
).href;

let SchemaValidator;
let routeNode;
try {
  ({ SchemaValidator } = await import(validatorUrl));
  ({ routeNode } = await import(routeUrl));
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}

const ajvPath = src + "/node_modules/ajv/package.json";
let ajvVersion = "";
try {
  ajvVersion = JSON.parse(readFileSync(ajvPath, "utf8")).version;
} catch {
  ajvVersion = "";
}

const schema = SchemaValidator.enforceStrictSchema(job.schema);
const started = process.hrtime.bigint();
const cases = [];

for (const row of job.cases) {
  const input = row.input;
  const result = SchemaValidator.validate(input, schema, {
    executionId: "probe",
    workflowId: "pfy-build-lane",
  });
  let output = null;
  if (result.isValid && input !== null && typeof input === "object" && !Array.isArray(input)) {
    const routed = routeNode(
      {
        completionCondition: row.completionCondition || "",
        cases: job.routeCases,
        connections: job.connections,
      },
      job.defaultOutput || "done",
      {
        variables: { ...input },
        executionId: "probe",
        workflowId: "pfy-build-lane",
      },
      undefined,
      "moira-probe",
    );
    output = routed.output;
  }
  cases.push({
    id: row.id,
    valid: result.isValid === true,
    output,
    error: result.isValid ? "" : String((result.errors && result.errors[0]) || ""),
  });
}

const elapsedUs = Number(process.hrtime.bigint() - started) / 1000;
process.stdout.write(
  "PFY_JSON " +
    JSON.stringify({
      engine: "SchemaValidator.validate+routeNode",
      ajv: ajvVersion,
      elapsed_us: elapsedUs,
      cases,
    }) +
    "\n",
);
