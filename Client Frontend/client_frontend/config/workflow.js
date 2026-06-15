import { access, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { loadFrontendPolicy, prepareFrontendPolicy, resolveFrontendPolicyPathForRoot } from "../frontend_policy.js";
import {
  applySavedSecrets,
  applySecretUpdates,
  ensurePortableSecrets,
  maskStoredSecrets,
  resolveRuntimeSecrets
} from "./adapter.js";
import { buildStoredConfigBase, filterSecretPayload, normalizeLoadedConfig, pickStoredContractConfig } from "./policy.js";
import { readConfigDocument, resolveConfigPath, writeConfigDocument } from "./repository.js";
import { DEFAULT_CONFIG } from "./types.js";

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function bundleSiblingPath(targetPath, marker, token, extension) {
  return path.join(path.dirname(targetPath), `.${marker}-${token}.${extension}`);
}

async function writeConfigBundleAtomically(rootDir, config, frontendPolicy) {
  const configPath = resolveConfigPath(rootDir);
  const frontendPolicyPath = resolveFrontendPolicyPathForRoot(rootDir);
  const token = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8) || "0"}`;
  const files = [
    {
      target: configPath,
      backup: bundleSiblingPath(configPath, "cfg", token, "bak"),
      temp: bundleSiblingPath(configPath, "cfg", token, "tmp"),
      payload: config
    },
    {
      target: frontendPolicyPath,
      backup: bundleSiblingPath(frontendPolicyPath, "fp", token, "bak"),
      temp: bundleSiblingPath(frontendPolicyPath, "fp", token, "tmp"),
      payload: frontendPolicy
    }
  ];

  await Promise.all(files.map((file) => writeFile(file.temp, `${JSON.stringify(file.payload, null, 2)}\n`, "utf8")));
  const promoted = [];
  const backedUp = [];
  try {
    for (const file of files) {
      if (await exists(file.target)) {
        await rename(file.target, file.backup);
        backedUp.push(file);
      }
      await rename(file.temp, file.target);
      promoted.push(file);
    }
    await Promise.all(backedUp.map((file) => rm(file.backup, { force: true, recursive: true })));
  } catch (error) {
    await Promise.all(promoted.map((file) => rm(file.target, { force: true })));
    for (const file of backedUp.reverse()) {
      if (!(await exists(file.target))) {
        await rename(file.backup, file.target);
      }
    }
    throw error;
  } finally {
    await Promise.all(
      files.flatMap((file) => [rm(file.temp, { force: true, recursive: true }), rm(file.backup, { force: true, recursive: true })])
    );
  }
}

export async function loadConfigWorkflow(rootDir) {
  const document = await readConfigDocument(rootDir);
  const normalizedConfig = document.status === "ok" ? normalizeLoadedConfig(document.parsed) : { ...DEFAULT_CONFIG };
  const portableConfig = ensurePortableSecrets(rootDir, normalizedConfig);

  if (portableConfig.changed) {
    await writeConfigDocument(rootDir, portableConfig.config);
  }

  return portableConfig.config;
}

export async function loadConfigStateWorkflow(rootDir) {
  const config = await loadConfigWorkflow(rootDir);
  const { frontendPolicy, frontendPolicyDiagnostics } = await loadFrontendPolicy(rootDir);
  return { config, frontendPolicy, frontendPolicyDiagnostics };
}

export async function seedPipelineRootConfigWorkflow(rootDir, currentConfig, pipelineRoot) {
  const configuredRoot = String(currentConfig?.pipeline_root || "").trim();
  const nextRoot = String(pipelineRoot || "").trim();
  if (configuredRoot || !nextRoot) return currentConfig;
  const nextConfig = { ...pickStoredContractConfig(currentConfig), pipeline_root: nextRoot };
  await writeConfigDocument(rootDir, nextConfig);
  return nextConfig;
}

export function resolveRuntimeConfigWorkflow(rootDir, config) {
  return resolveRuntimeSecrets(rootDir, config);
}

export function getMaskedConfigWorkflow(_rootDir, config) {
  return maskStoredSecrets(config);
}

export async function saveConfigWorkflow(rootDir, payload, currentConfig) {
  const baseConfig = buildStoredConfigBase(payload, currentConfig);
  const nextConfig = ensurePortableSecrets(rootDir, applySavedSecrets(rootDir, baseConfig, payload)).config;
  await writeConfigDocument(rootDir, nextConfig);
  return nextConfig;
}

export async function saveConfigStateWorkflow(rootDir, payload, currentConfig) {
  const baseConfig = buildStoredConfigBase(payload, currentConfig);
  const nextConfig = ensurePortableSecrets(rootDir, applySavedSecrets(rootDir, baseConfig, payload)).config;
  const frontendPolicy = prepareFrontendPolicy(payload?.frontend_policy);
  await writeConfigBundleAtomically(rootDir, nextConfig, frontendPolicy);
  return { config: nextConfig, frontendPolicy, frontendPolicyDiagnostics: null };
}

export async function updateSecretsWorkflow(rootDir, currentConfig, updates) {
  const baseConfig = pickStoredContractConfig(currentConfig);
  const nextConfig = ensurePortableSecrets(rootDir, applySecretUpdates(rootDir, baseConfig, filterSecretPayload(updates)))
    .config;
  await writeConfigDocument(rootDir, nextConfig);
  return nextConfig;
}
