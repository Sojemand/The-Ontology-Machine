import { mkdir, open, readFile, unlink } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { decryptSecret, encryptSecret } from "../vault.js";
import { buildTokenBundle } from "./oauth_metadata.js";
import { OAUTH_TOKEN_FILE, OAUTH_TOKEN_LOCK_FILE } from "./types.js";

const LOCK_TIMEOUT_MS = 5_000;
const LOCK_RETRY_MS = 10;

function tokenCachePath(stateDir) {
  return path.join(stateDir, OAUTH_TOKEN_FILE);
}

function tokenLockPath(stateDir) {
  return path.join(stateDir, OAUTH_TOKEN_LOCK_FILE);
}

function tokenReadError(targetPath, error) {
  const reason = error instanceof Error ? error.message : String(error);
  return new Error(`OAuth token cache could not be read: ${targetPath}. ${reason}`);
}

async function withTokenLock(stateDir, task) {
  await mkdir(stateDir, { recursive: true });
  const deadline = Date.now() + LOCK_TIMEOUT_MS;
  while (true) {
    let handle;
    let acquired = false;
    try {
      handle = await open(tokenLockPath(stateDir), "wx");
      acquired = true;
      await handle.writeFile(String(process.pid), "utf8");
      return await task();
    } catch (error) {
      if (error?.code !== "EEXIST") {
        throw error;
      }
      if (Date.now() >= deadline) {
        throw new Error(`OAuth token lock could not be acquired: ${tokenLockPath(stateDir)}`);
      }
      await new Promise((resolve) => setTimeout(resolve, LOCK_RETRY_MS));
    } finally {
      await handle?.close().catch(() => {});
      if (acquired) {
        await unlink(tokenLockPath(stateDir)).catch(() => {});
      }
    }
  }
}

export async function saveToken(stateDir, token) {
  const encrypted = encryptSecret(
    stateDir,
    JSON.stringify({
      access_token: token.access_token,
      refresh_token: token.refresh_token,
      id_token: token.id_token,
      token_type: token.token_type,
      expires_at: token.expires_at,
      account_id: token.account_id,
      client_id: token.client_id,
      session_id: token.session_id,
      scope: token.scope,
      token_status_code: token.token_status_code
    })
  );
  await withTokenLock(stateDir, async () => {
    await writeTextAtomically(tokenCachePath(stateDir), encrypted);
  });
}

export async function loadToken(stateDir) {
  const targetPath = tokenCachePath(stateDir);
  let encrypted;
  try {
    encrypted = await readFile(targetPath, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      return null;
    }
    throw tokenReadError(targetPath, error);
  }

  let payload;
  try {
    payload = JSON.parse(decryptSecret(stateDir, encrypted));
  } catch (error) {
    throw tokenReadError(targetPath, error);
  }
  if (!payload?.access_token) {
    throw tokenReadError(targetPath, new Error("Token payload is missing access_token."));
  }
  return buildTokenBundle(payload);
}

export async function deleteToken(stateDir) {
  let deleted = false;
  await withTokenLock(stateDir, async () => {
    try {
      await unlink(tokenCachePath(stateDir));
      deleted = true;
    } catch (error) {
      if (error?.code !== "ENOENT") {
        throw error;
      }
    }
  });
  return deleted;
}
