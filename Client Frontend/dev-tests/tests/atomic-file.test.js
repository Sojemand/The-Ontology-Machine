import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { makeShortSiblingPath, writeTextAtomically } from "../../client_frontend/atomic_file.js";

test("atomic write temp names stay short and do not repeat the target basename", () => {
  const targetPath = path.join("C:\\very\\deep\\app-home\\config", "frontend_policy.json");
  const tempPath = makeShortSiblingPath(targetPath);
  const oldStylePath = path.join(
    path.dirname(targetPath),
    `${path.basename(targetPath)}.${process.pid}.${"0".repeat(36)}.tmp`
  );

  assert.equal(path.dirname(tempPath), path.dirname(targetPath));
  assert.match(path.basename(tempPath), /^\.tmp-/);
  assert.equal(path.basename(tempPath).includes(path.basename(targetPath)), false);
  assert.equal(tempPath.length < oldStylePath.length, true);
});

test("atomic writes stay within the classic Windows path budget for deep app-home paths", async (t) => {
  if (process.platform !== "win32") {
    t.skip("Windows path-budget probe");
    return;
  }

  const rootDir = mkdtempSync(path.join(os.tmpdir(), "vp-atomic-long-"));
  try {
    let targetDir = rootDir;
    let index = 0;
    while (targetDir.length < 232) {
      const segment = `deep${String(index).padStart(2, "0")}`;
      const nextDir = path.join(targetDir, segment);
      if (nextDir.length > 232) break;
      targetDir = nextDir;
      index += 1;
    }
    mkdirSync(targetDir, { recursive: true });
    const targetPath = path.join(targetDir, "config.json");
    const oldStylePath = path.join(
      path.dirname(targetPath),
      `${path.basename(targetPath)}.${process.pid}.${"0".repeat(36)}.tmp`
    );
    const shortTempPath = makeShortSiblingPath(targetPath);

    assert.equal(targetPath.length < 260, true);
    assert.equal(oldStylePath.length > 260, true);
    assert.equal(shortTempPath.length < 260, true);

    await writeTextAtomically(targetPath, "{\"ok\":true}\n");
    assert.equal(readFileSync(targetPath, "utf8"), "{\"ok\":true}\n");
    assert.equal(existsSync(shortTempPath), false);
  } finally {
    rmSync(rootDir, { recursive: true, force: true });
  }
});
