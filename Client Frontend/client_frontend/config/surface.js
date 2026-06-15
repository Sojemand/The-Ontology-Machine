import { DEFAULT_CONFIG, DEFAULT_DEMO_DB_RELATIVE_PATH, DEFAULT_SQL_DATABASE_PATH } from "./types.js";
import { validateRootDir } from "./validation.js";
import {
  getMaskedConfigWorkflow,
  loadConfigWorkflow,
  loadConfigStateWorkflow,
  resolveRuntimeConfigWorkflow,
  seedPipelineRootConfigWorkflow,
  saveConfigWorkflow,
  saveConfigStateWorkflow,
  updateSecretsWorkflow
} from "./workflow.js";

export { DEFAULT_CONFIG, DEFAULT_DEMO_DB_RELATIVE_PATH, DEFAULT_SQL_DATABASE_PATH };

export async function loadConfig(rootDir) {
  return await loadConfigWorkflow(validateRootDir(rootDir));
}

export async function loadConfigState(rootDir) {
  return await loadConfigStateWorkflow(validateRootDir(rootDir));
}

export async function seedPipelineRootConfig(rootDir, currentConfig, pipelineRoot) {
  return await seedPipelineRootConfigWorkflow(validateRootDir(rootDir), currentConfig, pipelineRoot);
}

export function resolveRuntimeConfig(rootDir, config) {
  return resolveRuntimeConfigWorkflow(validateRootDir(rootDir), config);
}

export function getMaskedConfig(rootDir, config) {
  validateRootDir(rootDir);
  return getMaskedConfigWorkflow(rootDir, config);
}

export async function saveConfig(rootDir, payload, currentConfig) {
  return await saveConfigWorkflow(validateRootDir(rootDir), payload, currentConfig);
}

export async function saveConfigState(rootDir, payload, currentConfig) {
  return await saveConfigStateWorkflow(validateRootDir(rootDir), payload, currentConfig);
}

export async function updateSecrets(rootDir, currentConfig, updates) {
  return await updateSecretsWorkflow(validateRootDir(rootDir), currentConfig, updates);
}
