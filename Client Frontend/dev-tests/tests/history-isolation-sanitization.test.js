import assert from "node:assert/strict";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture, createStubAgent } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

test("chat and history payloads do not leak internal filesystem fields", async () => {
  const fixture = createSimpleServerFixture("vp-history-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, createMinimalAgentFn: () => createStubAgent() });
  const baseUrl = await listen(app.server);

  try {
    const chatResponse = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "show sources" })
    });
    const cookie = extractCookie(chatResponse);
    const chatBody = await chatResponse.json();
    assert.equal(chatBody.sources[0].file_name, "alpha.pdf");
    assert.equal("file_path" in chatBody.sources[0], false);
    assert.equal("page_images" in chatBody.sources[0], false);

    const historyResponse = await fetch(`${baseUrl}/api/chat/history`, { headers: cookie ? { Cookie: cookie } : {} });
    const chatId = (await historyResponse.json()).chats[0].id;
    const detailResponse = await fetch(`${baseUrl}/api/chat/history/${encodeURIComponent(chatId)}`, {
      headers: cookie ? { Cookie: cookie } : {}
    });
    const storedSource = (await detailResponse.json()).messages.at(-1).sources[0];
    assert.equal(storedSource.file_name, "alpha.pdf");
    assert.equal("file_path" in storedSource, false);
    assert.equal("page_images" in storedSource, false);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
