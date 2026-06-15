import assert from "node:assert/strict";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture, createStubAgent } from "./http-server-fixtures.js";
import { cleanupFixture, extractCookie, listen } from "./server-fixtures.js";

function parseCookieHeader(cookieHeader) {
  return new Map(
    String(cookieHeader || "")
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const separatorIndex = part.indexOf("=");
        return separatorIndex >= 0 ? [part.slice(0, separatorIndex), part.slice(separatorIndex + 1)] : [part, ""];
      })
  );
}

test("chat history is isolated per owner and foreign access is blocked", async () => {
  const fixture = createSimpleServerFixture("vp-history-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, createMinimalAgentFn: () => createStubAgent() });
  const baseUrl = await listen(app.server);

  try {
    const chatResponse = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "secret from A" })
    });
    assert.equal(chatResponse.status, 200);
    const cookieA = extractCookie(chatResponse);

    const ownerList = await fetch(`${baseUrl}/api/chat/history`, { headers: cookieA ? { Cookie: cookieA } : {} });
    const chatId = (await ownerList.json()).chats?.[0]?.id;
    assert.ok(chatId);

    const foreignList = await fetch(`${baseUrl}/api/chat/history`);
    assert.deepEqual((await foreignList.json()).chats, []);
    assert.equal((await fetch(`${baseUrl}/api/chat/history/${encodeURIComponent(chatId)}`)).status, 404);
    assert.equal((await fetch(`${baseUrl}/api/chat/restore/${encodeURIComponent(chatId)}`, { method: "POST" })).status, 404);
    assert.equal((await fetch(`${baseUrl}/api/chat/history/${encodeURIComponent(chatId)}`, { method: "DELETE" })).status, 404);
    assert.equal((await fetch(`${baseUrl}/api/chat/history/${encodeURIComponent(chatId)}`, { headers: { Cookie: cookieA } })).status, 200);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("unsigned or tampered vp_user cookies no longer grant history access", async () => {
  const fixture = createSimpleServerFixture("vp-history-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, createMinimalAgentFn: () => createStubAgent() });
  const baseUrl = await listen(app.server);

  try {
    const chatResponse = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "secret from A" })
    });
    const signedUser = parseCookieHeader(extractCookie(chatResponse)).get("vp_user");
    assert.ok(signedUser);

    const unsignedUser = signedUser.slice(0, signedUser.lastIndexOf("."));
    const tamperedUser = `${signedUser.slice(0, -1)}${signedUser.endsWith("0") ? "1" : "0"}`;

    const unsignedList = await fetch(`${baseUrl}/api/chat/history`, { headers: { Cookie: `vp_user=${unsignedUser}` } });
    const tamperedList = await fetch(`${baseUrl}/api/chat/history`, { headers: { Cookie: `vp_user=${tamperedUser}` } });
    assert.deepEqual((await unsignedList.json()).chats, []);
    assert.deepEqual((await tamperedList.json()).chats, []);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("legacy owner-less chats stay hidden from scoped history", async () => {
  const fixture = createSimpleServerFixture("vp-history-");
  const db = new DatabaseSync(path.join(fixture.stateDir, "chats.db"));
  db.exec(`
    CREATE TABLE IF NOT EXISTS chats (
      id TEXT PRIMARY KEY,
      owner_id TEXT NOT NULL DEFAULT '',
      title TEXT NOT NULL DEFAULT '',
      messages TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    )
  `);
  db.prepare(`
    INSERT INTO chats (id, owner_id, title, messages, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run("legacy-chat", "", "Legacy", JSON.stringify([{ role: "user", content: "legacy" }]), Date.now(), Date.now());
  db.close();
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome, createMinimalAgentFn: () => createStubAgent() });
  const baseUrl = await listen(app.server);

  try {
    const chatResponse = await fetch(`${baseUrl}/api/v2/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "visible chat" })
    });
    const cookie = extractCookie(chatResponse);
    const historyResponse = await fetch(`${baseUrl}/api/chat/history`, { headers: cookie ? { Cookie: cookie } : {} });
    const body = await historyResponse.json();
    assert.equal(body.chats.length, 1);
    assert.equal(body.chats[0].title, "visible chat");
    assert.ok(!body.chats.some((chat) => chat.id === "legacy-chat"));
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
