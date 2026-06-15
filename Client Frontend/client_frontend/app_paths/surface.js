import {
  ensureAppHomeLayoutWorkflow,
  importStateSnapshotWorkflow,
  migrateLegacyRootStateWorkflow,
  readStateSnapshotEntriesWorkflow,
  resolveAppPathsWorkflow
} from "./workflow.js";
import { validateModuleRoot } from "./validation.js";

export function resolveAppPaths(options = {}) {
  validateModuleRoot(options.moduleRoot);
  return resolveAppPathsWorkflow(options);
}

export function ensureAppHomeLayout(options = {}) {
  validateModuleRoot(options.moduleRoot);
  return ensureAppHomeLayoutWorkflow(options);
}

export function migrateLegacyRootState(options = {}) {
  validateModuleRoot(options.moduleRoot);
  return migrateLegacyRootStateWorkflow(options);
}

export function readStateSnapshotEntries(options = {}, snapshotDir) {
  validateModuleRoot(options.moduleRoot);
  return readStateSnapshotEntriesWorkflow(options, snapshotDir);
}

export function importStateSnapshot(options = {}, snapshotDir) {
  validateModuleRoot(options.moduleRoot);
  return importStateSnapshotWorkflow(options, snapshotDir);
}
