import { statSync } from "node:fs";
import path from "node:path";

import { resolveSqlDataDir, resolveSqlDatabasePath, SqlDatabasePathError } from "../config/database_path.js";
import { DEFAULT_DEMO_DB_RELATIVE_PATH, DEFAULT_SQL_DATABASE_PATH, resolveRuntimeConfig } from "../config.js";
import { writeConfigDocument } from "../config/repository.js";
import { pickStoredContractConfig } from "../config/policy.js";
import { inferInstalledPipelineRoot, resolvePipelineRootFromConfig } from "../pipeline_root.js";

function fileExists(filePath) {
  try {
    return statSync(filePath).isFile();
  } catch {
    return false;
  }
}

function isInside(parentPath, childPath) {
  const relativePath = path.relative(path.resolve(parentPath), path.resolve(childPath));
  return Boolean(relativePath) && !relativePath.startsWith("..") && !path.isAbsolute(relativePath);
}

function pathHasSegment(candidatePath, segment) {
  const expected = segment.toLowerCase();
  return path.resolve(candidatePath).split(path.sep).some((part) => part.toLowerCase() === expected);
}

function samePath(leftPath, rightPath) {
  return path.resolve(leftPath).toLowerCase() === path.resolve(rightPath).toLowerCase();
}

function shouldUseInstalledPipelineRoot(configuredRoot, moduleRoot, installedRoot) {
  const trimmedRoot = String(configuredRoot || "").trim();
  if (!trimmedRoot) return true;
  return samePath(resolvePipelineRootFromConfig(trimmedRoot, moduleRoot), installedRoot);
}

function shouldUseInstalledDemoDb(configuredPath, moduleRoot, installedRoot, mayRebindExternalSampleDb = false) {
  const trimmedPath = String(configuredPath || "").trim();
  if (!trimmedPath || trimmedPath === DEFAULT_SQL_DATABASE_PATH) return true;
  const resolvedPath = path.resolve(moduleRoot, trimmedPath);
  if (samePath(resolvedPath, path.resolve(installedRoot, DEFAULT_DEMO_DB_RELATIVE_PATH))) return true;
  return mayRebindExternalSampleDb
    && path.basename(resolvedPath).toLowerCase() === "corpus.db"
    && pathHasSegment(resolvedPath, "SampleDB")
    && !isInside(installedRoot, resolvedPath);
}

async function writeInstalledDefaultConfig(configDir, currentConfig, nextConfig) {
  const normalized = pickStoredContractConfig({ ...currentConfig, ...nextConfig });
  await writeConfigDocument(configDir, normalized);
  return normalized;
}

function createUnavailableAgent(error) {
  const message = error instanceof Error ? error.message : "Active corpus is not configured.";
  const corpusError = error instanceof SqlDatabasePathError ? error : new SqlDatabasePathError(message);
  return {
    schemaSummary: "",
    async chat() {
      throw corpusError;
    },
    countDocuments() {
      return 0;
    },
    databaseStatus() {
      return {
        base_graph: {
          available: false,
          dirty: false,
          document_count: 0,
          unmapped_document_count: 0,
          source_document_count: 0,
          source_page_count: 0,
          structural_unit_count: 0,
          base_unit_count: 0,
          page_unit_count: 0,
          relation_count: 0
        },
        ontology_lenses: { available: false, count: 0, active_count: 0, primary_ontology_id: null }
      };
    },
    resolveImage() {
      return { available: false, source: "unavailable", contentType: null, path: null };
    },
    resolveSource() {
      return null;
    },
    resolveSourcesFromText() {
      return [];
    },
    close() {}
  };
}

export async function ensureInstalledPipelineRootConfig({ appPaths, moduleRoot, config }) {
  const installedRoot = inferInstalledPipelineRoot(moduleRoot);
  if (!installedRoot) return config;
  const demoDbPath = path.join(installedRoot, ...DEFAULT_DEMO_DB_RELATIVE_PATH.split(/[\\/]+/));
  const nextConfig = { ...config };
  let changed = false;
  const useInstalledPipelineRoot = shouldUseInstalledPipelineRoot(nextConfig.pipeline_root, moduleRoot, installedRoot);
  if (useInstalledPipelineRoot) {
    nextConfig.pipeline_root = installedRoot;
    changed = true;
  }
  if (fileExists(demoDbPath) && shouldUseInstalledDemoDb(nextConfig.sql_database_path, moduleRoot, installedRoot, useInstalledPipelineRoot)) {
    nextConfig.sql_database_path = demoDbPath;
    changed = true;
  }
  if (!changed) return config;
  try {
    return await writeInstalledDefaultConfig(appPaths.config_dir, config, nextConfig);
  } catch {
    return nextConfig;
  }
}

export function createAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, soulProfile, createMinimalAgentFn }) {
  return (agentConfig = getConfig()) => {
    try {
      return createMinimalAgentFn({
        dbPath: resolveSqlDatabasePath(moduleRoot, agentConfig),
        dataDir: resolveSqlDataDir(moduleRoot, agentConfig),
        rootDir: moduleRoot,
        configDir: appPaths.config_dir,
        stateRoot: appPaths.state_dir,
        soulContext: soulProfile.text,
        getRuntimeConfig: () => ({ ...resolveRuntimeConfig(appPaths.config_dir, getConfig()), state_dir: appPaths.state_dir }),
        getFrontendPolicy
      });
    } catch (error) {
      return createUnavailableAgent(error);
    }
  };
}

export function createOntologyAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, soulProfile, createOntologyAgentFn }) {
  return (agentConfig = getConfig()) => {
    try {
      const configuredPipelineRoot = String(agentConfig.pipeline_root || "").trim();
      return createOntologyAgentFn({
        dbPath: resolveSqlDatabasePath(moduleRoot, agentConfig),
        dataDir: resolveSqlDataDir(moduleRoot, agentConfig),
        rootDir: moduleRoot,
        pipelineRoot: resolvePipelineRootFromConfig(configuredPipelineRoot, moduleRoot) || path.dirname(moduleRoot),
        stateRoot: path.join(appPaths.state_dir, "ontology_agent_kernel"),
        soulContext: soulProfile.text,
        getRuntimeConfig: () => ({ ...resolveRuntimeConfig(appPaths.config_dir, getConfig()), state_dir: appPaths.state_dir }),
        getFrontendPolicy
      });
    } catch (error) {
      return createUnavailableAgent(error);
    }
  };
}

export function createPipelineAgentFactory({ moduleRoot, appPaths, getConfig, getFrontendPolicy, createPipelineManagerAgentFn }) {
  return (agentConfig = getConfig()) => createPipelineManagerAgentFn({
    pipelineRoot: agentConfig.pipeline_root,
    moduleRoot,
    getRuntimeConfig: () => ({ ...resolveRuntimeConfig(appPaths.config_dir, getConfig()), state_dir: appPaths.state_dir }),
    getFrontendPolicy
  });
}
