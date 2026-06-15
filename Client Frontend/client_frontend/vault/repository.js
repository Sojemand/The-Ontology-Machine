import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { writeFileAtomicallySync } from "../atomic_file.js";
import { SALT_FILENAME } from "./types.js";

export function saltPath(rootDir) {
  return path.join(rootDir, SALT_FILENAME);
}

export function hasSalt(rootDir) {
  return existsSync(saltPath(rootDir));
}

export function readSalt(rootDir) {
  return readFileSync(saltPath(rootDir));
}

export function writeSalt(rootDir, salt) {
  writeFileAtomicallySync(saltPath(rootDir), salt);
  return salt;
}
