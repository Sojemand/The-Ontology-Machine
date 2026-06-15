import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("agent deduplicates page bundle sources by corpus source identity", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-source-dedupe-");
  insertDocument(fixture.database, {
    id: "doc-1",
    file_name: "mail_case.msg",
    file_path: "mail_case.msg::page=001-of-003",
    content_hash: "sha256:bundle-hash",
    promotions: [{ slot: "mail_title", slot_label: "Mail Title", query_role: "title", display_value: "Mail body", ordinal: 0 }]
  });
  insertDocument(fixture.database, {
    id: "doc-2",
    file_name: "mail_case.msg",
    file_path: "mail_case.msg::page=002-of-003",
    content_hash: "sha256:bundle-hash",
    document_type: "order",
    promotions: [{ slot: "mail_title", slot_label: "Mail Title", query_role: "title", display_value: "Attachment order", ordinal: 0 }]
  });
  fixture.database.close();
  fixture.database = null;

  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, _messages) => ({
      choices: [{
        message: {
          content: _messages.some((message) => message.role === "tool") ? "Es gibt eine passende Quelle." : "",
          tool_calls: _messages.some((message) => message.role === "tool")
            ? []
            : [{
                id: "tool-1",
                type: "function",
                function: { name: "sql_query", arguments: JSON.stringify({ query: "SELECT id, file_name FROM documents ORDER BY id" }) }
              }]
        }
      }]
    })
  });

  try {
    const result = await agent.chat({ message: "Welche Quellen passen?" });
    assert.equal(result.sources.length, 1);
    assert.equal(result.sources[0].source_key, "hash:sha256:bundle-hash");
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("semantic_search fallback ranks document_promotions as top-level facts", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-promotion-search-", `
    ${`
      CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        document_type TEXT,
        category TEXT,
        subcategory TEXT,
        page_count INTEGER DEFAULT 1,
        content_free_text TEXT
      );
    `}
    CREATE TABLE document_promotions (promotion_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT, slot TEXT, slot_label TEXT, value_type TEXT, query_role TEXT, display_value TEXT, ordinal INTEGER, is_current INTEGER DEFAULT 1);
  `);
  insertDocument(fixture.database, {
    id: "doc-promo-search",
    file_name: "artifact.pdf",
    file_path: "page_images/artifact.pdf.hash",
    content_hash: "sha256:promotion-search",
    content_free_text: "",
    promotions: []
  });
  fixture.database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-promo-search", "artifact_code", "Artifact Code", "string", "identifier", "Orbital Seal 77", 0, 1);
  fixture.database.close();
  fixture.database = null;

  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      if (calls.length === 1) {
        return {
          choices: [{
            message: {
              content: "",
              tool_calls: [{
                id: "tool-semantic",
                type: "function",
                function: { name: "semantic_search", arguments: JSON.stringify({ text: "Orbital Seal", limit: 5 }) }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { content: "Promotion gefunden.", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Suche Orbital Seal" });
    const toolPayload = JSON.parse(String(calls[1].find((message) => message.role === "tool")?.content || "{}"));
    assert.equal(toolPayload.fallback.results[0].id, "doc-promo-search");
    assert.match(toolPayload.fallback.results[0].snippet, /Orbital Seal 77/);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});
