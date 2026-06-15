import assert from "node:assert/strict";
import test from "node:test";

import { createLoopbackCallbackServer } from "../../client_frontend/credentials/oauth_callback.js";

test("OAuth loopback ignores non-callback paths without consuming the login", async () => {
  const seen = [];
  const server = createLoopbackCallbackServer({
    port: 0,
    returnUrl: "http://127.0.0.1/config",
    onCallback: async (params) => {
      seen.push(String(params.get("code") || ""));
    }
  });

  try {
    await server.start();
    const wrongUrl = server.callback_url.replace("/auth/callback", "/favicon.ico");
    const wrongRes = await fetch(wrongUrl, { redirect: "manual" });
    assert.equal(wrongRes.status, 404);
    assert.deepEqual(seen, []);

    const callbackRes = await fetch(`${server.callback_url}?code=ok&state=state-1`, { redirect: "manual" });
    assert.equal(callbackRes.status, 302);
    assert.deepEqual(seen, ["ok"]);
  } finally {
    await server.close().catch(() => {});
  }
});
