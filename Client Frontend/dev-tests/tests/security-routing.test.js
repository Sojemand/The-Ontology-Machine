import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("legacy chat endpoint is gone", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/chat`)).status, 404);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("heartbeat endpoint is gone and the server stays up without browser pings", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/heartbeat`, { method: "POST" })).status, 404);
    t.mock.timers.tick(11_000);
    assert.equal((await fetch(`${baseUrl}/api/v2/health`)).status, 200);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("method mismatches still return 404", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/v2/chat`)).status, 404);
    assert.equal((await fetch(`${baseUrl}/api/v2/health`, { method: "POST" })).status, 404);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("content types stay stable", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.match((await fetch(`${baseUrl}/api/v2/health`)).headers.get("content-type"), /application\/json/);
    assert.match((await fetch(`${baseUrl}/`)).headers.get("content-type"), /text\/html/);
    assert.match((await fetch(`${baseUrl}/config`)).headers.get("content-type"), /text\/html/);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
