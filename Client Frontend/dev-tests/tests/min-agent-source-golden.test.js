import assert from "node:assert/strict";
import test from "node:test";

import { createMinimalAgent } from "../../server/min_agent.js";
import { createMinimalRepository } from "../../client_frontend/min_agent/repository.js";
import { extractDocIdsFromRows, extractSourceHintsFromText } from "../../client_frontend/min_agent/source_domain.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture, insertDocument } from "./min-agent-test-fixtures.js";

test("semantic search returns lexical fallback sources when embeddings are empty", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-semantic-fallback-");
  insertDocument(fixture.database, {
    document_type: "report",
    category: "technical",
    promotions: [{ slot: "report_title", slot_label: "Report Title", query_role: "title", display_value: "Machbarkeitsuntersuchung", ordinal: 0 }],
    content_free_text: "Abhitzekessel Deckelentfernung Ammoniakanlage Katalysatorstaub"
  });
  fixture.database.close();
  fixture.database = null;
  const toolPayloads = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      const toolMessage = messages.find((message) => message.role === "tool");
      if (toolMessage) {
        toolPayloads.push(JSON.parse(toolMessage.content));
        return { choices: [{ message: { content: "Ich finde ein Dokument mit Chemiebezug.", tool_calls: [] } }] };
      }
      return {
        choices: [{
          message: {
            content: "",
            tool_calls: [{ id: "tool-1", type: "function", function: { name: "semantic_search", arguments: JSON.stringify({ text: "Welche Dokumente haben Chemiebezug?", limit: 5 }) } }]
          }
        }]
      };
    }
  });
  try {
    const result = await agent.chat({ message: "Welche Dokumente haben Chemiebezug?" });
    assert.equal(toolPayloads[0].available, false);
    assert.equal(toolPayloads[0].fallback.results.length, 1);
    assert.equal(result.sources.length, 1);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("agent does not infer sources from final answer text alone", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-answer-sources-");
  insertDocument(fixture.database, {
    content_hash: "sha256:bbbbbbbb",
    document_type: "report",
    category: "other",
    subcategory: "note",
    promotions: [
      { slot: "answer_title", slot_label: "Answer Title", query_role: "title", display_value: "Alpha", ordinal: 0 },
      { slot: "answer_actor", slot_label: "Answer Actor", query_role: "actor", display_value: "ACME", ordinal: 1 }
    ],
    content_free_text: "Antwortquelle"
  });
  fixture.database.close();
  fixture.database = null;
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async () => ({
      choices: [{ message: { content: "Bitte pruefen Sie alpha.pdf {{cite:doc:doc-1}} fuer die Details.", tool_calls: [] } }]
    })
  });
  try {
    const result = await agent.chat({ message: "Welche Datei ist relevant?" });
    assert.equal(result.sources.length, 0);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("SQL row source extraction keeps typed document references sourceable", () => {
  const docIds = extractDocIdsFromRows([
    {
      target_id: "node_preconscious_intention_formation",
      evidence_ref_type: "document",
      evidence_ref_id: "book.pdf.p015.of102"
    },
    {
      target_id: "node_source_level",
      evidence_ref_type: "source_document",
      evidence_ref_id: "../../source/book.pdf"
    },
    {
      subject_ref_type: "document",
      subject_ref_id: "book.pdf.p010.of102",
      object_ref_type: "node",
      object_ref_id: "node_ignored"
    },
    {
      source_ref_type: "document",
      source_ref_id: "book.pdf.p047.of102"
    },
    {
      target_document_id: "book.pdf.p016.of102",
      source_document_id: "../../source/book.pdf"
    }
  ]);

  assert.deepEqual(docIds, [
    "book.pdf.p015.of102",
    "book.pdf.p010.of102",
    "book.pdf.p047.of102",
    "book.pdf.p016.of102"
  ]);
});

test("JSON source hint extraction keeps typed document references sourceable", () => {
  const hints = extractSourceHintsFromText(JSON.stringify({
    rows: [
      {
        target_id: "assertion-1",
        evidence_ref_type: "document",
        evidence_ref_id: "book.pdf.p015.of102"
      },
      {
        evidence_ref_type: "source_document",
        evidence_ref_id: "../../source/book.pdf"
      },
      {
        first_document_id: "book.pdf.p001.of102",
        source_document_id: "../../source/book.pdf"
      }
    ]
  }));

  assert.ok(hints.some((hint) => hint.type === "id" && hint.value === "book.pdf.p015.of102"));
  assert.ok(hints.some((hint) => hint.type === "id" && hint.value === "book.pdf.p001.of102"));
  assert.equal(hints.some((hint) => hint.type === "id" && hint.value === "../../source/book.pdf"), false);
});

test("source display falls back to file name and opens page-scoped images at the source page", () => {
  const fixture = createTempAgentFixture("vp-min-agent-source-display-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      source_page INTEGER,
      source_page_count INTEGER,
      content_hash TEXT NOT NULL,
      document_type TEXT,
      page_count INTEGER DEFAULT 1
    );
    CREATE TABLE document_promotions (
      promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id TEXT,
      slot TEXT,
      slot_label TEXT,
      value_type TEXT,
      query_role TEXT,
      display_value TEXT,
      ordinal INTEGER,
      is_current INTEGER DEFAULT 1
    );
    CREATE TABLE document_page_images (
      document_id TEXT,
      page INTEGER,
      content_type TEXT,
      image_blob BLOB
    );
  `);
  fixture.database.prepare("INSERT INTO documents (id, file_name, file_path, source_page, source_page_count, content_hash, document_type, page_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-page-14", "fantasy-story.pdf", "fantasy-story.pdf::page=014-of-026", 14, 26, "sha256:story", "story", 26);
  fixture.database.prepare("INSERT INTO document_promotions (document_id, slot, slot_label, value_type, query_role, display_value, ordinal, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .run("doc-page-14", "document_themes", "Themes", "string", "secondary", "This is document text, not a display title.", 0, 1);
  fixture.database.prepare("INSERT INTO document_page_images (document_id, page, content_type, image_blob) VALUES (?, ?, ?, ?)")
    .run("doc-page-14", 14, "image/png", Buffer.from([0x89, 0x50, 0x4e, 0x47]));
  fixture.database.close();
  fixture.database = null;

  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });
  try {
    const source = repository.buildSource("doc-page-14");
    assert.equal(source.title, "fantasy-story.pdf");
    assert.equal(source.page, 14);
    assert.equal(source.page_count, 26);
    assert.equal(source.image_url, "/api/image/doc-page-14/14");
    assert.equal(source.viewer_available, true);
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});
