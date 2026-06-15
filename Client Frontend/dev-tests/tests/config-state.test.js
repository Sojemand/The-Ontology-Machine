import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, loadConfigState, saveConfigState } from "../../server/config.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import {
  cleanupTempDir,
  makeTempDir,
  readConfigJson,
  readFrontendPolicyJson,
  writeConfigJson,
  writeFrontendPolicyJson
} from "./config-test-fixtures.js";

test("loadConfigState auto-creates missing frontend_policy.json", async () => {
  const tempDir = makeTempDir();
  try {
    const result = await loadConfigState(tempDir);
    assert.equal(result.frontendPolicyDiagnostics, null);
    assert.deepEqual(result.frontendPolicy, buildDefaultFrontendPolicy());
    assert.deepEqual(readFrontendPolicyJson(tempDir), buildDefaultFrontendPolicy());
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState migrates legacy default frontend_policy model seeds", async () => {
  const tempDir = makeTempDir();
  try {
    const legacyPolicy = buildDefaultFrontendPolicy();
    legacyPolicy.model_catalog.llm_seed_models = [
      "gpt-5.4-pro",
      "gpt-5.4",
      "gpt-5.4-mini",
      "gpt-5.4-nano",
      "gpt-5",
      "gpt-5-mini",
      "gpt-5-nano",
      "gpt-4.1"
    ];
    legacyPolicy.model_catalog.embedding_seed_models = ["text-embedding-3-small"];
    writeFrontendPolicyJson(tempDir, legacyPolicy);

    const loaded = await loadConfigState(tempDir);
    const migratedFile = readFrontendPolicyJson(tempDir);
    const defaults = buildDefaultFrontendPolicy();

    assert.equal(loaded.frontendPolicyDiagnostics, null);
    assert.deepEqual(loaded.frontendPolicy.model_catalog.llm_seed_models, defaults.model_catalog.llm_seed_models);
    assert.deepEqual(loaded.frontendPolicy.model_catalog.embedding_seed_models, defaults.model_catalog.embedding_seed_models);
    assert.deepEqual(migratedFile.model_catalog.llm_seed_models, defaults.model_catalog.llm_seed_models);
    assert.deepEqual(migratedFile.model_catalog.embedding_seed_models, defaults.model_catalog.embedding_seed_models);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState preserves custom frontend_policy model seeds", async () => {
  const tempDir = makeTempDir();
  try {
    const customPolicy = buildDefaultFrontendPolicy();
    customPolicy.model_catalog.llm_seed_models = ["local-custom-model", "gpt-5.4"];
    customPolicy.model_catalog.embedding_seed_models = ["local-custom-embedding"];
    writeFrontendPolicyJson(tempDir, customPolicy);

    const loaded = await loadConfigState(tempDir);

    assert.equal(loaded.frontendPolicyDiagnostics, null);
    assert.deepEqual(loaded.frontendPolicy.model_catalog.llm_seed_models, customPolicy.model_catalog.llm_seed_models);
    assert.deepEqual(loaded.frontendPolicy.model_catalog.embedding_seed_models, customPolicy.model_catalog.embedding_seed_models);
    assert.deepEqual(readFrontendPolicyJson(tempDir).model_catalog.llm_seed_models, customPolicy.model_catalog.llm_seed_models);
    assert.deepEqual(readFrontendPolicyJson(tempDir).model_catalog.embedding_seed_models, customPolicy.model_catalog.embedding_seed_models);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState migrates the legacy file-name-only source prompt rule", async () => {
  const tempDir = makeTempDir();
  try {
    const legacyPolicy = buildDefaultFrontendPolicy();
    legacyPolicy.min_agent.prompt.answer_rules = legacyPolicy.min_agent.prompt.answer_rules.replace(
      /When citing corpus evidence[\s\S]*?Use citation tokens as the only machine-readable source link format\./,
      "Always name the source where you found the information using the document file name. Do not use any other source format."
    );
    writeFrontendPolicyJson(tempDir, legacyPolicy);

    const loaded = await loadConfigState(tempDir);
    const migratedRules = loaded.frontendPolicy.min_agent.prompt.answer_rules;

    assert.equal(loaded.frontendPolicyDiagnostics, null);
    assert.doesNotMatch(migratedRules, /document file name\. Do not use any other source format/);
    assert.match(migratedRules, /\{\{cite:doc:<page_level_document_id>\}\}/);
    assert.match(readFrontendPolicyJson(tempDir).min_agent.prompt.answer_rules, /citation token/);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState migrates legacy bracket source prompt examples", async () => {
  const tempDir = makeTempDir();
  try {
    const legacyPolicy = buildDefaultFrontendPolicy();
    const currentLine = "Use citation tokens as the only machine-readable source link format.";
    const legacyLine = "Do not use bracket citations like [1] or [10] for sources; they are not machine-readable source references.";
    legacyPolicy.min_agent.prompt.answer_rules = legacyPolicy.min_agent.prompt.answer_rules.replace(currentLine, legacyLine);
    legacyPolicy.ontology_agent.prompt.answer_rules = legacyPolicy.ontology_agent.prompt.answer_rules.replace(currentLine, legacyLine);
    writeFrontendPolicyJson(tempDir, legacyPolicy);

    const loaded = await loadConfigState(tempDir);
    const migratedFile = readFrontendPolicyJson(tempDir);

    assert.equal(loaded.frontendPolicyDiagnostics, null);
    assert.doesNotMatch(loaded.frontendPolicy.min_agent.prompt.answer_rules, /\[1\]|\[10\]/);
    assert.doesNotMatch(loaded.frontendPolicy.ontology_agent.prompt.answer_rules, /\[1\]|\[10\]/);
    assert.match(migratedFile.min_agent.prompt.answer_rules, /only machine-readable source link format/);
    assert.match(migratedFile.ontology_agent.prompt.answer_rules, /only machine-readable source link format/);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfigState roundtrips config.json and frontend_policy.json together", async () => {
  const tempDir = makeTempDir();
  try {
    const frontendPolicy = buildDefaultFrontendPolicy();
    frontendPolicy.chat_history.max_history = 7;
    const saved = await saveConfigState(tempDir, { ...DEFAULT_CONFIG, customer_name: "ACME", frontend_policy: frontendPolicy }, DEFAULT_CONFIG);
    assert.equal(saved.config.customer_name, "ACME");
    assert.equal(saved.frontendPolicy.chat_history.max_history, 7);
    assert.equal(readConfigJson(tempDir).customer_name, "ACME");
    assert.equal(readFrontendPolicyJson(tempDir).chat_history.max_history, 7);
    const loaded = await loadConfigState(tempDir);
    assert.equal(loaded.frontendPolicy.chat_history.max_history, 7);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState fills ontology_agent prompt for legacy frontend_policy files", async () => {
  const tempDir = makeTempDir();
  try {
    const legacyPolicy = buildDefaultFrontendPolicy();
    delete legacyPolicy.ontology_agent;
    writeFrontendPolicyJson(tempDir, legacyPolicy);

    const loaded = await loadConfigState(tempDir);

    assert.equal(loaded.frontendPolicyDiagnostics, null);
    assert.equal(typeof loaded.frontendPolicy.ontology_agent.prompt.identity, "string");
    assert.equal(loaded.frontendPolicy.ontology_agent.prompt.identity.length > 0, true);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfigState rejects unknown frontend_policy keys fail-closed", async () => {
  const tempDir = makeTempDir();
  try {
    const frontendPolicy = { ...buildDefaultFrontendPolicy(), rogue_flag: true };
    await assert.rejects(
      () => saveConfigState(tempDir, { ...DEFAULT_CONFIG, frontend_policy: frontendPolicy }, DEFAULT_CONFIG),
      /invalid or missing keys/i
    );
    assert.throws(() => readFrontendPolicyJson(tempDir));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfigState surfaces invalid frontend_policy diagnostics without overwriting the file", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "frontend_policy.json"), JSON.stringify({ rogue_flag: true }), "utf8");
    const result = await loadConfigState(tempDir);
    assert.equal(result.frontendPolicyDiagnostics?.status, "invalid_policy");
    assert.equal(result.frontendPolicyDiagnostics?.policy_path, "frontend_policy");
    assert.match(result.frontendPolicyDiagnostics?.message || "", /invalid or missing keys/i);
    assert.deepEqual(readFrontendPolicyJson(tempDir), { rogue_flag: true });
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfigState restores config.json when frontend_policy promotion fails", async () => {
  const tempDir = makeTempDir();
  const originalDateNow = Date.now;
  const originalRandom = Math.random;
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, customer_name: "Stable Customer" });
    writeFrontendPolicyJson(tempDir, buildDefaultFrontendPolicy());
    Date.now = () => 1000;
    Math.random = () => 0.5;
    mkdirSync(path.join(tempDir, ".fp-rs-i.bak"), { recursive: true });
    const nextPolicy = buildDefaultFrontendPolicy();
    nextPolicy.chat_history.max_history = 2;
    await assert.rejects(
      () => saveConfigState(tempDir, { ...DEFAULT_CONFIG, customer_name: "Broken Save", frontend_policy: nextPolicy }, DEFAULT_CONFIG)
    );
    assert.equal(readConfigJson(tempDir).customer_name, "Stable Customer");
    assert.equal(readFrontendPolicyJson(tempDir).chat_history.max_history, 100);
  } finally {
    Date.now = originalDateNow;
    Math.random = originalRandom;
    cleanupTempDir(tempDir);
  }
});
