import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { clearStaleServerPort, isAllowedExecutablePath, parseNetstatPortOwners } from "../../tools/clear-stale-server-port.mjs";

const BUNDLED_NODE = "C:\\Apps\\Sachbearbeiter\\node\\node.exe";

test("isAllowedExecutablePath compares Windows paths case-insensitively", () => {
  assert.equal(isAllowedExecutablePath("c:/apps/sachbearbeiter/node/NODE.exe", BUNDLED_NODE), true);
  assert.equal(isAllowedExecutablePath("C:\\Other\\node.exe", BUNDLED_NODE), false);
});

test("clearStaleServerPort leaves a free port alone", async () => {
  let queried = 0;
  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    queryOwners: async () => {
      queried += 1;
      return [];
    }
  });

  assert.equal(queried, 1);
  assert.deepEqual(result, { killed: [] });
});

test("parseNetstatPortOwners detects localized listening rows", () => {
  const output = [
    "  Proto  Lokale Adresse         Remoteadresse          Status           PID",
    "  TCP    127.0.0.1:3000         0.0.0.0:0              ABHOEREN         3360",
    "  TCP    127.0.0.1:3000         127.0.0.1:54000        HERGESTELLT      3360",
    "  TCP    [::1]:3001             [::]:0                 LISTENING        4455"
  ].join("\n");

  assert.deepEqual(parseNetstatPortOwners(output, 3000), [{ pid: 3360, processName: null, path: null }]);
  assert.deepEqual(parseNetstatPortOwners(output, 3001), [{ pid: 4455, processName: null, path: null }]);
});

test("clearStaleServerPort kills bundled stale server processes and waits for release", async () => {
  const killed = [];
  let queryCount = 0;
  const staleOwner = { pid: 1234, processName: "node", path: BUNDLED_NODE };

  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    sleepFn: async () => {},
    queryOwners: async () => {
      queryCount += 1;
      return queryCount < 3 ? [staleOwner] : [];
    },
    killProcess: async (pid) => {
      killed.push(pid);
    }
  });

  assert.deepEqual(killed, [1234]);
  assert.deepEqual(result, { killed: [staleOwner] });
});

test("clearStaleServerPort refuses to kill foreign port owners", async () => {
  await assert.rejects(
    clearStaleServerPort({
      port: 3000,
      allowedExecutablePath: BUNDLED_NODE,
      queryOwners: async () => [{ pid: 4321, processName: "node", path: "C:\\Other\\node.exe" }],
      killProcess: async () => {
        throw new Error("should not kill");
      }
    }),
    /fremden Prozess/
  );
});

test("clearStaleServerPort refuses node owners without resolved path", async () => {
  const killed = [];
  let queryCount = 0;
  await assert.rejects(
    clearStaleServerPort({
      port: 3000,
      allowedExecutablePath: BUNDLED_NODE,
      sleepFn: async () => {},
      queryOwners: async () => {
        queryCount += 1;
        return [{ pid: 4321, processName: "node", path: null }];
      },
      killProcess: async (pid) => {
        killed.push(pid);
      },
      releaseAttempts: 2,
      releaseIntervalMs: 0
    }),
    /nicht eindeutig zugeordneten Prozess/
  );

  assert.equal(queryCount, 1);
  assert.deepEqual(killed, []);
});

test("clearStaleServerPort fails if the stale process does not release the port", async () => {
  await assert.rejects(
    clearStaleServerPort({
      port: 3000,
      allowedExecutablePath: BUNDLED_NODE,
      releaseAttempts: 2,
      releaseIntervalMs: 0,
      sleepFn: async () => {},
      queryOwners: async () => [{ pid: 1234, processName: "node", path: BUNDLED_NODE }],
      killProcess: async () => {}
    }),
    /nicht rechtzeitig frei/
  );
});

test("clearStaleServerPort kills a recorded stale server process before checking the port", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-clear-port-"));
  const serverStateFile = path.join(tempDir, "server-chat.json");
  writeFileSync(
    serverStateFile,
    JSON.stringify({
      pid: 2222,
      executablePath: BUNDLED_NODE
    }),
    "utf8"
  );
  const killed = [];
  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    serverStateFile,
    queryOwners: async () => [],
    queryProcessInfoByPid: async (pid) => ({ pid, processName: "node", path: BUNDLED_NODE }),
    killProcess: async (pid) => {
      killed.push(pid);
    }
  });

  assert.deepEqual(killed, [2222]);
  assert.deepEqual(result, { killed: [] });
});

test("clearStaleServerPort trusts recorded state when process path is unresolved", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-clear-port-"));
  const serverStateFile = path.join(tempDir, "server-chat.json");
  writeFileSync(
    serverStateFile,
    JSON.stringify({
      pid: 2223,
      executablePath: BUNDLED_NODE
    }),
    "utf8"
  );
  const killed = [];
  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    serverStateFile,
    queryOwners: async () => [],
    queryProcessInfoByPid: async (pid) => ({ pid, processName: "node", path: null }),
    killProcess: async (pid) => {
      killed.push(pid);
    }
  });

  assert.deepEqual(killed, [2223]);
  assert.deepEqual(result, { killed: [] });
});

test("clearStaleServerPort removes a stale server state file when the recorded process is gone", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-clear-port-"));
  const serverStateFile = path.join(tempDir, "server-chat.json");
  writeFileSync(serverStateFile, JSON.stringify({ pid: 3333, executablePath: BUNDLED_NODE }), "utf8");

  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    serverStateFile,
    queryOwners: async () => [],
    queryProcessInfoByPid: async () => null
  });

  assert.deepEqual(result, { killed: [] });
});

test("clearStaleServerPort removes a stale server state file when process lookup yields only an empty placeholder", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-clear-port-"));
  const serverStateFile = path.join(tempDir, "server-chat.json");
  writeFileSync(serverStateFile, JSON.stringify({ pid: 4444, executablePath: BUNDLED_NODE }), "utf8");

  const result = await clearStaleServerPort({
    port: 3000,
    allowedExecutablePath: BUNDLED_NODE,
    serverStateFile,
    queryOwners: async () => [],
    queryProcessInfoByPid: async (pid) => ({ pid, processName: null, path: null })
  });

  assert.deepEqual(result, { killed: [] });
});
