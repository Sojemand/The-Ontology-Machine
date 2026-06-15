import { buildRuntimeManifestPath, bundledRuntimeExists, readRuntimeManifestDocument, resolveRootDir, toBundledRuntimePath } from "./adapter.js";
import { RUNTIME_LABELS, SUPPORTED_RUNTIMES } from "./types.js";
import { normalizeRuntimeName, validateManifest } from "./validation.js";

function loadManifestContext(rootDir) {
  const normalizedRootDir = resolveRootDir(rootDir);
  const manifestPath = buildRuntimeManifestPath(normalizedRootDir);
  const raw = readRuntimeManifestDocument(manifestPath);
  return {
    rootDir: normalizedRootDir,
    manifestPath,
    manifest: validateManifest(JSON.parse(raw), manifestPath)
  };
}

function resolveManifestContext(options = {}) {
  if (options.manifest) {
    const normalizedRootDir = resolveRootDir(options.rootDir);
    const manifestPath = buildRuntimeManifestPath(normalizedRootDir);
    return {
      rootDir: normalizedRootDir,
      manifestPath,
      manifest: validateManifest(options.manifest, manifestPath)
    };
  }
  return loadManifestContext(options.rootDir);
}

function getRuntimeCandidatesFromContext(runtime, context) {
  const normalizedRuntime = normalizeRuntimeName(runtime);
  return {
    runtime: normalizedRuntime,
    expected: context.manifest[normalizedRuntime].map((relativePath) =>
      toBundledRuntimePath(context.rootDir, relativePath)
    )
  };
}

function inspectBundledRuntime(runtime, context) {
  const candidates = getRuntimeCandidatesFromContext(runtime, context);
  const resolvedPath = candidates.expected.find((candidate) => bundledRuntimeExists(candidate)) || "";
  return {
    runtime: candidates.runtime,
    expected: candidates.expected,
    path: resolvedPath,
    ok: Boolean(resolvedPath)
  };
}

export function runtimeManifestPathWorkflow(rootDir) {
  return buildRuntimeManifestPath(rootDir);
}

export function loadRuntimeManifestWorkflow(rootDir) {
  return loadManifestContext(rootDir).manifest;
}

export function getBundledRuntimeCandidatesWorkflow(runtime, options = {}) {
  const context = resolveManifestContext(options);
  return getRuntimeCandidatesFromContext(runtime, context).expected;
}

export function missingBundledRuntimeErrorWorkflow(runtime, candidates) {
  const normalizedRuntime = normalizeRuntimeName(runtime);
  const error = new Error(
    `Bundled ${RUNTIME_LABELS[normalizedRuntime]} runtime is missing or damaged. Expected at ${candidates[0]}`
  );
  error.code = "ENOENT";
  return error;
}

export function resolveBundledRuntimeWorkflow(runtime, options = {}) {
  const context = resolveManifestContext(options);
  const inspection = inspectBundledRuntime(runtime, context);
  if (inspection.ok) {
    return inspection.path;
  }
  throw missingBundledRuntimeErrorWorkflow(inspection.runtime, inspection.expected);
}

export function getBundledRuntimeStatusWorkflow(rootDir) {
  const context = loadManifestContext(rootDir);
  const runtimes = {};
  let ok = true;

  for (const runtime of SUPPORTED_RUNTIMES) {
    const inspection = inspectBundledRuntime(runtime, context);
    runtimes[runtime] = {
      ok: inspection.ok,
      path: inspection.path,
      expected: inspection.expected
    };
    ok = ok && inspection.ok;
  }

  return {
    ok,
    root_dir: context.rootDir,
    manifest_path: context.manifestPath,
    runtimes
  };
}
