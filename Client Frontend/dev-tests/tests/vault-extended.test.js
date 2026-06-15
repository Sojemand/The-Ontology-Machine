import assert from "node:assert/strict";
import { existsSync, linkSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  decryptSecret,
  encryptSecret,
  isEncryptedValue,
  isLegacyEncryptedValue,
  maskSecret,
  migrateEncryptedSecret,
  signScopedValue,
  verifySignedValue
} from "../../server/vault.js";
import { readSalt, writeSalt } from "../../client_frontend/vault/repository.js";
import { encryptLegacySecret } from "./vault-legacy-support.js";

test("encryptSecret returns empty string for null/undefined/whitespace input", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    assert.equal(encryptSecret(tempDir, null), "");
    assert.equal(encryptSecret(tempDir, undefined), "");
    assert.equal(encryptSecret(tempDir, ""), "");
    assert.equal(encryptSecret(tempDir, "   "), "");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("encryptSecret creates .salt file when missing", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    assert.equal(existsSync(path.join(tempDir, ".salt")), false);
    encryptSecret(tempDir, "test-secret");
    assert.equal(existsSync(path.join(tempDir, ".salt")), true);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("encryptSecret produces different ciphertext for same plaintext (random IV)", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    const a = encryptSecret(tempDir, "same-secret");
    const b = encryptSecret(tempDir, "same-secret");
    assert.notEqual(a, b, "two encryptions of the same value should differ due to random IV");
    assert.equal(decryptSecret(tempDir, a), "same-secret");
    assert.equal(decryptSecret(tempDir, b), "same-secret");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("portable secrets stay readable after copying .salt to a second root", () => {
  const firstDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-a-"));
  const secondDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-b-"));
  try {
    const encrypted = encryptSecret(firstDir, "portable-secret");
    writeFileSync(path.join(secondDir, ".salt"), readFileSync(path.join(firstDir, ".salt")));
    assert.equal(decryptSecret(secondDir, encrypted), "portable-secret");
  } finally {
    rmSync(firstDir, { recursive: true, force: true });
    rmSync(secondDir, { recursive: true, force: true });
  }
});

test("decryptSecret still supports legacy v1 ciphertext for migration", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-legacy-"));
  try {
    const encrypted = encryptLegacySecret(tempDir, "legacy-secret");
    assert.equal(decryptSecret(tempDir, encrypted), "legacy-secret");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("isLegacyEncryptedValue only matches the legacy v1 prefix", () => {
  assert.equal(isLegacyEncryptedValue("enc:v1:aes256gcm:abc"), true);
  assert.equal(isLegacyEncryptedValue("enc:v2:aes256gcm:abc"), false);
  assert.equal(isLegacyEncryptedValue("plain-text"), false);
});

test("migrateEncryptedSecret rewrites legacy ciphertext to portable v2 and no-ops otherwise", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-legacy-"));
  try {
    const legacy = encryptLegacySecret(tempDir, "legacy-secret");
    const migrated = migrateEncryptedSecret(tempDir, legacy);
    const current = encryptSecret(tempDir, "portable-secret");

    assert.equal(isLegacyEncryptedValue(migrated), false);
    assert.equal(isEncryptedValue(migrated), true);
    assert.equal(decryptSecret(tempDir, migrated), "legacy-secret");
    assert.equal(migrateEncryptedSecret(tempDir, current), current);
    assert.equal(migrateEncryptedSecret(tempDir, "plain-text"), "plain-text");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("decryptSecret returns empty string for null/empty input", () => {
  assert.equal(decryptSecret("/unused", null), "");
  assert.equal(decryptSecret("/unused", ""), "");
});

test("decryptSecret passes through non-encrypted string unchanged", () => {
  assert.equal(decryptSecret("/unused", "CobraMK3"), "CobraMK3");
  assert.equal(decryptSecret("/unused", "sk-plain-key-1234"), "sk-plain-key-1234");
});

test("decryptSecret throws for corrupted encrypted payload", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    const valid = encryptSecret(tempDir, "real-secret");
    const corrupted = valid.slice(0, -4) + "XXXX";
    assert.throws(() => decryptSecret(tempDir, corrupted));
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("decryptSecret rejects unknown enc prefixes while verifySignedValue still soft-fails", () => {
  assert.throws(() => decryptSecret("/unused", "enc:v3:aes256gcm:anything"), /Unbekanntes Secret-Format/);
  assert.equal(verifySignedValue("/unused", "cookie:vp_user", `user-123.${"a".repeat(64)}`), null);
});

test("maskSecret returns **** for secrets 4 chars or shorter", () => {
  assert.equal(maskSecret("ab"), "****");
  assert.equal(maskSecret("abcd"), "****");
  assert.equal(maskSecret(""), "");
});

test("maskSecret preserves sk- prefix for API keys", () => {
  assert.equal(maskSecret("sk-demo-secret-1234"), "sk-****1234");
  assert.equal(maskSecret("normal-long-key-5678"), "****5678");
});

test("signScopedValue verifies only for the same scope", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    const signed = signScopedValue(tempDir, "cookie:vp_user", "user-123");
    assert.equal(verifySignedValue(tempDir, "cookie:vp_user", signed), "user-123");
    assert.equal(verifySignedValue(tempDir, "cookie:vp_session", signed), null);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("verifySignedValue rejects tampered or unsigned payloads", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));
  try {
    const signed = signScopedValue(tempDir, "cookie:vp_user", "user-123");
    const tampered = `${signed.slice(0, -1)}${signed.endsWith("0") ? "1" : "0"}`;
    const unsigned = "user-123";

    assert.equal(verifySignedValue(tempDir, "cookie:vp_user", tampered), null);
    assert.equal(verifySignedValue(tempDir, "cookie:vp_user", unsigned), null);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("writeSalt replaces salt without writing the final path in place", (t) => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-salt-"));
  try {
    const targetPath = path.join(tempDir, ".salt");
    const linkedPath = path.join(tempDir, "linked-salt");
    writeFileSync(linkedPath, Buffer.alloc(32, 1));
    try {
      linkSync(linkedPath, targetPath);
    } catch (error) {
      t.skip(`hard links unavailable for atomic replacement probe: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }

    writeSalt(tempDir, Buffer.alloc(32, 2));

    assert.equal(readSalt(tempDir).toString("hex"), Buffer.alloc(32, 2).toString("hex"));
    assert.equal(readFileSync(linkedPath).toString("hex"), Buffer.alloc(32, 1).toString("hex"));
    assert.deepEqual(readdirSync(tempDir).filter((name) => /^\.tmp-/.test(name)), []);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

