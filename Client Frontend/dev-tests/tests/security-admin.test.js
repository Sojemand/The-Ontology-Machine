import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

test("path traversal under /assets is blocked", async () => {
  const fixture = createSimpleServerFixture("vp-sec-");
  writeFileSync(path.join(fixture.moduleRoot, "secret.txt"), "TOP SECRET DATA");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/assets/%2e%2e/secret.txt`);
    if (res.status === 200) {
      assert.ok(!(await res.text()).includes("TOP SECRET"));
    }
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("admin update-key is blocked without the configured secret", async () => {
  const fixture = createSimpleServerFixture("vp-sec-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/admin/update-key`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer wrong-token" },
      body: JSON.stringify({ llm_api_key: "sk-hack" })
    });
    assert.equal(res.status, 403);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("tampered admin cookie cannot unlock protected config routes", async () => {
  const fixture = createSimpleServerFixture("vp-sec-", { admin_secret: "admin-pass" });
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const unlockRes = await fetch(`${baseUrl}/config/api/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret: "admin-pass" })
    });
    assert.equal(unlockRes.status, 200);

    const cookie = extractCookie(unlockRes);
    const tamperedCookie = cookie.replace(/.$/, (char) => (char === "0" ? "1" : "0"));
    const saveRes = await fetch(`${baseUrl}/config/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Cookie: tamperedCookie },
      body: JSON.stringify({ customer_name: "Tampered" })
    });
    assert.equal(saveRes.status, 403);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
