import path from "node:path";

export function createWorkbenchPolicyError(message) {
  const error = new Error(message);
  error.code = "WORKBENCH_POLICY";
  return error;
}

function ensureUniquePaths(values) {
  return Array.from(new Set(values.filter(Boolean).map((value) => path.resolve(value))));
}

function pathStartsWith(parentPath, candidatePath) {
  return candidatePath === parentPath || candidatePath.startsWith(parentPath + path.sep);
}

function isWorkbenchPathAllowed(candidatePath, scope) {
  return scope.allowedFiles.includes(candidatePath) || scope.allowedRoots.some((allowedRoot) => pathStartsWith(allowedRoot, candidatePath));
}

function workbenchRuntimeLabel(runtime) {
  return runtime === "python" ? "Python" : "PowerShell";
}

export function buildWorkbenchScope({ rootDir, dataDir, configDir, allowedFiles = [] } = {}) {
  const resolvedRootDir = path.resolve(rootDir || path.dirname(dataDir || process.cwd()));
  const resolvedDataDir = dataDir ? path.resolve(dataDir) : "";
  const resolvedConfigDir = path.resolve(configDir || resolvedRootDir);
  return {
    rootDir: resolvedRootDir,
    allowedRoots: ensureUniquePaths([resolvedDataDir]),
    allowedFiles: ensureUniquePaths([
      path.join(resolvedRootDir, "assistant", "soul.txt"),
      path.join(resolvedRootDir, "soul.txt"),
      path.join(resolvedRootDir, "config.json"),
      path.join(resolvedRootDir, "frontend_policy.json"),
      path.join(resolvedConfigDir, "config.json"),
      path.join(resolvedConfigDir, "frontend_policy.json"),
      ...allowedFiles
    ])
  };
}

export function looksLikeInspectablePathLiteral(value) {
  const trimmed = String(value || "").trim();
  return Boolean(
    trimmed
    && (/^[A-Za-z]:/.test(trimmed)
      || /^[.]{1,2}(?:[\\/]|$)/.test(trimmed)
      || /[\\/]/.test(trimmed)
      || /^(data|assistant|soul\.txt|config\.json|frontend_policy\.json|\.salt)$/i.test(trimmed))
  );
}

export function resolveWorkbenchPathLiteral(literal, scope, runtime) {
  const rawValue = String(literal || "").trim();
  if (!rawValue) return null;
  const runtimeLabel = workbenchRuntimeLabel(runtime);
  if (/^[a-z]+:\/\//i.test(rawValue) || /^\\\\/.test(rawValue)) {
    throw createWorkbenchPolicyError(`${runtimeLabel} workbench blocks network and UNC paths.`);
  }
  const resolvedPath = path.resolve(path.isAbsolute(rawValue) ? rawValue : path.join(scope.rootDir, rawValue));
  if (!isWorkbenchPathAllowed(resolvedPath, scope)) {
    throw createWorkbenchPolicyError(`${runtimeLabel} workbench may read only active corpus files and explicitly allowed config/soul files.`);
  }
  return resolvedPath;
}
