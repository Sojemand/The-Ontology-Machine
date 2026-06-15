import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { runBasicRelationMiningWithKernel } from "../../client_frontend/ontology_agent/kernel_basic_relation_mining.js";
import { validateOntologyPatchWithKernel } from "../../client_frontend/ontology_agent/kernel_validation.js";

function makeRuntimeRoot() {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-kernel-runtime-"));
  const pythonPath = path.join(rootDir, "runtime", "python", "python.exe");
  mkdirSync(path.dirname(pythonPath), { recursive: true });
  mkdirSync(path.join(rootDir, "runtime"), { recursive: true });
  writeFileSync(
    path.join(rootDir, "runtime", "runtime-manifest.json"),
    JSON.stringify({
      node: ["node/node.exe"],
      python: ["runtime/python/python.exe"],
      powershell: ["runtime/powershell/powershell.exe"]
    }),
    "utf8"
  );
  writeFileSync(pythonPath, "");
  return { rootDir, pythonPath };
}

test("ontology patch validation uses bundled Python instead of host PATH python", async () => {
  const { rootDir, pythonPath } = makeRuntimeRoot();
  try {
    let captured = null;
    const result = await validateOntologyPatchWithKernel({
      runtimeRoot: rootDir,
      pipelineRoot: "C:\\Pipeline",
      dbPath: "C:\\Corpus\\corpus.db",
      ontologyId: "lens_test",
      execFileFn: async (command, args, options) => {
        captured = { command, args, options };
        return { stdout: JSON.stringify({ status: "pass", checks: [], warnings: [], errors: [] }) };
      }
    });

    assert.equal(result.status, "pass");
    assert.equal(captured.command, pythonPath);
    assert.notEqual(captured.command, "python");
    assert.equal(captured.options.cwd, path.join("C:\\Pipeline", "08 - Semantic Control Kernel"));
    assert.match(captured.options.env.PYTHONPATH, /Semantic Control Kernel/);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});

test("basic relation mining uses bundled Python instead of host PATH python", async () => {
  const { rootDir, pythonPath } = makeRuntimeRoot();
  try {
    let captured = null;
    const result = await runBasicRelationMiningWithKernel({
      runtimeRoot: rootDir,
      pipelineRoot: "C:\\Pipeline",
      dbPath: "C:\\Corpus\\corpus.db",
      stateRoot: "C:\\State",
      dryRun: true,
      execFileFn: async (command, args, options) => {
        captured = { command, args, options };
        return {
          stdout: JSON.stringify({
            status: "ok",
            database_path: args[3],
            dry_run: true,
            output: {},
            adapter_result: { status: "ok", adapter_call_id: "call-1" },
            blocker: null
          })
        };
      }
    });

    assert.equal(result.ok, true);
    assert.equal(captured.command, pythonPath);
    assert.notEqual(captured.command, "python");
    assert.equal(captured.args[2], "C:\\Pipeline");
    assert.equal(captured.args[4], "C:\\State");
    assert.equal(captured.options.cwd, path.join("C:\\Pipeline", "08 - Semantic Control Kernel"));
    assert.match(captured.options.env.PYTHONPATH, /Semantic Control Kernel/);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});
