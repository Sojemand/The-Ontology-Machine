import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, statSync } from "node:fs";
import path from "node:path";

function hasDirectoryContent(targetPath) {
  return existsSync(targetPath) && readdirSync(targetPath).length > 0;
}

function resolveConflictPath(targetPath) {
  const parsed = path.parse(targetPath);
  let nextPath = targetPath;
  let index = 1;
  while (existsSync(nextPath)) {
    nextPath = path.join(parsed.dir, `${parsed.name}.legacy-${index}${parsed.ext}`);
    index += 1;
  }
  return nextPath;
}

function copyEntry(sourcePath, targetPath, options = {}) {
  const nextTargetPath = options.renameConflicts && existsSync(targetPath) ? resolveConflictPath(targetPath) : targetPath;
  mkdirSync(path.dirname(nextTargetPath), { recursive: true });
  cpSync(sourcePath, nextTargetPath, { recursive: true, force: false });
}

function copyDirectoryContents(sourcePath, targetPath, options = {}) {
  mkdirSync(targetPath, { recursive: true });
  for (const entry of readdirSync(sourcePath)) {
    const sourceEntryPath = path.join(sourcePath, entry);
    const targetEntryPath = path.join(targetPath, entry);
    if (statSync(sourceEntryPath).isDirectory() && existsSync(targetEntryPath) && statSync(targetEntryPath).isDirectory()) {
      copyDirectoryContents(sourceEntryPath, targetEntryPath, options);
      continue;
    }
    copyEntry(sourceEntryPath, targetEntryPath, options);
  }
}

function moveEntry(sourcePath, targetPath, options = {}) {
  if (!existsSync(sourcePath)) {
    return;
  }
  if (existsSync(targetPath)) {
    const sourceIsDirectory = statSync(sourcePath).isDirectory();
    const targetIsDirectory = statSync(targetPath).isDirectory();
    if (!sourceIsDirectory || !targetIsDirectory || (!options.allowTargetContent && hasDirectoryContent(targetPath))) {
      throw new Error(`Konflikt beim State-Move: ${targetPath} existiert bereits.`);
    }
    copyDirectoryContents(sourcePath, targetPath, options);
    rmSync(sourcePath, { recursive: true, force: true });
    return;
  }
  copyEntry(sourcePath, targetPath, options);
  rmSync(sourcePath, { recursive: true, force: true });
}

function collectLegacyEntries(paths) {
  return [
    { label: "config.json", source: paths.legacy_config_path, target: paths.config_path, exists: existsSync(paths.legacy_config_path) },
    {
      label: "frontend_policy.json",
      source: paths.legacy_frontend_policy_path,
      target: paths.frontend_policy_path,
      exists: existsSync(paths.legacy_frontend_policy_path)
    },
    { label: ".salt", source: paths.legacy_salt_path, target: paths.salt_path, exists: existsSync(paths.legacy_salt_path) },
    {
      label: "logs",
      source: paths.legacy_log_dir,
      target: paths.log_dir,
      exists: hasDirectoryContent(paths.legacy_log_dir)
    },
    ...paths.legacy_chat_db_paths.map((sourcePath, index) => ({
      label: path.basename(sourcePath),
      source: sourcePath,
      target: paths.state_chat_db_paths[index],
      exists: existsSync(sourcePath)
    }))
  ].filter((entry) => entry.exists);
}

function collectTargetEntries(paths) {
  return [
    { label: "config.json", exists: existsSync(paths.config_path) },
    { label: "frontend_policy.json", exists: existsSync(paths.frontend_policy_path) },
    { label: ".salt", exists: existsSync(paths.salt_path) },
    { label: "logs", exists: hasDirectoryContent(paths.log_dir) },
    ...paths.state_chat_db_paths.map((targetPath) => ({ label: path.basename(targetPath), exists: existsSync(targetPath) }))
  ].filter((entry) => entry.exists);
}

function copySnapshotTree(sourceDir, targetDir) {
  if (!hasDirectoryContent(sourceDir)) {
    return [];
  }
  if (hasDirectoryContent(targetDir)) {
    throw new Error(`State-Snapshot-Konflikt: ${targetDir} enthaelt bereits Daten.`);
  }
  mkdirSync(path.dirname(targetDir), { recursive: true });
  cpSync(sourceDir, targetDir, { recursive: true, force: false });
  return readdirSync(sourceDir);
}

export function ensureLayout(paths) {
  mkdirSync(paths.app_home, { recursive: true });
  mkdirSync(paths.config_dir, { recursive: true });
  mkdirSync(paths.state_dir, { recursive: true });
  mkdirSync(paths.log_dir, { recursive: true });
  return paths;
}

export function migrateLegacyEntries(paths) {
  const legacyEntries = collectLegacyEntries(paths);
  if (!legacyEntries.length) {
    return { migrated: false, entries: [] };
  }
  const targetEntries = collectTargetEntries(paths).filter((entry) => entry.label !== "logs");
  if (targetEntries.length) {
    throw new Error(
      `Legacy root state and external app-home state cannot exist at the same time. Conflicts: ${targetEntries.map((entry) => entry.label).join(", ")}.`
    );
  }
  ensureLayout(paths);
  for (const entry of legacyEntries) {
    moveEntry(entry.source, entry.target, entry.label === "logs" ? { allowTargetContent: true, renameConflicts: true } : {});
  }
  return { migrated: true, entries: legacyEntries.map((entry) => entry.label) };
}

export function readSnapshotEntries(paths, snapshotDir = paths.snapshot_dir) {
  const configDir = path.join(snapshotDir, "config");
  const stateDir = path.join(snapshotDir, "state");
  return {
    snapshot_dir: snapshotDir,
    config_dir: configDir,
    state_dir: stateDir,
    has_snapshot: hasDirectoryContent(configDir) || hasDirectoryContent(stateDir)
  };
}

export function importSnapshotEntries(paths, snapshotDir = paths.snapshot_dir) {
  const snapshot = readSnapshotEntries(paths, snapshotDir);
  if (!snapshot.has_snapshot) {
    return { imported: false, entries: [] };
  }
  ensureLayout(paths);
  const entries = [
    ...copySnapshotTree(snapshot.config_dir, paths.config_dir),
    ...copySnapshotTree(snapshot.state_dir, paths.state_dir)
  ];
  return { imported: entries.length > 0, entries };
}
