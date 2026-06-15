import { DEFAULT_SCOPE } from "./types.js";

export function normalizeSecretValue(value) {
  return String(value || "").trim();
}

export function normalizeScope(scope) {
  return String(scope || DEFAULT_SCOPE);
}

export function normalizeSignedValue(value) {
  return String(value || "").trim();
}

export function maskSecret(value) {
  const secret = String(value || "");
  if (!secret) {
    return "";
  }
  if (secret.length <= 4) {
    return "****";
  }
  const prefix = secret.startsWith("sk-") ? "sk-" : "";
  return `${prefix}****${secret.slice(-4)}`;
}
