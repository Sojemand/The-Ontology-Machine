import { createCipheriv, pbkdf2Sync, randomBytes } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { buildDefaultFrontendPolicy } from "../../server/frontend_policy.js";

export function makeTempDir() {
  return mkdtempSync(path.join(os.tmpdir(), "vp-config-"));
}

export function cleanupTempDir(tempDir) {
  rmSync(tempDir, { recursive: true, force: true });
}

export function writeConfigJson(rootDir, payload) {
  writeFileSync(path.join(rootDir, "config.json"), JSON.stringify(payload), "utf8");
}

export function readConfigJson(rootDir) {
  return JSON.parse(readFileSync(path.join(rootDir, "config.json"), "utf8"));
}

export function writeFrontendPolicyJson(rootDir, payload = buildDefaultFrontendPolicy()) {
  writeFileSync(path.join(rootDir, "frontend_policy.json"), JSON.stringify(payload), "utf8");
}

export function readFrontendPolicyJson(rootDir) {
  return JSON.parse(readFileSync(path.join(rootDir, "frontend_policy.json"), "utf8"));
}

export function encryptLegacySecret(rootDir, plainText) {
  const saltPath = path.join(rootDir, ".salt");
  const salt = existsSync(saltPath) ? readFileSync(saltPath) : createSalt(saltPath);
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
