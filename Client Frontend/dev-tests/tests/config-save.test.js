import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, saveConfig, saveConfigState } from "../../server/config.js";
import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";
import { cleanupTempDir, makeTempDir } from "./config-test-fixtures.js";

test("saveConfig normalizes provider -- unknown becomes openai-compatible custom provider", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, llm_provider: "unknown", embedding_provider: "mammouth" }, DEFAULT_CONFIG);
    assert.equal(saved.llm_provider, "openai_compat");
    assert.equal(saved.embedding_provider, "mammouth");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig normalizes theme -- unknown becomes dark", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, theme: "neon" }, DEFAULT_CONFIG);
    const savedLight = await saveConfig(tempDir, { ...DEFAULT_CONFIG, theme: "light" }, DEFAULT_CONFIG);
    assert.equal(saved.theme, "dark");
    assert.equal(savedLight.theme, "light");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig normalizes port -- invalid values fallback to 3000", async () => {
  const tempDir = makeTempDir();
  try {
    for (const badPort of [0, -1, 1023, 65536, "abc", null]) {
      const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: badPort }, DEFAULT_CONFIG);
      assert.equal(saved.port, 3000, `port ${badPort} should fallback to 3000`);
    }
    const validSave = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 8080 }, DEFAULT_CONFIG);
    assert.equal(validSave.port, 8080);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig migrates legacy default context_limit to accepted default", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, context_limit: 128000 }, DEFAULT_CONFIG);
    assert.equal(saved.context_limit, 127096);
    assert.equal(JSON.parse(readFileSync(path.join(tempDir, "config.json"), "utf8")).context_limit, 127096);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig ignores extra unknown fields in payload", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, unknown_field: "hello", another: 42 }, DEFAULT_CONFIG);
    assert.equal(saved.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(JSON.parse(readFileSync(path.join(tempDir, "config.json"), "utf8")).unknown_field, undefined);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig persists llm_model", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, llm_model: "gpt-5.4-mini" }, DEFAULT_CONFIG);
    assert.equal(saved.llm_model, "gpt-5.4-mini");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig persists sql_database_path and normalizes empty input back to explicit unconfigured state", async () => {
  const tempDir = makeTempDir();
  try {
    const customPath = "C:\\Corpus\\customer\\corpus.db";
    const savedCustom = await saveConfig(tempDir, { ...DEFAULT_CONFIG, sql_database_path: `  ${customPath}  ` }, DEFAULT_CONFIG);
    assert.equal(savedCustom.sql_database_path, customPath);

    const resetToDefault = await saveConfig(tempDir, { ...DEFAULT_CONFIG, sql_database_path: "   " }, savedCustom);
    assert.equal(resetToDefault.sql_database_path, "");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfigState preserves pipeline_root when saving a partial state payload", async () => {
  const tempDir = makeTempDir();
  try {
    const currentConfig = {
      ...DEFAULT_CONFIG,
      sql_database_path: "C:\\Corpus\\customer\\corpus.db",
      pipeline_root: "F:\\Ontology Machine",
      port: 4242,
      theme: "light"
    };
    const saved = await saveConfigState(tempDir, { frontend_policy: buildDefaultFrontendPolicy() }, currentConfig);

    assert.equal(saved.config.sql_database_path, currentConfig.sql_database_path);
    assert.equal(saved.config.pipeline_root, currentConfig.pipeline_root);
    assert.equal(saved.config.port, currentConfig.port);
    assert.equal(saved.config.theme, currentConfig.theme);
  } finally {
    cleanupTempDir(tempDir);
  }
});
