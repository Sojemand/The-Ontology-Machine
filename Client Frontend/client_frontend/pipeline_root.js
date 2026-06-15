import { statSync } from "node:fs";
import path from "node:path";

const PIPELINE_ROOT_MARKER_DIRS = ["07 - MCP Server", "08 - Semantic Control Kernel"];

function isDirectory(candidatePath) {
  try {
    return statSync(candidatePath).isDirectory();
  } catch {
    return false;
  }
}

export function looksLikeInstalledPipelineRoot(candidateRoot = "") {
  const root = String(candidateRoot || "").trim();
  if (!root) return false;
  return PIPELINE_ROOT_MARKER_DIRS.every((markerDir) => isDirectory(path.join(root, markerDir)));
}

export function inferInstalledPipelineRoot(moduleRoot = "") {
  const rawModuleRoot = String(moduleRoot || "").trim();
  if (!rawModuleRoot) return "";
  const resolvedModuleRoot = path.resolve(rawModuleRoot);
  const candidateRoot = path.dirname(resolvedModuleRoot);
  if (candidateRoot === resolvedModuleRoot) return "";
  return looksLikeInstalledPipelineRoot(candidateRoot) ? candidateRoot : "";
}

export function resolvePipelineRootFromConfig(pipelineRoot = "", moduleRoot = "") {
  const rawRoot = String(pipelineRoot || "").trim();
  if (rawRoot) {
    if (path.isAbsolute(rawRoot)) return path.resolve(rawRoot);
    const baseRoot = String(moduleRoot || "").trim() || process.cwd();
    return path.resolve(baseRoot, rawRoot);
  }
  return inferInstalledPipelineRoot(moduleRoot);
}
