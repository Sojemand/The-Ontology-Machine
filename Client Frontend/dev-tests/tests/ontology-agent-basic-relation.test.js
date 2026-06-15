import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { buildSchemaSummary } from "../../client_frontend/min_agent/schema_summary.js";
import { ONTOLOGY_TOOL_DEFINITIONS } from "../../client_frontend/ontology_agent/types.js";
import { createOntologyAgent } from "../../client_frontend/ontology_agent/workflow.js";

import { cleanupFixture, createFixture } from "../support/ontology-agent-fixtures.js";

test("schema summary exposes CHECK constraints so agents can see enum values", () => {
  const fixture = createFixture();
  const database = new DatabaseSync(fixture.dbPath);
  try {
    const summary = buildSchemaSummary(database);
    assert.match(summary, /ontology_lenses\(.*status.*\) CHECKS:.*status IN \('draft', 'ready', 'archived'\)/s);
    assert.match(summary, /ontology_activation\(.*is_active.*is_primary.*\) CHECKS:.*is_active IN \(0, 1\).*is_primary IN \(0, 1\)/s);
  } finally {
    database.close();
    cleanupFixture(fixture);
  }
});

test("basic_relation_mining tool exposes no database path parameter", () => {
  const tool = ONTOLOGY_TOOL_DEFINITIONS.find((definition) => definition?.function?.name === "basic_relation_mining");
  assert.ok(tool);
  assert.deepEqual(Object.keys(tool.function.parameters.properties), ["dry_run"]);
  assert.equal(tool.function.parameters.additionalProperties, false);
});

test("ontology agent runs basic_relation_mining against configured DB path", async () => {
  const fixture = createFixture();
  let capturedArgs = null;
  let completionCalls = 0;
  const agent = createOntologyAgent({
    dbPath: fixture.dbPath,
    dataDir: fixture.dataDir,
    pipelineRoot: "C:\\OntologyMachine",
    stateRoot: path.join(fixture.tempDir, "kernel-state"),
    runtimeConfig: { context_limit: 128_000 },
    embedTextsFn: async (_runtimeConfig, texts) => texts.map(() => [0.1, 0.2]),
    runBasicRelationMiningFn: async (args) => {
      capturedArgs = args;
      return {
        ok: true,
        status: "pass",
        database_path: args.dbPath,
        dry_run: args.dryRun,
        report: { source_documents: 1, source_document_pages: 1, relations: 0, warnings: [] }
      };
    },
    createChatCompletionFn: async (_runtimeConfig, _messages, tools) => {
      completionCalls += 1;
      if (completionCalls === 1) {
        assert.ok(tools.find((definition) => definition?.function?.name === "basic_relation_mining"));
        return {
          choices: [{
            message: {
              role: "assistant",
              content: "",
              tool_calls: [{
                id: "call-basic-relation-mining",
                type: "function",
                function: {
                  name: "basic_relation_mining",
                  arguments: JSON.stringify({ dry_run: false, database_path: "F:\\wrong\\corpus.db" })
                }
              }]
            }
          }]
        };
      }
      return { choices: [{ message: { role: "assistant", content: "Base Graph construction completed." } }] };
    }
  });

  try {
    const result = await agent.chat({ message: "starte mal die base db construction" });
    assert.equal(result.method, "ontology_agent");
    assert.equal(result.answer, "Base Graph construction completed.");
    assert.equal(capturedArgs.dbPath, fixture.dbPath);
    assert.equal(capturedArgs.dryRun, false);
    assert.equal(Object.hasOwn(capturedArgs, "database_path"), false);
  } finally {
    agent.close();
    cleanupFixture(fixture);
  }
});
