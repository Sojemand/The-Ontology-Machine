import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("oversized request body returns 413", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "x".repeat(300_000) })
    });
    assert.equal(res.status, 413);
    assert.match((await res.json()).error, /too large/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("malformed JSON body returns 400", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{\"message\":"
    });
    assert.equal(res.status, 400);
    assert.match((await res.json()).error, /valid JSON/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("malformed cookies do not crash the health route", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    for (const cookie of [";;;", "=value", "key=", "no-equals-sign", "vp_session=", "a".repeat(10000)]) {
      const res = await fetch(`${baseUrl}/api/v2/health`, { headers: { Cookie: cookie } });
      assert.equal(res.status, 200);
    }
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("weird document ids on /api/v2/documents do not crash the server", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/v2/documents/${encodeURIComponent("Ä_Ö_Ü_ß_日本語.pdf")}`)).status, 404);
    assert.equal((await fetch(`${baseUrl}/api/v2/documents/${"a".repeat(5000)}`)).status, 404);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("bad percent-encoding on history and image routes returns 400", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/chat/history/%E0%A4%A`)).status, 400);
    assert.equal((await fetch(`${baseUrl}/api/image/%E0%A4%A/1`)).status, 400);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("invalid image page values return 400", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    for (const page of ["0", "-1", "1.5", "banana"]) {
      const res = await fetch(`${baseUrl}/api/image/doc-1/${page}`);
      assert.equal(res.status, 400);
      assert.match((await res.json()).error, /positive integer/i);
    }
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("image route rejects missing or extra path segments", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    assert.equal((await fetch(`${baseUrl}/api/image/doc-1`)).status, 400);
    const extraSegment = await fetch(`${baseUrl}/api/image/doc-1/1/extra`);
    assert.equal(extraSegment.status, 400);
    assert.match((await extraSegment.json()).error, /document ID and page/i);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
