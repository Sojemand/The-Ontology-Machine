import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, loadConfig } from "../../server/config.js";
import { encryptSecret } from "../../server/vault.js";
import { cleanupTempDir, makeTempDir } from "./config-test-fixtures.js";

test("loadConfig with binary garbage in config.json falls back to defaults", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), Buffer.from([0x00, 0xff, 0xfe, 0x80]));
    assert.equal((await loadConfig(tempDir)).customer_name, DEFAULT_CONFIG.customer_name);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig with empty file falls back to defaults", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), "");
    assert.equal((await loadConfig(tempDir)).customer_name, DEFAULT_CONFIG.customer_name);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig with JSON array instead of object", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), "[1,2,3]");
    assert.equal((await loadConfig(tempDir)).customer_name, DEFAULT_CONFIG.customer_name);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig with null JSON falls back to defaults", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), "null");
    assert.equal((await loadConfig(tempDir)).customer_name, DEFAULT_CONFIG.customer_name);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig does not re-encrypt already encrypted values", async () => {
  const tempDir = makeTempDir();
  try {
    const encrypted = encryptSecret(tempDir, "sk-test-key");
    writeFileSync(path.join(tempDir, "config.json"), JSON.stringify({ ...DEFAULT_CONFIG, llm_api_key: encrypted }), "utf8");
    assert.equal((await loadConfig(tempDir)).llm_api_key, encrypted);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("loadConfig with extra unknown fields preserves them", async () => {
  const tempDir = makeTempDir();
  try {
    writeFileSync(path.join(tempDir, "config.json"), JSON.stringify({ ...DEFAULT_CONFIG, custom_field: "hello", features: { vision: true } }), "utf8");
    const config = await loadConfig(tempDir);
    assert.equal(config.custom_field, "hello");
    assert.deepEqual(config.features, { vision: true });
  } finally {
    cleanupTempDir(tempDir);
  }
});
