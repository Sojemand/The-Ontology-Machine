import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_CONFIG,
  getMaskedConfig,
  loadConfig,
  resolveRuntimeConfig,
  saveConfig,
  updateSecrets
} from "../../server/config.js";
import { isEncryptedValue } from "../../server/vault.js";
import { cleanupTempDir, makeTempDir, writeConfigJson } from "./config-test-fixtures.js";

test("resolveRuntimeConfig decrypts all SECRET_FIELDS", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-test-123", admin_secret: "mypass" });
    const runtime = resolveRuntimeConfig(tempDir, await loadConfig(tempDir));
    assert.equal(runtime.llm_api_key, "sk-test-123");
    assert.equal(runtime.admin_secret, "mypass");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("resolveRuntimeConfig returns empty string for missing secret fields", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "", embedding_api_key: "", admin_secret: "" });
    const runtime = resolveRuntimeConfig(tempDir, await loadConfig(tempDir));
    assert.equal(runtime.llm_api_key, "");
    assert.equal(runtime.embedding_api_key, "");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("getMaskedConfig replaces secrets with configured or empty string", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-real", embedding_api_key: "", admin_secret: "pass" });
    const masked = getMaskedConfig(tempDir, await loadConfig(tempDir));
    assert.equal(masked.llm_api_key, "configured");
    assert.equal(masked.embedding_api_key, "");
    assert.equal(masked.admin_secret, "configured");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig encrypts incoming secret fields", async () => {
  const tempDir = makeTempDir();
  try {
    const saved = await saveConfig(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-new-key" }, DEFAULT_CONFIG);
    assert.ok(isEncryptedValue(saved.llm_api_key));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("saveConfig preserves existing secret when incoming is empty", async () => {
  const tempDir = makeTempDir();
  try {
    const first = await saveConfig(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-first" }, DEFAULT_CONFIG);
    const second = await saveConfig(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "" }, first);
    assert.equal(second.llm_api_key, first.llm_api_key);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("updateSecrets encrypts only non-empty incoming fields", async () => {
  const tempDir = makeTempDir();
  try {
    writeConfigJson(tempDir, { ...DEFAULT_CONFIG, llm_api_key: "sk-old", admin_secret: "old-pass" });
    const config = await loadConfig(tempDir);
    const updated = await updateSecrets(tempDir, config, { llm_api_key: "sk-new", admin_secret: "" });
    assert.notEqual(updated.llm_api_key, config.llm_api_key);
    assert.ok(isEncryptedValue(updated.llm_api_key));
    assert.equal(updated.admin_secret, config.admin_secret);
  } finally {
    cleanupTempDir(tempDir);
  }
});
