import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { decryptSecret, encryptSecret, isEncryptedValue, maskSecret } from "../../server/vault.js";

test("vault encrypts and decrypts portable secrets", () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-vault-"));

  try {
    const encrypted = encryptSecret(tempDir, "sk-demo-secret-1234");
    assert.equal(isEncryptedValue(encrypted), true);
    assert.equal(decryptSecret(tempDir, encrypted), "sk-demo-secret-1234");
    assert.equal(maskSecret("sk-demo-secret-1234"), "sk-****1234");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

