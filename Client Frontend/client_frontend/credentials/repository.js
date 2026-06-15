import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { CREDENTIALS_STATE_FILE, PENDING_LOGIN_TTL_MS } from "./types.js";
import { defaultCredentialsState, normalizeCredentialsState } from "./validation.js";

function credentialsStatePath(stateDir) {
  return path.join(stateDir, CREDENTIALS_STATE_FILE);
}

function credentialsStateReadError(targetPath, error) {
  const reason = error instanceof Error ? error.message : String(error);
  return new Error(`Credentials state could not be read: ${targetPath}. ${reason}`);
}

export async function loadCredentialsState(stateDir) {
  const targetPath = credentialsStatePath(stateDir);
  let raw;
  try {
    raw = await readFile(targetPath, "utf8");
  } catch (error) {
    if (error?.code !== "ENOENT") {
      throw credentialsStateReadError(targetPath, error);
    }
    return defaultCredentialsState();
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw credentialsStateReadError(targetPath, error);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw credentialsStateReadError(targetPath, new Error("Expected a JSON object."));
  }
  return normalizeCredentialsState(parsed);
}

export async function saveCredentialsState(stateDir, state) {
  await mkdir(stateDir, { recursive: true });
  await writeTextAtomically(credentialsStatePath(stateDir), `${JSON.stringify(normalizeCredentialsState(state), null, 2)}\n`);
}

export function createPendingLoginStore() {
  const pending = new Map();
  const prune = () => {
    const now = Date.now();
    for (const [key, value] of pending.entries()) {
      if (value.expires_at <= now) {
        pending.delete(key);
      }
    }
  };
  return {
    start(entry) {
      prune();
      pending.clear();
      pending.set(entry.state, { ...entry, expires_at: Date.now() + PENDING_LOGIN_TTL_MS });
    },
    consume(state) {
      prune();
      const key = String(state || "").trim();
      const value = pending.get(key) || null;
      if (value) {
        pending.delete(key);
      }
      return value;
    }
  };
}
