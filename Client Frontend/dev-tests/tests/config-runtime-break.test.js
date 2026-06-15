import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_CONFIG, getMaskedConfig, resolveRuntimeConfig, updateSecrets } from "../../server/config.js";
import { decryptSecret, encryptSecret, isEncryptedValue } from "../../server/vault.js";
import { cleanupTempDir, makeTempDir } from "./config-test-fixtures.js";

test("resolveRuntimeConfig with empty config returns empty secrets", () => {
  const tempDir = makeTempDir();
  try {
    const runtime = resolveRuntimeConfig(tempDir, { ...DEFAULT_CONFIG });
    assert.equal(runtime.llm_api_key, "");
    assert.equal(runtime.embedding_api_key, "");
    assert.equal(runtime.admin_secret, "");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("resolveRuntimeConfig preserves non-secret fields", () => {
  const tempDir = makeTempDir();
  try {
    const runtime = resolveRuntimeConfig(tempDir, { ...DEFAULT_CONFIG, customer_name: "MyCompany", port: 4000, theme: "light" });
    assert.equal(runtime.customer_name, "MyCompany");
    assert.equal(runtime.port, 4000);
    assert.equal(runtime.theme, "light");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("getMaskedConfig does not leak actual secret values", () => {
  const tempDir = makeTempDir();
  try {
    const masked = getMaskedConfig(tempDir, { ...DEFAULT_CONFIG, llm_api_key: encryptSecret(tempDir, "sk-real-api-key-12345") });
    assert.equal(masked.llm_api_key, "configured");
    assert.ok(!JSON.stringify(masked).includes("sk-real-api-key"));
    assert.ok(!JSON.stringify(masked).includes("enc:v"));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("updateSecrets ignores non-secret fields", async () => {
  const tempDir = makeTempDir();
  try {
    const updated = await updateSecrets(tempDir, { ...DEFAULT_CONFIG }, { customer_name: "Hacker", port: 9999, llm_api_key: "sk-new" });
    assert.equal(updated.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(updated.port, DEFAULT_CONFIG.port);
    assert.ok(isEncryptedValue(updated.llm_api_key));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("updateSecrets handles all three secret fields simultaneously", async () => {
  const tempDir = makeTempDir();
  try {
    const updated = await updateSecrets(tempDir, { ...DEFAULT_CONFIG }, { llm_api_key: "sk-llm", embedding_api_key: "sk-embed", admin_secret: "admin-pass" });
    assert.ok(isEncryptedValue(updated.llm_api_key));
    assert.ok(isEncryptedValue(updated.embedding_api_key));
    assert.ok(isEncryptedValue(updated.admin_secret));
    assert.equal(decryptSecret(tempDir, updated.llm_api_key), "sk-llm");
    assert.equal(decryptSecret(tempDir, updated.embedding_api_key), "sk-embed");
    assert.equal(decryptSecret(tempDir, updated.admin_secret), "admin-pass");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("updateSecrets with whitespace-only values does not update", async () => {
  const tempDir = makeTempDir();
  try {
    const original = encryptSecret(tempDir, "original");
    const updated = await updateSecrets(tempDir, { ...DEFAULT_CONFIG, llm_api_key: original }, { llm_api_key: "   " });
    assert.equal(updated.llm_api_key, original);
  } finally {
    cleanupTempDir(tempDir);
  }
});
