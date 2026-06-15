import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  getBundledRuntimeCandidates,
  getBundledRuntimeStatus,
  loadRuntimeManifest,
  missingBundledRuntimeError,
  resolveBundledRuntime,
  runtimeManifestPath
} from "../../server/runtime_paths.js";

const TEST_RUNTIME_MANIFEST = {
  node: ["node/node.exe"],
  python: [
    "runtime/python/python.exe",
    "runtime/python/Scripts/python.exe",
    "runtime/python/bin/python"
  ],
  powershell: [
    "runtime/powershell/pwsh.exe",
    "runtime/powershell/powershell.exe",
    "runtime/powershell/pwsh/pwsh.exe"
  ]
};

function writeRuntimeManifest(rootDir, manifest = TEST_RUNTIME_MANIFEST) {
  const runtimeDir = path.join(rootDir, "runtime");
  mkdirSync(runtimeDir, { recursive: true });
  writeFileSync(path.join(runtimeDir, "runtime-manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
}

test("runtime path surface keeps manifest path, loader and candidate contract stable", () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-runtime-contract-"));
  try {
    writeRuntimeManifest(rootDir);

    assert.equal(runtimeManifestPath(rootDir), path.join(rootDir, "runtime", "runtime-manifest.json"));
    assert.deepEqual(loadRuntimeManifest(rootDir), TEST_RUNTIME_MANIFEST);
    assert.deepEqual(getBundledRuntimeCandidates("python", { rootDir }), [
      path.join(rootDir, "runtime", "python", "python.exe"),
      path.join(rootDir, "runtime", "python", "Scripts", "python.exe"),
      path.join(rootDir, "runtime", "python", "bin", "python")
    ]);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});

test("getBundledRuntimeStatus resolves manifest candidates independently", () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-runtime-status-"));
  try {
    writeRuntimeManifest(rootDir);
    mkdirSync(path.join(rootDir, "node"), { recursive: true });
    mkdirSync(path.join(rootDir, "runtime", "python"), { recursive: true });
    writeFileSync(path.join(rootDir, "node", "node.exe"), "", "utf8");
    writeFileSync(path.join(rootDir, "runtime", "python", "python.exe"), "", "utf8");

    const status = getBundledRuntimeStatus(rootDir);
    assert.equal(status.runtimes.node.ok, true);
    assert.equal(status.runtimes.python.ok, true);
    assert.equal(status.runtimes.powershell.ok, false);
    assert.equal(status.ok, false);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});

test("runtime validation rejects invalid contracts and missing runtimes keep the ENOENT surface", () => {
  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-runtime-resolve-"));
  try {
    writeRuntimeManifest(rootDir);
    const scriptsDir = path.join(rootDir, "runtime", "python", "Scripts");
    mkdirSync(scriptsDir, { recursive: true });
    const pythonPath = path.join(scriptsDir, "python.exe");
    writeFileSync(pythonPath, "", "utf8");

    assert.equal(resolveBundledRuntime("python", { rootDir }), pythonPath);

    const missingError = missingBundledRuntimeError("powershell", [path.join(rootDir, "runtime", "powershell", "pwsh.exe")]);
    assert.equal(missingError.code, "ENOENT");
    assert.match(missingError.message, /Bundled PowerShell runtime is missing/);
    assert.throws(() => getBundledRuntimeCandidates("ruby", { rootDir }), /Unknown runtime: ruby/);
    assert.throws(() => resolveBundledRuntime("powershell", { rootDir }), (error) => {
      assert.equal(error?.code, "ENOENT");
      return /Bundled PowerShell runtime is missing/.test(String(error?.message || ""));
    });

    writeRuntimeManifest(rootDir, { node: [] });
    assert.throws(() => loadRuntimeManifest(rootDir), /Runtime manifest has no valid entries for node/);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});
