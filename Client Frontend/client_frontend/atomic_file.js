import { randomUUID } from "node:crypto";
import { rename, rm, writeFile } from "node:fs/promises";
import { renameSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

let tempCounter = 0;

function nextTempToken() {
  tempCounter = (tempCounter + 1) % Number.MAX_SAFE_INTEGER;
  return `${process.pid.toString(36)}-${tempCounter.toString(36)}-${randomUUID().slice(0, 8)}`;
}

export function makeShortSiblingPath(targetPath, marker = "tmp") {
  const normalizedMarker = String(marker || "tmp").replace(/[^a-z0-9_-]/gi, "") || "tmp";
  return path.join(path.dirname(targetPath), `.${normalizedMarker}-${nextTempToken()}`);
}

export async function writeFileAtomically(targetPath, content, options) {
  const tempPath = makeShortSiblingPath(targetPath);
  await writeFile(tempPath, content, options);
  try {
    await rename(tempPath, targetPath);
  } finally {
    await rm(tempPath, { force: true });
  }
}

export async function writeTextAtomically(targetPath, content) {
  await writeFileAtomically(targetPath, content, "utf8");
}

export function writeFileAtomicallySync(targetPath, content, options) {
  const tempPath = makeShortSiblingPath(targetPath);
  writeFileSync(tempPath, content, options);
  try {
    renameSync(tempPath, targetPath);
  } finally {
    rmSync(tempPath, { force: true });
  }
}

export function writeTextAtomicallySync(targetPath, content) {
  writeFileAtomicallySync(targetPath, content, "utf8");
}
