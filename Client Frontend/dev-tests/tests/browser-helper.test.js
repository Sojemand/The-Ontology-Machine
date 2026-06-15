import assert from "node:assert/strict";
import test from "node:test";

import { openUrlInBrowser, waitForReady } from "../../runtime/open-browser-when-ready.js";

test("waitForReady retries until the probe succeeds", async () => {
  let attempts = 0;

  const result = await waitForReady("http://127.0.0.1:3000/api/v2/health", {
    attempts: 5,
    intervalMs: 0,
    sleepFn: async () => {},
    probe: async () => {
      attempts += 1;
      if (attempts < 3) {
        return { ok: false, statusCode: 503 };
      }
      return { ok: true, statusCode: 200 };
    }
  });

  assert.equal(attempts, 3);
  assert.deepEqual(result, { ok: true, statusCode: 200 });
});

test("waitForReady throws after the final failed probe", async () => {
  await assert.rejects(
    waitForReady("http://127.0.0.1:3000/api/v2/health", {
      attempts: 2,
      intervalMs: 0,
      sleepFn: async () => {},
      probe: async () => ({ ok: false, statusCode: 503 })
    }),
    /Server wurde nicht rechtzeitig bereit/
  );
});

test("openUrlInBrowser falls back to the next Windows launcher", async () => {
  const calls = [];

  const launcher = await openUrlInBrowser("http://127.0.0.1:3000", {
    platform: "win32",
    spawnProcess(command, args, options) {
      calls.push({ command, args, options });
      if (calls.length === 1) {
        throw new Error("explorer missing");
      }
      return {
        unref() {}
      };
    }
  });

  assert.equal(launcher.command, "rundll32.exe");
  assert.deepEqual(
    calls.map((entry) => entry.command),
    ["explorer.exe", "rundll32.exe"]
  );
  assert.equal(calls[1].options.detached, true);
  assert.equal(calls[1].options.windowsHide, true);
});

test("openUrlInBrowser rejects non-Windows platforms", async () => {
  await assert.rejects(
    openUrlInBrowser("http://127.0.0.1:3000", { platform: "linux" }),
    /nur unter Windows/
  );
});

