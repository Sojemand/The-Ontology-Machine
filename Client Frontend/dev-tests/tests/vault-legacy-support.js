import { createCipheriv, pbkdf2Sync, randomBytes } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

export function encryptLegacySecret(rootDir, plainText) {
  const saltPath = path.join(rootDir, ".salt");
  const salt = existsSync(saltPath) ? requireSalt(saltPath) : createSalt(saltPath);
  const fingerprint = [
    os.hostname(),
    os.userInfo().username,
    os.cpus()[0]?.model || "unknown-cpu",
    salt.toString("hex")
  ].join("|");
  const key = pbkdf2Sync(fingerprint, salt, 100000, 32, "sha512");
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(String(plainText), "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return "enc:v1:aes256gcm:" + Buffer.concat([iv, encrypted, tag]).toString("base64");
}

function createSalt(targetPath) {
  const salt = randomBytes(32);
  writeFileSync(targetPath, salt);
  return salt;
}

function requireSalt(targetPath) {
  return readFileSync(targetPath);
}
