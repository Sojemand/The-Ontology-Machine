import assert from "node:assert/strict";
import test from "node:test";

import { buildOntologySystemPrompt } from "../../client_frontend/ontology_agent/policy.js";
import { ONTOLOGY_TOOL_DEFINITIONS } from "../../client_frontend/ontology_agent/types.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

test("ontology system prompt distinguishes lens status from activation", () => {
  const prompt = buildOntologySystemPrompt({ schemaSummary: "ontology_lenses(status)\nontology_activation(is_active, is_primary)" });
  assert.match(prompt, /ontology_lenses\.status is only one of draft, ready, archived/);
  assert.match(prompt, /Never write active or inactive into ontology_lenses\.status/);
  assert.match(prompt, /active\/primary state lives only in ontology_activation/);
  assert.match(prompt, /scope = 'corpus', scope_ref = 'self', is_active = 1, is_primary = 1/);
});

test("ontology system prompt frames the agent as an ontology architect", () => {
  const prompt = buildOntologySystemPrompt({ schemaSummary: "ontology_lenses(status)" });
  assert.match(prompt, /careful local ontology engineer/);
  assert.match(prompt, /Support the user as an ontology architect/);
  assert.match(prompt, /Notice uncertainty, hidden assumptions and under-specified intent/);
  assert.match(prompt, /what an ontology is/);
  assert.match(prompt, /Translate user intent into factual semantic material/);
  assert.match(prompt, /For real page totals.*count source_document_pages or structural_units/i);
  assert.match(prompt, /Never sum documents\.page_count or documents\.source_page_count/i);
  assert.match(prompt, /Use compact document views before heavy document reads/i);
  assert.match(prompt, /get_document_summary first/i);
  assert.match(prompt, /get_document_ontology_evidence for lens\/evidence work/i);
  assert.match(prompt, /Citation contract override:/);
  assert.match(prompt, /\{\{cite:doc:<page_level_document_id>\}\}/);
  assert.match(prompt, /Do not use file_name-only citations, source_document_id-only citations/i);
  assert.doesNotMatch(prompt, /\[1\]|\[10\]/);
  assert.match(prompt, /Preflight repair loop:/);
  assert.match(prompt, /up to three repair rounds/i);
  assert.doesNotMatch(prompt, /ontology_mining_run/);
});

test("ontology system prompt keeps sectioned schema and filters conflicting shared rules", () => {
  const prompt = buildOntologySystemPrompt({
    schemaSummary: "ontology_lenses(status)",
    frontendPolicy: {
      min_agent: {
        prompt: {
          answer_rules: [
            "If a tool returns an error, repair the query.",
            "This environment is local and read-only.",
            "You do not have a mandate to modify corpus data or local files while answering database questions.",
            "Always name the source where you found the information using the document file name. Do not use any other source format.",
            "Do not expose chain-of-thought or hidden internal reasoning."
          ].join("\n")
        }
      }
    }
  });
  assert.match(prompt, /^Identity:/m);
  assert.match(prompt, /^Ontology mission:/m);
  assert.match(prompt, /^Intent architecture:/m);
  assert.match(prompt, /^Working method:/m);
  assert.match(prompt, /^Tool routing:/m);
  assert.match(prompt, /^Foreign-key write order:/m);
  assert.match(prompt, /^Required insert contract:/m);
  assert.match(prompt, /^Write discipline:/m);
  assert.match(prompt, /^Preflight repair loop:/m);
  assert.match(prompt, /^Answer rules:/m);
  assert.match(prompt, /Write ontology rows parent-first/);
  assert.match(prompt, /Create ontology_nodes before ontology_edges/);
  assert.match(prompt, /ontology_terms are vocabulary labels/);
  assert.match(prompt, /preflight checks table columns/i);
  assert.match(prompt, /ontology_evidence_links: evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id/);
  assert.match(prompt, /Never use NULL, empty string, rowid, or omitted primary-key fields/);
  assert.match(prompt, /If a tool returns an error, repair the query/);
  assert.match(prompt, /Do not expose chain-of-thought/);
  assert.doesNotMatch(prompt, /local and read-only/);
  assert.doesNotMatch(prompt, /mandate to modify/);
  assert.doesNotMatch(prompt, /using the document file name/);
});

test("ontology system prompt uses configured ontology prompt sections", () => {
  const frontendPolicy = buildDefaultFrontendPolicy();
  frontendPolicy.ontology_agent.prompt.identity = "Custom ontology identity.";
  frontendPolicy.ontology_agent.prompt.mission = "Custom ontology mission.";
  const prompt = buildOntologySystemPrompt({
    schemaSummary: "ontology_lenses(status)",
    frontendPolicy
  });

  assert.match(prompt, /Custom ontology identity\./);
  assert.match(prompt, /Custom ontology mission\./);
});

test("sql_batch_execute tool text exposes the required insert contract", () => {
  const tool = ONTOLOGY_TOOL_DEFINITIONS.find((definition) => definition?.function?.name === "sql_batch_execute");
  assert.ok(tool);
  assert.match(tool.function.description, /Required insert contract/);
  assert.match(tool.function.description, /explicit column list and explicit VALUES/);
  assert.match(tool.function.description, /ontology_evidence_links: evidence_link_id, ontology_id, target_type, target_id, evidence_ref_type, evidence_ref_id/);
  assert.match(tool.function.description, /Never use NULL, empty string, rowid, or omitted primary-key fields/);
  assert.match(tool.function.description, /ontology_nodes are graph objects and the only valid ontology_edges endpoints/);
  assert.match(tool.function.description, /returns error_type='ontology_write_preflight' with repairable=true/);
  assert.match(tool.function.description, /if post-write validation fails, do not continue writing new ontology content/i);
});

test("ontology agent tool text prevents page-wise page_count overcounting", () => {
  const basicMiningTool = ONTOLOGY_TOOL_DEFINITIONS.find((definition) => definition?.function?.name === "basic_relation_mining");
  const sqlTool = ONTOLOGY_TOOL_DEFINITIONS.find((definition) => definition?.function?.name === "sql_query");

  assert.ok(basicMiningTool);
  assert.ok(sqlTool);
  assert.match(basicMiningTool.function.description, /real page totals.*source_document_pages/i);
  assert.match(basicMiningTool.function.description, /not by summing documents\.page_count\/source_page_count/i);
  assert.match(sqlTool.function.description, /never sum documents\.page_count or documents\.source_page_count/i);
});

test("ontology agent exposes compact document view tools", () => {
  const names = new Set(ONTOLOGY_TOOL_DEFINITIONS.map((definition) => definition?.function?.name));
  assert.equal(names.has("get_document_summary"), true);
  assert.equal(names.has("get_document_ontology_evidence"), true);
  assert.equal(names.has("get_document_rows"), true);
  assert.equal(names.has("get_document_provenance"), true);
  assert.equal(names.has("get_document_full"), true);
});
