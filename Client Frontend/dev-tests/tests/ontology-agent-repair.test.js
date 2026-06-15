import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { createOntologyAgent } from "../../client_frontend/ontology_agent/workflow.js";

import { cleanupFixture, createFixture } from "../support/ontology-agent-fixtures.js";

test("ontology agent repairs repairable preflight write failures inside the same call", async () => {
  const fixture = createFixture();
  let completionCalls = 0;
  let sawRepairInstruction = false;
  const agent = createOntologyAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: { context_limit: 128_000, embedding_model: "test-embedding" },
    validatePatchFn: async () => ({ status: "pass", checks: [], warnings: [], errors: [] }),
    embedTextsFn: async (_runtimeConfig, texts) => texts.map(() => [0.1, 0.2]),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      completionCalls += 1;
      if (completionCalls === 1) {
        return {
          choices: [{
            message: {
              role: "assistant",
              content: "",
              tool_calls: [{
                id: "call-bad-write",
                type: "function",
                function: {
                  name: "sql_batch_execute",
                  arguments: JSON.stringify({
                    ontology_id: "lens_repaired",
                    edit_summary: "Create lens with bad timestamp column",
                    statements: [{
                      sql: "INSERT INTO ontology_lenses (ontology_id, name, CURRENT_TIMESTAMP) VALUES (?, ?, CURRENT_TIMESTAMP)",
                      params: ["lens_repaired", "Repaired Lens"]
                    }]
                  })
                }
              }]
            }
          }]
        };
      }
      if (completionCalls === 2) {
        const transcript = messages.map((entry) => String(entry.content || "")).join("\n");
        const serializedMessages = JSON.stringify(messages);
        assert.match(transcript, /\[internal ontology write repair 1\/3\]/);
        assert.match(transcript, /ontology_write_preflight/);
        assert.match(serializedMessages, /compacted_sql_batch_execute/);
        assert.doesNotMatch(serializedMessages, /INSERT INTO ontology_lenses \(ontology_id, name, CURRENT_TIMESTAMP\)/);
        sawRepairInstruction = true;
        return {
          choices: [{
            message: {
              role: "assistant",
              content: "",
              tool_calls: [{
                id: "call-repaired-write",
                type: "function",
                function: {
                  name: "sql_batch_execute",
                  arguments: JSON.stringify({
                    ontology_id: "lens_repaired",
                    edit_summary: "Create lens after preflight repair",
                    statements: [{
                      sql: "INSERT INTO ontology_lenses (ontology_id, name, status, intent_json) VALUES (?, ?, ?, ?)",
                      params: ["lens_repaired", "Repaired Lens", "ready", "{}"]
                    }]
                  })
                }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { role: "assistant", content: "Die Linse ist repariert und angelegt." } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Lege die Linse an." });
    assert.equal(result.answer, "Die Linse ist repariert und angelegt.");
    assert.equal(completionCalls, 3);
    assert.equal(sawRepairInstruction, true);
    assert.doesNotMatch(result.answer, /ontology_write_preflight/);
  } finally {
    agent.close();
  }
  const database = new DatabaseSync(fixture.dbPath);
  try {
    assert.equal(database.prepare("SELECT status FROM ontology_lenses WHERE ontology_id = ?").get("lens_repaired")?.status, "ready");
  } finally {
    database.close();
    cleanupFixture(fixture);
  }
});

test("ontology agent compacts successful sql_batch_execute receipts in follow-up model context", async () => {
  const fixture = createFixture();
  let completionCalls = 0;
  const agent = createOntologyAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    runtimeConfig: { context_limit: 128_000, embedding_model: "test-embedding" },
    validatePatchFn: async () => ({ status: "pass", checks: [], warnings: [], errors: [] }),
    embedTextsFn: async (_runtimeConfig, texts) => texts.map(() => [0.1, 0.2]),
    createChatCompletionFn: async (_runtimeConfig, messages) => {
      completionCalls += 1;
      if (completionCalls === 1) {
        return {
          choices: [{
            message: {
              role: "assistant",
              content: "",
              tool_calls: [{
                id: "call-good-write",
                type: "function",
                function: {
                  name: "sql_batch_execute",
                  arguments: JSON.stringify({
                    ontology_id: "lens_success_receipt",
                    edit_summary: "Create lens with a long successful SQL batch",
                    statements: [{
                      sql: "INSERT INTO ontology_lenses (ontology_id, name, status, intent_json) VALUES (?, ?, ?, ?)",
                      params: ["lens_success_receipt", "Successful Receipt Lens", "ready", "{}"]
                    }]
                  })
                }
              }]
            }
          }]
        };
      }
      const serializedMessages = JSON.stringify(messages);
      const toolMessage = messages.find((entry) => entry.role === "tool" && entry.tool_call_id === "call-good-write");
      const receipt = JSON.parse(toolMessage.content);
      const assistantMessage = messages.find((entry) => entry.role === "assistant" && entry.tool_calls?.[0]?.id === "call-good-write");
      const compactedArguments = JSON.parse(assistantMessage.tool_calls[0].function.arguments);
      assert.equal(receipt.compacted_sql_batch_execute, true);
      assert.equal(receipt.status, "success");
      assert.match(receipt.edit_unit_id, /^oeu_/);
      assert.equal(receipt.validation.status, "pass");
      assert.equal(compactedArguments.compacted_sql_batch_execute, true);
      assert.doesNotMatch(serializedMessages, /INSERT INTO ontology_lenses \(ontology_id, name, status, intent_json\)/);
      return { choices: [{ message: { role: "assistant", content: "Die erfolgreiche Linse ist angelegt." } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "Lege die Linse an." });
    assert.equal(result.answer, "Die erfolgreiche Linse ist angelegt.");
    assert.equal(completionCalls, 2);
  } finally {
    agent.close();
  }
  const database = new DatabaseSync(fixture.dbPath);
  try {
    assert.equal(database.prepare("SELECT status FROM ontology_lenses WHERE ontology_id = ?").get("lens_success_receipt")?.status, "ready");
  } finally {
    database.close();
    cleanupFixture(fixture);
  }
});
