import {
  decryptSecret,
  encryptSecret,
  isEncryptedValue,
  isLegacyEncryptedValue,
  migrateEncryptedSecret
} from "../vault.js";
import { SECRET_FIELDS } from "./types.js";

function normalizeIncomingSecret(value) {
  return String(value ?? "").trim();
}

export function ensurePortableSecrets(rootDir, config) {
  let changed = false;
  const nextConfig = { ...config };

  for (const field of SECRET_FIELDS) {
    const value = nextConfig[field];
    if (value && !isEncryptedValue(value)) {
      nextConfig[field] = encryptSecret(rootDir, value);
      changed = true;
      continue;
    }

    if (isLegacyEncryptedValue(value)) {
      try {
        nextConfig[field] = migrateEncryptedSecret(rootDir, value);
      } catch (error) {
        const reason = error instanceof Error ? error.message : String(error);
        throw new Error(`Legacy secret ${field} could not be migrated to the portable format: ${reason}`);
      }
      changed = true;
    }
  }

  return { config: nextConfig, changed };
}

export function resolveRuntimeSecrets(rootDir, config) {
  const resolved = { ...config };
  for (const field of SECRET_FIELDS) {
    resolved[field] = config[field] ? decryptSecret(rootDir, config[field]) : "";
  }
  return resolved;
}

export function maskStoredSecrets(config) {
  const masked = { ...config };
  for (const field of SECRET_FIELDS) {
    masked[field] = config[field] ? "configured" : "";
  }
  return masked;
}

export function applySavedSecrets(rootDir, currentConfig, payload) {
  const nextConfig = { ...currentConfig };
  for (const field of SECRET_FIELDS) {
    const incoming = normalizeIncomingSecret(payload?.[field]);
    nextConfig[field] = incoming ? encryptSecret(rootDir, incoming) : currentConfig[field] || "";
  }
  return nextConfig;
}

export function applySecretUpdates(rootDir, currentConfig, updates) {
  const nextConfig = { ...currentConfig };
  for (const field of SECRET_FIELDS) {
    const incoming = normalizeIncomingSecret(updates?.[field]);
    if (incoming) {
      nextConfig[field] = encryptSecret(rootDir, incoming);
    }
  }
  return nextConfig;
}
