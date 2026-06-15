import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { migrateLegacyRootState, resolveAppPaths } from "../../server/app_paths.js";

test("legacy log migration tolerates a pre-created app-home log directory from the starter", () => {
  const moduleRoot = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-log-root-"));
  const appHome = mkdtempSync(path.join(os.tmpdir(), "vp-app-paths-log-home-"));
  try {
    const paths = resolveAppPaths({ moduleRoot, appHome });
    mkdirSync(path.join(moduleRoot, "logs"), { recursive: true });
    mkdirSync(paths.log_dir, { recursive: true });
    writeFileSync(path.join(moduleRoot, "logs", "startup.log"), "legacy root log", "utf8");
    writeFileSync(path.join(moduleRoot, "logs", "worker.log"), "legacy worker log", "utf8");
    writeFileSync(path.join(paths.log_dir, "startup.log"), "current app-home log", "utf8");

    const result = migrateLegacyRootState({ moduleRoot, appHome });

    assert.equal(result.migrated, true);
    assert.deepEqual(result.entries, ["logs"]);
    assert.equal(existsSync(path.join(moduleRoot, "logs")), false);
    assert.equal(readFileSync(path.join(paths.log_dir, "startup.log"), "utf8"), "current app-home log");
    assert.equal(readFileSync(path.join(paths.log_dir, "startup.legacy-1.log"), "utf8"), "legacy root log");
    assert.equal(readFileSync(path.join(paths.log_dir, "worker.log"), "utf8"), "legacy worker log");
    assert.deepEqual(readdirSync(paths.log_dir).sort(), ["startup.legacy-1.log", "startup.log", "worker.log"]);
  } finally {
    rmSync(moduleRoot, { recursive: true, force: true });
    rmSync(appHome, { recursive: true, force: true });
  }
});
