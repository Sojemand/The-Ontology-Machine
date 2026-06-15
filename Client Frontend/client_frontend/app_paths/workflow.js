import { buildAppPaths } from "./policy.js";
import { ensureLayout, importSnapshotEntries, migrateLegacyEntries, readSnapshotEntries } from "./repository.js";

export function resolveAppPathsWorkflow(options = {}) {
  return buildAppPaths(options);
}

export function ensureAppHomeLayoutWorkflow(options = {}) {
  return ensureLayout(resolveAppPathsWorkflow(options));
}

export function migrateLegacyRootStateWorkflow(options = {}) {
  return migrateLegacyEntries(resolveAppPathsWorkflow(options));
}

export function readStateSnapshotEntriesWorkflow(options = {}, snapshotDir) {
  return readSnapshotEntries(resolveAppPathsWorkflow(options), snapshotDir);
}

export function importStateSnapshotWorkflow(options = {}, snapshotDir) {
  return importSnapshotEntries(resolveAppPathsWorkflow(options), snapshotDir);
}
