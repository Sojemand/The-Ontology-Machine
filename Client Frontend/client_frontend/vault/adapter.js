import { createCipheriv, createDecipheriv, createHmac, pbkdf2Sync, randomBytes, timingSafeEqual } from "node:crypto";
import os from "node:os";

import {
  AES_GCM_IV_BYTES,
  AES_GCM_TAG_BYTES,
  DERIVED_KEY_BYTES,
  PBKDF2_ITERATIONS,
  PORTABLE_KEY_CONTEXT,
  SALT_BYTES
} from "./types.js";

const portableKeyCache = new Map();
const legacyKeyCache = new Map();

function buildLegacyFingerprint(salt) {
  return [
    os.hostname(),
    os.userInfo().username,
    os.cpus()[0]?.model || "unknown-cpu",
    salt.toString("hex")
  ].join("|");
}

export function createSaltBytes() {
  return randomBytes(SALT_BYTES);
}

function deriveCachedKey(cache, cacheKey, derive) {
  const cached = cache.get(cacheKey);
  if (cached) {
    return cached;
  }
  const key = derive();
  cache.set(cacheKey, key);
  return key;
}

function saltCacheKey(salt) {
  return Buffer.from(salt).toString("base64");
}

export function derivePortableKey(salt) {
  const cacheKey = saltCacheKey(salt);
  return deriveCachedKey(
    portableKeyCache,
    cacheKey,
    () => pbkdf2Sync(PORTABLE_KEY_CONTEXT, salt, PBKDF2_ITERATIONS, DERIVED_KEY_BYTES, "sha512")
  );
}

export function deriveLegacyKey(salt) {
  const cacheKey = saltCacheKey(salt);
  return deriveCachedKey(
    legacyKeyCache,
    cacheKey,
    () => pbkdf2Sync(buildLegacyFingerprint(salt), salt, PBKDF2_ITERATIONS, DERIVED_KEY_BYTES, "sha512")
  );
}

export function buildScopedMacKey(portableKey, scope) {
  return createHmac("sha256", portableKey).update(scope).digest();
}

export function buildSignature(macKey, payload) {
  return createHmac("sha256", macKey).update(payload).digest("hex");
}

export function encryptPayload(prefix, key, plainText) {
  const iv = randomBytes(AES_GCM_IV_BYTES);
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(plainText, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return prefix + Buffer.concat([iv, encrypted, tag]).toString("base64");
}

export function decryptPayload(prefix, key, value) {
  const payload = Buffer.from(value.slice(prefix.length), "base64");
  const iv = payload.subarray(0, AES_GCM_IV_BYTES);
  const tag = payload.subarray(payload.length - AES_GCM_TAG_BYTES);
  const encrypted = payload.subarray(AES_GCM_IV_BYTES, payload.length - AES_GCM_TAG_BYTES);
  const decipher = createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString("utf8");
}

export function signaturesMatch(providedSignature, expectedSignature) {
  const providedBuffer = Buffer.from(providedSignature, "utf8");
  const expectedBuffer = Buffer.from(expectedSignature, "utf8");
  if (providedBuffer.length !== expectedBuffer.length) {
    return false;
  }
  return timingSafeEqual(providedBuffer, expectedBuffer);
}
