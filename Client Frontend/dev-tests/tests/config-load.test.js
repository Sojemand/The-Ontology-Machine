import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, loadConfig } from "../../server/config.js";
import { decryptSecret, isEncryptedValue } from "../../server/vault.js";
import { cleanupTempDir, encryptLegacySecret, makeTempDir, writeConfigJson } from "./config-test-fixtures.js";

test("loadConfig returns defaults with empty admin_secret when config.json missing", async () => {
  const tempDir = makeTempDir();
  try {
    const config = await loadConfig(tempDir);
    assert.equal(config.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(config.llm_provider, "openai");
    assert.equal(config.port, 3000);
    assert.equal(config.context_limit, 127096);
    assert.equal(config.admin_secret, "");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig migrates legacy default context_limit to accepted default", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, context_limit: 128000 });
    const config = await loadConfig(tempDir);
    assert.equal(config.context_limit, 127096);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig encrypts plaintext secrets on load and rewrites config.json", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-plaintext-key", admin_secret: "" });
    const config = await loadConfig(tempDir);
    assert.ok(isEncryptedValue(config.llm_api_key));
    assert.ok(isEncryptedValue(JSON.parse(readFileSync(path.join(tempDir, "config.json"), "utf8")).llm_api_key));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig migrates legacy encrypted secrets to portable v2 and keeps them portable", async () => {
  const tempDir = makeTempDir();
  const copiedDir = makeTempDir();
  try {
    const legacy = encryptLegacySecret(tempDir, "sk-legacy-key");
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: legacy });

    const config = await loadConfig(tempDir);
    assert.match(config.llm_api_key, /^enc:v2:/);
    const raw = JSON.parse(readFileSync(path.join(tempDir, "config.json"), "utf8"));
    assert.match(raw.llm_api_key, /^enc:v2:/);

    writeFileSync(path.join(copiedDir, ".salt"), readFileSync(path.join(tempDir, ".salt")));
    assert.equal(decryptSecret(copiedDir, raw.llm_api_key), "sk-legacy-key");
  } finally {
    cleanupTempDir(tempDir);
    cleanupTempDir(copiedDir);
  }
});

test("loadConfig merges saved config with DEFAULT_CONFIG for missing fields", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { customer_name: "TestCo" });
    const config = await loadConfig(tempDir);
    assert.equal(config.customer_name, "TestCo");
    assert.equal(config.llm_provider, DEFAULT_CONFIG.llm_provider);
    assert.equal(config.port, DEFAULT_CONFIG.port);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig keeps a saved llm_model value intact", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { customer_name: "TestCo", llm_model: "gpt-4.1-mini" });
    const config = await loadConfig(tempDir);
    assert.equal(config.llm_model, "gpt-4.1-mini");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig handles corrupted JSON gracefully -- fallback to defaults", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), "NOT-VALID-JSON{{{", "utf8");
    const config = await loadConfig(tempDir);
    assert.equal(config.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(config.admin_secret, "");
  } finally {
    cleanupTempDir(tempDir);
  }
});
