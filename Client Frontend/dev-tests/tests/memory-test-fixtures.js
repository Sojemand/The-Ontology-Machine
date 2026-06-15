import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { createMemoryStore } from "../../server/memory.js";

export function makeTempDir() {
  return mkdtempSync(path.join(os.tmpdir(), "vp-memory-"));
}

export function cleanupTempDir(tempDir) {
  rmSync(tempDir, { recursive: true, force: true });
}

export function withMemoryStore(callback) {
  const tempDir = makeTempDir();
  const store = createMemoryStore({ rootDir: tempDir });
  try {
    return callback(store, tempDir);
  } finally {
    store.close();
    cleanupTempDir(tempDir);
  }
}
