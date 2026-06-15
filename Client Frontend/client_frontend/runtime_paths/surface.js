import {
  getBundledRuntimeCandidatesWorkflow,
  getBundledRuntimeStatusWorkflow,
  loadRuntimeManifestWorkflow,
  missingBundledRuntimeErrorWorkflow,
  resolveBundledRuntimeWorkflow,
  runtimeManifestPathWorkflow
} from "./workflow.js";

export function runtimeManifestPath(rootDir) {
  return runtimeManifestPathWorkflow(rootDir);
}

export function loadRuntimeManifest(rootDir) {
  return loadRuntimeManifestWorkflow(rootDir);
}

export function getBundledRuntimeCandidates(runtime, options) {
  return getBundledRuntimeCandidatesWorkflow(runtime, options);
}

export function missingBundledRuntimeError(runtime, candidates) {
  return missingBundledRuntimeErrorWorkflow(runtime, candidates);
}

export function resolveBundledRuntime(runtime, options) {
  return resolveBundledRuntimeWorkflow(runtime, options);
}

export function getBundledRuntimeStatus(rootDir) {
  return getBundledRuntimeStatusWorkflow(rootDir);
}
