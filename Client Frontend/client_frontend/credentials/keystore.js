import { createHash } from "node:crypto";
import { mkdir, open, readFile, unlink } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { decryptSecret, encryptSecret } from "../vault.js";
import { normalizeProviderId, providerDefinition } from "../shared/provider_catalog.js";

const STORE_FILE = "keystore.enc";
const LOCK_FILE = "keystore.lock";
const LOCK_TIMEOUT_MS = 5_000;
const LOCK_RETRY_MS = 10;

function storePath(stateDir) {
  return path.join(stateDir, STORE_FILE);
}

function lockPath(stateDir) {
  return path.join(stateDir, LOCK_FILE);
}

function keystoreReadError(targetPath, error) {
  const reason = error instanceof Error ? error.message : String(error);
  return new Error(`Credential keystore could not be read: ${targetPath}. ${reason}`);
}

function normalizedBaseUrl(providerSettings = {}) {
  const providerId = normalizeProviderId(providerSettings.provider_id || providerSettings.provider);
  return String(providerSettings.base_url || providerDefinition(providerId).default_base_url || "").trim().replace(/\/+$/, "");
}

function secretName(target, providerSettings = {}) {
  const providerId = normalizeProviderId(providerSettings.provider_id || providerSettings.provider);
  const digest = createHash("sha256").update(normalizedBaseUrl(providerSettings)).digest("hex").slice(0, 12);
  return `${providerId}.${digest}.${target}.api_key`;
}

function legacySecretNames(target, providerSettings = {}) {
  const providerId = normalizeProviderId(providerSettings.provider_id || providerSettings.provider);
  const baseUrl = normalizedBaseUrl(providerSettings);
  return providerId === "openai" && baseUrl === "https://api.openai.com/v1"
    ? [`openai.${target}.api_key`]
    : [];
}

function candidateNames(target, providerSettings = {}) {
  return Array.from(new Set([secretName(target, providerSettings), ...legacySecretNames(target, providerSettings)]));
}

async function withStoreLock(stateDir, task) {
  await mkdir(stateDir, { recursive: true });
  const deadline = Date.now() + LOCK_TIMEOUT_MS;
  while (true) {
    let handle;
    let acquired = false;
    try {
      handle = await open(lockPath(stateDir), "wx");
      acquired = true;
      await handle.writeFile(String(process.pid), "utf8");
      return await task();
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      if (Date.now() >= deadline) throw new Error(`Credential keystore lock could not be acquired: ${lockPath(stateDir)}`);
      await new Promise((resolve) => setTimeout(resolve, LOCK_RETRY_MS));
    } finally {
      await handle?.close().catch(() => {});
      if (acquired) await unlink(lockPath(stateDir)).catch(() => {});
    }
  }
}

async function loadStore(stateDir) {
  const targetPath = storePath(stateDir);
  let raw;
  try {
    raw = await readFile(targetPath, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      return {};
    }
    throw keystoreReadError(targetPath, error);
  }

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    throw keystoreReadError(targetPath, error);
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw keystoreReadError(targetPath, new Error("Expected a JSON object."));
  }
  return payload;
}

async function saveStore(stateDir, store) {
  await mkdir(stateDir, { recursive: true });
  await writeTextAtomically(storePath(stateDir), `${JSON.stringify(store, null, 2)}\n`);
}

export async function saveApiKey(stateDir, target, value, providerSettings = {}) {
  const secret = String(value || "").trim();
  if (!secret) return false;
  await withStoreLock(stateDir, async () => {
    const store = await loadStore(stateDir);
    store[secretName(target, providerSettings)] = encryptSecret(stateDir, secret);
    await saveStore(stateDir, store);
  });
  return true;
}

export async function loadApiKey(stateDir, target, providerSettings = {}) {
  const store = await loadStore(stateDir);
  for (const name of candidateNames(target, providerSettings)) {
    if (!store[name]) continue;
    try {
      return decryptSecret(stateDir, store[name]);
    } catch (error) {
      throw keystoreReadError(storePath(stateDir), error);
    }
  }
  return "";
}

export async function hasApiKey(stateDir, target, providerSettings = {}) {
  const store = await loadStore(stateDir);
  return candidateNames(target, providerSettings).some((name) => Boolean(store[name]));
}

export async function deleteApiKey(stateDir, target, providerSettings = {}) {
  let deleted = false;
  await withStoreLock(stateDir, async () => {
    const store = await loadStore(stateDir);
    for (const name of candidateNames(target, providerSettings)) {
      deleted = Boolean(store[name]) || deleted;
      delete store[name];
    }
    if (deleted) await saveStore(stateDir, store);
  });
  return deleted;
}
