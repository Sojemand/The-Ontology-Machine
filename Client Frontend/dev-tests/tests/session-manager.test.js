import assert from "node:assert/strict";
import test from "node:test";

import { createSessionManager } from "../../server/index.js";

test("session manager evicts the least recently touched session", () => {
  const manager = createSessionManager({ maxSessions: 2, ttlMs: 60_000 });

  manager.setHistory("a", [{ role: "user", content: "A" }]);
  manager.touch("a");
  manager.setHistory("b", [{ role: "user", content: "B" }]);
  manager.touch("b");
  manager.touch("a");
  manager.setHistory("c", [{ role: "user", content: "C" }]);
  manager.touch("c");

  assert.equal(manager.getHistory("a").length, 1);
  assert.equal(manager.getHistory("b").length, 0);
  assert.equal(manager.getHistory("c").length, 1);
});

test("runSerialized executes same-session tasks strictly in order", async () => {
  const manager = createSessionManager();
  const order = [];
  let releaseFirst;
  const firstGate = new Promise((resolve) => {
    releaseFirst = resolve;
  });

  const firstTask = manager.runSerialized("same-session", async () => {
    order.push("start:first");
    await firstGate;
    order.push("finish:first");
    return "first";
  });

  const secondTask = manager.runSerialized("same-session", async () => {
    order.push("start:second");
    order.push("finish:second");
    return "second";
  });

  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.deepEqual(order, ["start:first"]);

  releaseFirst();

  assert.equal(await firstTask, "first");
  assert.equal(await secondTask, "second");
  assert.deepEqual(order, ["start:first", "finish:first", "start:second", "finish:second"]);
});

test("runSerialized remains usable after a task rejects", async () => {
  const manager = createSessionManager();
  const order = [];

  await assert.rejects(
    () =>
      manager.runSerialized("same-session", async () => {
        order.push("fail");
        throw new Error("boom");
      }),
    /boom/
  );

  const result = await manager.runSerialized("same-session", async () => {
    order.push("recover");
    return "ok";
  });

  assert.equal(result, "ok");
  assert.deepEqual(order, ["fail", "recover"]);
});

test("runSerialized does not block independent sessions", async () => {
  const manager = createSessionManager();
  const order = [];
  let releaseA;
  const gateA = new Promise((resolve) => {
    releaseA = resolve;
  });

  const taskA = manager.runSerialized("session-a", async () => {
    order.push("start:a");
    await gateA;
    order.push("finish:a");
  });

  const taskB = manager.runSerialized("session-b", async () => {
    order.push("start:b");
    order.push("finish:b");
  });

  await taskB;
  assert.deepEqual(order, ["start:a", "start:b", "finish:b"]);

  releaseA();
  await taskA;
  assert.deepEqual(order, ["start:a", "start:b", "finish:b", "finish:a"]);
});

