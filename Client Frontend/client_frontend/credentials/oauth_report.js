import { mkdir } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { OAUTH_REPORT_FILE } from "./types.js";

export function utcNowIso() {
  return new Date().toISOString();
}

function sanitizeReport(value) {
  if (Array.isArray(value)) {
    return value.map(sanitizeReport);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [
        key,
        ["access_token", "refresh_token", "authorization_code", "code", "id_token"].includes(key.toLowerCase())
          ? "[REDACTED]"
          : sanitizeReport(child)
      ])
    );
  }
  return value;
}

export async function writeOAuthReport(stateDir, report) {
  await mkdir(stateDir, { recursive: true });
  const target = path.join(stateDir, OAUTH_REPORT_FILE);
  await writeTextAtomically(target, `${JSON.stringify(sanitizeReport(report), null, 2)}\n`);
  return target;
}
