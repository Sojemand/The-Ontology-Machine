import assert from "node:assert/strict";
import { createServer } from "node:net";
import { existsSync, linkSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { runCli, startApplication } from "../../server/index.js";
import { cleanupFixture } from "./server-fixtures.js";
import { createSimpleServerFixture, createStubAgent } from "./http-server-fixtures.js";

function createFakeProcess() {
  return {
    handlers: [],
    exitCalls: [],
    once(eventName, handler) {
      this.handlers.push({ eventName, handler });
    },
    exit(code) {
      this.exitCalls.push(code);
    }
  };
}

function createStubApp() {
  return {
    close: async () => {},
    configMode: false,
    serverStatePath: "",
    getPort() {
      return 3000;
    }
  };
}

async function findFreePort() {
  const server = createServer();
  await new Promise((resolve, reject) => server.listen(0, "127.0.0.1", (error) => (error ? reject(error) : resolve(undefined))));
  const port = server.address().port;
  await new Promise((resolve) => server.close(() => resolve(undefined)));
  return port;
}

function createStubPipelineAgent() {
  return {
    ...createStubAgent(),
    initialize() {}
  };
}

test("runCli opens the browser only after the server start succeeds", async () => {
  const calls = [];
  const fakeProcess = createFakeProcess();
  const app = createStubApp();

  const result = await runCli(
    [
      "--config",
      "--open-browser-url",
      "http://127.0.0.1:3001/config",
      "--browser-log-file",
      "browser.log",
      "--session-id",
      "session-1"
    ],
    {
      processObject: fakeProcess,
      startApp: async (options) => {
        calls.push({ type: "start", options });
        return app;
      },
      openBrowser: async (url, options) => {
        calls.push({ type: "browser", url, options });
      },
      logError: (message) => {
        calls.push({ type: "error", message });
      }
    }
  );

  assert.equal(result, app);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].type, "start");
  assert.equal(calls[0].options.configMode, true);
  assert.match(calls[0].options.rootDir, /Client Frontend[\\/]?$/);
  assert.deepEqual(calls[1], {
    type: "browser",
    url: "http://127.0.0.1:3001/config",
    options: { logFile: "browser.log", sessionId: "session-1" }
  });
  assert.equal(fakeProcess.handlers.length, 4);
});

test("runCli does not open the browser when server startup fails", async () => {
  let browserOpened = false;

  await assert.rejects(
    runCli(["--open-browser-url", "http://127.0.0.1:3000"], {
      processObject: createFakeProcess(),
      startApp: async () => {
        throw new Error("listen failed");
      },
      openBrowser: async () => {
        browserOpened = true;
      }
    }),
    /listen failed/
  );

  assert.equal(browserOpened, false);
});

test("runCli keeps the server alive when browser launch fails", async () => {
  const errors = [];
  const app = createStubApp();

  const result = await runCli(
    ["--open-browser-url", "http://127.0.0.1:3000", "--session-id", "session-2"],
    {
      processObject: createFakeProcess(),
      startApp: async () => app,
      openBrowser: async () => {
        throw new Error("launcher missing");
      },
      logError: (message) => {
        errors.push(message);
      }
    }
  );

  assert.equal(result, app);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /\[session-2\] Browser startup failed: launcher missing/);
});

test("startApplication rejects occupied ports without writing stale server state", async () => {
  const portBlocker = createServer();
  await new Promise((resolve, reject) => portBlocker.listen(0, "127.0.0.1", (error) => (error ? reject(error) : resolve(undefined))));
  const occupiedPort = portBlocker.address().port;
  const fixture = createSimpleServerFixture("vp-server-port-collision-", { port: occupiedPort });
  try {
    await assert.rejects(
      startApplication({
        rootDir: fixture.moduleRoot,
        appHome: fixture.appHome,
        createMinimalAgentFn: createStubAgent,
        createOntologyAgentFn: createStubAgent,
        createPipelineManagerAgentFn: createStubPipelineAgent
      }),
      /EADDRINUSE|address already in use/i
    );
    assert.equal(existsSync(path.join(fixture.appHome, "state", "server-chat.json")), false);
  } finally {
    await new Promise((resolve) => portBlocker.close(() => resolve(undefined)));
    cleanupFixture(fixture);
  }
});

test("startApplication replaces server state without writing the final path in place", async (t) => {
  const fixture = createSimpleServerFixture("vp-server-state-", { port: await findFreePort() });
  let app = null;
  try {
    const serverStatePath = path.join(fixture.appHome, "state", "server-chat.json");
    const linkedPath = path.join(fixture.appHome, "state", "linked-server-chat.json");
    writeFileSync(linkedPath, JSON.stringify({ pid: 1, executablePath: "before-node.exe" }, null, 2) + "\n", "utf8");
    try {
      linkSync(linkedPath, serverStatePath);
    } catch (error) {
      t.skip(`hard links unavailable for atomic replacement probe: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }

    app = await startApplication({
      rootDir: fixture.moduleRoot,
      appHome: fixture.appHome,
      createMinimalAgentFn: createStubAgent,
      createOntologyAgentFn: createStubAgent,
      createPipelineManagerAgentFn: createStubPipelineAgent
    });

    const state = JSON.parse(readFileSync(serverStatePath, "utf8"));
    const linkedState = JSON.parse(readFileSync(linkedPath, "utf8"));
    assert.equal(state.port, fixture ? JSON.parse(readFileSync(path.join(fixture.configDir, "config.json"), "utf8")).port : state.port);
    assert.equal(state.configMode, false);
    assert.equal(typeof state.executablePath, "string");
    assert.equal(linkedState.executablePath, "before-node.exe");
    assert.deepEqual(readdirSync(path.dirname(serverStatePath)).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    if (app) {
      await app.close();
    }
    cleanupFixture(fixture);
  }
});
