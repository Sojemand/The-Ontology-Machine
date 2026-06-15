import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { resolveWorkbenchCommandPlans } from "../../server/min_agent.js";
import { cleanupWorkbenchFixture, createWorkbenchFixture, writeRuntimeManifest } from "./min-agent-workbench-test-fixtures.js";

test("python workbench resolves the bundled runtime through the isolated runner script", () => {
  const fixture = createWorkbenchFixture({ runtimeBacked: true });
  try {
    const plans = resolveWorkbenchCommandPlans("python", { rootDir: fixture.rootDir });
    assert.equal(plans.length, 1);
    assert.match(plans[0].command, /runtime[\\/]+python[\\/]+python\.exe$/i);
    assert.match(plans[0].args[0], /^-I$/);
    assert.match(plans[0].args[1], /server[\\/]workbench_python_runner\.py$/i);
  } finally {
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});

test("workbench resolves bundled powershell runtime without host fallback", () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-min-wb-ps-"));
  try {
    writeRuntimeManifest(rootDir);
    const pwshExe = path.join(rootDir, "runtime", "powershell", "pwsh.exe");
    mkdirSync(path.dirname(pwshExe), { recursive: true });
    writeFileSync(pwshExe, "", "utf8");
    assert.deepEqual(resolveWorkbenchCommandPlans("powershell", { rootDir }), [
      { command: pwshExe, args: ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "-"] }
    ]);
  } finally {
    cleanupWorkbenchFixture(rootDir);
  }
});

test("workbench rejects missing bundled runtimes in strict mode", () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-min-wb-strict-"));
  try {
    writeRuntimeManifest(rootDir);
    assert.throws(() => resolveWorkbenchCommandPlans("powershell", { rootDir }), /Bundled PowerShell runtime is missing/);
    assert.throws(() => resolveWorkbenchCommandPlans("python", { rootDir }), /Bundled Python runtime is missing/);
  } finally {
    cleanupWorkbenchFixture(rootDir);
  }
});
