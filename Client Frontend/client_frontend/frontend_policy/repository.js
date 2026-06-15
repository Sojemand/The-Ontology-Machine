import { readFile } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { FRONTEND_POLICY_FILE_NAME } from "./types.js";

function frontendPolicyPath(rootDir) {
  return path.join(String(rootDir || "").trim(), FRONTEND_POLICY_FILE_NAME);
}

export function resolveFrontendPolicyPath(rootDir) {
  return frontendPolicyPath(rootDir);
}

export async function readFrontendPolicyDocument(rootDir) {
  try {
    const raw = await readFile(frontendPolicyPath(rootDir), "utf8");
    try {
      return { status: "ok", raw, parsed: JSON.parse(raw) };
    } catch (error) {
      return {
        status: "invalid_json",
        raw,
        parsed: null,
        reason: error instanceof Error ? error.message : String(error)
      };
    }
  } catch (error) {
    if (error && typeof error === "object" && error.code === "ENOENT") {
      return { status: "missing", raw: "", parsed: null };
    }
    return {
      status: "invalid_json",
      raw: "",
      parsed: null,
      reason: error instanceof Error ? error.message : String(error)
    };
  }
}

export async function writeFrontendPolicyDocument(rootDir, frontendPolicy) {
  await writeTextAtomically(frontendPolicyPath(rootDir), `${JSON.stringify(frontendPolicy, null, 2)}\n`);
}
