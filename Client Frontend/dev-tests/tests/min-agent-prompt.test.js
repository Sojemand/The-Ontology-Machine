import assert from "node:assert/strict";
import test from "node:test";

import { TOOL_DEFINITIONS } from "../../client_frontend/min_agent/types.js";
import { createMinimalAgent } from "../../server/min_agent.js";
import { cleanupAgentFixture, createRuntimeConfig, createTempAgentFixture } from "./min-agent-test-fixtures.js";

test("agent includes soul context as a separate system prompt block", async () => {
  const fixture = createTempAgentFixture("vp-min-agent-soul-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      content_hash TEXT NOT NULL,
      page_count INTEGER DEFAULT 1
    );
  `);
  fixture.database.close();
  fixture.database = null;

  const calls = [];
  const agent = createMinimalAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    soulContext: "Name: Herr M.\nStil: Direkt, freundlich, unaufgeregt",
    runtimeConfig: createRuntimeConfig(),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      calls.push(messages);
      return { choices: [{ message: { content: "Keine passenden Dokumente gefunden.", tool_calls: [] } }] };
    }
  });

  try {
    await agent.chat({ message: "Test" });
    const systemPrompt = String(calls[0]?.[0]?.content || "");
    assert.match(systemPrompt, /Corpus size hint: This corpus contains approximately 0 documents\./);
    assert.match(systemPrompt, /do not rely on semantic_search samples/i);
    assert.match(systemPrompt, /document_promotions.*top-level semantic fact surface/i);
    assert.match(systemPrompt, /document_payloads\.normalized_json/);
    assert.match(systemPrompt, /Use get_provenance when the user asks where a fact came from/i);
    assert.match(systemPrompt, /Tool routing:/);
    assert.match(systemPrompt, /help the user narrow or clarify the request/i);
    assert.match(systemPrompt, /Ontology lenses are an integral part of the corpus DB and its meaning/);
    assert.match(systemPrompt, /database overviews, corpus summaries, comparison questions, detail questions and interpretive answers/);
    assert.match(systemPrompt, /even when the user did not explicitly ask for ontology/);
    assert.match(systemPrompt, /correction, audit, review, critique or corrected DB view/);
    assert.match(systemPrompt, /contradict materialized facts/);
    assert.match(systemPrompt, /For real page totals.*count source_document_pages or structural_units/i);
    assert.match(systemPrompt, /Never sum documents\.page_count or documents\.source_page_count/i);
    assert.match(systemPrompt, /Citation contract override:/);
    assert.match(systemPrompt, /\{\{cite:doc:<page_level_document_id>\}\}/);
    assert.match(systemPrompt, /Do not use file_name-only citations, source_document_id-only citations/i);
    assert.match(systemPrompt, /Soul context:/);
    assert.match(systemPrompt, /Name: Herr M\./);
    assert.match(systemPrompt, /Stil: Direkt, freundlich, unaufgeregt/);
  } finally {
    agent.close();
    cleanupAgentFixture(fixture);
  }
});

test("query agent ontology tools describe lenses as integral DB meaning", () => {
  const listTool = TOOL_DEFINITIONS.find((tool) => tool?.function?.name === "list_ontology_lenses");
  const getTool = TOOL_DEFINITIONS.find((tool) => tool?.function?.name === "get_ontology_lens");

  assert.ok(listTool);
  assert.ok(getTool);
  assert.match(listTool.function.description, /integral DB meaning/i);
  assert.match(listTool.function.description, /even if the user did not explicitly ask for ontology/i);
  assert.match(getTool.function.description, /DB overviews, corpus summaries, comparisons, detail questions and interpretive answers/);
  assert.match(getTool.function.description, /interpretive DB context/);
});

test("query agent tool text prevents page-wise page_count overcounting", () => {
  const sqlTool = TOOL_DEFINITIONS.find((tool) => tool?.function?.name === "sql_query");
  const coverageTool = TOOL_DEFINITIONS.find((tool) => tool?.function?.name === "database_coverage_snapshot");

  assert.ok(sqlTool);
  assert.ok(coverageTool);
  assert.match(sqlTool.function.description, /count source_document_pages or structural_units/i);
  assert.match(sqlTool.function.description, /never sum documents\.page_count or documents\.source_page_count/i);
  assert.match(coverageTool.function.description, /not SUM\(documents\.page_count\)/i);
});
