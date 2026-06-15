import {
  CURRENT_SECRET_PREFIX,
  ENCRYPTED_SECRET_PREFIX,
  LEGACY_SECRET_PREFIX,
  SIGNATURE_HEX_LENGTH
} from "./types.js";

const SIGNATURE_PATTERN = new RegExp(`^[0-9a-f]{${SIGNATURE_HEX_LENGTH}}$`, "i");

export function validateRootDir(rootDir) {
  const normalizedRootDir = String(rootDir || "").trim();
  if (!normalizedRootDir) {
    throw new TypeError("rootDir ist erforderlich.");
  }
  return normalizedRootDir;
}

export function isCurrentEncryptedValue(value) {
  return typeof value === "string" && value.startsWith(CURRENT_SECRET_PREFIX);
}

export function isLegacyEncryptedValue(value) {
  return typeof value === "string" && value.startsWith(LEGACY_SECRET_PREFIX);
}

export function isEncryptedValue(value) {
  return typeof value === "string" && value.startsWith(ENCRYPTED_SECRET_PREFIX);
}

export function assertKnownEncryptedValue(value) {
  if (!isEncryptedValue(value) || isCurrentEncryptedValue(value) || isLegacyEncryptedValue(value)) {
    return;
  }
  throw new Error("Unbekanntes Secret-Format.");
}

export function parseSignedValue(raw) {
  const separatorIndex = raw.lastIndexOf(".");
  if (separatorIndex <= 0 || separatorIndex >= raw.length - 1) {
    return null;
  }

  const payload = raw.slice(0, separatorIndex);
  const providedSignature = raw.slice(separatorIndex + 1);
  if (!SIGNATURE_PATTERN.test(providedSignature)) {
    return null;
  }

  return { payload, providedSignature };
}
