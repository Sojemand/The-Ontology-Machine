import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

test("minimal-agent direct-run bootstrap keeps the stable help usage", async () => {
  const serverPath = path.resolve(fileURLToPath(new URL("../../server/min_agent.js", import.meta.url)));
  const originalArgv = [...process.argv];
  const originalLog = console.log;
  const originalError = console.error;
  const logs = [];
  const errors = [];
  try {
    process.argv = [originalArgv[0], serverPath, "--help"];
    console.log = (...args) => logs.push(args.join(" "));
    console.error = (...args) => errors.push(args.join(" "));
    await import(`${pathToFileURL(serverPath).href}?cli-test=${Date.now()}`);
    await new Promise((resolve) => setImmediate(resolve));
  } finally {
    process.argv = originalArgv;
    console.log = originalLog;
    console.error = originalError;
  }
  const cliErrors = errors.filter((error) => !/ExperimentalWarning: SQLite/.test(error));
  assert.equal(cliErrors.length, 0);
  assert.match(logs.join("\n"), /Usage: node server\/min_agent\.js --db <path-to-corpus\.db>/);
});
