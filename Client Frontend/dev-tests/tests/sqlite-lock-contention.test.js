import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createChatStore } from "../../server/chat_store.js";
import { createMemoryStore } from "../../server/memory.js";

function makeTempDir() {
  return mkdtempSync(path.join(os.tmpdir(), "vp-sqlite-lock-"));
}

function startLockHolder(dbPath) {
  const script = `
    import { DatabaseSync } from "node:sqlite";
    const database = new DatabaseSync(${JSON.stringify(dbPath)});
    database.exec("CREATE TABLE IF NOT EXISTS lock_probe (id INTEGER); BEGIN IMMEDIATE; INSERT INTO lock_probe (id) VALUES (1);");
    console.log("LOCKED");
    setTimeout(() => {
      try {
        database.exec("COMMIT");
      } finally {
        database.close();
      }
    }, 500);
  `;
  return spawn(process.execPath, ["--disable-warning=ExperimentalWarning", "--input-type=module", "-e", script], {
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true
  });
}

async function waitForLock(child) {
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`lock holder did not become ready: ${stderr}`)), 3000);
    child.stdout.on("data", (chunk) => {
      if (String(chunk).includes("LOCKED")) {
        clearTimeout(timeout);
        resolve(undefined);
      }
    });
    child.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    child.on("exit", (code) => {
      if (code !== 0) {
        clearTimeout(timeout);
        reject(new Error(`lock holder exited early with ${code}: ${stderr}`));
      }
    });
  });
}

async function waitForExit(child, { allowNonZero = false } = {}) {
  if (child.exitCode !== null) {
    if (child.exitCode === 0 || allowNonZero) return;
    throw new Error(`lock holder exited with ${child.exitCode}`);
  }
  await new Promise((resolve, reject) => {
    child.on("exit", (code) => (code === 0 || allowNonZero ? resolve(undefined) : reject(new Error(`lock holder exited with ${code}`))));
  });
}

async function cleanupLockTest(child, tempDir) {
  if (child.exitCode === null) {
    child.kill();
    await waitForExit(child, { allowNonZero: true });
  }
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      rmSync(tempDir, { recursive: true, force: true });
      return;
    } catch (error) {
      if (attempt === 4) throw error;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
}

test("chat store waits for a short overlapping SQLite write lock", async () => {
  const tempDir = makeTempDir();
  const child = startLockHolder(path.join(tempDir, "chats.db"));
  let store = null;
  try {
    await waitForLock(child);
    store = createChatStore({ rootDir: tempDir });
    store.save("user-1", "chat-1", "Hallo", [{ role: "user", content: "Hi" }]);
    await waitForExit(child);
    assert.equal(store.get("user-1", "chat-1").title, "Hallo");
  } finally {
    store?.close();
    await cleanupLockTest(child, tempDir);
  }
});

test("memory store waits for a short overlapping SQLite write lock", async () => {
  const tempDir = makeTempDir();
  const child = startLockHolder(path.join(tempDir, "chats.db"));
  let store = null;
  try {
    await waitForLock(child);
    store = createMemoryStore({ rootDir: tempDir });
    store.record("chat-1", "Frage eins", "Antwort eins.");
    await waitForExit(child);
    assert.equal(store.recent(1)[0].user_message, "Frage eins");
  } finally {
    store?.close();
    await cleanupLockTest(child, tempDir);
  }
});
