import { SUPPORTED_RUNTIMES } from "./types.js";

const SUPPORTED_RUNTIME_SET = new Set(SUPPORTED_RUNTIMES);

export function normalizeRuntimeName(runtime) {
  const normalized = String(runtime || "").trim().toLowerCase();
  if (!SUPPORTED_RUNTIME_SET.has(normalized)) {
    throw new Error(`Unknown runtime: ${runtime}`);
  }
  return normalized;
}

export function validateManifest(manifest, targetPath) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw new Error(`Runtime manifest is invalid: ${targetPath}`);
  }

  for (const runtime of SUPPORTED_RUNTIMES) {
    const entries = manifest[runtime];
    if (!Array.isArray(entries) || !entries.length || entries.some((entry) => !String(entry || "").trim())) {
      throw new Error(`Runtime manifest has no valid entries for ${runtime}: ${targetPath}`);
    }
  }

  return manifest;
}
