import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { createChatStore } from "../../server/chat_store.js";

export const OWNER_ID = "user-1";
export const OTHER_OWNER_ID = "user-2";

export function withChatStore(run) {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-chatstore-"));
  const store = createChatStore({ rootDir: tempDir });
  try {
    return run(store, tempDir);
  } finally {
    store.close();
    rmSync(tempDir, { recursive: true, force: true });
  }
}
