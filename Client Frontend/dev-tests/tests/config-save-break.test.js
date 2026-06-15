import assert from "node:assert/strict";
import { linkSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, saveConfig } from "../../server/config.js";
import { buildDefaultFrontendPolicy, saveFrontendPolicy } from "../../server/frontend_policy.js";
import { cleanupTempDir, makeTempDir } from "./config-test-fixtures.js";

test("saveConfig with null payload values uses fallbacks", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, {
      customer_name: null,
      llm_base_url: null,
      llm_model: null,
      embedding_base_url: null,
      embedding_model: null,
      port: null,
      theme: null,
      llm_provider: null,
      embedding_provider: null
    }, { ...DEFAULT_CONFIG });
    assert.equal(saved.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(saved.llm_base_url, DEFAULT_CONFIG.llm_base_url);
    assert.equal(saved.port, DEFAULT_CONFIG.port);
    assert.equal(saved.theme, "dark");
    assert.equal(saved.llm_provider, "openai");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig with undefined payload values uses fallbacks", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, {}, { ...DEFAULT_CONFIG });
    assert.equal(saved.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(saved.port, DEFAULT_CONFIG.port);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig with port boundary values", async () => {
  const tempDir = makeTempDir();
  try {
    let saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 1024 }, { ...DEFAULT_CONFIG });
    assert.equal(saved.port, 1024);
    saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 65535 }, { ...DEFAULT_CONFIG });
    assert.equal(saved.port, 65535);
    saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 1023 }, { ...DEFAULT_CONFIG });
    assert.equal(saved.port, DEFAULT_CONFIG.port);
    saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 65536 }, { ...DEFAULT_CONFIG });
    assert.equal(saved.port, DEFAULT_CONFIG.port);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig rejects float, NaN and Infinity ports", async () => {
  const tempDir = makeTempDir();
  try {
    assert.equal((await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: 3000.5 }, { ...DEFAULT_CONFIG })).port, DEFAULT_CONFIG.port);
    assert.equal((await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: NaN }, { ...DEFAULT_CONFIG })).port, DEFAULT_CONFIG.port);
    assert.equal((await saveConfig(tempDir, { ...DEFAULT_CONFIG, port: Infinity }, { ...DEFAULT_CONFIG })).port, DEFAULT_CONFIG.port);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig with very long customer_name", async () => {
  const tempDir = makeTempDir();
  try {
    const longName = "A".repeat(10000);
    assert.equal((await saveConfig(tempDir, { ...DEFAULT_CONFIG, customer_name: longName }, { ...DEFAULT_CONFIG })).customer_name, longName);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig with whitespace-only customer_name falls back to existing", async () => {
  const tempDir = makeTempDir();
  try {
    const existing = { ...DEFAULT_CONFIG, customer_name: "ExistingCo" };
    assert.equal((await saveConfig(tempDir, { ...existing, customer_name: "   " }, existing)).customer_name, "ExistingCo");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig writes valid JSON to disk", async () => {
  const tempDir = makeTempDir();
  try {
    await saveConfig(tempDir, { ...DEFAULT_CONFIG, customer_name: "Test\nNewline\tTab" }, { ...DEFAULT_CONFIG });
    assert.equal(JSON.parse(readFileSync(path.join(tempDir, "config.json"), "utf8")).customer_name, "Test\nNewline\tTab");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig replaces config without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const configPath = path.join(tempDir, "config.json");
    const linkedPath = path.join(tempDir, "linked-config.json");
    const initialConfig = { ...DEFAULT_CONFIG, customer_name: "BeforeCo", sql_database_path: "C:\\Corpus\\before.db" };
    writeFileSync(linkedPath, `${JSON.stringify(initialConfig, null, 2)}\n`, "utf8");
    try {
      linkSync(linkedPath, configPath);
    } catch (error) {
      t.skip(`hard links unavailable for atomic replacement probe: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }

    await saveConfig(
      tempDir,
      { ...DEFAULT_CONFIG, customer_name: "AfterCo", sql_database_path: "C:\\Corpus\\after.db" },
      initialConfig
    );

    const savedConfig = JSON.parse(readFileSync(configPath, "utf8"));
    const linkedConfig = JSON.parse(readFileSync(linkedPath, "utf8"));
    assert.equal(savedConfig.customer_name, "AfterCo");
    assert.equal(savedConfig.sql_database_path, "C:\\Corpus\\after.db");
    assert.equal(linkedConfig.customer_name, "BeforeCo");
    assert.equal(linkedConfig.sql_database_path, "C:\\Corpus\\before.db");
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.(tmp|bak|cfg|fp)-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveFrontendPolicy replaces policy without writing the final path in place", async (t) => {
  const tempDir = makeTempDir();
  try {
    const policyPath = path.join(tempDir, "frontend_policy.json");
    const linkedPath = path.join(tempDir, "linked-frontend-policy.json");
    const beforePolicy = buildDefaultFrontendPolicy();
    beforePolicy.chat_history.max_history = 41;
    const afterPolicy = buildDefaultFrontendPolicy();
    afterPolicy.chat_history.max_history = 42;
    writeFileSync(linkedPath, `${JSON.stringify(beforePolicy, null, 2)}\n`, "utf8");
    try {
      linkSync(linkedPath, policyPath);
    } catch (error) {
      t.skip(`hard links unavailable for atomic replacement probe: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }

    await saveFrontendPolicy(tempDir, afterPolicy);

    const savedPolicy = JSON.parse(readFileSync(policyPath, "utf8"));
    const linkedPolicy = JSON.parse(readFileSync(linkedPath, "utf8"));
    assert.equal(savedPolicy.chat_history.max_history, 42);
    assert.equal(linkedPolicy.chat_history.max_history, 41);
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.(tmp|bak|cfg|fp)-/.test(name)), []);
  } finally {
    cleanupTempDir(tempDir);
  }
});
