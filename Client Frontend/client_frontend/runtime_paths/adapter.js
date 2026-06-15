import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function defaultRootDir() {
  return path.resolve(fileURLToPath(new URL("../../", import.meta.url)));
}

export function resolveRootDir(rootDir = defaultRootDir()) {
  return path.resolve(rootDir || defaultRootDir());
}

export function buildRuntimeManifestPath(rootDir) {
  return path.join(resolveRootDir(rootDir), "runtime", "runtime-manifest.json");
}

export function readRuntimeManifestDocument(targetPath) {
  return readFileSync(targetPath, "utf8");
}

export function toBundledRuntimePath(rootDir, relativePath) {
  return path.join(rootDir, String(relativePath).replace(/[\\/]/g, path.sep));
}

export function bundledRuntimeExists(targetPath) {
  return existsSync(targetPath);
}
