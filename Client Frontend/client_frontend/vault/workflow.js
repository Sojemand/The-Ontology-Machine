import {
  buildScopedMacKey,
  buildSignature,
  createSaltBytes,
  decryptPayload,
  deriveLegacyKey,
  derivePortableKey,
  encryptPayload,
  signaturesMatch
} from "./adapter.js";
import { normalizeScope, normalizeSecretValue, normalizeSignedValue } from "./policy.js";
import { hasSalt, readSalt, writeSalt } from "./repository.js";
import {
  assertKnownEncryptedValue,
  isCurrentEncryptedValue,
  isEncryptedValue,
  isLegacyEncryptedValue,
  parseSignedValue
} from "./validation.js";
import { CURRENT_SECRET_PREFIX, LEGACY_SECRET_PREFIX } from "./types.js";

function loadSalt(rootDir, createIfMissing = false) {
  if (hasSalt(rootDir)) {
    return readSalt(rootDir);
  }
  if (!createIfMissing) {
    throw new Error(".salt is missing. Encrypted keys cannot be read.");
  }
  return writeSalt(rootDir, createSaltBytes());
}

function deriveRootPortableKey(rootDir, createIfMissing = false) {
  return derivePortableKey(loadSalt(rootDir, createIfMissing));
}

function deriveRootLegacyKey(rootDir) {
  return deriveLegacyKey(loadSalt(rootDir, false));
}

function buildScopedSignature(rootDir, scope, payload, createIfMissing = false) {
  const portableKey = deriveRootPortableKey(rootDir, createIfMissing);
  const macKey = buildScopedMacKey(portableKey, normalizeScope(scope));
  return buildSignature(macKey, payload);
}

export function encryptSecretWorkflow(rootDir, plainText) {
  const payload = normalizeSecretValue(plainText);
  if (!payload) {
    return "";
  }
  return encryptPayload(CURRENT_SECRET_PREFIX, deriveRootPortableKey(rootDir, true), payload);
}

export function decryptSecretWorkflow(rootDir, value) {
  if (!value) {
    return "";
  }
  if (isLegacyEncryptedValue(value)) {
    return decryptPayload(LEGACY_SECRET_PREFIX, deriveRootLegacyKey(rootDir), value);
  }
  if (isCurrentEncryptedValue(value)) {
    return decryptPayload(CURRENT_SECRET_PREFIX, deriveRootPortableKey(rootDir, false), value);
  }
  if (!isEncryptedValue(value)) {
    return value;
  }
  assertKnownEncryptedValue(value);
  return value;
}

export function migrateEncryptedSecretWorkflow(rootDir, value) {
  if (!isLegacyEncryptedValue(value)) {
    return value;
  }
  return encryptSecretWorkflow(rootDir, decryptSecretWorkflow(rootDir, value));
}

export function signScopedValueWorkflow(rootDir, scope, plainValue) {
  const payload = normalizeSecretValue(plainValue);
  if (!payload) {
    return "";
  }
  return `${payload}.${buildScopedSignature(rootDir, scope, payload, true)}`;
}

export function verifySignedValueWorkflow(rootDir, scope, signedValue) {
  const parsed = parseSignedValue(normalizeSignedValue(signedValue));
  if (!parsed) {
    return null;
  }
  try {
    const expectedSignature = buildScopedSignature(rootDir, scope, parsed.payload, false);
    return signaturesMatch(parsed.providedSignature, expectedSignature) ? parsed.payload : null;
  } catch {
    return null;
  }
}
