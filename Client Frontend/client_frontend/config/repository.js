import { readFile } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { CONFIG_FILE_NAME } from "./types.js";
import { validateRootDir } from "./validation.js";

function configPath(rootDir) {
  return path.join(validateRootDir(rootDir), CONFIG_FILE_NAME);
}

export function resolveConfigPath(rootDir) {
  return configPath(rootDir);
}

export async function readConfigDocument(rootDir) {
  try {
    const raw = (await readFile(configPath(rootDir), "utf8")).replace(/^\uFEFF/, "");
    try {
      return {
        status: "ok",
        parsed: JSON.parse(raw)
      };
    } catch (error) {
      return {
        status: "invalid",
        parsed: null,
        reason: error instanceof Error ? error.message : String(error)
      };
    }
  } catch (error) {
    if (error && typeof error === "object" && error.code === "ENOENT") {
      return {
        status: "missing",
        parsed: null
      };
    }
    return {
      status: "invalid",
      parsed: null,
      reason: error instanceof Error ? error.message : String(error)
    };
  }
}

export async function writeConfigDocument(rootDir, config) {
  const targetPath = configPath(rootDir);
  await writeTextAtomically(targetPath, JSON.stringify(config, null, 2) + "\n");
}
